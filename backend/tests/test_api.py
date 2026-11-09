from app.domain import Publication
from app.models import Institution


def test_catalog_pagination_watch_and_queue(authenticated, database):
    client = authenticated
    with database[0]() as db:
        db.add_all([Institution(id=f'https://ror.org/{i}', name=f'Universidade {i:02}', country='Brazil') for i in range(30)])
        db.commit()
    first = client.get('/api/institutions').json()
    second = client.get('/api/institutions?offset=25').json()
    assert first['total'] == 30 and len(first['items']) == 25 and len(second['items']) == 5
    assert client.post('/api/watch', json={'institution_id': first['items'][0]['id'], 'watched': True}).status_code == 200
    assert client.get('/api/institutions?watched=true').json()['total'] == 1
    response = client.post('/api/sync', json={'source': 'ror'})
    assert response.status_code == 202
    assert client.post('/api/sync', json={'source': 'ror'}).status_code == 409
    assert client.get('/api/runs').json()['items'][0]['status'] == 'queued'


def test_export_escapes_spreadsheet_formulas(authenticated, database):
    with database[0]() as db:
        db.add(Publication(id='test', openalex_id='test', title='=1+1'))
        db.commit()
    response = authenticated.get('/api/exports/publications.csv')
    assert response.status_code == 200
    assert "'=1+1" in response.text


def test_invalid_source_payload_and_invalid_orcid_are_rejected(authenticated):
    assert authenticated.post('/api/sync', json={'source': 'unknown'}).status_code == 422
    assert authenticated.post('/api/sync', json={'source': 'orcid', 'orcid': 'invalid'}).status_code == 422
    assert authenticated.post('/api/sync', json={'source': 'ror', 'max_pages': 501}).status_code == 422


def test_admin_metrics_and_user_actions_are_audited(authenticated):
    assert 'campusops_runs_total' in authenticated.get('/api/metrics').text
    authenticated.post('/api/rules', json={'name': 'Network radar', 'kind': 'new_publication', 'topic': 'networks'})
    assert any(row['action'] == 'rule.created' for row in authenticated.get('/api/audit').json())
