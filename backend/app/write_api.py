from fastapi import APIRouter, Depends, HTTPException

from . import domain as d
from .automation import webhook_target
from .database import Session
from .models import Institution
from .operations import enqueue
from .read_api import serialize
from .schemas import RuleCreate, ScheduleCreate, SyncRequest, Toggle, Watch, WebhookCreate
from .security import admin, operator

router = APIRouter()


def audit(db, user, action, detail=None):
    db.add(d.Audit(actor=user['username'], action=action, detail=detail or {}))


@router.post('/watch')
def watch(payload: Watch, user=Depends(operator)):
    with Session() as db:
        if not db.get(Institution, payload.institution_id):
            raise HTTPException(404, 'Instituição não encontrada.')
        profile = db.get(d.Profile, payload.institution_id)
        if not profile:
            profile = d.Profile(institution_id=payload.institution_id)
            db.add(profile)
        profile.watched = payload.watched
        audit(db, user, 'institution.watch', payload.model_dump())
        db.commit()
    return {'ok': True}


@router.post('/sync', status_code=202)
def sync(payload: SyncRequest, user=Depends(operator)):
    if payload.source == 'orcid' and not (payload.orcid or payload.auto_discover):
        raise HTTPException(422, 'Informe um ORCID para a consulta.')
    try:
        identifier = enqueue(payload.source, payload.model_dump(), user['username'])
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    return {'execution_id': identifier, 'message': 'Execução registrada na fila.'}


@router.post('/runs/{identifier}/retry', status_code=202)
def retry(identifier: int, user=Depends(operator)):
    with Session() as db:
        run = db.get(d.Run, identifier)
        if not run:
            raise HTTPException(404, 'Execução não encontrada.')
        if run.status in {'running', 'queued'}:
            raise HTTPException(409, 'A execução ainda está em andamento.')
        source, params = run.source, dict(run.params)
    try:
        new = enqueue(source, params, user['username'])
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from None
    return {'execution_id': new}


@router.post('/schedules', status_code=201)
def add_schedule(payload: ScheduleCreate, user=Depends(operator)):
    params = payload.params.model_copy(update={'source': payload.source})
    if payload.source == 'orcid' and not params.orcid:
        raise HTTPException(422, 'Agendamento ORCID exige identificador.')
    with Session() as db:
        schedule = d.Schedule(source=payload.source, interval_minutes=payload.interval_minutes, params=params.model_dump())
        db.add(schedule)
        audit(db, user, 'schedule.created', {'source': payload.source})
        db.commit()
        return serialize(schedule)


@router.post('/rules', status_code=201)
def add_rule(payload: RuleCreate, user=Depends(operator)):
    with Session() as db:
        if payload.webhook_id and not db.get(d.Webhook, payload.webhook_id):
            raise HTTPException(422, 'Webhook não encontrado.')
        rule = d.Rule(**payload.model_dump())
        db.add(rule)
        audit(db, user, 'rule.created', {'name': rule.name})
        db.commit()
        return serialize(rule)


@router.patch('/{collection}/{identifier}/enabled')
def toggle_configuration(collection: str, identifier: int, payload: Toggle, user=Depends(operator)):
    model = {'rules': d.Rule, 'schedules': d.Schedule, 'webhooks': d.Webhook}.get(collection)
    if not model:
        raise HTTPException(404, 'Configuração desconhecida.')
    if collection == 'webhooks' and user['role'] != 'admin':
        raise HTTPException(403, 'Somente administradores podem alterar destinos externos.')
    with Session() as db:
        item = db.get(model, identifier)
        if not item:
            raise HTTPException(404, 'Configuração não encontrada.')
        item.enabled = payload.enabled
        audit(db, user, f'{collection}.toggled', {'id': identifier, 'enabled': payload.enabled})
        db.commit()
        return serialize(item)


@router.post('/incidents/{identifier}/resolve')
def resolve_incident(identifier: int, user=Depends(operator)):
    with Session() as db:
        item = db.get(d.Incident, identifier)
        if not item:
            raise HTTPException(404, 'Incidente não encontrado.')
        item.status, item.active_key, item.resolved_at = 'resolved', None, d.utcnow()
        audit(db, user, 'incident.resolved', {'id': identifier})
        db.commit()
        return serialize(item)


@router.post('/webhooks', status_code=201)
def add_webhook(payload: WebhookCreate, user=Depends(admin)):
    try:
        webhook_target(payload.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    with Session() as db:
        webhook = d.Webhook(**payload.model_dump())
        db.add(webhook)
        audit(db, user, 'webhook.created', {'name': webhook.name})
        db.commit()
        return serialize(webhook)
