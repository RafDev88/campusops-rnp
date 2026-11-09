"""Transactional event creation and durable webhook outbox."""
import hashlib
import hmac
import ipaddress
import json
import os
import socket
from datetime import timedelta
from urllib.parse import urlsplit

import httpx
from sqlalchemy import select, update

from .database import Session
from .domain import Delivery, Event, Incident, Publication, Rule, Run, Webhook, utcnow


def aware(value):
    from datetime import timezone
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def topic_matches(publication,topic):
    from .search_index import fold
    return not topic or fold(topic) in fold(publication.title+' '+' '.join(t['name'] for t in publication.topics))


def webhook_target(url):
    parsed = urlsplit(url)
    allowed = {s.strip().lower() for s in os.getenv('WEBHOOK_ALLOWED_HOSTS', '').split(',') if s.strip()}
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Use uma URL HTTPS sem credenciais ou fragmento.')
    if parsed.hostname.lower() not in allowed or parsed.port not in (None, 443):
        raise ValueError('O domínio precisa estar em WEBHOOK_ALLOWED_HOSTS no servidor; apenas porta 443.')
    return parsed.hostname


def validate_public_destination(url):
    host = webhook_target(url)
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
        raise ValueError('O destino do webhook deve resolver apenas para endereços públicos.')


def add_event(db, key, kind, title, payload, webhook_id=None):
    event = db.scalar(select(Event).where(Event.dedupe_key == key))
    if event:
        return event
    event = Event(dedupe_key=key, kind=kind, title=title, payload=payload)
    db.add(event)
    db.flush()
    if webhook_id:
        target = db.get(Webhook, webhook_id)
        if target and target.enabled:
            db.add(Delivery(webhook_id=target.id, event_id=event.id))
    return event


def open_incident(db, key, source, title, detail, rule=None):
    if db.scalar(select(Incident).where(Incident.active_key == key)):
        return
    incident = Incident(active_key=key, source=source, title=title, detail=detail)
    db.add(incident)
    db.flush()
    add_event(db, f'incident:{incident.id}', 'incident', title,
              {'incident_id': incident.id, 'source': source, 'detail': detail}, rule.webhook_id if rule else None)


def evaluate_run(db, run, new_publications=(), changed_datasets=()):
    db.flush()
    rules = db.scalars(select(Rule).where(Rule.enabled.is_(True), Rule.source.in_(['all', run.source]))).all()
    for rule in rules:
        if rule.kind == 'failure_streak':
            key = f'failure:{rule.id}:{run.source}'
            if run.status == 'success':
                incident = db.scalar(select(Incident).where(Incident.active_key == key))
                if incident:
                    incident.status, incident.active_key, incident.resolved_at = 'resolved', None, utcnow()
                    add_event(db, f'recovery:{incident.id}', 'recovery', f'Integração {run.source} recuperada',
                              {'incident_id': incident.id, 'run_id': run.id}, rule.webhook_id)
            else:
                recent = db.scalars(select(Run.status).where(Run.source == run.source,
                    Run.status.in_(['success', 'failed', 'partial'])).order_by(Run.id.desc()).limit(rule.threshold)).all()
                if len(recent) == rule.threshold and all(s == 'failed' for s in recent):
                    open_incident(db, key, run.source, f'Falhas recorrentes em {run.source}',
                                  f'{rule.threshold} execuções consecutivas falharam. Última: #{run.id}.', rule)
        if rule.kind == 'schema_change' and run.error_code == 'schema_change':
            open_incident(db, f'schema:{rule.id}:{run.source}', run.source,
                          f'Contrato alterado em {run.source}', run.message, rule)
        if rule.kind == 'new_publication' and run.status in {'success', 'partial'}:
            for publication in new_publications:
                text = (publication.title + ' ' + ' '.join(t['name'] for t in publication.topics)).casefold()
                if not topic_matches(publication,rule.topic):
                    continue
                add_event(db, f'publication:{rule.id}:{publication.id}', 'publication', publication.title,
                    {'publication_id': publication.id, 'doi': publication.doi, 'source': run.source,
                     'rule': rule.name, 'year': publication.year}, rule.webhook_id)
        if rule.kind == 'dataset_changed':
            for dataset in changed_datasets:
                add_event(db, f'dataset:{rule.id}:{dataset.id}:{dataset.fingerprint}', 'dataset',
                          f'Conjunto atualizado: {dataset.title}', {'dataset_id': dataset.id, 'url': dataset.url}, rule.webhook_id)


def evaluate_stale(db):
    for rule in db.scalars(select(Rule).where(Rule.enabled.is_(True), Rule.kind == 'stale_source')):
        sources = [rule.source] if rule.source != 'all' else ['ror', 'openalex', 'crossref', 'orcid', 'ufrn']
        for source in sources:
            latest = db.scalar(select(Run).where(Run.source == source, Run.status == 'success').order_by(Run.id.desc()))
            if not latest:
                latest = db.scalar(select(Run).where(Run.source == source).order_by(Run.id))
            if not latest:
                continue
            key = f'stale:{rule.id}:{source}'
            stale = utcnow() - aware(latest.finished_at or latest.created_at) > timedelta(minutes=rule.threshold)
            if stale:
                open_incident(db, key, source, f'Dados desatualizados: {source}',
                              f'Sem coleta completa bem-sucedida há mais de {rule.threshold} minutos.', rule)
            else:
                incident = db.scalar(select(Incident).where(Incident.active_key == key))
                if incident:
                    incident.status, incident.active_key, incident.resolved_at = 'resolved', None, utcnow()


def evaluate_digest(db, now=None):
    from zoneinfo import ZoneInfo
    now = now or utcnow()
    local = now.astimezone(ZoneInfo('America/Sao_Paulo'))
    if local.weekday() != 0 or local.hour < 9:
        return
    cutoff = now - timedelta(days=7)
    works = db.scalars(select(Publication).where(Publication.fetched_at >= cutoff)).all()
    for rule in db.scalars(select(Rule).where(Rule.enabled.is_(True), Rule.kind == 'weekly_digest')):
        selected = [w for w in works if topic_matches(w,rule.topic)]
        iso_year, iso_week, _ = local.isocalendar()
        add_event(db, f'digest:{rule.id}:{iso_year}:{iso_week}', 'digest', f'Resumo semanal: {rule.name}',
                  {'period_from': cutoff.isoformat(), 'period_to': now.isoformat(), 'count': len(selected),
                   'scope': 'Publicações coletadas ou atualizadas; não necessariamente publicadas no período.',
                   'publications': [{'id': w.id, 'title': w.title, 'doi': w.doi} for w in selected[:50]]}, rule.webhook_id)


def deliver_pending(only_id=None):
    """At-least-once delivery: receivers must deduplicate Idempotency-Key."""
    with Session() as db:
        expired = db.scalars(select(Delivery).where(Delivery.status == 'sending', Delivery.next_at < utcnow())).all()
        for delivery in expired:
            delivery.status = 'pending' if delivery.attempts < 5 else 'dead'
        db.commit()
        query=select(Delivery.id).where(Delivery.status == 'pending', Delivery.next_at <= utcnow())
        if only_id is not None:query=query.where(Delivery.id==only_id)
        ids = db.scalars(query.limit(20)).all()
    for identifier in ids:
        with Session() as db:
            claimed = db.execute(update(Delivery).where(Delivery.id == identifier, Delivery.status == 'pending').values(
                status='sending', attempts=Delivery.attempts + 1, next_at=utcnow() + timedelta(minutes=5)))
            db.commit()
            if not claimed.rowcount:
                continue
            delivery = db.get(Delivery, identifier)
            webhook, event = db.get(Webhook, delivery.webhook_id), db.get(Event, delivery.event_id)
            if not webhook or not webhook.enabled:
                delivery.status, delivery.message = 'dead', 'Webhook desativado.'
                db.commit()
                continue
            body = json.dumps({'id': event.id, 'kind': event.kind, 'title': event.title, 'payload': event.payload},
                              sort_keys=True, ensure_ascii=False).encode()
            url, attempts = webhook.url, delivery.attempts
        try:
            secret = os.getenv('WEBHOOK_SIGNING_SECRET', '')
            if not secret:
                raise ValueError('Configure WEBHOOK_SIGNING_SECRET no servidor.')
            validate_public_destination(url)
            signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
                response = client.post(url, content=body, headers={'Content-Type': 'application/json',
                    'X-CampusOps-Signature': f'sha256={signature}', 'Idempotency-Key': f'campusops-{identifier}'})
                response.raise_for_status()
                if not 200 <= response.status_code < 300:
                    raise ValueError('O destino não retornou confirmação 2xx.')
            status, message = 'delivered', f'HTTP {response.status_code}'
        except (httpx.HTTPError, ValueError, OSError) as exc:
            status, message = ('dead' if attempts >= 5 else 'pending'), type(exc).__name__
        with Session() as db:
            delivery = db.get(Delivery, identifier)
            delivery.status, delivery.message = status, message
            delivery.next_at = utcnow() + timedelta(seconds=min(3600, 30 * 2 ** attempts))
            db.commit()
