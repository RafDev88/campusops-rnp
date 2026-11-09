"""Run inside the API container: isolated PostgreSQL auth/migration smoke test."""
import os
import re
import secrets
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

original_url = make_url(os.environ['DATABASE_URL'])
database_name = 'campusops_qa_' + uuid4().hex
assert re.fullmatch(r'campusops_qa_[0-9a-f]{32}', database_name)
management = create_engine(original_url, isolation_level='AUTOCOMMIT')
with management.connect() as connection:
    connection.exec_driver_sql(f'CREATE DATABASE "{database_name}"')
try:
    os.environ['DATABASE_URL'] = original_url.set(database=database_name).render_as_string(hide_password=False)
    os.environ['REDIS_URL'] = 'memory://'
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import engine
    password = secrets.token_urlsafe(32)
    with TestClient(app, headers={'X-CampusOps': '1'}) as client:
        assert client.get('/api/dashboard').status_code == 401
        assert client.post('/api/auth/setup', json={'username': 'qa-admin', 'password': password}).status_code == 200
        response = client.post('/api/users', json={'username': 'qa-viewer', 'password': password, 'role': 'viewer'})
        assert response.status_code == 201, response.text
        assert response.json()['id'] > 1
        assert client.get('/api/dashboard').status_code == 200
        assert client.get('/api/catalog-status').status_code == 200
        assert client.get('/api/automation-overview').status_code == 200
        assert client.get('/api/account/sessions').json()['items'][0]['current'] is True
        from app.database import Session
        from app.models import Institution
        from app.domain import Profile, Publication
        with Session() as db:
            db.add(Institution(id='https://ror.org/qa',name='Universidade de Educação',country='Brazil'))
            db.add(Profile(institution_id='https://ror.org/qa',data={'ror':{'names':[{'value':'UEDU'}],'types':['education'],'locations':[{'geonames_details':{'name':'Natal','country_subdivision_name':'Rio Grande do Norte'}}]}}))
            for i in range(2):
                db.add(Publication(id=f'W{i}',openalex_id=f'W{i}',title=f'Redes e Educação {i}',year=2025,is_oa=True,
                    doi='10.1234/qa'+('-more' if i else ''),openalex={'language':'en' if i else 'pt','type':'article','is_retracted':False,'abstract_inverted_index':{'aprendizagem':[0],'digital':[1]}},
                    topics=[{'id':'T1','name':'Redes'}],authors=[{'name':'Ana','orcid':'https://orcid.org/0000-0002-1825-0097'}]))
            db.commit()
        response=client.get('/api/search?q=educacao')
        assert response.status_code==200,response.text
        assert response.json()['counts']['publication']==2
        assert client.get('/api/search?q=univercidade%20de%20educacao&kind=institution&approximate=true').json()['total']==1
        assert client.get('/api/search?q=univercidade%20de%20educacao&kind=institution').json()['total']==0
        with Session() as db:
            indexes=set(db.scalars(text("SELECT indexname FROM pg_indexes WHERE tablename='search_documents'")))
            assert {'ix_discovery_body_trgm','ix_discovery_title_trgm','ix_discovery_fts'} <= indexes
        assert client.get('/api/search?q=uedu&kind=institution').json()['total']==1
        assert client.get('/api/publications?topic=T1&year_from=2024&oa=true').json()['total']==2
        assert client.get('/api/publication-facets').status_code==200
        assert client.get('/api/publications',params={'q':'https://doi.org/10.1234/qa','approximate':'true'}).json()['total']==1
        exact={'q':'aprendizagem digital','search_in':'abstract','mode':'phrase','language':'pt','work_type':'article','has_doi':'true','has_abstract':'true','retracted':'false'}
        filtered=client.get('/api/publications',params=exact)
        assert filtered.status_code==200,filtered.text
        assert filtered.json()['total']==1
        assert len(client.get('/api/publication-facets?language=pt').json()['languages'])==2
        assert client.get('/api/institutions?city=Natal&institution_type=education').json()['total']==1
        assert client.get('/api/catalog-coverage').json()['available']['abstract']==2
        assert client.post('/api/saved-searches',json={'name':'QA saved search','filters':{'topic':'T1'},'alerts_enabled':True}).status_code==201
        with Session() as db:
            from app.discovery import evaluate_saved_searches
            db.add(Publication(id='Wnew',openalex_id='Wnew',title='Nova rede',topics=[{'id':'T1','name':'Redes'}]))
            evaluate_saved_searches(db)
            db.commit()
        assert len(client.get('/api/search-alerts').json())==1
        # Exercise additive automation tables against real PostgreSQL, without
        # publishing any QA identifiers to the workspace's Redis broker.
        template=client.post('/api/report-templates',json={'name':'QA report','filters':{'year_from':2024}})
        assert template.status_code==201,template.text
        report=client.post(f"/api/report-templates/{template.json()['id']}/generate").json()['report_id']
        from app.reports import render_report
        render_report(report)
        assert client.get(f'/api/reports/{report}/download').status_code==200
        workflow=client.post('/api/workflows',json={'name':'QA flow','steps':['report']})
        assert workflow.status_code==201,workflow.text
        started=client.post(f"/api/workflows/{workflow.json()['id']}/start")
        assert started.status_code==202,started.text
        calendar=client.post('/api/calendar-schedules',json={'name':'QA agenda','target':'workflow','target_id':workflow.json()['id'],'cron':'0 8 * * *','timezone':'America/Sao_Paulo'})
        assert calendar.status_code==201,calendar.text
        queued=client.post('/api/sync',json={'source':'ror'})
        assert queued.status_code==202,queued.text
        run_id=queued.json()['execution_id']
        assert client.post(f'/api/runs/{run_id}/control',json={'action':'pause'}).status_code==200
        assert client.get(f'/api/runs/{run_id}/runtime').json()['run']['status']=='paused'
        assert client.post(f'/api/runs/{run_id}/control',json={'action':'cancel'}).status_code==200
        from app.operations import enqueue,perform
        from app.automation_tick import automation_tick
        from types import SimpleNamespace
        import asyncio
        class LocalProvider:
            net=SimpleNamespace(calls=1,retries=0)
            name='QA University'
            async def ror(self,params):
                return [{'id':'https://ror.org/qatest','name':self.name,'country':'Brazil','data':{}}],{'complete':True}
        provider=LocalProvider()
        asyncio.run(perform(enqueue('ror',{}),provider))
        provider.name='QA University revised'
        asyncio.run(perform(enqueue('ror',{}),provider))
        assert client.get('/api/data-changes?source=ror').json()['total']==1
        automation_tick()
        assert client.post('/api/monitors/discover').status_code==200
        monitor=client.post('/api/monitors',json={'name':'QA PostgreSQL monitor','url':'https://example.org/pg-check'})
        assert monitor.status_code==201,monitor.text
        target_id=monitor.json()['id']
        check=client.post(f'/api/monitors/{target_id}/check')
        assert check.status_code==202,check.text
        from app.monitor_service import perform_check,monitor_tick
        calls=[]
        def local_probe(*args,**kwargs):
            calls.append(1)
            return {'ok':True,'outcome':'available','message':'Isolated QA probe','http_status':200,'tls':{'days_remaining':90}}
        perform_check(check.json()['check_id'],local_probe)
        perform_check(check.json()['check_id'],local_probe)
        assert len(calls)==1
        detail=client.get(f'/api/monitors/{target_id}').json()
        assert detail['target']['status']=='available' and detail['checks']['total']==1
        listing=client.get('/api/monitors')
        assert listing.status_code==200,listing.text
        monitor_tick()
        assert client.post('/api/auth/login', json={'username': 'qa-viewer', 'password': password}).status_code == 200
        assert client.get('/api/dashboard').status_code == 200
        assert client.post('/api/sync', json={'source': 'ror'}).status_code == 403
        assert client.get('/api/users').status_code == 403
        assert client.get('/api/monitors').status_code==200
        assert client.post(f'/api/monitors/{target_id}/check').status_code==403
    engine.dispose()
    print('PostgreSQL: migrations, research, workflows, calendars, monitoring inventory/history/queue claims and viewer permissions verified.')
finally:
    with management.connect() as connection:
        connection.exec_driver_sql(f'DROP DATABASE "{database_name}" WITH (FORCE)')
    management.dispose()
