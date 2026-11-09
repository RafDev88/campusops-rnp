from datetime import timedelta
from uuid import uuid4
from urllib.parse import urlsplit
from sqlalchemy import delete,select,update,and_,or_
from sqlalchemy.exc import IntegrityError
import structlog
from .database import Session
from .domain import Audit,Incident,Run,utcnow
from .automation import aware,add_event,open_incident
from . import monitor_models as m
from .monitor_inventory import config,sync_inventory
from .monitor_network import probe,ProbeError

logger=structlog.get_logger()


def reserve(host,source=''):
    now=utcnow()
    with Session() as db:
        settings=db.scalar(select(m.MonitorConfig).where(m.MonitorConfig.id==1).with_for_update())
        if not settings:settings=config(db)
        windows=[('all',now.strftime('day:%Y-%m-%d'),settings.per_day,((now+timedelta(days=1)).replace(hour=0,minute=0,second=0,microsecond=0)-now).total_seconds()+1),
                 (host,now.strftime('minute:%Y-%m-%dT%H:%M'),settings.per_host_minute,61-now.second)]
        for scope,window,maximum,delay in windows:
            item=db.get(m.MonitorUsage,(scope,window))
            if item and item.count>=maximum:raise ProbeError('deferred','Limite local de monitoramento atingido; a verificação foi adiada.',delay)
        for scope,window,_,_ in windows:
            item=db.get(m.MonitorUsage,(scope,window))
            if not item:item=m.MonitorUsage(scope=scope,window=window,count=0);db.add(item)
            item.count+=1
        if source:
            from .monitor_network import API_ENDPOINTS
            from .job_runtime import policy
            from . import orchestration_models as om
            if host==urlsplit(API_ENDPOINTS[source][1]).hostname:
                settings=policy(db,source)
                db.scalar(select(om.SourcePolicy).where(om.SourcePolicy.source==source).with_for_update())
                if not settings.enabled:raise ProbeError('deferred','A fonte está pausada na política de consultas.',900)
                for window,maximum,delay in [(now.strftime('day:%Y-%m-%d'),settings.per_day,windows[0][3]),(now.strftime('minute:%Y-%m-%dT%H:%M'),settings.per_minute,61-now.second)]:
                    usage=db.get(om.Usage,(source,window))
                    if usage and usage.count>=maximum:raise ProbeError('deferred','Limite compartilhado de chamadas da fonte atingido.',delay)
                    if not usage:usage=om.Usage(source=source,window=window,count=0);db.add(usage)
                    usage.count+=1
        db.commit()


def enqueue_check(identifier,actor='scheduler',manual=False):
    with Session() as db:
        target=db.scalar(select(m.MonitorTarget).where(m.MonitorTarget.id==identifier).with_for_update())
        if not target or target.archived:raise ValueError('Endereço não encontrado ou arquivado.')
        existing=db.scalar(select(m.MonitorCheck.id).where(m.MonitorCheck.active_key==f'monitor:{identifier}'))
        if existing:return existing
        if not manual and (not target.enabled or not config(db).enabled):raise ValueError('Monitoramento automático pausado.')
        latest=db.scalar(select(m.MonitorCheck).where(m.MonitorCheck.target_id==identifier).order_by(m.MonitorCheck.id.desc()))
        if manual and latest and aware(latest.created_at)>utcnow()-timedelta(seconds=60):raise ValueError('Aguarde um minuto entre verificações manuais do mesmo endereço.')
        target.next_at=utcnow()+timedelta(minutes=target.interval_minutes)
        item=m.MonitorCheck(target_id=identifier,active_key=f'monitor:{identifier}',actor=actor,manual=manual)
        db.add(item)
        try:
            db.flush();result=item.id
            if manual:db.add(Audit(actor=actor,action='monitor.check',detail={'target_id':identifier,'check_id':result}))
            db.commit()
        except IntegrityError:
            db.rollback();existing=db.scalar(select(m.MonitorCheck.id).where(m.MonitorCheck.active_key==f'monitor:{identifier}'))
            if existing:return existing
            raise
    from .tasks import monitor_check
    try:monitor_check.delay(result)
    except Exception:logger.warning('monitor_publish_deferred',check_id=result)
    return result


def incidents(db,target,check):
    if check.ok is None:return
    failure_key=f'monitor:failure:{target.id}'
    certificate_key=f'monitor:certificate:{target.id}'
    if not check.ok:
        target.failures+=1;target.recoveries=0
        if target.alerts and target.failures>=target.failure_threshold:
            rule=type('Destination',(),{'webhook_id':target.webhook_id})()
            open_incident(db,failure_key,target.source or 'links','Problema persistente: '+target.name[:240],check.message,rule)
    else:
        target.failures=0;target.recoveries+=1
        if target.recoveries>=2:
            incident=db.scalar(select(Incident).where(Incident.active_key==failure_key))
            if incident:
                incident.status,incident.active_key,incident.resolved_at='resolved',None,utcnow()
                add_event(db,f'monitor:recovery:{incident.id}','recovery','Endereço recuperado: '+target.name[:240],{'target_id':target.id,'incident_id':incident.id},target.webhook_id if target.alerts else None)
    days=(check.tls or {}).get('days_remaining')
    if days is not None and days<=target.certificate_days and target.alerts:
        rule=type('Destination',(),{'webhook_id':target.webhook_id})()
        open_incident(db,certificate_key,target.source or 'links','Certificado próximo do vencimento: '+target.host,
            f'Certificado válido por mais {days} dias. O diagnóstico se refere ao endereço verificado.',rule)
    elif days is not None and days>target.certificate_days:
        incident=db.scalar(select(Incident).where(Incident.active_key==certificate_key))
        if incident:
            incident.status,incident.active_key,incident.resolved_at='resolved',None,utcnow()
            add_event(db,f'monitor:renewal:{incident.id}','recovery','Certificado renovado: '+target.host,{'target_id':target.id,'incident_id':incident.id},target.webhook_id if target.alerts else None)


def perform_check(identifier,prober=None):
    lease=uuid4().hex
    with Session() as db:
        changed=db.execute(update(m.MonitorCheck).where(m.MonitorCheck.id==identifier,m.MonitorCheck.state=='queued').values(state='running',started_at=utcnow(),lease=lease))
        db.commit()
        if not changed.rowcount:return
        item=db.get(m.MonitorCheck,identifier);target=db.get(m.MonitorTarget,item.target_id)
        if target.archived or (not item.manual and (not target.enabled or not config(db).enabled)):
            item.state,item.active_key,item.outcome,item.message,item.finished_at='completed',None,'skipped','Monitoramento pausado ou endereço arquivado.',utcnow();db.commit();return
        params=(target.url,target.source,target.kind,target.certificate_days,target.expected_type)
    try:result=(prober or probe)(params[0],source=params[1],kind=params[2],certificate_days=params[3],expected_type=params[4],reserve=lambda host:reserve(host,params[1] if params[2]=='api' else ''))
    except Exception:
        logger.exception('monitor_check_failed',check_id=identifier)
        result={'outcome':'internal','ok':None,'message':'Falha interna na verificação. Consulte o identificador nos logs.'}
    with Session() as db:
        item=db.scalar(select(m.MonitorCheck).where(m.MonitorCheck.id==identifier).with_for_update())
        if item.state!='running' or item.lease!=lease:return
        target=db.scalar(select(m.MonitorTarget).where(m.MonitorTarget.id==item.target_id).with_for_update())
        for key in ('outcome','ok','message','http_status','final_url','method','duration_ms','timings','redirects','tls'):
            if key in result:setattr(item,key,result[key])
        item.state,item.active_key,item.finished_at='completed',None,utcnow()
        if item.outcome in {'deferred','internal'}:
            item.ok=None
            target.next_at=utcnow()+timedelta(seconds=result.get('retry_after') or 900)
        else:
            target.status,target.checked_at,target.last_check_id=item.outcome,item.finished_at,item.id
            if item.outcome=='rate_limited':target.next_at=utcnow()+timedelta(seconds=result.get('retry_after') or 900)
            elif not item.ok:target.next_at=utcnow()+timedelta(minutes=min(target.interval_minutes,15*2**min(target.failures,5)))
            incidents(db,target,item)
        db.commit()


def monitor_tick():
    from .tasks import monitor_check
    with Session() as db:
        settings=config(db)
        for item in db.scalars(select(m.MonitorCheck).where(m.MonitorCheck.state=='running',m.MonitorCheck.started_at<utcnow()-timedelta(minutes=3)).with_for_update(skip_locked=True)):
            item.state,item.active_key,item.outcome,item.ok,item.message,item.finished_at='completed',None,'interrupted',None,'Worker interrompido. Uma nova verificação será agendada.',utcnow()
            db.get(m.MonitorTarget,item.target_id).next_at=utcnow()+timedelta(minutes=1)
        enabled,discover=settings.enabled,settings.discovery and aware(settings.next_discovery)<=utcnow()
        # Attempt history is retained for the configured window. Keep the latest
        # completed check for each target so its summary never points to nothing.
        latest=select(m.MonitorTarget.last_check_id).where(m.MonitorTarget.last_check_id.is_not(None))
        db.execute(delete(m.MonitorCheck).where(m.MonitorCheck.finished_at<utcnow()-timedelta(days=settings.retention_days),m.MonitorCheck.active_key.is_(None),m.MonitorCheck.id.not_in(latest)))
        db.execute(delete(m.MonitorUsage).where(or_(and_(m.MonitorUsage.window.startswith('day:'),m.MonitorUsage.window<utcnow().strftime('day:%Y-%m-%d')),and_(m.MonitorUsage.window.startswith('minute:'),m.MonitorUsage.window<utcnow().strftime('minute:%Y-%m-%d')))))
        db.commit()
    if discover:
        try:sync_inventory()
        except Exception:logger.exception('monitor_discovery_failed')
    if enabled:
        with Session() as db:due=list(db.scalars(select(m.MonitorTarget.id).where(m.MonitorTarget.enabled.is_(True),m.MonitorTarget.archived.is_(False),m.MonitorTarget.next_at<=utcnow()).order_by(m.MonitorTarget.next_at).limit(10)))
        for identifier in due:
            try:enqueue_check(identifier)
            except ValueError:pass
            except Exception:logger.exception('monitor_enqueue_failed',target_id=identifier)
    with Session() as db:pending=list(db.scalars(select(m.MonitorCheck.id).where(m.MonitorCheck.state=='queued').order_by(m.MonitorCheck.id).limit(30)))
    for identifier in pending:
        try:monitor_check.delay(identifier)
        except Exception:logger.warning('monitor_publish_deferred',check_id=identifier)
