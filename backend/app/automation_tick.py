from datetime import timedelta
from sqlalchemy import delete,select,update
import structlog
from .database import Session
from .domain import Delivery,Run,utcnow
from . import orchestration_models as m
from .job_runtime import handle_failure
from .calendar_jobs import dispatch_calendar
from .orchestration import advance_workflows

logger=structlog.get_logger()


def safe_publish(task,identifier):
    try:task.delay(identifier)
    except Exception:logger.warning('automation_publish_deferred',task=task.name,job_id=identifier)


def automation_tick():
    from .tasks import execute_run,generate_report,deliver_webhook
    with Session() as db:
        for state in db.scalars(select(m.Runtime).join(Run).where(Run.status=='running',m.Runtime.stage.in_(['collecting','applying']),m.Runtime.heartbeat<utcnow()-timedelta(minutes=10)).with_for_update(of=Run,skip_locked=True)):
            state.lease=''
            handle_failure(db,db.get(Run,state.run_id),'network','Execução perdeu o heartbeat; retomada pelo checkpoint.')
        for state in db.scalars(select(m.Runtime).join(Run).where(Run.status=='retry_wait',m.Runtime.next_at<=utcnow())):
            run=db.get(Run,state.run_id)
            run.status,run.finished_at='queued',None
            state.stage='queued'
        # Worker loss while generating a report is safe to recover; no external effects.
        for report in db.scalars(select(m.Report).where(m.Report.status=='running',m.Report.started_at<utcnow()-timedelta(minutes=20))):
            report.status='queued'
        for delivery in db.scalars(select(Delivery).where(Delivery.status=='sending',Delivery.next_at<utcnow())):
            delivery.status='pending' if delivery.attempts<5 else 'dead'
        for report in db.scalars(select(m.Report).where(m.Report.status=='ready',m.Report.finished_at<utcnow()-timedelta(days=30))):
            report.status,report.content,report.message='expired','','Arquivo expirado após 30 dias.'
        db.commit()
    for operation in (dispatch_calendar,advance_workflows,advance_workflows):
        try:operation()
        except Exception:logger.exception('automation_tick_segment_failed',operation=operation.__name__)
    with Session() as db:
        runs=list(db.scalars(select(Run.id).where(Run.status=='queued').limit(50)))
        reports=list(db.scalars(select(m.Report.id).where(m.Report.status=='queued').limit(20)))
        deliveries=list(db.scalars(select(Delivery.id).where(Delivery.status=='pending',Delivery.next_at<=utcnow()).limit(50)))
    for identifier in runs:safe_publish(execute_run,identifier)
    for identifier in reports:safe_publish(generate_report,identifier)
    for identifier in deliveries:safe_publish(deliver_webhook,identifier)
