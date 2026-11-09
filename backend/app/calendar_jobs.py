from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
from croniter import croniter
from sqlalchemy import select,update
from .database import Session
from .domain import utcnow
from .automation import aware
from . import orchestration_models as m


def next_occurrence(expression,zone,base=None):
    if len(expression.split())!=5 or not croniter.is_valid(expression):raise ValueError('Use uma expressão cron válida com cinco campos.')
    try:tz=ZoneInfo(zone)
    except (KeyError,ValueError):raise ValueError('Fuso horário desconhecido.') from None
    base=base or utcnow()
    return croniter(expression,base.astimezone(tz)).get_next(datetime).astimezone(timezone.utc)


def validate_calendar(expression,zone):
    first=next_occurrence(expression,zone)
    previous=first
    for _ in range(32):
        following=next_occurrence(expression,zone,previous)
        if (following-previous).total_seconds()<900:raise ValueError('O intervalo mínimo entre disparos é de 15 minutos.')
        previous=following
    return first


def dispatch_calendar():
    from .operations import enqueue
    from .orchestration import start_workflow
    from .reports import enqueue_report
    with Session() as db:
        due=list(db.scalars(select(m.CalendarSchedule.id).where(m.CalendarSchedule.enabled.is_(True),m.CalendarSchedule.next_at<=utcnow())))
    for identifier in due:
        try:
            with Session() as db:
                item=db.scalar(select(m.CalendarSchedule).where(m.CalendarSchedule.id==identifier).with_for_update())
                if not item.enabled or aware(item.next_at)>utcnow():continue
                due_at=item.next_at
                item.next_at=next_occurrence(item.cron,item.timezone)
                db.add(m.CalendarFire(schedule_id=item.id,scheduled_at=due_at))
                db.commit()
        except Exception:
            import structlog
            structlog.get_logger().exception('calendar_claim_failed',schedule_id=identifier)
    with Session() as db:
        pending=list(db.scalars(select(m.CalendarFire.id).where(m.CalendarFire.status=='pending').limit(50)))
    for identifier in pending:
        try:
            with Session() as db:
                fire=db.scalar(select(m.CalendarFire).where(m.CalendarFire.id==identifier).with_for_update())
                if fire.status!='pending':continue
                schedule=db.get(m.CalendarSchedule,fire.schedule_id)
                if not schedule.enabled:fire.status,fire.message='skipped','Agendamento pausado.';db.commit();continue
                key=f'calendar:{identifier}'
                try:
                    if schedule.target=='workflow':job=start_workflow(schedule.target_id,'calendar',key)
                    elif schedule.target=='report':
                        template=db.get(m.ReportTemplate,schedule.target_id)
                        if not template or not template.enabled:raise ValueError('Modelo de relatório desativado.')
                        job=enqueue_report(template.owner_id,template.name,template.filters,template.id,key)
                    else:job=enqueue(schedule.source,schedule.params,'calendar',key)
                    fire.job_id,fire.status=job,'dispatched'
                except ValueError as exc:fire.status,fire.message='skipped',str(exc)
                db.commit()
        except Exception:
            import structlog
            structlog.get_logger().exception('calendar_dispatch_failed',fire_id=identifier)
