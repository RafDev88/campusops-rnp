from fastapi import APIRouter,Depends,HTTPException,Query,Response
from pydantic import BaseModel,Field
from sqlalchemy import func,select
from .database import Session
from . import orchestration_models as m
from .domain import Audit,Run
from .read_api import serialize,SOURCES
from .security import current_user,operator,admin
from .schemas import RunControl,PolicyUpdate,WorkflowCreate,CalendarCreate,Toggle,RuleCreate
from .job_runtime import control,policy
from .orchestration import start_workflow,workflow_control,advance_workflows
from .reports import enqueue_report
from .calendar_jobs import validate_calendar,next_occurrence
from .discovery import PublicationFilters

router=APIRouter()


@router.get('/runs/{identifier}/runtime')
def progress(identifier:int,user=Depends(current_user)):
    with Session() as db:
        run=db.get(Run,identifier)
        if not run:raise HTTPException(404,'Execução não encontrada.')
        state=db.get(m.Runtime,identifier)
        return {'run':serialize(run),'runtime':serialize(state,exclude=('context',)) if state else None,
                'log':[serialize(row) for row in db.scalars(select(m.RunLog).where(m.RunLog.run_id==identifier).order_by(m.RunLog.id.desc()).limit(50))]}


@router.post('/runs/{identifier}/control')
def run_control(identifier:int,payload:RunControl,user=Depends(operator)):
    try:control(identifier,payload.action,user['username'],payload.reset_checkpoint)
    except ValueError as exc:raise HTTPException(409,str(exc)) from None
    return {'ok':True}


@router.get('/source-policies')
def policies(user=Depends(current_user)):
    with Session() as db:
        items=[serialize(policy(db,source)) for source in SOURCES];db.commit();return items


@router.put('/source-policies/{source}')
def update_policy(source:str,payload:PolicyUpdate,user=Depends(admin)):
    if source not in SOURCES:raise HTTPException(404,'Fonte desconhecida.')
    with Session() as db:
        item=policy(db,source)
        for key,value in payload.model_dump().items():setattr(item,key,value)
        db.add(Audit(actor=user['username'],action='source.policy',detail={'source':source,**payload.model_dump()}))
        db.commit();return serialize(item)


@router.get('/workflows')
def workflows(user=Depends(current_user)):
    with Session() as db:
        return {'items':[serialize(row) for row in db.scalars(select(m.Workflow).order_by(m.Workflow.id))],
                'runs':[serialize(row) for row in db.scalars(select(m.WorkflowRun).order_by(m.WorkflowRun.id.desc()).limit(100))]}


@router.post('/workflows',status_code=201)
def add_workflow(payload:WorkflowCreate,user=Depends(operator)):
    with Session() as db:
        item=m.Workflow(owner_id=user['id'],name=payload.name,steps=payload.steps,params=payload.params.model_dump(),allow_partial=payload.allow_partial)
        db.add(item);db.flush();db.add(Audit(actor=user['username'],action='workflow.created',detail={'workflow_id':item.id}))
        db.commit();return serialize(item)


@router.patch('/workflows/{identifier}')
def enable_workflow(identifier:int,payload:Toggle,user=Depends(operator)):
    with Session() as db:
        item=db.get(m.Workflow,identifier)
        if not item:raise HTTPException(404,'Fluxo não encontrado.')
        item.enabled=payload.enabled;db.add(Audit(actor=user['username'],action='workflow.toggled',detail={'id':identifier,'enabled':payload.enabled}))
        db.commit();return serialize(item)


@router.post('/workflows/{identifier}/start',status_code=202)
def launch(identifier:int,user=Depends(operator)):
    try:result=start_workflow(identifier,user['username'])
    except ValueError as exc:raise HTTPException(409,str(exc)) from None
    advance_workflows();return {'workflow_run_id':result}


@router.post('/workflow-runs/{identifier}/control')
def control_flow(identifier:int,payload:RunControl,user=Depends(operator)):
    try:workflow_control(identifier,payload.action,user['username'],payload.reset_checkpoint)
    except ValueError as exc:raise HTTPException(409,str(exc)) from None
    advance_workflows();return {'ok':True}


@router.post('/calendar-preview')
def calendar_preview(payload:CalendarCreate,user=Depends(current_user)):
    try:
        first=validate_calendar(payload.cron,payload.timezone);times=[first]
        for _ in range(4):times.append(next_occurrence(payload.cron,payload.timezone,times[-1]))
    except (ValueError,KeyError) as exc:raise HTTPException(422,str(exc)) from None
    return {'next':[time.isoformat() for time in times],'timezone':payload.timezone}


@router.get('/calendar-schedules')
def calendars(user=Depends(current_user)):
    with Session() as db:
        rows=[r for r in db.scalars(select(m.CalendarSchedule).order_by(m.CalendarSchedule.id)) if r.target!='report' or r.owner_id==user['id']]
        return {'items':[serialize(r) for r in rows],'fires':[serialize(r) for r in db.scalars(select(m.CalendarFire).where(m.CalendarFire.schedule_id.in_([i.id for i in rows])).order_by(m.CalendarFire.id.desc()).limit(50))]}


@router.post('/calendar-schedules',status_code=201)
def add_calendar(payload:CalendarCreate,user=Depends(current_user)):
    if payload.target!='report' and user['role']=='viewer':raise HTTPException(403,'Agendamentos operacionais exigem perfil de operador.')
    try:next_at=validate_calendar(payload.cron,payload.timezone)
    except (ValueError,KeyError) as exc:raise HTTPException(422,str(exc)) from None
    with Session() as db:
        if payload.target=='workflow' and not db.get(m.Workflow,payload.target_id):raise HTTPException(422,'Fluxo não encontrado.')
        if payload.target=='report':
            template=db.get(m.ReportTemplate,payload.target_id)
            if not template or template.owner_id!=user['id']:raise HTTPException(404,'Modelo de relatório não encontrado.')
        if payload.target=='source' and payload.source not in SOURCES:raise HTTPException(422,'Escolha uma fonte.')
        if payload.target=='source' and payload.source=='orcid' and not (payload.params.orcid or payload.params.auto_discover):raise HTTPException(422,'Informe um ORCID ou habilite descoberta de autores.')
        item=m.CalendarSchedule(owner_id=user['id'],name=payload.name,target=payload.target,target_id=payload.target_id,source=payload.source,
            params={**payload.params.model_dump(),'source':payload.source},cron=payload.cron,timezone=payload.timezone,next_at=next_at)
        db.add(item);db.flush();db.add(Audit(actor=user['username'],action='calendar.created',detail={'id':item.id,'target':item.target}))
        db.commit();return serialize(item)


@router.patch('/calendar-schedules/{identifier}')
def toggle_calendar(identifier:int,payload:Toggle,user=Depends(current_user)):
    with Session() as db:
        item=db.get(m.CalendarSchedule,identifier)
        if not item or (item.target=='report' and item.owner_id!=user['id']):raise HTTPException(404,'Agendamento não encontrado.')
        if item.target!='report' and user['role']=='viewer':raise HTTPException(403,'Operação exige perfil de operador.')
        item.enabled=payload.enabled
        if item.enabled:item.next_at=next_occurrence(item.cron,item.timezone)
        db.add(Audit(actor=user['username'],action='calendar.toggled',detail={'id':identifier,'enabled':payload.enabled}));db.commit();return serialize(item)


class ReportCreate(BaseModel):
    name:str=Field(min_length=3,max_length=100)
    filters:PublicationFilters=Field(default_factory=PublicationFilters)


@router.get('/report-templates')
def report_templates(user=Depends(current_user)):
    with Session() as db:return [serialize(row) for row in db.scalars(select(m.ReportTemplate).where(m.ReportTemplate.owner_id==user['id']).order_by(m.ReportTemplate.id.desc()))]


@router.post('/report-templates',status_code=201)
def add_report_template(payload:ReportCreate,user=Depends(current_user)):
    with Session() as db:
        item=m.ReportTemplate(owner_id=user['id'],name=payload.name,filters=payload.filters.model_dump());db.add(item);db.commit();return serialize(item)


@router.post('/report-templates/{identifier}/generate',status_code=202)
def generate(identifier:int,user=Depends(current_user)):
    with Session() as db:
        item=db.get(m.ReportTemplate,identifier)
        if not item or item.owner_id!=user['id']:raise HTTPException(404,'Modelo não encontrado.')
        name,filters=item.name,item.filters
    return {'report_id':enqueue_report(user['id'],name,filters,identifier)}


@router.get('/reports')
def reports(user=Depends(current_user)):
    with Session() as db:return [serialize(row,exclude=('content',)) for row in db.scalars(select(m.Report).where(m.Report.owner_id==user['id']).order_by(m.Report.id.desc()).limit(100))]


@router.get('/reports/{identifier}/download')
def download_report(identifier:int,user=Depends(current_user)):
    with Session() as db:
        item=db.get(m.Report,identifier)
        if not item or item.owner_id!=user['id']:raise HTTPException(404,'Relatório não encontrado.')
        if item.status!='ready':raise HTTPException(409,'O arquivo ainda não está disponível ou expirou.')
        return Response(item.content,media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="campusops-relatorio-{identifier}.csv"'})


@router.get('/record-reviews')
def reviews(status:str='',source:str='',offset:int=Query(0,ge=0),user=Depends(current_user)):
    with Session() as db:
        query=select(m.Review)
        if status:query=query.where(m.Review.status==status)
        if source:query=query.where(m.Review.source==source)
        return {'total':db.scalar(select(func.count()).select_from(query.subquery())),
                'items':[serialize(row) for row in db.scalars(query.order_by(m.Review.id.desc()).offset(offset).limit(25))]}


@router.post('/record-reviews/{identifier}/retry',status_code=202)
def retry_review(identifier:int,user=Depends(operator)):
    from .operations import enqueue
    with Session() as db:
        item=db.get(m.Review,identifier)
        if not item:raise HTTPException(404,'Registro não encontrado.')
        if item.status not in {'pending','ignored'}:raise HTTPException(409,'Este registro já foi reprocessado ou está em andamento.')
        if item.entity_id=='schema':
            try:control(item.run_id,'resume',user['username'],reset=True)
            except ValueError as exc:raise HTTPException(409,str(exc)) from None
            new=item.run_id
        else:
            try:new=enqueue(item.source,item.params,user['username'])
            except ValueError as exc:raise HTTPException(409,str(exc)) from None
        item.status,item.retry_run_id='retrying',new
        db.add(Audit(actor=user['username'],action='review.retry',detail={'review_id':identifier,'run_id':new}));db.commit();return {'execution_id':new}


@router.post('/record-reviews/{identifier}/ignore')
def ignore_review(identifier:int,user=Depends(operator)):
    with Session() as db:
        item=db.get(m.Review,identifier)
        if not item:raise HTTPException(404,'Registro não encontrado.')
        item.status,item.active_key='ignored',None
        db.add(Audit(actor=user['username'],action='review.ignored',detail={'review_id':identifier}));db.commit();return {'ok':True}


@router.get('/data-changes')
def changes(source:str='',entity_id:str='',offset:int=Query(0,ge=0),user=Depends(current_user)):
    with Session() as db:
        query=select(m.Change)
        if source:query=query.where(m.Change.source==source)
        if entity_id:query=query.where(m.Change.entity_id==entity_id)
        return {'total':db.scalar(select(func.count()).select_from(query.subquery())),
                'items':[serialize(row) for row in db.scalars(query.order_by(m.Change.id.desc()).offset(offset).limit(25))]}


@router.post('/rules/preview')
def rule_preview(payload:RuleCreate,user=Depends(operator)):
    from .rule_preview import preview
    return preview(payload)
