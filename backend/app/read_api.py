import os
import re
from collections import Counter
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, inspect, select

from . import domain as d
from .automation import aware
from .database import Session
from .models import Execution, Institution
from .security import admin, current_user

router = APIRouter()
SOURCES = ['ror', 'openalex', 'crossref', 'orcid', 'ufrn']


def serialize(row, exclude=()):
    result = {}
    for column in inspect(type(row)).columns:
        if column.key in exclude:
            continue
        value = getattr(row, column.key)
        result[column.key] = aware(value).isoformat() if hasattr(value, 'isoformat') else value
    return result


@router.get('/dashboard')
def dashboard(user=Depends(current_user)):
    with Session() as db:
        runs = db.scalars(select(d.Run).order_by(d.Run.id.desc()).limit(50)).all()
        counts = {name: db.scalar(select(func.count()).select_from(model)) for name, model in
                  [('institutions', Institution), ('publications', d.Publication), ('researchers', d.Researcher), ('datasets', d.Dataset)]}
        counts['watched'] = db.scalar(select(func.count()).select_from(d.Profile).where(d.Profile.watched.is_(True)))
        counts['open_incidents'] = db.scalar(select(func.count()).select_from(d.Incident).where(d.Incident.status == 'open'))
        counts['pending'] = db.scalar(select(func.count()).select_from(d.Run).where(d.Run.status.in_(['queued', 'running'])))
        return {'counts': counts, 'executions': [serialize(row) for row in runs],
                'legacy_executions': db.scalar(select(func.count()).select_from(Execution)),
                'events': [serialize(row) for row in db.scalars(select(d.Event).order_by(d.Event.id.desc()).limit(8))]}


@router.get('/institutions')
def institutions(q: str = '', watched: bool = False,country:str='',city:str='',region:str='',institution_type:str='',status:str='',
                 approximate:bool=False,offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), user=Depends(current_user)):
    with Session() as db:
        query = select(Institution, d.Profile).outerjoin(d.Profile, d.Profile.institution_id == Institution.id)
        if q:
            from .discovery import matching
            from .discovery_models import SearchDocument
            condition, _ = matching(db, q[:150],approximate=approximate)
            query = query.where(Institution.id.in_(select(SearchDocument.entity_id).where(SearchDocument.kind == 'institution', condition)))
        if watched:
            query = query.where(d.Profile.watched.is_(True))
        from .discovery_models import InstitutionField
        from .search_index import fold
        for field,value in [('country',country),('city',city),('region',region),('type',institution_type),('status',status)]:
            if value:query=query.where(Institution.id.in_(select(InstitutionField.institution_id).where(InstitutionField.field==field,InstitutionField.value==fold(value))))
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        rows = db.execute(query.order_by(Institution.name).offset(offset).limit(limit)).all()
        return {'total': total, 'items': [{**serialize(inst), 'watched': bool(profile and profile.watched)} for inst, profile in rows]}


@router.get('/institution-profile')
def institution_profile(id: str, user=Depends(current_user)):
    with Session() as db:
        institution = db.get(Institution, id)
        if not institution:
            raise HTTPException(404, 'Instituição não encontrada.')
        profile = db.get(d.Profile, id)
        works = db.scalars(select(d.Publication).join(d.WorkInstitution).where(d.WorkInstitution.institution_id == id)).all()
        years, topics, collaborations = Counter(), Counter(), Counter()
        for work in works:
            if work.year:
                years[work.year] += 1
            for topic in work.topics:
                topics[topic['name']] += 1
            for affiliation in work.affiliations:
                if affiliation.get('ror') != id:
                    collaborations[affiliation['name']] += 1
        return {'institution': serialize(institution), 'profile': serialize(profile) if profile else None,
                'metrics': {'imported': len(works), 'open_access': sum(w.is_oa for w in works),
                            'citations': sum(w.citations for w in works), 'years': sorted(years.items()),
                            'topics': topics.most_common(12), 'collaborations': collaborations.most_common(15)},
                'scope': 'Indicadores calculados sobre as publicações importadas; não representam um ranking de qualidade.'}


@router.get('/quality')
def quality(offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(current_user)):
    def normalize(value):
        return re.sub(r'\W+', '', value.casefold())
    with Session() as db:
        issues = []
        doi_groups = Counter(db.scalars(select(d.Publication.doi).where(d.Publication.doi.is_not(None))))
        for work in db.scalars(select(d.Publication)):
            reasons = []
            if not work.doi:
                reasons.append('Sem DOI')
            if not work.affiliations:
                reasons.append('Sem afiliação na fonte')
            if work.doi and doi_groups[work.doi] > 1:
                reasons.append('DOI repetido: possível duplicação')
            if work.crossref.get('title') and normalize(work.title) != normalize(work.crossref['title'][0]):
                reasons.append('Título divergente entre OpenAlex e Crossref')
            if d.utcnow() - aware(work.fetched_at) > timedelta(days=30):
                reasons.append('Sem atualização há mais de 30 dias')
            if reasons:
                issues.append({'id': work.id, 'title': work.title, 'reasons': reasons, 'doi': work.doi,
                               'openalex_title': work.title, 'crossref_title': (work.crossref.get('title') or [''])[0]})
        return {'total': len(issues), 'items': issues[offset:offset + limit],
                'counts': dict(Counter(reason for issue in issues for reason in issue['reasons'])),
                'policy': 'Sinalizações para revisão humana. Nenhum campo é sobrescrito entre fontes.'}


@router.get('/sources')
def sources(user=Depends(current_user)):
    with Session() as db:
        result = []
        for source in SOURCES:
            runs = db.scalars(select(d.Run).where(d.Run.source == source).order_by(d.Run.id.desc()).limit(50)).all()
            success = next((row for row in runs if row.status == 'success'), None)
            terminal = [row for row in runs if row.status in {'success', 'partial', 'failed'}]
            result.append({'id': source, 'last_run': serialize(runs[0]) if runs else None,
                           'last_success': aware(success.finished_at).isoformat() if success and success.finished_at else None,
                           'success_rate': round(sum(r.status == 'success' for r in terminal) / len(terminal) * 100, 1) if terminal else None,
                           'average_ms': round(sum(r.duration_ms for r in terminal) / len(terminal)) if terminal else None,
                           'retries': sum(r.attempts for r in terminal), 'sample_size': len(terminal)})
        return {'items': result, 'credentials': {'openalex': bool(os.getenv('OPENALEX_API_KEY')), 'orcid': bool(os.getenv('ORCID_ACCESS_TOKEN'))}}


@router.get('/runs')
def runs(source: str = '', status: str = '', offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), user=Depends(current_user)):
    with Session() as db:
        query = select(d.Run)
        if source:
            query = query.where(d.Run.source == source)
        if status:
            query = query.where(d.Run.status == status)
        return {'total': db.scalar(select(func.count()).select_from(query.subquery())),
                'items': [serialize(row) for row in db.scalars(query.order_by(d.Run.id.desc()).offset(offset).limit(limit))]}


@router.get('/legacy-executions')
def legacy_executions(user=Depends(current_user)):
    with Session() as db:
        return [serialize(row) for row in db.scalars(select(Execution).order_by(Execution.id.desc()).limit(100))]


@router.get('/schedules')
def schedules(user=Depends(current_user)):
    with Session() as db:
        return [serialize(row) for row in db.scalars(select(d.Schedule).order_by(d.Schedule.id))]


@router.get('/rules')
def rules(user=Depends(current_user)):
    with Session() as db:
        return [serialize(row) for row in db.scalars(select(d.Rule).order_by(d.Rule.id))]


@router.get('/incidents')
def incidents(user=Depends(current_user)):
    with Session() as db:
        return [serialize(row) for row in db.scalars(select(d.Incident).order_by(d.Incident.id.desc()).limit(200))]


@router.get('/events')
def events(offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), user=Depends(current_user)):
    with Session() as db:
        return {'total': db.scalar(select(func.count()).select_from(d.Event)),
                'items': [serialize(row) for row in db.scalars(select(d.Event).order_by(d.Event.id.desc()).offset(offset).limit(limit))]}


@router.get('/digest')
def digest(user=Depends(current_user)):
    cutoff = d.utcnow() - timedelta(days=7)
    with Session() as db:
        works = db.scalars(select(d.Publication).where(d.Publication.fetched_at >= cutoff)).all()
        return {'period_from': cutoff.isoformat(), 'period_to': d.utcnow().isoformat(),
                'updated_publications': len(works), 'open_access': sum(w.is_oa for w in works),
                'topics': Counter(t['name'] for w in works for t in w.topics).most_common(10),
                'events': [serialize(row) for row in db.scalars(select(d.Event).where(d.Event.created_at >= cutoff).order_by(d.Event.id.desc()).limit(100))],
                'scope': 'Publicações coletadas ou atualizadas nos últimos sete dias; não necessariamente publicadas neste período.'}


@router.get('/researchers')
def researchers(user=Depends(current_user)):
    with Session() as db:
        return [serialize(row) for row in db.scalars(select(d.Researcher).order_by(d.Researcher.name).limit(200))]


@router.get('/datasets')
def datasets(q: str = '', offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), user=Depends(current_user)):
    with Session() as db:
        query = select(d.Dataset).where(d.Dataset.title.ilike(f'%{q[:150]}%'))
        return {'total': db.scalar(select(func.count()).select_from(query.subquery())),
                'items': [serialize(row) for row in db.scalars(query.order_by(d.Dataset.title).offset(offset).limit(limit))]}


@router.get('/webhooks')
def webhooks(user=Depends(admin)):
    with Session() as db:
        return {'items': [serialize(row) for row in db.scalars(select(d.Webhook))],
                'deliveries': [serialize(row) for row in db.scalars(select(d.Delivery).order_by(d.Delivery.id.desc()).limit(100))],
                'signing_configured': bool(os.getenv('WEBHOOK_SIGNING_SECRET')),
                'allowed_hosts': os.getenv('WEBHOOK_ALLOWED_HOSTS', '')}


@router.get('/audit')
def audit_log(user=Depends(admin)):
    with Session() as db:
        return [serialize(row) for row in db.scalars(select(d.Audit).order_by(d.Audit.id.desc()).limit(200))]


@router.get('/metrics', response_class=Response)
def metrics(user=Depends(admin)):
    lines = ['# TYPE campusops_runs_total gauge', '# TYPE campusops_run_duration_seconds gauge']
    with Session() as db:
        for source in SOURCES:
            for status in ['queued', 'running', 'success', 'partial', 'failed']:
                count = db.scalar(select(func.count()).select_from(d.Run).where(d.Run.source == source, d.Run.status == status))
                lines.append(f'campusops_runs_total{{source="{source}",status="{status}"}} {count}')
            run = db.scalar(select(d.Run).where(d.Run.source == source, d.Run.finished_at.is_not(None)).order_by(d.Run.id.desc()))
            if run:
                lines.append(f'campusops_run_duration_seconds{{source="{source}"}} {run.duration_ms / 1000}')
    return Response('\n'.join(lines) + '\n', media_type='text/plain; version=0.0.4')
