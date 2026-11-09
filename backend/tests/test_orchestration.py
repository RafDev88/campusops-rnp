import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import func, select

from app import orchestration_models as m
from app.automation_tick import automation_tick
from app.calendar_jobs import dispatch_calendar, next_occurrence, validate_calendar
from app.domain import Event, Publication, Run, User, utcnow
from app.job_runtime import JobNetwork, control, handle_failure, set_stage
from app.operations import enqueue, perform
from app.orchestration import advance_workflows, start_workflow, workflow_control
from app.providers import SourceError
from app.reports import render_report
from test_operations import FakeProvider


def test_checkpoint_survives_pause_without_repeating_http(database):
    factory, _ = database
    identifier = enqueue('ror', {})
    requests = []
    async def response(request):
        requests.append(str(request.url))
        return httpx.Response(200, json={'results': [1]})
    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
            net = JobNetwork(identifier, client)
            assert await net.get('https://example.org/organizations') == {'results': [1]}
            control(identifier, 'pause', 'test')
            with pytest.raises(SourceError, match='Pausa'):
                await net.get('https://example.org/organizations')
            control(identifier, 'resume', 'test')
            assert await JobNetwork(identifier, client).get('https://example.org/organizations') == {'results': [1]}
    asyncio.run(scenario())
    assert len(requests) == 1
    with factory() as db:
        assert db.get(Run, identifier).http_calls == 1
        assert db.get(m.Runtime, identifier).pages == 1


def test_control_before_apply_and_exclusive_paused_source(database):
    factory, _ = database
    identifier = enqueue('ror', {})
    control(identifier, 'pause', 'test')
    with pytest.raises(ValueError):
        enqueue('ror', {})
    with pytest.raises(SourceError):
        set_stage(identifier, 'applying')
    control(identifier, 'cancel', 'test')
    assert enqueue('ror', {}) != identifier


def test_execution_retry_and_due_dispatch(database):
    factory, published = database
    with factory() as db:
        db.get(m.SourcePolicy, 'ror').auto_retries = 1
        db.commit()
    identifier = enqueue('ror', {})
    broken = FakeProvider()
    broken.fail = True
    asyncio.run(perform(identifier, broken))
    with factory() as db:
        assert db.get(Run, identifier).status == 'retry_wait'
        state = db.get(m.Runtime, identifier)
        assert state.retries == 1
        state.next_at = utcnow() - timedelta(seconds=1)
        db.commit()
    automation_tick()
    assert published.count(identifier) >= 2
    asyncio.run(perform(identifier, FakeProvider()))
    with factory() as db:
        assert db.get(Run, identifier).status == 'success'
        assert db.get(Run, identifier).error_code == ''


def test_schema_failure_is_not_automatically_retried(database):
    factory, _ = database
    identifier = enqueue('ror', {})
    class Broken(FakeProvider):
        async def ror(self, params):
            raise SourceError('schema_change', 'Contrato mudou')
    asyncio.run(perform(identifier, Broken()))
    with factory() as db:
        assert db.get(Run, identifier).status == 'failed'
        assert db.scalar(select(m.Review)).entity_id == 'schema'


def test_request_policy_stops_before_external_call(database):
    factory, _ = database
    identifier = enqueue('ror', {})
    with factory() as db:
        db.get(m.SourcePolicy, 'ror').per_run = 1
        db.commit()
    async def scenario():
        net = JobNetwork(identifier)
        await net.before_request()
        with pytest.raises(SourceError) as error:
            await net.before_request()
        assert error.value.code == 'budget'
    asyncio.run(scenario())
    with factory() as db:
        assert db.get(Run, identifier).http_calls == 1


def test_lost_worker_is_fenced_before_applying_response(database):
    factory, _ = database
    identifier=enqueue('ror',{})
    with factory() as db:
        run=db.get(Run,identifier)
        run.status='running'
        state=db.get(m.Runtime,identifier)
        state.stage,state.lease,state.heartbeat='collecting','previous-attempt',utcnow()-timedelta(minutes=11)
        db.commit()
    automation_tick()
    with pytest.raises(SourceError) as error:
        set_stage(identifier,'applying','previous-attempt')
    assert error.value.code=='superseded'


def test_incremental_marker_advances_only_for_complete_scope(database):
    from app.domain import Profile
    factory,_=database
    asyncio.run(perform(enqueue('ror',{}),FakeProvider()))
    with factory() as db:
        db.get(Profile,'https://ror.org/01abcde12').watched=True
        db.commit()
    asyncio.run(perform(enqueue('openalex',{'year_from':2024}),FakeProvider()))
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.Watermark))==0
    seen=[]
    class Complete(FakeProvider):
        async def openalex(self,institution_id,params):
            seen.append(params['_since'])
            profile,works,details=await super().openalex(institution_id,params)
            return profile,works,{**details,'complete':True}
    for _ in range(2):asyncio.run(perform(enqueue('openalex',{'year_from':2024}),Complete()))
    assert seen[0]=='2024-01-01'
    assert seen[1]==(utcnow().date()-timedelta(days=2)).isoformat()


def test_single_rejected_doi_can_be_reprocessed(authenticated,database):
    factory,_=database
    with factory() as db:
        db.add(Publication(id='Wbad',openalex_id='Wbad',title='Original',doi='10.1000/missing'))
        db.commit()
    class Missing(FakeProvider):
        async def crossref(self,doi):raise SourceError('not_found','Missing')
    asyncio.run(perform(enqueue('crossref',{}),Missing()))
    pending=authenticated.get('/api/record-reviews?status=pending').json()['items'][0]
    response=authenticated.post(f"/api/record-reviews/{pending['id']}/retry")
    assert response.status_code==202,response.text
    identifier=response.json()['execution_id']
    with factory() as db:
        assert db.get(Run,identifier).params['publication_ids']==['Wbad']
    class Fixed(FakeProvider):
        async def crossref(self,doi):return {'DOI':doi,'title':['Fixed']}
    asyncio.run(perform(identifier,Fixed()))
    with factory() as db:
        assert db.get(m.Review,pending['id']).status=='resolved'


def test_calendar_timezone_and_minimum_gap():
    base = datetime(2026, 11, 8, 9, tzinfo=timezone.utc)
    assert next_occurrence('0 8 * * *', 'America/Sao_Paulo', base) == datetime(2026, 11, 8, 11, tzinfo=timezone.utc)
    for expression in ('* * * * *', '0,5,30 * * * *', 'bad'):
        with pytest.raises(ValueError):
            validate_calendar(expression, 'America/Sao_Paulo')
    with pytest.raises(ValueError):
        validate_calendar('0 8 * * *', 'Unknown/Zone')


def test_calendar_claim_is_idempotent_and_skips_busy_source(authenticated, database):
    factory, _ = database
    payload = {'name': 'Coleta diária', 'target': 'source', 'source': 'ror', 'cron': '0 8 * * *', 'timezone': 'America/Sao_Paulo'}
    created = authenticated.post('/api/calendar-schedules', json=payload)
    assert created.status_code == 201, created.text
    identifier = created.json()['id']
    with factory() as db:
        db.get(m.CalendarSchedule, identifier).next_at = utcnow() - timedelta(minutes=1)
        db.commit()
    dispatch_calendar()
    dispatch_calendar()
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(m.CalendarFire)) == 1
        assert db.scalar(select(m.CalendarFire)).status == 'dispatched'
        db.get(m.CalendarSchedule, identifier).next_at = utcnow() - timedelta(minutes=1)
        db.commit()
    dispatch_calendar()
    with factory() as db:
        assert db.scalars(select(m.CalendarFire).order_by(m.CalendarFire.id)).all()[-1].status == 'skipped'


def test_workflow_chains_sources_and_private_report(authenticated, database):
    factory, _ = database
    response = authenticated.post('/api/workflows', json={'name': 'Pipeline completo', 'steps': ['ror', 'ufrn', 'report']})
    assert response.status_code == 201, response.text
    identifier = start_workflow(response.json()['id'], 'test', 'unique-dispatch')
    assert start_workflow(response.json()['id'], 'test', 'unique-dispatch') == identifier
    with pytest.raises(ValueError):
        start_workflow(response.json()['id'], 'test')
    for source in ('ror', 'ufrn'):
        advance_workflows()
        with factory() as db:
            child_id = db.get(m.WorkflowRun, identifier).child_id
            assert db.get(Run, child_id).source == source
        asyncio.run(perform(child_id, FakeProvider()))
        advance_workflows()
    advance_workflows()
    with factory() as db:
        report_id = db.get(m.WorkflowRun, identifier).report_id
    render_report(report_id)
    advance_workflows()
    advance_workflows()
    with factory() as db:
        flow = db.get(m.WorkflowRun, identifier)
        assert flow.status == 'success' and len(flow.history) == 3
    assert authenticated.get(f'/api/reports/{report_id}/download').status_code == 200


def test_workflow_pause_cancel_and_busy_wait(authenticated, database):
    factory, _ = database
    busy = enqueue('ror', {})
    definition = authenticated.post('/api/workflows', json={'name': 'Pausável', 'steps': ['ror']}).json()['id']
    identifier = start_workflow(definition, 'test')
    advance_workflows()
    with factory() as db:
        assert db.get(m.WorkflowRun, identifier).status == 'waiting'
    control(busy, 'cancel', 'test')
    advance_workflows()
    workflow_control(identifier, 'pause', 'test')
    advance_workflows()
    with factory() as db:
        assert db.get(m.WorkflowRun, identifier).status == 'paused'
    workflow_control(identifier, 'resume', 'test')
    workflow_control(identifier, 'cancel', 'test')
    advance_workflows()
    with factory() as db:
        assert db.get(m.WorkflowRun, identifier).status == 'cancelled'
        assert db.get(Run, db.get(m.WorkflowRun, identifier).child_id).status == 'cancelled'


def test_report_filters_and_ownership(authenticated, database):
    factory, _ = database
    with factory() as db:
        db.add_all([Publication(id='W1', openalex_id='W1', title='Included', year=2025), Publication(id='W2', openalex_id='W2', title='Excluded', year=2020)])
        db.commit()
    template = authenticated.post('/api/report-templates', json={'name': 'Publicações recentes', 'filters': {'year_from': 2024}}).json()['id']
    identifier = authenticated.post(f'/api/report-templates/{template}/generate').json()['report_id']
    render_report(identifier)
    content = authenticated.get(f'/api/reports/{identifier}/download').text
    assert 'Included' in content and 'Excluded' not in content
    assert authenticated.post('/api/users', json={'username': 'other-viewer', 'password': 'another-password-12345', 'role': 'viewer'}).status_code == 201
    assert authenticated.post('/api/auth/login', json={'username': 'other-viewer', 'password': 'another-password-12345'}).status_code == 200
    assert authenticated.get('/api/reports').json() == []
    assert authenticated.get(f'/api/reports/{identifier}/download').status_code == 404
    assert authenticated.post(f'/api/report-templates/{template}/generate').status_code == 404
    assert authenticated.post('/api/workflows', json={'name': 'Forbidden', 'steps': ['ror']}).status_code == 403


def test_preview_has_no_effects_and_changes_have_before_after(authenticated, database):
    factory, _ = database
    response = authenticated.post('/api/rules/preview', json={'name': 'Prévia', 'kind': 'new_publication', 'source': 'openalex', 'topic': 'redes'})
    assert response.status_code == 200, response.text
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Event)) == 0
    first = enqueue('ror', {})
    asyncio.run(perform(first, FakeProvider()))
    class Changed(FakeProvider):
        async def ror(self, params):
            return [{'id': 'https://ror.org/01abcde12', 'name': 'Novo nome', 'country': 'Brazil', 'data': {}}], {'complete': True}
    second = enqueue('ror', {})
    asyncio.run(perform(second, Changed()))
    response = authenticated.get('/api/data-changes?source=ror').json()
    assert any(row['before'] == 'Universidade' and row['after'] == 'Novo nome' for row in response['items'])
