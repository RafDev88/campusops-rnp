"""Isolated browser-test API. Never uses the user's database or broker."""
import os
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'backend'))

with tempfile.TemporaryDirectory(prefix='campusops-qa-') as directory:
    os.environ['DATABASE_URL'] = 'sqlite:///' + (Path(directory) / 'qa.db').as_posix()
    os.environ['REDIS_URL'] = 'memory://'
    from app.migrate import migrate
    from app.database import Session
    from app.models import Institution
    from app.domain import Profile, Publication, WorkInstitution, utcnow
    migrate()
    with Session() as db:
        db.add(Institution(id='https://ror.org/01abcde12', name='Universidade de Teste E2E', country='Brazil'))
        db.flush()
        db.add(Profile(institution_id='https://ror.org/01abcde12', data={'ror': {'names':[{'value':'UE2E'}],'types':['education'],'status':'active','locations':[{'geonames_details':{'name':'Natal','country_subdivision_name':'Rio Grande do Norte','country_code':'BR'}}]}}, watched=False))
        db.add(Publication(id='https://openalex.org/W123', openalex_id='https://openalex.org/W123',
               title='Computer networks integration test', year=2025, is_oa=True, citations=10,
               openalex={'language':'en','type':'article','is_retracted':False,'publication_date':'2025-03-01','primary_location':{'landing_page_url':'https://example.org/qa-paper'}},
               topics=[{'id': 'T1', 'name': 'Computer networks'}],
               authors=[{'name':'Ana Silva E2E','orcid':'https://orcid.org/0000-0002-1825-0097'}],
               crossref={'abstract':'<jats:p>Resumo de pesquisa sobre redes.</jats:p>','container-title':['Revista de Redes E2E'],
                         'funder':[{'name':'Agência E2E'}]},crossref_at=utcnow(),
               affiliations=[{'id': 'I1', 'ror': 'https://ror.org/01abcde12', 'name': 'Universidade de Teste E2E'},
                             {'id': 'I2', 'ror': 'https://ror.org/02abcde12', 'name': 'Instituição Parceira E2E'}]))
        db.flush()
        db.add(WorkInstitution(publication_id='https://openalex.org/W123', institution_id='https://ror.org/01abcde12'))
        db.add(Publication(id='https://openalex.org/W124',openalex_id='https://openalex.org/W124',title='Educational biology E2E',year=2020,is_oa=False,topics=[{'id':'T2','name':'Biology'}]))
        db.commit()
    from app import monitor_models as monitoring
    from app.monitor_network import url_key
    from datetime import timedelta
    with Session() as db:
        target=monitoring.MonitorTarget(name='Repositório de teste E2E',url='https://example.org/qa-paper',url_hash=url_key('https://example.org/qa-paper'),host='example.org',kind='publication',managed=True,status='tls_expiring',checked_at=utcnow(),next_at=utcnow()+timedelta(days=1))
        db.add(target);db.flush()
        check=monitoring.MonitorCheck(target_id=target.id,state='completed',outcome='tls_expiring',ok=True,message='Certificado de exemplo válido, com vencimento em 5 dias.',http_status=200,final_url=target.url,duration_ms=120,finished_at=utcnow(),tls={'days_remaining':5,'host':'example.org','expires_at':(utcnow()+timedelta(days=5)).isoformat(),'certificates':[{'host':'example.org','days_remaining':5,'expires_at':(utcnow()+timedelta(days=5)).isoformat(),'issuer':'CA de teste','version':'TLSv1.3'}]})
        db.add(check);db.flush();target.last_check_id=check.id;db.commit()
    import uvicorn
    uvicorn.run('app.main:app', host='127.0.0.1', port=8001)
