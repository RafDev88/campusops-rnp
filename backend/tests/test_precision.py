import asyncio
from urllib.parse import urlencode

import httpx
from sqlalchemy import select

from app import discovery_models as s
from app.domain import Publication,Profile,utcnow
from app.models import Institution
from app.providers import Providers,Network


def seed(factory):
    with factory() as db:
        db.add(Institution(id='https://ror.org/precision',name='Universidade de Pesquisa',country='Brazil'))
        db.add(Profile(institution_id='https://ror.org/precision',data={'ror':{'types':['education'],'status':'active','locations':[{'geonames_details':{'name':'Natal','country_subdivision_name':'Rio Grande do Norte','country_code':'BR'}}]}}))
        db.add_all([
            Publication(id='W10',openalex_id='https://openalex.org/W10',title='Redes para educação',doi='10.1234/exact',year=2025,citations=10,openalex={'language':'pt','type':'article','is_retracted':False,'publication_date':'2025-02-03','primary_location':{'source':{'display_name':'Revista Aberta','issn':['1234-5678']},'landing_page_url':'https://example.org/work'},'abstract_inverted_index':{'aprendizagem':[0],'digital':[1]}},authors=[{'name':'Ana Silva','orcid':'https://orcid.org/0000-0002-1825-0097'}]),
            Publication(id='W11',openalex_id='https://openalex.org/W11',title='Paredes na construção',doi='10.1234/exact-extra',year=2024,openalex={'language':'en','type':'book','is_retracted':True},authors=[{'name':'Mariana Silva'}]),
            Publication(id='W12',openalex_id='https://openalex.org/W12',title='Educação e redes',year=2023),
        ])
        db.commit()


def test_word_boundaries_and_modes(authenticated,database):
    seed(database[0])
    assert authenticated.get('/api/publications?q=redes').json()['total']==2
    assert authenticated.get('/api/publications?q=rede').json()['total']==0
    assert authenticated.get('/api/publications?'+urlencode({'q':'redes para','mode':'phrase'})).json()['total']==1
    assert authenticated.get('/api/publications?'+urlencode({'q':'redes para educação','mode':'exact'})).json()['total']==1
    assert authenticated.get('/api/publications?'+urlencode({'q':'construção educação','mode':'all'})).json()['total']==0
    assert authenticated.get('/api/publications?'+urlencode({'q':'construção educação','mode':'any'})).json()['total']==3
    assert authenticated.get('/api/search/suggestions?q=pesqu').json()


def test_identifiers_never_match_longer_identifiers(authenticated,database):
    seed(database[0])
    for value in ('10.1234/exact','https://doi.org/10.1234/exact','DOI:10.1234/exact'):
        result=authenticated.get('/api/publications',params={'q':value,'approximate':'true'}).json()
        assert [r['id'] for r in result['items']]==['W10']
    assert authenticated.get('/api/search',params={'q':'https://openalex.org/W10','kind':'publication'}).json()['total']==1
    assert authenticated.get('/api/search',params={'q':'https://orcid.org/0000-0002-1825-0097','kind':'researcher'}).json()['total']==1


def test_metadata_filters_and_abstract_scope_match_export_and_saved_search(authenticated,database):
    seed(database[0])
    params={'q':'aprendizagem','search_in':'abstract','language':'pt','work_type':'article','has_abstract':'true','has_doi':'true','journal':'aberta','citations_min':5,'retracted':'false'}
    response=authenticated.get('/api/publications',params=params)
    assert response.status_code==200,response.text
    assert [r['id'] for r in response.json()['items']]==['W10']
    assert authenticated.get('/api/publications',params={'q':'aprendizagem','search_in':'title'}).json()['total']==0
    exported=authenticated.get('/api/exports/publications.csv',params=params).text
    assert 'Redes para educação' in exported and 'Paredes' not in exported
    saved=authenticated.post('/api/saved-searches',json={'name':'Consulta precisa','filters':params,'alerts_enabled':True})
    assert saved.status_code==201,saved.text
    assert authenticated.get('/api/publications?retracted=false').json()['total']==1  # unknown is distinct from false
    assert authenticated.get('/api/publications?has_doi=false').json()['total']==1


def test_source_metadata_fallback_is_readable_without_crossref(authenticated,database):
    seed(database[0])
    detail=authenticated.get('/api/publication?id=W10').json()
    assert detail['journal']=='Revista Aberta' and detail['language']=='pt'
    assert detail['issn']==['1234-5678'] and detail['abstract']=='aprendizagem digital'
    assert detail['publication_date']=='2025-02-03'
    assert detail['landing_url']=='https://example.org/work'
    listing=authenticated.get('/api/publications?q=redes').json()
    assert listing['features']['approximate'] is False
    assert next(r for r in listing['items'] if r['id']=='W10')['abstract_preview']=='aprendizagem digital'


def test_author_filter_does_not_confuse_ana_with_mariana(authenticated,database):
    seed(database[0])
    assert [r['id'] for r in authenticated.get('/api/publications?author=ana').json()['items']]==['W10']
    assert authenticated.get('/api/publications',params={'author':'https://orcid.org/0000-0002-1825-0097'}).json()['total']==1


def test_crossref_can_supply_missing_authors_and_orphan_authors_leave_search(authenticated,database):
    seed(database[0])
    with database[0]() as db:
        work=db.get(Publication,'W11')
        work.authors=[]
        work.crossref={'author':[{'given':'Beatriz','family':'Costa','ORCID':'https://orcid.org/0000-0001-2345-6789'}]}
        work.crossref_at=utcnow()
        db.commit()
    assert authenticated.get('/api/search?q=mariana&kind=researcher').json()['total']==0
    assert authenticated.get('/api/publications?author=beatriz').json()['total']==1
    assert authenticated.get('/api/publication?id=W11').json()['authors'][0]['name']=='Beatriz Costa'


def test_institution_location_type_and_source_coverage(authenticated,database):
    seed(database[0])
    params={'city':'Natal','region':'Rio Grande do Norte','institution_type':'education','status':'active'}
    assert authenticated.get('/api/institutions',params=params).json()['total']==1
    assert authenticated.get('/api/institutions?city=Recife').json()['total']==0
    assert authenticated.get('/api/institution-facets').json()['city'][0]['name']=='Natal'
    coverage=authenticated.get('/api/catalog-coverage').json()
    assert coverage['total']==3 and coverage['available']['doi']==2 and coverage['available']['abstract']==1


def test_contextual_facets_allow_changing_selected_facet(authenticated,database):
    seed(database[0])
    result=authenticated.get('/api/publication-facets?language=pt').json()
    assert {r['id'] for r in result['languages']}=={'pt','en'}
    assert {r['id'] for r in result['work_types']}=={'article'}


def test_remote_openalex_scope_filters_are_sent_without_increasing_page_size(monkeypatch):
    monkeypatch.delenv('OPENALEX_API_KEY',raising=False)
    def handler(request):
        if '/institutions/' in request.url.path:return httpx.Response(200,json={'id':'https://openalex.org/I1'})
        assert request.url.params['search']=='educação'
        assert request.url.params['per_page']=='100'
        filters=request.url.params['filter']
        assert 'to_publication_date:2025-12-31' in filters and 'language:pt' in filters and 'type:article' in filters
        return httpx.Response(200,json={'results':[],'meta':{'count':0}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await Providers(Network(client)).openalex('https://ror.org/precision',{'query':'educação','year_from':2024,'year_to':2025,'language':'pt','work_type':'article'})
    asyncio.run(run())


def test_confirmed_missing_record_is_not_requested_again_on_resume(database):
    from app.operations import enqueue
    from app.job_runtime import JobNetwork
    from app.providers import SourceError
    import pytest
    calls=[]
    identifier=enqueue('crossref',{})
    async def run():
        def missing(request):
            calls.append(1)
            return httpx.Response(404)
        async with httpx.AsyncClient(transport=httpx.MockTransport(missing)) as client:
            for _ in range(2):
                with pytest.raises(SourceError) as error:
                    await JobNetwork(identifier,client).get('https://api.crossref.org/works/10.1234/missing')
                assert error.value.code=='not_found'
    asyncio.run(run())
    assert len(calls)==1
