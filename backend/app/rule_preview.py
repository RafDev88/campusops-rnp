from datetime import timedelta
from sqlalchemy import select
from .database import Session
from .domain import Run,Publication,Dataset,utcnow
from . import orchestration_models as m
from .automation import aware,topic_matches


def preview(payload):
    samples=[]
    sources=[payload.source] if payload.source!='all' else ['ror','openalex','crossref','orcid','ufrn']
    explanation='Simulação com dados atuais. Não cria eventos, incidentes nem entregas externas.'
    with Session() as db:
        if payload.kind in {'new_publication','weekly_digest'}:
            query=select(Publication)
            if payload.kind=='weekly_digest':query=query.where(Publication.fetched_at>=utcnow()-timedelta(days=7))
            for work in db.scalars(query):
                if (payload.kind=='weekly_digest' or payload.source in {'all','openalex'}) and topic_matches(work,payload.topic):
                    samples.append({'id':work.id,'title':work.title,'kind':'publication'})
            explanation+=' Publicações atuais compatíveis; novas publicações só disparam após próximas coletas.'
        elif payload.kind=='failure_streak':
            for source in sources:
                recent=list(db.scalars(select(Run).where(Run.source==source,Run.status.in_(['success','partial','failed'])).order_by(Run.id.desc()).limit(payload.threshold)))
                if len(recent)==payload.threshold and all(r.status=='failed' for r in recent):samples.append({'id':source,'title':f'{source}: {payload.threshold} falhas consecutivas','kind':'source'})
        elif payload.kind=='schema_change':
            for run in db.scalars(select(Run).where(Run.source.in_(sources),Run.error_code=='schema_change').order_by(Run.id.desc()).limit(50)):
                samples.append({'id':str(run.id),'title':f'Execução #{run.id}: {run.source}','kind':'run'})
        elif payload.kind=='stale_source':
            for source in sources:
                run=db.scalar(select(Run).where(Run.source==source,Run.status=='success').order_by(Run.id.desc()))
                if not run:run=db.scalar(select(Run).where(Run.source==source).order_by(Run.id))
                if run and utcnow()-aware(run.finished_at or run.created_at)>timedelta(minutes=payload.threshold):samples.append({'id':source,'title':f'{source}: atualização fora do prazo','kind':'source'})
        elif payload.kind=='dataset_changed':
            ids=set(db.scalars(select(m.Change.entity_id).where(m.Change.source=='ufrn',m.Change.created_at>=utcnow()-timedelta(days=7))))
            for item in db.scalars(select(Dataset).where(Dataset.id.in_(ids))):samples.append({'id':item.id,'title':item.title,'kind':'dataset'})
            explanation+=' Mostra mudanças registradas nos últimos sete dias.'
    return {'matched_count':len(samples),'samples':samples[:20],'explanation':explanation}
