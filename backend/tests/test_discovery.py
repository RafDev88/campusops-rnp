import csv
import io
from sqlalchemy import select

from app import discovery_models as s
from app.discovery import evaluate_saved_searches
from app.domain import Dataset, Profile, Publication, Researcher, WorkInstitution, utcnow
from app.models import Institution


def seed(factory):
    with factory() as db:
        db.add(Institution(id='https://ror.org/test',name='Universidade de Educação',country='Brazil'))
        db.add(Profile(institution_id='https://ror.org/test',data={'ror':{'names':[{'value':'UEDU'}]}},watched=True))
        db.add_all([
            Publication(id='W1',openalex_id='W1',title='Redes e Educação',year=2025,is_oa=True,citations=10,
                topics=[{'id':'T1','name':'Redes'}],authors=[{'name':'Ana Silva','orcid':'https://orcid.org/0000-0002-1825-0097'}],
                affiliations=[{'id':'I1','ror':'https://ror.org/test','name':'Universidade de Educação'}],
                crossref={'container-title':['Revista Teste'],'abstract':'<jats:p>Resumo acessível.</jats:p>','funder':[{'name':'Agência Teste'}]},crossref_at=utcnow()),
            Publication(id='W2',openalex_id='W2',title='Redes antigas',year=2021,is_oa=False,citations=50,
                topics=[{'id':'T1','name':'Redes'}],authors=[{'name':'Ana Silva','orcid':None}]),
            Publication(id='W3',openalex_id='W3',title='Biologia',year=2026,is_oa=True,citations=2),
        ])
        db.add(Dataset(id='D1',title='Cursos de Educação',url='https://dados.ufrn.br/example',fingerprint='test',resources=[]))
        db.flush()
        db.add(WorkInstitution(publication_id='W1',institution_id='https://ror.org/test'))
        db.commit()


def test_search_folds_accents_and_searches_aliases_and_all_entities(authenticated,database):
    seed(database[0])
    result=authenticated.get('/api/search?q=educacao').json()
    assert {'institution','publication','dataset'} <= set(result['counts'])
    assert authenticated.get('/api/search?q=uedu&kind=institution').json()['total']==1
    assert authenticated.get('/api/institutions?q=uedu').json()['total']==1
    assert authenticated.get('/api/search/suggestions?q=educacao').json()
    assert authenticated.get('/api/search?q=%25%25').json()['total']==0


def test_search_accepts_pasted_doi_and_orcid_urls(authenticated,database):
    seed(database[0])
    with database[0]() as db:
        db.get(Publication,'W1').doi='10.1000/example'
        db.commit()
    assert authenticated.get('/api/publications',params={'q':'https://doi.org/10.1000/example'}).json()['total']==1
    result=authenticated.get('/api/search',params={'q':'https://orcid.org/0000-0002-1825-0097','kind':'researcher'}).json()
    assert result['total']==1


def test_combined_filters_and_csv_use_exact_same_query(authenticated,database):
    seed(database[0])
    params={'q':'educacao','institution_id':'https://ror.org/test','year_from':2024,'year_to':2026,'oa':'true',
            'topic':'T1','author':'ana','source':'crossref','sort':'citations'}
    result=authenticated.get('/api/publications',params=params)
    assert result.status_code==200,result.text
    assert [i['id'] for i in result.json()['items']]==['W1']
    export=authenticated.get('/api/exports/publications.csv',params=params)
    rows=list(csv.reader(io.StringIO(export.text.lstrip('\ufeff'))))
    assert len(rows)==2 and rows[1][0]=='Redes e Educação'
    assert authenticated.get('/api/publications?year_from=2026&year_to=2020').status_code==422
    assert authenticated.get('/api/publications?oa=false').json()['total']==1


def test_ordering_topics_and_readable_publication(authenticated,database):
    seed(database[0])
    assert authenticated.get('/api/publications?sort=citations').json()['items'][0]['id']=='W2'
    assert authenticated.get('/api/publications?sort=recent').json()['items'][0]['id']=='W3'
    assert authenticated.get('/api/publications?topic=T1').json()['total']==2
    detail=authenticated.get('/api/publication?id=W1').json()
    assert detail['abstract']=='Resumo acessível.' and detail['journal']=='Revista Teste'
    assert detail['funders']==['Agência Teste']
    assert 'openalex' not in detail
    assert authenticated.get('/api/publication-facets?topic=T1').json()['topics'][0]['count']==2


def test_normalized_relationships_update_without_stale_matches(authenticated,database):
    seed(database[0])
    with database[0]() as db:
        work=db.get(Publication,'W1')
        work.topics=[{'id':'T2','name':'Segurança'}]
        work.authors=[{'name':'Maria','orcid':None}]
        db.commit()
    assert authenticated.get('/api/publications?topic=T1').json()['total']==1
    assert authenticated.get('/api/publications?topic=seguranca').json()['total']==1
    assert authenticated.get('/api/publications?author=ana').json()['total']==1


def test_same_name_without_orcid_is_not_automatically_merged(authenticated,database):
    seed(database[0])
    authors=authenticated.get('/api/search?q=ana&kind=researcher').json()['items']
    assert len(authors)==2
    profiles=[authenticated.get('/api/researcher-profile',params={'id':a['id']}).json() for a in authors]
    assert sorted(p['identity_confirmed'] for p in profiles)==[False,True]


def test_private_favorites_and_saved_searches(authenticated,database):
    seed(database[0])
    client=authenticated
    favorite={'kind':'publication','entity_id':'W1','enabled':True}
    assert client.post('/api/favorites',json=favorite).status_code==200
    assert client.post('/api/favorites',json=favorite).status_code==200
    assert client.get('/api/publications?favorites=true').json()['total']==1
    saved=client.post('/api/saved-searches',json={'name':'Minhas redes','filters':{'topic':'T1'},'alerts_enabled':True}).json()
    client.post('/api/users',json={'username':'other','password':'other-password-123','role':'viewer'})
    client.post('/api/auth/login',json={'username':'other','password':'other-password-123'})
    assert client.get('/api/saved-searches').json()==[]
    assert client.get('/api/search?favorites=true').json()['total']==0
    assert client.delete('/api/saved-searches/'+str(saved['id'])).status_code==404
    # A read-only operator profile may personalize its own research, but cannot run integrations.
    assert client.post('/api/favorites',json=favorite).status_code==200
    assert client.post('/api/sync',json={'source':'ror'}).status_code==403


def test_saved_search_alerts_only_for_new_matches_and_never_duplicate(authenticated,database):
    seed(database[0])
    response=authenticated.post('/api/saved-searches',json={'name':'Novas redes','filters':{'topic':'T1'},'alerts_enabled':True})
    assert response.status_code==201,response.text
    with database[0]() as db:
        evaluate_saved_searches(db)
        db.commit()
    assert authenticated.get('/api/search-alerts').json()==[]
    with database[0]() as db:
        db.add(Publication(id='W4',openalex_id='W4',title='Nova pesquisa',topics=[{'id':'T1','name':'Redes'}]))
        evaluate_saved_searches(db)
        db.commit()
        evaluate_saved_searches(db)
        db.commit()
    alerts=authenticated.get('/api/search-alerts').json()
    assert len(alerts)==1 and alerts[0]['publication_id']=='W4'
    assert authenticated.post(f"/api/search-alerts/{alerts[0]['id']}/read").status_code==200
    assert authenticated.get('/api/search-alerts').json()[0]['read'] is True


def test_public_orcid_affiliations_are_presented_as_fields(authenticated,database):
    seed(database[0])
    with database[0]() as db:
        db.add(Researcher(orcid='0000-0002-1825-0097',name='Ana Silva',data={'activities-summary':{
            'employments':{'affiliation-group':[{'summaries':[{'employment-summary':{'organization':{'name':'Universidade de Educação'},'role-title':'Pesquisadora'}}]}]}}}))
        db.commit()
    profile=authenticated.get('/api/researcher-profile?id=orcid:0000-0002-1825-0097').json()
    assert profile['employments'][0]['organization']=='Universidade de Educação'
    assert len(profile['works'])==1 and profile['public_profile_imported'] is True
