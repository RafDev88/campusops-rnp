from fastapi.testclient import TestClient
from sqlalchemy import select

from app.domain import Run, User, SessionToken, utcnow
from app.orchestration_models import CalendarSchedule, Report
from app.security import COOKIE


def test_catalog_never_invents_complete_coverage(authenticated, database):
    with database[0]() as db:
        db.add(Run(source='ror', status='partial', finished_at=utcnow(), details={'complete':False}))
        db.add(Run(source='crossref', status='success', finished_at=utcnow()))
        db.commit()
    sources = {item['source']: item for item in authenticated.get('/api/catalog-status').json()['sources']}
    assert sources['ror']['coverage'] == 'partial'
    assert sources['crossref']['coverage'] == 'unknown'
    assert sources['openalex']['status'] == 'not_collected'


def test_automation_summary_does_not_leak_private_reports(authenticated, database):
    with database[0]() as db:
        other = User(username='other', password_hash='not-a-password', role='viewer')
        db.add(other); db.flush()
        db.add(Report(owner_id=other.id, name='PRIVATE OTHER REPORT', filters={}))
        db.add(CalendarSchedule(owner_id=other.id, name='PRIVATE OTHER AGENDA', target='report', cron='0 0 * * *', timezone='UTC', next_at=utcnow()))
        db.add(Run(source='openalex', status='failed', error_code='credentials'))
        db.commit()
    response = authenticated.get('/api/automation-overview')
    assert response.status_code == 200
    assert 'PRIVATE OTHER' not in response.text
    assert response.json()['failed_runs'] == 1
    assert 'credencial' in response.json()['items'][0]['action']


def test_errors_correlate_without_echoing_sensitive_input(client):
    response = client.post('/api/auth/login', json={'username':'?', 'password':'tiny-secret'})
    assert response.status_code == 422
    assert 'tiny-secret' not in response.text
    assert response.json()['code'] == 'validation_error'
    assert response.json()['request_id'] == response.headers['X-Request-ID']
    csrf = client.post('/api/auth/login', headers={'X-CampusOps':''}, json={})
    assert csrf.status_code == 403
    assert csrf.json()['request_id'] == csrf.headers['X-Request-ID']


def test_internal_error_is_sanitized_and_correlated(authenticated, monkeypatch):
    from app import read_api
    def unavailable():
        raise RuntimeError('private-database-details')
    monkeypatch.setattr(read_api, 'Session', unavailable)
    response = authenticated.get('/api/dashboard')
    assert response.status_code == 500
    assert response.json()['code'] == 'internal_error'
    assert response.json()['request_id'] == response.headers['X-Request-ID']
    assert 'private-database-details' not in response.text


def test_password_change_rotates_sessions_and_rejects_old_password(authenticated, database):
    old = authenticated.cookies.get(COOKIE)
    response = authenticated.post('/api/account/password', json={'current_password':'wrong-password', 'new_password':'a-new-password-123'})
    assert response.status_code == 400
    assert authenticated.get('/api/auth/me').status_code == 200
    response = authenticated.post('/api/account/password', json={'current_password':'test-password-12345', 'new_password':'a-new-password-123'})
    assert response.status_code == 200
    assert authenticated.cookies.get(COOKIE) != old
    assert authenticated.get('/api/auth/me').status_code == 200
    with database[0]() as db:
        assert len(db.scalars(select(SessionToken)).all()) == 1
    authenticated.post('/api/auth/logout')
    assert authenticated.post('/api/auth/login', json={'username':'admin','password':'test-password-12345'}).status_code == 401
    assert authenticated.post('/api/auth/login', json={'username':'admin','password':'a-new-password-123'}).status_code == 200


def test_sessions_are_owned_and_revocation_invalidates_cookie(authenticated, database):
    old = authenticated.cookies.get(COOKIE)
    old_id = authenticated.get('/api/account/sessions').json()['items'][0]['id']
    authenticated.post('/api/auth/login', json={'username':'admin','password':'test-password-12345'})
    assert len(authenticated.get('/api/account/sessions').json()['items']) == 2
    assert authenticated.delete('/api/account/sessions/' + old_id).status_code == 200
    assert len(authenticated.get('/api/account/sessions').json()['items']) == 1
    admin_id = authenticated.get('/api/account/sessions').json()['items'][0]['id']
    from app.main import app
    with TestClient(app, cookies={COOKIE:old}) as other:
        assert other.get('/api/auth/me').status_code == 401
    authenticated.post('/api/users', json={'username':'viewer','password':'viewer-password-123','role':'viewer'})
    authenticated.post('/api/auth/login', json={'username':'viewer','password':'viewer-password-123'})
    assert authenticated.delete('/api/account/sessions/' + admin_id).status_code == 404
