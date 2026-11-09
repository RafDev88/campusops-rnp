"""Workflow engine and page-independent collection outcomes."""
from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .database import Session
from .domain import Audit, Run, utcnow
from . import orchestration_models as m
from .job_runtime import runtime,log,control


def record_changes(db,run,identifier,before,after):
    for key,value in after.items():
        if before.get(key)!=value:
            db.add(m.Change(run_id=run.id,source=run.source,entity_id=identifier,field=key,before=before.get(key),after=value))


def review(db,run,identifier,reason,params):
    key=f'{run.source}:{identifier}'
    item=db.scalar(select(m.Review).where(m.Review.active_key==key))
    if not item:
        item=m.Review(active_key=key,run_id=run.id,source=run.source,entity_id=identifier,reason=reason,params=params)
        db.add(item)
    else:
        item.run_id,item.reason,item.status=run.id,reason,'pending'


def finalize_collection(db,run,source,items,details,rejects):
    state=runtime(db,run.id)
    state.stage,state.requested,state.next_at='completed','',None
    state.heartbeat=utcnow()
    if source=='openalex':
        ids={row['id'] for _,row in items}
        for key in ids:
            if not db.get(m.RunEntity,(run.id,'publication',key)):
                db.add(m.RunEntity(run_id=run.id,kind='publication',entity_id=key))
        for scope in details.get('coverage',[]):
            if scope.get('complete') and scope.get('watermark_key'):
                marker=db.get(m.Watermark,scope['watermark_key'])
                if not marker: marker=m.Watermark(scope=scope['watermark_key']);db.add(marker)
                marker.date,marker.updated_at=scope.get('collected_on',run.started_at.date().isoformat()),utcnow()
    successful=set()
    if source=='crossref': successful={work_id for work_id,_ in items}
    if source=='orcid': successful={row['orcid'] for row in items}
    for item in db.scalars(select(m.Review).where(m.Review.source==source,m.Review.status.in_(['pending','retrying']))):
        if item.entity_id in successful or item.entity_id=='schema':
            item.status,item.active_key='resolved',None
    for rejected in rejects:
        identifier=rejected.get('publication_id') or rejected.get('orcid')
        params={**run.params,'source':source}
        if source=='crossref': params.update(publication_ids=[identifier],limit=1,only_pending=False,from_run_id=None)
        else: params.update(orcid=identifier,auto_discover=False)
        review(db,run,identifier,rejected['reason'],params)
    log(db,run.id,'completed',run.message,{'records':run.records,'new':run.new,'updated':run.updated,'rejected':run.rejected})


def start_workflow(identifier,actor,dispatch_key=None):
    with Session() as db:
        if dispatch_key:
            existing=db.scalar(select(m.WorkflowRun.id).where(m.WorkflowRun.dispatch_key==dispatch_key))
            if existing: return existing
        definition=db.get(m.Workflow,identifier)
        if not definition or not definition.enabled: raise ValueError('Fluxo não encontrado ou desativado.')
        item=m.WorkflowRun(workflow_id=identifier,owner_id=definition.owner_id,active_key=f'workflow:{identifier}',
            snapshot={'steps':definition.steps,'params':definition.params,'allow_partial':definition.allow_partial,'name':definition.name},dispatch_key=dispatch_key)
        db.add(item)
        try: db.flush();db.add(Audit(actor=actor,action='workflow.started',detail={'workflow_run_id':item.id}));db.commit()
        except IntegrityError: db.rollback();raise ValueError('Este fluxo já tem uma execução ativa.') from None
        return item.id


def workflow_control(identifier,action,actor,reset=False):
    with Session() as db:
        item=db.scalar(select(m.WorkflowRun).where(m.WorkflowRun.id==identifier).with_for_update())
        if not item: raise ValueError('Execução de fluxo não encontrada.')
        if action in {'pause','cancel'}:
            if item.status not in {'running','waiting','paused','pausing'}: raise ValueError('O fluxo já terminou.')
            item.requested=action
            if item.child_id:
                child=db.get(Run,item.child_id)
                child_id=child.id if child and child.status in {'queued','running','paused','retry_wait'} else None
            else: child_id=None
            item.status='pausing' if action=='pause' else 'cancelling'
        elif action=='resume':
            if item.status not in {'paused','failed'}: raise ValueError('Este fluxo não pode ser retomado.')
            other=db.scalar(select(m.WorkflowRun.id).where(m.WorkflowRun.active_key==f'workflow:{item.workflow_id}',m.WorkflowRun.id!=item.id))
            if other: raise ValueError('Outra execução deste fluxo está ativa.')
            child=db.get(Run,item.child_id) if item.child_id else None
            child_id=child.id if child and child.status in {'paused','failed','retry_wait'} else None
            item.requested,item.status,item.active_key,item.finished_at='','running',f'workflow:{item.workflow_id}',None
            if item.report_id:
                report=db.get(m.Report,item.report_id)
                if report and report.status=='failed':report.status,report.finished_at='queued',None
        else: raise ValueError('Comando desconhecido.')
        db.add(Audit(actor=actor,action='workflow.'+action,detail={'workflow_run_id':identifier}))
        db.commit()
    if child_id:
        try:control(child_id,action,actor,reset=reset)
        except ValueError:
            if action=='resume':raise


def advance_workflows():
    from .operations import enqueue
    from .reports import enqueue_report
    with Session() as db:
        identifiers=list(db.scalars(select(m.WorkflowRun.id).where(m.WorkflowRun.status.in_(['running','waiting','pausing','cancelling']))))
    for identifier in identifiers:
        try:
            with Session() as db:
                item=db.scalar(select(m.WorkflowRun).where(m.WorkflowRun.id==identifier).with_for_update())
                if item.requested:
                    child=db.get(Run,item.child_id) if item.child_id else None
                    if child and child.status in {'running','queued','retry_wait'}: continue
                    item.status='paused' if item.requested=='pause' else 'cancelled'
                    item.message='Fluxo pausado.' if item.status=='paused' else 'Fluxo cancelado.'
                    if item.status=='cancelled': item.active_key,item.finished_at=None,utcnow()
                    db.commit();continue
                steps=item.snapshot['steps']
                if item.step>=len(steps):
                    item.status,item.active_key,item.finished_at,item.message='success',None,utcnow(),'Todas as etapas terminaram.'
                    db.commit();continue
                source=steps[item.step]
                if item.child_id:
                    child=db.get(Run,item.child_id)
                    if child.status in {'queued','running','retry_wait'}:
                        item.status,item.message='running',f'Etapa {item.step+1}: {source} · {child.status}'
                        db.commit();continue
                    if child.status=='paused': item.status,item.message='paused','Etapa pausada; retome o fluxo para continuar.';db.commit();continue
                    accepted=child.status=='success' or (child.status=='partial' and item.snapshot['allow_partial'])
                    if not accepted:
                        item.status,item.active_key,item.finished_at='failed',None,utcnow()
                        item.message=f'Etapa {source} terminou como {child.status}. Revise a execução #{child.id}.'
                        db.commit();continue
                    item.history=[*item.history,{'step':source,'run_id':child.id,'status':child.status,'records':child.records}]
                    item.step,item.child_id=item.step+1,None
                    db.commit();continue
                if source=='report':
                    if item.report_id:
                        report=db.get(m.Report,item.report_id)
                        if report.status in {'queued','running'}: continue
                        if report.status!='ready': item.status,item.active_key,item.message='failed',None,report.message;db.commit();continue
                        item.history=[*item.history,{'step':'report','report_id':report.id,'status':'ready'}]
                        item.step+=1;item.report_id=None;db.commit();continue
                    filters={}
                    if item.snapshot['params'].get('institution_id'): filters['institution_id']=item.snapshot['params']['institution_id']
                    report_id=enqueue_report(item.owner_id,item.snapshot['name'],filters,dispatch_key=f'flow:{item.id}:{item.step}')
                    item.report_id=report_id;db.commit();continue
                params={**item.snapshot['params'],'source':source,'_workflow':True}
                previous=next((h['run_id'] for h in reversed(item.history) if h['step']=='openalex'),None)
                if source in {'crossref','orcid'}:
                    params.update(only_pending=True,auto_discover=source=='orcid',orcid='',from_run_id=previous)
                try: child_id=enqueue(source,params,actor='workflow',dispatch_key=f'flow:{item.id}:{item.step}')
                except ValueError as exc:
                    item.status,item.message='waiting',str(exc);db.commit();continue
                item.child_id,item.status,item.message=child_id,'running',f'Etapa {item.step+1}: {source}'
                db.commit()
        except Exception:
            import structlog
            structlog.get_logger().exception('workflow_tick_failed',workflow_run_id=identifier)
