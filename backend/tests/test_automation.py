import hashlib
import hmac
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app import automation
from app.domain import Delivery, Event, Incident, Rule, Run, Schedule, Webhook, utcnow


def test_private_and_non_allowlisted_webhook_destinations_are_rejected(monkeypatch):
    monkeypatch.setenv('WEBHOOK_ALLOWED_HOSTS', 'example.com,localhost')
    for url in ['http://example.com/events', 'https://evil.com/events', 'https://user:pass@example.com/events', 'https://example.com:8443/events']:
        with pytest.raises(ValueError):
            automation.webhook_target(url)
    monkeypatch.setattr(automation.socket, 'getaddrinfo', lambda *a, **kw: [(2, 1, 6, '', ('127.0.0.1', 443))])
    with pytest.raises(ValueError, match='públicos'):
        automation.validate_public_destination('https://localhost/events')


def test_webhook_outbox_signs_delivery_and_retries_without_new_event(database, monkeypatch):
    factory, _ = database
    monkeypatch.setenv('WEBHOOK_SIGNING_SECRET', 'test-signing-secret')
    monkeypatch.setattr(automation, 'validate_public_destination', lambda _: None)
    sent = []
    def handler(request):
        sent.append(request)
        expected = 'sha256=' + hmac.new(b'test-signing-secret', request.content, hashlib.sha256).hexdigest()
        assert request.headers['X-CampusOps-Signature'] == expected
        return httpx.Response(503 if len(sent) == 1 else 204)
    original_client = httpx.Client
    monkeypatch.setattr(automation.httpx, 'Client', lambda **kw: original_client(transport=httpx.MockTransport(handler), **kw))
    with factory() as db:
        hook = Webhook(name='Test', url='https://example.com/events')
        db.add(hook)
        db.flush()
        event = automation.add_event(db, 'unique-event', 'test', 'Test event', {}, hook.id)
        automation.add_event(db, 'unique-event', 'test', 'Test event', {}, hook.id)
        db.commit()
    automation.deliver_pending()
    with factory() as db:
        delivery = db.scalar(select(Delivery))
        assert delivery.status == 'pending' and delivery.attempts == 1
        delivery.next_at = utcnow() - timedelta(seconds=1)
        db.commit()
    automation.deliver_pending()
    with factory() as db:
        delivery = db.scalar(select(Delivery))
        assert delivery.status == 'delivered' and delivery.attempts == 2
        assert sent[0].headers['Idempotency-Key'] == sent[1].headers['Idempotency-Key']


def test_stale_source_incident_and_recovery(database):
    factory, _ = database
    with factory() as db:
        db.add(Rule(name='Stale', kind='stale_source', source='ror', threshold=60))
        db.add(Run(source='ror', status='success', created_at=utcnow() - timedelta(days=2), finished_at=utcnow() - timedelta(days=2)))
        db.commit()
        automation.evaluate_stale(db)
        db.commit()
        assert db.scalar(select(Incident)).status == 'open'
        db.add(Run(source='ror', status='success', finished_at=utcnow()))
        db.commit()
        automation.evaluate_stale(db)
        db.commit()
        assert db.scalar(select(Incident)).status == 'resolved'


def test_scheduler_advances_due_schedule_and_recovers_interrupted_run(database):
    from app.operations import tick
    factory, published = database
    with factory() as db:
        schedule = Schedule(source='ror', interval_minutes=30, params={})
        db.add(schedule)
        db.add(Run(source='ufrn', status='running', active_key='ufrn', created_at=utcnow() - timedelta(hours=3)))
        db.commit()
    tick()
    with factory() as db:
        assert db.scalar(select(Schedule)).next_at > utcnow().replace(tzinfo=None)
        assert db.scalar(select(Run).where(Run.source == 'ufrn')).error_code == 'interrupted'
        assert db.scalar(select(Run).where(Run.source == 'ror')).status == 'queued'
    assert published


def test_weekly_digest_is_emitted_once_per_week(database):
    from datetime import datetime, timezone
    factory, _ = database
    monday = datetime(2026, 11, 9, 13, 0, tzinfo=timezone.utc)
    with factory() as db:
        db.add(Rule(name='Weekly research', kind='weekly_digest', source='openalex'))
        db.commit()
        automation.evaluate_digest(db, now=monday)
        automation.evaluate_digest(db, now=monday + timedelta(minutes=10))
        db.commit()
        assert len(db.scalars(select(Event).where(Event.kind == 'digest')).all()) == 1
