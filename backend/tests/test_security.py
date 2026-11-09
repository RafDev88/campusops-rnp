from sqlalchemy import select

from app.domain import SessionToken, User


def test_setup_login_logout_and_hashed_secrets(client, database):
    assert client.get('/api/dashboard').status_code == 401
    assert client.get('/api/auth/status').json()['setup_required'] is True
    credentials = {'username': 'admin', 'password': 'test-password-12345'}
    response = client.post('/api/auth/setup', json=credentials)
    assert response.status_code == 200
    assert 'HttpOnly' in response.headers['set-cookie']
    assert client.post('/api/auth/setup', json=credentials).status_code == 409
    with database[0]() as db:
        assert db.scalar(select(User)).password_hash.startswith('$argon2')
        assert db.scalar(select(SessionToken)).token_hash != client.cookies.get('campusops_session')
    assert client.post('/api/auth/logout').status_code == 200
    assert client.get('/api/dashboard').status_code == 401
    assert client.post('/api/auth/login', json=credentials).status_code == 200


def test_viewer_cannot_mutate_and_disabled_session_is_rejected(authenticated):
    client = authenticated
    admin_cookie = client.cookies.get('campusops_session')
    response = client.post('/api/users', json={'username': 'viewer', 'password': 'viewer-password-123', 'role': 'viewer'})
    assert response.status_code == 201
    identifier = response.json()['id']
    client.post('/api/auth/logout')
    assert client.post('/api/auth/login', json={'username': 'viewer', 'password': 'viewer-password-123'}).status_code == 200
    viewer_cookie = client.cookies.get('campusops_session')
    assert client.get('/api/dashboard').status_code == 200
    assert client.post('/api/sync', json={'source': 'ror'}).status_code == 403
    assert client.get('/api/users').status_code == 403
    client.post('/api/auth/login', json={'username': 'admin', 'password': 'test-password-12345'})
    assert client.patch(f'/api/users/{identifier}', json={'enabled': False}).status_code == 200
    client.cookies.set('campusops_session', viewer_cookie)
    assert client.get('/api/dashboard').status_code == 401


def test_missing_csrf_and_login_rate_limit(client):
    assert client.post('/api/auth/setup', headers={'X-CampusOps': ''}, json={'username': 'admin', 'password': 'password-12345'}).status_code == 403
    credentials = {'username': 'missing', 'password': 'bad-password-123'}
    for _ in range(10):
        assert client.post('/api/auth/login', json=credentials).status_code == 401
    assert client.post('/api/auth/login', json=credentials).status_code == 429


def test_operator_cannot_register_external_destination(authenticated):
    authenticated.post('/api/users', json={'username': 'operator', 'password': 'operator-password-123', 'role': 'operator'})
    authenticated.post('/api/auth/login', json={'username': 'operator', 'password': 'operator-password-123'})
    assert authenticated.post('/api/webhooks', json={'name': 'External', 'url': 'https://example.com'}).status_code == 403
