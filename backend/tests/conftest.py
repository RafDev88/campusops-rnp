import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def database(tmp_path, monkeypatch):
    from app import database as storage, domain, models, operations, automation, security, read_api, write_api, main, discovery_api, job_runtime, collector, orchestration, orchestration_api, reports, calendar_jobs, rule_preview, automation_tick
    engine = create_engine(f'sqlite:///{tmp_path / "operations.db"}', connect_args={'check_same_thread': False})
    storage.Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    for module in (storage, operations, automation, security, read_api, write_api, main, discovery_api, job_runtime, collector, orchestration, orchestration_api, reports, calendar_jobs, rule_preview, automation_tick):
        monkeypatch.setattr(module, 'Session', factory)
    monkeypatch.setattr(storage, 'engine', engine)
    monkeypatch.setattr(main, 'migrate', lambda: None)
    from app import catalog_api
    monkeypatch.setattr(catalog_api,'Session',factory)
    from app import reliability_api, account_api
    for module in (reliability_api, account_api): monkeypatch.setattr(module, 'Session', factory)
    from app import monitor_api,monitor_inventory,monitor_service
    for module in (monitor_api,monitor_inventory,monitor_service):monkeypatch.setattr(module,'Session',factory)
    from app.tasks import monitor_check
    monkeypatch.setattr(monitor_check,'delay',lambda identifier:None)
    from app.orchestration_models import SourcePolicy
    with factory() as db:
        db.add_all([SourcePolicy(source=s,auto_retries=0) for s in ['ror','openalex','crossref','orcid','ufrn']])
        db.commit()
    from app.tasks import execute_run
    published = []
    monkeypatch.setattr(execute_run, 'delay', lambda identifier: published.append(identifier))
    from app.tasks import generate_report,deliver_webhook
    monkeypatch.setattr(generate_report,'delay',lambda identifier:None)
    monkeypatch.setattr(deliver_webhook,'delay',lambda identifier:None)
    yield factory, published
    engine.dispose()


@pytest.fixture
def client(database):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, headers={'X-CampusOps': '1'}) as client:
        yield client


@pytest.fixture
def authenticated(client):
    response = client.post('/api/auth/setup', json={'username': 'admin', 'password': 'test-password-12345'})
    assert response.status_code == 200
    return client
