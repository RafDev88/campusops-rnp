import json
import socket
import ssl
from datetime import timedelta
import pytest
from sqlalchemy import func,select
from app import monitor_models as m
from app.monitor_network import normalize_url,resolve_public,request_once,probe,ProbeError,API_ENDPOINTS,MAX_BODY
from app.monitor_inventory import config,sync_inventory
from app.monitor_service import enqueue_check,perform_check,monitor_tick,reserve
from app.domain import Publication,Incident,Event,utcnow


def response(code=200,body=b'',headers=None,days=90):
    return {'status':code,'headers':headers or {},'body':body,'timings':{'dns_ms':1,'tls_ms':2,'http_ms':3},
            'tls':{'days_remaining':days,'expires_at':(utcnow()+timedelta(days=days)).isoformat(),'issuer':'Test CA','version':'TLSv1.3'}}


@pytest.mark.parametrize('url',['http://127.0.0.1/','http://[::1]/','https://10.0.0.1/','https://169.254.169.254/','https://239.1.1.1/','https://[ff02::1]/','https://localhost/','https://server.internal/','ftp://example.org/file','https://user:password@example.org/','https://example.org:8443/','https://example.org/?api_key=secret'])
def test_monitor_rejects_private_destinations_and_credentials(url):
    with pytest.raises(ValueError):normalize_url(url)


def test_canonical_urls_preserve_query_semantics():
    assert normalize_url('https://EXAMPLE.org:443/paper?a=1&b=2#section')=='https://example.org/paper?a=1&b=2'
    assert normalize_url('http://example.org/path').startswith('http:')


def test_dns_checks_every_address_before_connecting(monkeypatch):
    monkeypatch.setattr(socket,'getaddrinfo',lambda *a,**kw:[(2,1,6,'',('9.9.9.9',443)),(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(ProbeError) as error:resolve_public('example.org',443)
    assert error.value.code=='blocked'
    def unavailable(*a,**kw):raise socket.gaierror()
    monkeypatch.setattr(socket,'getaddrinfo',unavailable)
    with pytest.raises(ProbeError) as error:resolve_public('example.org',443)
    assert error.value.code=='dns_error'


def test_http_connection_pins_validated_ip_and_bounds_body(monkeypatch):
    import app.monitor_network as network
    seen={}
    monkeypatch.setattr(network,'resolve_public',lambda host,port:'9.9.9.9')
    class FakeConnection:
        timings={'tls_ms':2};tls={}
        def __init__(self,host,ip,secure,timeout,context):
            seen.update(host=host,ip=ip,verify=context.verify_mode,hostname=context.check_hostname)
        def connect(self):pass
        def request(self,method,path,headers):seen['method']=method
        def getresponse(self):return self
        status=200
        def read(self,limit):seen['limit']=limit;return b'{}'
        def getheaders(self):return []
        def close(self):seen['closed']=True
    monkeypatch.setattr(network,'PinnedConnection',FakeConnection)
    request_once('https://example.org/path','GET',{},lambda host:None,5)
    assert seen=={'host':'example.org','ip':'9.9.9.9','verify':ssl.CERT_REQUIRED,'hostname':True,'method':'GET','limit':MAX_BODY+1,'closed':True}


def test_head_fallback_and_redirect_are_bounded():
    seen=[]
    def requester(url,method,*args):
        seen.append((url,method))
        if len(seen)==1:return response(405)
        if len(seen)==2:return response(302,headers={'location':'https://other.example.org/paper'})
        return response()
    result=probe('https://example.org/paper',requester=requester)
    assert result['ok'] and len(seen)==3
    assert seen[0][1]=='HEAD' and seen[1][1]=='GET' and seen[2][1]=='GET'
    assert len(result['redirects'])==1


def test_redirect_loop_downgrade_and_private_redirect_are_not_followed():
    for destination,outcome in [('https://example.org/','redirect_error'),('http://example.org/','redirect_error'),('http://127.0.0.1/','blocked')]:
        result=probe('https://example.org/',requester=lambda *a:response(302,headers={'location':destination}))
        assert not result['ok'] and result['outcome']==outcome


def test_provider_credentials_never_follow_cross_host_redirects(monkeypatch):
    monkeypatch.setenv('OPENALEX_API_KEY','qa-only-token')
    seen=[]
    def requester(url,method,headers,*args):
        seen.append(dict(headers))
        return response(302,headers={'location':'https://example.org/result'}) if len(seen)==1 else response(body=json.dumps({'results':[],'meta':{}}).encode())
    result=probe(API_ENDPOINTS['openalex'][1],source='openalex',kind='api',requester=requester)
    assert result['ok']
    assert seen[0]['Authorization']=='Bearer qa-only-token' and 'Authorization' not in seen[1]


@pytest.mark.parametrize('code,outcome',[(401,'auth_required'),(403,'forbidden'),(404,'not_found'),(429,'rate_limited'),(503,'server_error')])
def test_http_statuses_have_distinct_diagnoses(code,outcome):
    result=probe('https://example.org/',requester=lambda *a:response(code,headers={'retry-after':'3600'}))
    assert result['outcome']==outcome and not result['ok']
    if code==429:assert result['retry_after']==3600


def test_html_error_page_is_not_a_healthy_api():
    result=probe(API_ENDPOINTS['crossref'][1],source='crossref',kind='api',requester=lambda *a:response(body=b'<html>Error</html>'))
    assert result['outcome']=='invalid_content' and not result['ok']
    result=probe(API_ENDPOINTS['crossref'][1],source='crossref',kind='api',requester=lambda *a:response(body=b'{"message":{"items":[]}}'))
    assert result['ok']


def test_html_login_is_not_a_healthy_pdf():
    result=probe('https://example.org/download',expected_type='pdf',requester=lambda *a:response(headers={'content-type':'text/html'}))
    assert result['outcome']=='invalid_content' and not result['ok']


def test_expiring_certificate_in_redirect_path_is_not_hidden():
    def requester(url,*args):
        return response(302,headers={'location':'https://other.example.org/'},days=5) if 'other.' not in url else response(days=90)
    result=probe('https://example.org/',requester=requester)
    assert result['outcome']=='tls_expiring' and result['ok']
    assert result['tls']['host']=='example.org' and result['tls']['days_remaining']==5
    assert len(result['tls']['certificates'])==2


def test_tls_validation_error_and_timeout_remain_failures():
    def invalid(*args):
        error=ssl.SSLCertVerificationError(1,'expired');error.verify_code=10;raise error
    result=probe('https://example.org/',requester=invalid)
    assert result['outcome']=='tls_error' and not result['ok'] and result['tls']['verify_code']==10
    def timeout(*args):raise TimeoutError()
    assert probe('https://example.org/',requester=timeout)['outcome']=='timeout'


def target(factory):
    from app.monitor_network import url_key
    with factory() as db:
        config(db)
        row=m.MonitorTarget(name='Test endpoint',url='https://example.org/',url_hash=url_key('https://example.org/'),host='example.org',kind='manual',failure_threshold=2)
        db.add(row);db.commit();return row.id


def run(factory,identifier,ok=True,outcome=None,days=90):
    check_id=enqueue_check(identifier)
    perform_check(check_id,lambda *a,**kw:{'ok':ok,'outcome':outcome or ('available' if ok else 'timeout'),'message':'QA check','http_status':200 if ok else None,'tls':{'days_remaining':days}})
    return check_id


def test_link_inventory_deduplicates_and_archives_without_deleting_history(authenticated,database):
    factory=database[0]
    with factory() as db:
        db.add_all([Publication(id=f'W{i}',openalex_id=f'W{i}',title=f'QA {i}',doi='10.1234/shared') for i in (1,2)])
        db.commit()
    first=sync_inventory('test');second=sync_inventory('test')
    assert first['created']==1 and second['created']==0
    with factory() as db:
        item=db.scalar(select(m.MonitorTarget).where(m.MonitorTarget.kind=='publication'))
        identifier=item.id
        assert db.scalar(select(func.count()).select_from(m.MonitorReference).where(m.MonitorReference.target_id==identifier))==2
    run(factory,identifier)
    with factory() as db:
        for work in db.scalars(select(Publication)):work.doi=None
        db.commit()
    sync_inventory()
    with factory() as db:
        assert db.get(m.MonitorTarget,identifier).archived
        assert db.scalar(select(func.count()).select_from(m.MonitorCheck).where(m.MonitorCheck.target_id==identifier))==1
    restored=authenticated.post('/api/monitors',json={'name':'Keep this public link','url':'https://doi.org/10.1234/shared'})
    assert restored.status_code==201 and restored.json()['id']==identifier
    assert not restored.json()['archived'] and not restored.json()['managed']


def test_duplicate_deliveries_and_manual_cooldown(database):
    factory=database[0];identifier=target(factory)
    first=enqueue_check(identifier,manual=True)
    assert enqueue_check(identifier,manual=True)==first
    calls=[]
    def prober(*a,**kw):calls.append(1);return {'ok':True,'outcome':'available','message':'OK'}
    perform_check(first,prober);perform_check(first,prober)
    assert calls==[1]
    with pytest.raises(ValueError):enqueue_check(identifier,manual=True)


def test_incident_is_deduplicated_and_recovers_after_two_successes(database):
    factory=database[0];identifier=target(factory)
    for _ in range(3):run(factory,identifier,False)
    with factory() as db:assert db.scalar(select(func.count()).select_from(Incident))==1
    run(factory,identifier)
    with factory() as db:assert db.scalar(select(Incident)).status=='open'
    run(factory,identifier);run(factory,identifier)
    with factory() as db:
        assert db.scalar(select(Incident)).status=='resolved'
        assert db.scalar(select(func.count()).select_from(Event).where(Event.kind=='recovery'))==1


def test_certificate_incident_does_not_wait_for_http_success(database):
    factory=database[0];identifier=target(factory)
    run(factory,identifier,False,'auth_required',days=5)
    with factory() as db:assert db.scalar(select(Incident)).active_key==f'monitor:certificate:{identifier}'
    run(factory,identifier,True,days=90)
    with factory() as db:assert db.scalar(select(Incident)).status=='resolved'


def test_rate_limits_and_deferred_checks_do_not_report_downtime(database):
    factory=database[0];identifier=target(factory)
    with factory() as db:config(db).per_host_minute=1;db.commit()
    reserve('example.org')
    with pytest.raises(ProbeError) as error:reserve('example.org')
    assert error.value.code=='deferred'
    first=enqueue_check(identifier)
    perform_check(first,lambda *a,**kw:{'outcome':'deferred','ok':False,'message':'Quota','retry_after':60})
    with factory() as db:
        assert db.get(m.MonitorTarget,identifier).failures==0
        assert db.get(m.MonitorTarget,identifier).status=='not_checked'
        assert db.get(m.MonitorCheck,first).ok is None


def test_monitor_respects_shared_source_budget(database):
    from app.orchestration_models import SourcePolicy,Usage
    factory=database[0]
    with factory() as db:config(db);db.get(SourcePolicy,'openalex').per_minute=1;db.commit()
    reserve('api.openalex.org','openalex')
    with pytest.raises(ProbeError):reserve('api.openalex.org','openalex')
    with factory() as db:
        assert db.get(Usage,('openalex',utcnow().strftime('minute:%Y-%m-%dT%H:%M'))).count==1


def test_paused_automatic_check_is_skipped_but_manual_is_possible(database):
    factory=database[0];identifier=target(factory);check_id=enqueue_check(identifier)
    with factory() as db:db.get(m.MonitorTarget,identifier).enabled=False;db.commit()
    calls=[]
    perform_check(check_id,lambda *a,**kw:calls.append(1))
    assert not calls
    with factory() as db:
        row=db.get(m.MonitorCheck,check_id);assert row.outcome=='skipped';row.created_at=utcnow()-timedelta(minutes=2);db.commit()
    second=enqueue_check(identifier,manual=True)
    perform_check(second,lambda *a,**kw:{'outcome':'available','ok':True,'message':'OK'})
    with factory() as db:assert db.get(m.MonitorCheck,second).ok


def test_stale_worker_is_fenced_and_requeued(database):
    factory=database[0];identifier=target(factory);check_id=enqueue_check(identifier)
    with factory() as db:
        row=db.get(m.MonitorCheck,check_id);row.state='running';row.started_at=utcnow()-timedelta(minutes=4);db.commit()
    monitor_tick()
    with factory() as db:
        row=db.get(m.MonitorCheck,check_id);assert row.state=='completed' and row.active_key is None and row.ok is None


def test_late_result_cannot_overwrite_interrupted_check(database):
    factory=database[0];identifier=target(factory);check_id=enqueue_check(identifier)
    def delayed_probe(*a,**kw):
        with factory() as db:
            db.get(m.MonitorCheck,check_id).started_at=utcnow()-timedelta(minutes=4);db.commit()
        monitor_tick()
        return {'ok':True,'outcome':'available','message':'Late response'}
    perform_check(check_id,delayed_probe)
    with factory() as db:
        assert db.get(m.MonitorCheck,check_id).outcome=='interrupted'
        assert db.get(m.MonitorTarget,identifier).status=='not_checked'


def test_monitor_api_permissions_history_and_warning_filter(authenticated,database):
    created=authenticated.post('/api/monitors',json={'name':'Public reference','url':'https://example.org/'});assert created.status_code==201,created.text
    identifier=created.json()['id'];run(database[0],identifier,True,'tls_expiring',days=5)
    assert authenticated.get('/api/monitors?problems=true').json()['total']==1
    detail=authenticated.get(f'/api/monitors/{identifier}').json();assert detail['checks']['total']==1
    new_check=enqueue_check(identifier)
    assert authenticated.get('/api/monitors?status=queued').json()['total']==1
    assert authenticated.post('/api/monitors',json={'name':'Blocked','url':'http://127.0.0.1/'}).status_code==422
    assert authenticated.post('/api/users',json={'username':'monitor-viewer','password':'test-viewer-password','role':'viewer'}).status_code==201
    assert authenticated.post('/api/auth/login',json={'username':'monitor-viewer','password':'test-viewer-password'}).status_code==200
    assert authenticated.get('/api/monitors').status_code==200
    assert authenticated.post(f'/api/monitors/{identifier}/check').status_code==403
    assert authenticated.post('/api/monitors/discover').status_code==403
    assert authenticated.put('/api/monitor-settings',json={}).status_code==403
