"""Seed fictitious demo data only. Run through the documented demo Compose project."""
import os
from sqlalchemy.engine import make_url

if os.getenv('CAMPUSOPS_DEMO') != 'true' or make_url(os.environ['DATABASE_URL']).database != 'campusops_demo':
    raise SystemExit('Refusing to seed outside the dedicated demonstration database.')

from sqlalchemy import select
from app.database import Session
from app.domain import User, Profile, Publication, WorkInstitution, Run, utcnow
from app.models import Institution
from app.security import passwords
from app import search_index  # Register transactional indexing listeners.
from app.orchestration_models import SourcePolicy
from app.monitor_models import MonitorConfig

with Session() as db:
    if db.scalar(select(User.id)):
        raise SystemExit('Demo already initialized; accounts and data were preserved.')
    db.add(User(username='demonstracao', password_hash=passwords.hash('CampusOps-Demo-2026'), role='admin'))
    university = Institution(id='https://ror.org/demo', name='Universidade Fictícia de Demonstração', country='Brazil')
    db.add(university); db.flush()
    db.add(Profile(institution_id=university.id, watched=True, fetched_at=utcnow(), data={'ror':{'names':[{'value':'UFD'}],'types':['education']}}))
    db.flush()
    for i, title in enumerate(['Redes de pesquisa e educação digital', 'Dados abertos para universidades', 'Automação de serviços acadêmicos']):
        work = Publication(id=f'demo:{i}',openalex_id=f'demo:{i}',title=title,year=2025,is_oa=True,
                           topics=[{'id':'demo-topic','name':'Tecnologia e educação'}],authors=[{'name':'Pesquisador fictício'}],
                           affiliations=[{'ror':university.id,'name':university.name}],
                           openalex={'language':'pt','type':'article','abstract_inverted_index':{'Exemplo':[0],'fictício':[1],'educacional':[2]}})
        db.add(work); db.flush()
        db.add(WorkInstitution(publication_id=work.id,institution_id=university.id))
    db.add(Run(source='openalex',status='partial',finished_at=utcnow(),records=3,message='Exemplo fictício de cobertura parcial.',details={'complete':False}))
    for source in ('ror','openalex','crossref','orcid','ufrn'):
        policy=db.get(SourcePolicy,source)
        if policy:policy.enabled=False
    config=db.get(MonitorConfig,1)
    if config:config.enabled=False
    db.commit()
print('Demonstração inicializada com registros fictícios; coletas automáticas desativadas.')
