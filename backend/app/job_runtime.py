import hashlib
import json
import random
from datetime import timedelta, timezone
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from .database import Session
from .domain import Audit, Run, utcnow
from . import orchestration_models as m
from .automation import aware
from .providers import Network, SourceError

ACTIVE = {'queued','running','paused','retry_wait'}
TRANSIENT = {'network','unavailable','rate_limited'}


def policy(db, source):
    item=db.get(m.SourcePolicy,source)
    if not item:
        item=m.SourcePolicy(source=source)
        db.add(item)
        db.flush()
    return item


def runtime(db, identifier):
    item=db.get(m.Runtime,identifier)
    if not item:
        item=m.Runtime(run_id=identifier)
        db.add(item)
        db.flush()
    return item


def log(db, identifier, kind, message, data=None):
    db.add(m.RunLog(run_id=identifier,kind=kind,message=message,data=data or {}))


def freeze(identifier,key,value):
    with Session() as db:
        state=runtime(db,identifier)
        context=dict(state.context)
        if key not in context:
            context[key]=value
            state.context=context
            db.commit()
        return context[key]


def check_control(identifier,lease=None):
    with Session() as db:
        state=runtime(db,identifier)
        if lease is not None and state.lease!=lease:
            raise SourceError('superseded','Tentativa substituída por outra execução.')
        if state.requested in {'pause','cancel'}:
            raise SourceError(state.requested,'Pausa solicitada.' if state.requested=='pause' else 'Cancelamento solicitado.')


def set_stage(identifier,stage,lease=None):
    with Session() as db:
        db.scalar(select(Run).where(Run.id==identifier).with_for_update())
        state=runtime(db,identifier)
        if lease is not None and state.lease!=lease:
            raise SourceError('superseded','Tentativa substituída por outra execução.')
        if state.requested in {'pause','cancel'}:
            raise SourceError(state.requested,'Comando solicitado antes da gravação.')
        state.stage,state.heartbeat=stage,utcnow()
        db.commit()


def control(identifier,action,actor,reset=False):
    with Session() as db:
        run=db.scalar(select(Run).where(Run.id==identifier).with_for_update())
        if not run: raise ValueError('Execução não encontrada.')
        state=runtime(db,identifier)
        if action in {'pause','cancel'}:
            if run.status not in ACTIVE: raise ValueError('A execução já terminou.')
            if state.stage=='applying' and run.status=='running':
                raise ValueError('A gravação da etapa já começou. Aguarde sua conclusão.')
            state.requested=action
            if run.status!='running':
                run.status='paused' if action=='pause' else 'cancelled'
                state.stage=run.status
                if action=='cancel': run.active_key,run.finished_at=None,utcnow()
        elif action=='resume':
            if run.status not in {'paused','failed','retry_wait'}: raise ValueError('Esta execução não pode ser retomada.')
            other=db.scalar(select(Run.id).where(Run.active_key==run.source,Run.id!=run.id))
            if other: raise ValueError('A fonte está ocupada por outra execução.')
            run.active_key,run.status,run.finished_at=run.source,'queued',None
            run.message,run.error_code='Retomada adicionada à fila.',''
            state.requested,state.stage,state.next_at,state.retries='','queued',None,0
            if reset:
                db.execute(delete(m.Checkpoint).where(m.Checkpoint.run_id==identifier))
                state.responses,state.pages,state.cache_bytes=0,0,0
                state.context={}
        else: raise ValueError('Comando desconhecido.')
        log(db,identifier,'control',f'Comando: {action}',{'actor':actor,'reset_checkpoint':reset})
        db.add(Audit(actor=actor,action='run.'+action,detail={'run_id':identifier}))
        try: db.commit()
        except IntegrityError:
            db.rollback();raise ValueError('A fonte foi ocupada por outra execução.') from None
    if action=='resume':
        from .tasks import execute_run
        try: execute_run.delay(identifier)
        except Exception: pass  # The durable dispatcher will retry publishing.


def handle_failure(db,run,code,message,retry_after=None):
    state=runtime(db,run.id)
    config=policy(db,run.source)
    state.heartbeat=utcnow()
    run.error_code,run.message=code,message
    if code in {'pause','policy_paused','budget'}:
        run.status,state.stage='paused','paused'
    elif code=='cancel':
        run.status,run.active_key,run.finished_at='cancelled',None,utcnow()
        state.stage='cancelled'
    elif code in {'local_minute','local_day'} or (code in TRANSIENT and state.retries<config.auto_retries):
        if code in TRANSIENT: state.retries+=1
        seconds=retry_after or min(3600,30*2**max(0,state.retries-1)+random.uniform(0,5))
        state.next_at=utcnow()+timedelta(seconds=seconds)
        run.status,state.stage='retry_wait','waiting_retry'
        run.message=message+' Nova tentativa agendada.'
    else:
        run.status,run.active_key,run.finished_at='failed',None,utcnow()
        state.stage='failed'
    if run.status in {'failed','cancelled'}:
        for item in db.scalars(select(m.Review).where(m.Review.retry_run_id==run.id,m.Review.status=='retrying')):
            item.status='pending'
    log(db,run.id,'state',run.message,{'status':run.status,'code':code,'next_at':state.next_at.isoformat() if state.next_at else None})


class JobNetwork(Network):
    def __init__(self,identifier,client=None):
        super().__init__(client)
        self.identifier=identifier
        with Session() as db:
            run=db.get(Run,identifier)
            self.calls,self.retries=run.http_calls,run.attempts
            self.lease=runtime(db,identifier).lease

    async def before_request(self):
        check_control(self.identifier,self.lease)
        now=utcnow()
        with Session() as db:
            run=db.get(Run,self.identifier)
            config=policy(db,run.source)
            db.scalar(select(m.SourcePolicy).where(m.SourcePolicy.source==run.source).with_for_update())
            if not config.enabled: raise SourceError('policy_paused','Fonte pausada na política de coleta.')
            if run.http_calls>=config.per_run: raise SourceError('budget','Limite de chamadas desta execução atingido. Ajuste a política antes de retomar.')
            for window,maximum,code,wait in [
                (now.strftime('day:%Y-%m-%d'),config.per_day,'local_day',((now+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)-now).total_seconds()+1),
                (now.strftime('minute:%Y-%m-%dT%H:%M'),config.per_minute,'local_minute',61-now.second)]:
                usage=db.get(m.Usage,(run.source,window))
                if usage and usage.count>=maximum:
                    raise SourceError(code,'Janela de chamadas da fonte atingida.',retry_after=wait)
            for window in (now.strftime('day:%Y-%m-%d'),now.strftime('minute:%Y-%m-%dT%H:%M')):
                usage=db.get(m.Usage,(run.source,window))
                if not usage: usage=m.Usage(source=run.source,window=window,count=0);db.add(usage)
                usage.count+=1
            run.http_calls+=1
            runtime(db,run.id).heartbeat=now
            db.commit()

    async def get(self,url,params=None,headers=None):
        check_control(self.identifier,self.lease)
        key=hashlib.sha256(json.dumps([url,params or {}],sort_keys=True).encode()).hexdigest()
        with Session() as db:
            cached=db.get(m.Checkpoint,(self.identifier,key))
            if cached: return cached.data
            missing=runtime(db,self.identifier).context.get('not_found:'+key)
            if missing:raise SourceError('not_found',missing)
        try:data=await super().get(url,params,headers)
        except SourceError as exc:
            if exc.code=='not_found':freeze(self.identifier,'not_found:'+key,exc.message)
            raise
        size=len(json.dumps(data,ensure_ascii=False).encode())
        with Session() as db:
            run=db.scalar(select(Run).where(Run.id==self.identifier).with_for_update())
            state=runtime(db,self.identifier)
            if state.lease!=self.lease:
                raise SourceError('superseded','Tentativa substituída antes de confirmar a resposta.')
            if state.cache_bytes+size>policy(db,run.source).cache_mb*1024*1024:
                raise SourceError('budget','Limite de armazenamento de checkpoints atingido. Amplie a política antes de retomar.')
            if not db.get(m.Checkpoint,(self.identifier,key)):
                db.add(m.Checkpoint(run_id=self.identifier,key=key,data=data))
                state.responses+=1
                if url.endswith(('/organizations','/works','/package_search')): state.pages+=1
                state.cache_bytes+=size
                state.heartbeat=utcnow()
                log(db,self.identifier,'checkpoint','Resposta confirmada.',{'responses':state.responses,'pages':state.pages})
                db.commit()
        check_control(self.identifier,self.lease)
        return data
