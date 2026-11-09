from datetime import timedelta
from typing import Literal
from urllib.parse import urlsplit
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field,field_validator
from sqlalchemy import func,select,or_,case
from .database import Session
from .domain import Audit,Webhook,utcnow
from .security import current_user,operator,admin
from .read_api import serialize
from . import monitor_models as m
from .monitor_inventory import config,sync_inventory
from .monitor_network import normalize_url,url_key
from .monitor_service import enqueue_check

router=APIRouter()
GOOD={'available','redirected','slow','tls_expiring','http_insecure'}


class TargetCreate(BaseModel):
    name:str=Field(min_length=3,max_length=300)
    url:str=Field(max_length=2048)
    interval_minutes:int=Field(default=1440,ge=15,le=10080)
    @field_validator('url')
    @classmethod
    def valid_url(cls,value):return normalize_url(value)


class TargetUpdate(BaseModel):
    enabled:bool
    interval_minutes:int=Field(default=1440,ge=15,le=10080)
    alerts:bool=True
    failure_threshold:int=Field(default=3,ge=2,le=10)
    certificate_days:int=Field(default=30,ge=1,le=90)
    webhook_id:int|None=None


class ConfigUpdate(BaseModel):
    enabled:bool=True
    discovery:bool=True
    per_day:int=Field(default=2000,ge=50,le=10000)
    per_host_minute:int=Field(default=10,ge=1,le=60)
    retention_days:int=Field(default=30,ge=7,le=90)


@router.get('/monitor-settings')
def settings(user=Depends(current_user)):
    with Session() as db:
        result=serialize(config(db));db.commit()
        return {'config':result,'destinations':[{'id':r.id,'name':r.name} for r in db.scalars(select(Webhook).where(Webhook.enabled.is_(True)))]}


@router.put('/monitor-settings')
def save_settings(payload:ConfigUpdate,user=Depends(admin)):
    with Session() as db:
        row=config(db)
        for key,value in payload.model_dump().items():setattr(row,key,value)
        db.add(Audit(actor=user['username'],action='monitor.settings',detail=payload.model_dump()));db.commit();return serialize(row)


@router.post('/monitors/discover')
def discover(user=Depends(operator)):
    return sync_inventory(user['username'])


@router.post('/monitors/check-apis',status_code=202)
def check_apis(user=Depends(operator)):
    with Session() as db:ids=list(db.scalars(select(m.MonitorTarget.id).where(m.MonitorTarget.kind=='api',m.MonitorTarget.archived.is_(False))))
    queued=[];skipped=[]
    for identifier in ids:
        try:queued.append(enqueue_check(identifier,user['username'],manual=True))
        except ValueError as exc:skipped.append(str(exc))
    return {'check_ids':queued,'skipped':skipped}


@router.get('/monitors')
def targets(q:str=Query('',max_length=150),kind:Literal['','api','publication','dataset','file','portal','manual']='',status:str='',source:str='',
            problems:bool=False,include_archived:bool=False,offset:int=Query(0,ge=0),limit:int=Query(25,ge=1,le=100),user=Depends(current_user)):
    with Session() as db:
        query=select(m.MonitorTarget)
        if not include_archived:query=query.where(m.MonitorTarget.archived.is_(False))
        if q:query=query.where(or_(func.lower(m.MonitorTarget.name).contains(q.casefold(),autoescape=True),func.lower(m.MonitorTarget.url).contains(q.casefold(),autoescape=True)))
        if kind:query=query.where(m.MonitorTarget.kind==kind)
        if source:query=query.where(m.MonitorTarget.source==source)
        if status in {'queued','running'}:
            query=query.where(m.MonitorTarget.id.in_(select(m.MonitorCheck.target_id).where(m.MonitorCheck.active_key.is_not(None),m.MonitorCheck.state==status)))
        elif status in {'deferred','interrupted','internal','skipped'}:
            latest=select(func.max(m.MonitorCheck.id)).group_by(m.MonitorCheck.target_id)
            query=query.where(m.MonitorTarget.id.in_(select(m.MonitorCheck.target_id).where(m.MonitorCheck.id.in_(latest),m.MonitorCheck.outcome==status)))
        elif status:query=query.where(m.MonitorTarget.status==status)
        if problems:query=query.where(m.MonitorTarget.status.not_in(['available','redirected','not_checked']))
        total=db.scalar(select(func.count()).select_from(query.subquery()))
        rows=list(db.scalars(query.order_by(m.MonitorTarget.kind,m.MonitorTarget.name,m.MonitorTarget.id).offset(offset).limit(limit)))
        ids=[row.id for row in rows]
        active={row.target_id:serialize(row) for row in db.scalars(select(m.MonitorCheck).where(m.MonitorCheck.target_id.in_(ids),m.MonitorCheck.active_key.is_not(None)))}
        references=dict(db.execute(select(m.MonitorReference.target_id,func.count()).where(m.MonitorReference.target_id.in_(ids)).group_by(m.MonitorReference.target_id)).all())
        recent=dict(db.execute(select(m.MonitorCheck.target_id,func.max(m.MonitorCheck.id)).where(m.MonitorCheck.target_id.in_(ids)).group_by(m.MonitorCheck.target_id)).all())
        checks={row.id:serialize(row) for row in db.scalars(select(m.MonitorCheck).where(m.MonitorCheck.id.in_([r.last_check_id for r in rows if r.last_check_id]+list(recent.values()))))}
        stats={r[0]:{'observations':r[1],'expected':r[2],'expected_percent':round(100*r[2]/r[1],1) if r[1] else None} for r in db.execute(select(m.MonitorCheck.target_id,func.count(),func.sum(case((m.MonitorCheck.ok.is_(True),1),else_=0))).where(m.MonitorCheck.target_id.in_(ids),m.MonitorCheck.finished_at>=utcnow()-timedelta(hours=24),m.MonitorCheck.ok.is_not(None)).group_by(m.MonitorCheck.target_id))}
        summary=dict(db.execute(select(m.MonitorTarget.status,func.count()).where(m.MonitorTarget.archived.is_(False)).group_by(m.MonitorTarget.status)).all())
        return {'total':total,'summary':summary,'items':[{**serialize(r),'last_check':checks.get(r.last_check_id),'last_attempt':checks.get(recent.get(r.id)),'active_check':active.get(r.id),'references':references.get(r.id,0),'window':stats.get(r.id,{'observations':0,'expected':0,'expected_percent':None})} for r in rows]}


@router.post('/monitors',status_code=201)
def create(payload:TargetCreate,user=Depends(operator)):
    with Session() as db:
        config(db);db.scalar(select(m.MonitorConfig).where(m.MonitorConfig.id==1).with_for_update())
        key=url_key(payload.url);existing=db.scalar(select(m.MonitorTarget).where(m.MonitorTarget.url_hash==key))
        if existing:
            if existing.archived:
                existing.archived,existing.managed,existing.enabled=False,False,True
                existing.kind,existing.source,existing.name='manual','',payload.name
                existing.interval_minutes,existing.next_at=payload.interval_minutes,utcnow()
                db.add(Audit(actor=user['username'],action='monitor.restored',detail={'target_id':existing.id}));db.commit()
            return serialize(existing)
        row=m.MonitorTarget(name=payload.name,url=payload.url,url_hash=key,host=urlsplit(payload.url).hostname,kind='manual',interval_minutes=payload.interval_minutes,next_at=utcnow())
        db.add(row);db.flush();db.add(Audit(actor=user['username'],action='monitor.created',detail={'target_id':row.id,'host':row.host}));db.commit();return serialize(row)


@router.get('/monitors/{identifier}')
def detail(identifier:int,offset:int=Query(0,ge=0),references_offset:int=Query(0,ge=0),user=Depends(current_user)):
    with Session() as db:
        row=db.get(m.MonitorTarget,identifier)
        if not row:raise HTTPException(404,'Endereço não encontrado.')
        checks=select(m.MonitorCheck).where(m.MonitorCheck.target_id==identifier)
        refs=select(m.MonitorReference).where(m.MonitorReference.target_id==identifier)
        return {'target':serialize(row),'checks':{'total':db.scalar(select(func.count()).select_from(checks.subquery())),'items':[serialize(c) for c in db.scalars(checks.order_by(m.MonitorCheck.id.desc()).offset(offset).limit(20))]},
            'references':{'total':db.scalar(select(func.count()).select_from(refs.subquery())),'items':[serialize(r) for r in db.scalars(refs.order_by(m.MonitorReference.kind,m.MonitorReference.entity_id,m.MonitorReference.role).offset(references_offset).limit(25))]}}


@router.patch('/monitors/{identifier}')
def update_target(identifier:int,payload:TargetUpdate,user=Depends(operator)):
    with Session() as db:
        row=db.get(m.MonitorTarget,identifier)
        if not row:raise HTTPException(404,'Endereço não encontrado.')
        if row.archived and payload.enabled:raise HTTPException(409,'Atualize a descoberta; este endereço não está mais vinculado ao catálogo.')
        if payload.webhook_id:
            destination=db.get(Webhook,payload.webhook_id)
            if not destination or not destination.enabled:raise HTTPException(422,'Destino de notificação inexistente ou pausado.')
        for key,value in payload.model_dump().items():setattr(row,key,value)
        if row.enabled:row.next_at=utcnow()+timedelta(minutes=row.interval_minutes)
        db.add(Audit(actor=user['username'],action='monitor.updated',detail={'target_id':identifier,**payload.model_dump()}));db.commit();return serialize(row)


@router.post('/monitors/{identifier}/check',status_code=202)
def check_now(identifier:int,user=Depends(operator)):
    try:return {'check_id':enqueue_check(identifier,user['username'],manual=True)}
    except ValueError as exc:raise HTTPException(409,str(exc)) from None
