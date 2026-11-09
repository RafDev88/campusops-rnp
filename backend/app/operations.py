import asyncio
from datetime import timedelta
from time import perf_counter
from uuid import uuid4

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from .automation import aware, evaluate_run, evaluate_stale
from .database import Session
from .domain import Audit, Dataset, Profile, Publication, Researcher, Run, Schedule, WorkInstitution, utcnow
from .models import Institution
from .discovery import evaluate_saved_searches
from .providers import Providers, SourceError
from .job_runtime import JobNetwork, runtime, policy, log, set_stage, handle_failure
from . import orchestration_models as m

logger = structlog.get_logger()


def enqueue(source, params, actor='scheduler', dispatch_key=None):
    with Session() as db:
        if dispatch_key:
            existing=db.scalar(select(m.Runtime.run_id).where(m.Runtime.dispatch_key==dispatch_key))
            if existing: return existing
        if not policy(db,source).enabled: raise ValueError('Fonte pausada na política de coleta.')
        run = Run(source=source, active_key=source, params=params, actor=actor)
        db.add(run)
        try:
            db.flush()
            db.add(m.Runtime(run_id=run.id,dispatch_key=dispatch_key))
            db.commit()
        except IntegrityError:
            db.rollback()
            raise ValueError('Já existe uma execução pendente ou em andamento para esta fonte.') from None
        identifier = run.id
        db.add(Audit(actor=actor, action='sync.queued', detail={'run_id': identifier, 'source': source}))
        db.commit()
    try:
        from .tasks import execute_run
        execute_run.delay(identifier)
    except Exception:
        # Durable run remains queued; beat republishes it when the broker recovers.
        logger.warning('queue_publish_deferred', run_id=identifier)
    return identifier


async def perform(identifier, provider=None):
    start = perf_counter()
    with Session() as db:
        result = db.execute(update(Run).where(Run.id == identifier, Run.status == 'queued').values(
            status='running', started_at=utcnow(), message='Coleta em andamento.'))
        db.commit()
        if not result.rowcount:
            return
        run = db.get(Run, identifier)
        source, params = run.source, dict(run.params)
        state=runtime(db,identifier)
        lease=state.lease=uuid4().hex
        state.stage,state.heartbeat='collecting',utcnow()
        log(db,identifier,'started','Coleta iniciada ou retomada.')
        db.commit()
    provider = provider or Providers(JobNetwork(identifier))
    try:
        from .collector import collect
        profiles, items, details, rejects = await collect(identifier, source, params, provider)
        set_stage(identifier, 'applying',lease)
        with Session() as db:
            run = db.scalar(select(Run).where(Run.id==identifier).with_for_update())
            if run.status!='running' or runtime(db,identifier).lease!=lease:return
            fresh, changed, publications, datasets = 0, 0, [], []
            if source == 'ror':
                for row in items:
                    institution = db.get(Institution, row['id'])
                    if not institution:
                        institution = Institution(id=row['id'], name=row['name'], country=row['country'])
                        db.add(institution)
                        fresh += 1
                    elif institution.name != row['name'] or institution.country != row['country']:
                        changed += 1
                        from .orchestration import record_changes
                        record_changes(db,run,institution.id,{'name':institution.name,'country':institution.country},{'name':row['name'],'country':row['country']})
                        institution.name, institution.country = row['name'], row['country']
                    db.flush()
                    profile = db.get(Profile, row['id'])
                    if not profile:
                        profile = Profile(institution_id=row['id'])
                        db.add(profile)
                    profile.data = {**(profile.data or {}), 'ror': row['data']}
                    profile.fetched_at = utcnow()
            elif source == 'openalex':
                for institution_id, remote in profiles:
                    profile = db.get(Profile, institution_id)
                    if not profile:
                        profile = Profile(institution_id=institution_id)
                        db.add(profile)
                    profile.data = {**(profile.data or {}), 'openalex': remote,
                                    'coverage': next(s for s in details['coverage'] if s['institution_id'] == institution_id)}
                    profile.fetched_at = utcnow()
                for institution_id, row in items:
                    publication = db.get(Publication, row['id'])
                    if not publication:
                        publication = Publication(**row)
                        db.add(publication)
                        fresh += 1
                        publications.append(publication)
                    else:
                        if publication.openalex != row['openalex']:
                            changed += 1
                        from .orchestration import record_changes
                        fields=['title','year','doi','is_oa','citations','topics','authors','affiliations']
                        record_changes(db,run,publication.id,{k:getattr(publication,k) for k in fields},{k:row[k] for k in fields})
                        for key, value in row.items():
                            setattr(publication, key, value)
                        publication.fetched_at = utcnow()
                    db.flush()
                    if not db.get(WorkInstitution, (publication.id, institution_id)):
                        db.add(WorkInstitution(publication_id=publication.id, institution_id=institution_id))
                        db.flush()
            elif source == 'crossref':
                for work_id, payload in items:
                    publication = db.get(Publication, work_id)
                    if publication.crossref != payload:
                        changed += 1
                    from .orchestration import record_changes
                    record_changes(db,run,publication.id,{'crossref':publication.crossref},{'crossref':payload})
                    publication.crossref, publication.crossref_at = payload, utcnow()
                    publication.crossref_checked_at = utcnow()
                for rejection in rejects:
                    db.get(Publication, rejection['publication_id']).crossref_checked_at = utcnow()
            elif source == 'orcid':
                for row in items:
                    researcher = db.get(Researcher, row['orcid'])
                    if not researcher:
                        db.add(Researcher(**row))
                        fresh += 1
                    else:
                        if researcher.data != row['data']:
                            changed += 1
                        from .orchestration import record_changes
                        record_changes(db,run,researcher.orcid,{'name':researcher.name},{'name':row['name']})
                        researcher.name, researcher.data, researcher.fetched_at = row['name'], row['data'], utcnow()
            elif source == 'ufrn':
                for row in items:
                    dataset = db.get(Dataset, row['id'])
                    if not dataset:
                        db.add(Dataset(**row))
                        fresh += 1
                    else:
                        if dataset.fingerprint != row['fingerprint']:
                            changed += 1
                            datasets.append(dataset)
                        from .orchestration import record_changes
                        record_changes(db,run,dataset.id,{'title':dataset.title,'resources':dataset.resources,'modified':dataset.modified},{k:row[k] for k in ['title','resources','modified']})
                        for key, value in row.items():
                            setattr(dataset, key, value)
                        dataset.fetched_at = utcnow()
            run.records, run.new, run.updated, run.rejected = len(items), fresh, changed, len(rejects)
            run.status = 'partial' if rejects or details.get('complete') is False else 'success'
            run.error_code = ''
            run.details, run.message = details, 'Coleta concluída.' if run.status == 'success' else 'Coleta parcial. Consulte a cobertura e os registros rejeitados.'
            run.active_key, run.finished_at = None, utcnow()
            run.duration_ms = (run.duration_ms or 0) + int((perf_counter() - start) * 1000)
            run.attempts, run.http_calls = provider.net.retries, provider.net.calls
            from .orchestration import finalize_collection
            finalize_collection(db,run,source,items,details,rejects)
            evaluate_run(db, run, publications, datasets)
            evaluate_saved_searches(db)
            db.commit()
        logger.info('run_completed', run_id=identifier, source=source, records=len(items))
    except Exception as exc:
        # Always finalize a claimed execution, including unexpected DB/contract failures.
        if isinstance(exc, SourceError):
            code, message = exc.code, exc.message
        elif isinstance(exc, (KeyError, TypeError, ValueError, IndexError)):
            code, message = 'schema_change', 'Resposta incompatível com o contrato esperado; alterações não foram aplicadas.'
        else:
            code, message = 'internal', 'Falha interna. Consulte os logs pelo identificador da execução.'
        with Session() as db:
            run = db.scalar(select(Run).where(Run.id==identifier).with_for_update())
            if run.status!='running' or runtime(db,identifier).lease!=lease:return
            handle_failure(db,run,code,message,getattr(exc,'retry_after',None))
            run.duration_ms = (run.duration_ms or 0) + int((perf_counter() - start) * 1000)
            run.attempts, run.http_calls = provider.net.retries, provider.net.calls
            if run.status=='failed': evaluate_run(db, run)
            if run.status=='failed' and code=='schema_change':
                from .orchestration import review
                review(db,run,'schema',message,run.params)
            db.commit()
        logger.error('run_failed', run_id=identifier, source=source, error_type=type(exc).__name__, error_code=code)
    finally:
        if hasattr(provider.net, 'aclose'):
            await provider.net.aclose()


def tick():
    from .tasks import execute_run
    with Session() as db:
        # A worker killed midway cannot hold the integration forever.
        for run in db.scalars(select(Run).where(Run.status == 'running',
                ~select(m.Runtime.run_id).where(m.Runtime.run_id==Run.id).exists(),
                func.coalesce(Run.started_at, Run.created_at) < utcnow() - timedelta(hours=2))):
            run.status, run.active_key, run.finished_at = 'failed', None, utcnow()
            run.error_code, run.message = 'interrupted', 'Execução interrompida ou excedeu duas horas. Reprocesse manualmente.'
            evaluate_run(db, run)
        due = [(s.id, s.source, s.params, s.interval_minutes) for s in db.scalars(
            select(Schedule).where(Schedule.enabled.is_(True), Schedule.next_at <= utcnow()))]
        evaluate_stale(db)
        from .automation import evaluate_digest
        evaluate_digest(db)
        db.commit()
    for schedule_id, source, params, minutes in due:
        with Session() as db:
            claimed = db.execute(update(Schedule).where(Schedule.id == schedule_id, Schedule.enabled.is_(True),
                Schedule.next_at <= utcnow()).values(next_at=utcnow() + timedelta(minutes=minutes)))
            db.commit()
            if not claimed.rowcount:
                continue
        try:
            enqueue(source, params)
        except ValueError:
            continue
    with Session() as db:
        pending = db.scalars(select(Run.id).where(Run.status == 'queued').limit(50)).all()
    for identifier in pending:
        try: execute_run.delay(identifier)
        except Exception: logger.warning('queue_publish_deferred',run_id=identifier)
