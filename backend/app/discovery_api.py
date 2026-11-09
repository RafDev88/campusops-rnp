import csv
import io
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, delete, exists, func, select
from sqlalchemy.exc import IntegrityError

from . import discovery_models as s
from .automation import aware
from .database import Session
from .discovery import PublicationFilters, matching, publication_query,active_document
from .domain import Dataset, Profile, Publication, Researcher
from .models import Institution
from .search_index import abstract, author_identity, plain
from .metadata import bibliographic,effective_authors
from .security import current_user
from .contracts import PublicationPage, PublicationResponse

router = APIRouter()
Filters = Annotated[PublicationFilters, Query()]


def iso(value):
    return aware(value).isoformat() if value else None


def publication_item(db, work, user_id, detailed=False):
    result = {key: getattr(work, key) for key in ('id', 'title', 'year', 'doi', 'is_oa', 'citations', 'topics', 'affiliations')}
    result['authors'] = [{**a, 'id': author_identity(work.id, i, a)[0]} for i, a in enumerate(effective_authors(work))]
    result['fetched_at'], result['crossref_at'] = iso(work.fetched_at), iso(work.crossref_at)
    result['source'] = 'OpenAlex + Crossref' if work.crossref_at else 'OpenAlex'
    result['favorite'] = db.get(s.Favorite, (user_id, 'publication', work.id)) is not None
    if detailed:
        metadata = work.crossref or {}
        result.update({**bibliographic(work),'crossref': metadata})
    else:
        derived=db.get(s.WorkMetadata,work.id)
        result.update({key:getattr(derived,key) if derived else None for key in ('language','work_type','journal','is_retracted','has_abstract')})
        text=abstract(work)
        result['abstract_preview']=text[:240]+('…' if len(text)>240 else '')
    return result


@router.get('/publications', response_model=PublicationPage)
def publications(filters: Filters, offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100), user=Depends(current_user)):
    with Session() as db:
        query = publication_query(db, filters, user['id'])
        total = db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))
        items = db.scalars(query.offset(offset).limit(limit)).all()
        return {'total': total, 'items': [publication_item(db, w, user['id']) for w in items],
                'features':{'approximate':db.bind.dialect.name=='postgresql'},
                'scope': 'Pesquisa no catálogo já importado. As fontes externas não são consultadas durante a busca.'}


@router.get('/publication', response_model=PublicationResponse)
def publication(id: str, user=Depends(current_user)):
    with Session() as db:
        work = db.get(Publication, id)
        if not work:
            raise HTTPException(404, 'Publicação não encontrada no catálogo local.')
        return publication_item(db, work, user['id'], detailed=True)


@router.get('/publication-facets')
def facets(filters: Filters, user=Depends(current_user)):
    with Session() as db:
        def ids_without(key):
            defaults={'topic':'','institution_id':'','language':'','work_type':''}
            adjusted=filters.model_copy(update={key:defaults[key]})
            return publication_query(db,adjusted,user['id']).with_only_columns(Publication.id).order_by(None)
        topics=db.execute(select(s.Topic.id,s.Topic.name,func.count()).join(s.WorkTopic).where(s.WorkTopic.publication_id.in_(ids_without('topic'))).group_by(s.Topic.id,s.Topic.name).order_by(func.count().desc(),s.Topic.id).limit(200)).all()
        from .domain import WorkInstitution
        affiliations=select(s.WorkAffiliation.institution_id.label('id'),s.WorkAffiliation.name.label('name'),s.WorkAffiliation.publication_id.label('work')).where(s.WorkAffiliation.publication_id.in_(ids_without('institution_id')))
        linked=select(WorkInstitution.institution_id.label('id'),Institution.name.label('name'),WorkInstitution.publication_id.label('work')).join(Institution,Institution.id==WorkInstitution.institution_id).where(WorkInstitution.publication_id.in_(ids_without('institution_id')))
        all_inst=affiliations.union(linked).subquery()
        institutions=db.execute(select(all_inst.c.id,func.min(all_inst.c.name),func.count(func.distinct(all_inst.c.work))).group_by(all_inst.c.id).order_by(func.min(all_inst.c.name)).limit(500)).all()
        result={'topics':[{'id':r[0],'name':r[1],'count':r[2]} for r in topics],'institutions':[{'id':r[0],'name':r[1],'count':r[2]} for r in institutions]}
        for key in ('language','work_type'):
            column=getattr(s.WorkMetadata,key)
            rows=db.execute(select(column,func.count()).where(s.WorkMetadata.publication_id.in_(ids_without(key)),column!='').group_by(column).order_by(func.count().desc(),column).limit(200)).all()
            result[key+'s']=[{'id':r[0],'count':r[1]} for r in rows]
        return result


@router.get('/exports/publications.csv')
def export_publications(filters: Filters, user=Depends(current_user)):
    def safe(value):
        value = str(value or '')
        return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(['titulo', 'ano', 'doi', 'acesso_aberto', 'citacoes', 'origem', 'coletado_em','idioma_metadados','tipo','periodico','editora','autores','data_publicacao','issn','pagina_fonte','pdf_fonte','retratado'])
    with Session() as db:
        for work in db.scalars(publication_query(db, filters, user['id']).limit(10000)):
            meta=bibliographic(work)
            writer.writerow([safe(work.title), work.year, safe(work.doi), work.is_oa, work.citations,
                             'OpenAlex + Crossref' if work.crossref_at else 'OpenAlex', iso(work.fetched_at),
                             *[safe(meta[k]) for k in ('language','work_type','journal','publisher')],
                             safe('; '.join(a.get('name') or '' for a in effective_authors(work))),safe(meta['publication_date']),safe('; '.join(meta['issn'])),safe(meta['landing_url']),safe(meta['pdf_url']),meta['is_retracted']])
    return Response('\ufeff' + buffer.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename="campusops-pesquisa.csv"'})


def search_result(db, row, user_id):
    return {'kind': row.kind, 'id': row.entity_id, 'title': row.title, 'subtitle': row.subtitle,
            'source': row.source, 'collected_at': iso(row.collected_at),
            'favorite': db.get(s.Favorite, (user_id, row.kind, row.entity_id)) is not None}


@router.get('/search')
def search(q: str = Query('', max_length=150), kind: Literal['', 'institution', 'publication', 'researcher', 'dataset'] = '',
           favorites: bool = False, mode:Literal['all','any','phrase','exact']='all', approximate:bool=False,
           offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), user=Depends(current_user)):
    with Session() as db:
        condition, rank = matching(db, q,mode,approximate)
        condition=and_(condition,active_document())
        query = select(s.SearchDocument).where(condition)
        if favorites:
            query = query.where(exists(select(s.Favorite.entity_id).where(s.Favorite.user_id == user['id'],
                s.Favorite.kind == s.SearchDocument.kind, s.Favorite.entity_id == s.SearchDocument.entity_id)))
        counts = dict(db.execute(select(s.SearchDocument.kind, func.count()).where(condition,
            *([exists(select(s.Favorite.entity_id).where(s.Favorite.user_id == user['id'], s.Favorite.kind == s.SearchDocument.kind,
                  s.Favorite.entity_id == s.SearchDocument.entity_id))] if favorites else [])).group_by(s.SearchDocument.kind)).all())
        if kind:
            query = query.where(s.SearchDocument.kind == kind)
        total = db.scalar(select(func.count()).select_from(query.subquery()))
        rows = db.scalars(query.order_by(rank.desc(), s.SearchDocument.normalized_title, s.SearchDocument.kind,
            s.SearchDocument.entity_id).offset(offset).limit(limit)).all()
        return {'total': total, 'counts': counts, 'items': [search_result(db, row, user['id']) for row in rows],
                'approximate_supported':db.bind.dialect.name=='postgresql',
                'scope': 'Resultados do catálogo importado. Identificadores usam correspondência exata; aproximações só são aplicadas quando solicitadas.'}


@router.get('/search/suggestions')
def suggestions(q: str = Query('', min_length=2, max_length=150), kind: str = '', user=Depends(current_user)):
    with Session() as db:
        condition, rank = matching(db, q,prefix=True)
        condition=and_(condition,active_document())
        query = select(s.SearchDocument).where(condition)
        if kind:
            query = query.where(s.SearchDocument.kind == kind)
        rows = db.scalars(query.order_by(rank.desc(), s.SearchDocument.normalized_title, s.SearchDocument.entity_id).limit(8)).all()
        return [search_result(db, row, user['id']) for row in rows]


class FavoriteRequest(BaseModel):
    kind: Literal['institution', 'publication', 'researcher', 'dataset']
    entity_id: str = Field(max_length=400)
    enabled: bool


@router.post('/favorites')
def favorite(payload: FavoriteRequest, user=Depends(current_user)):
    with Session() as db:
        if not db.get(s.SearchDocument, (payload.kind, payload.entity_id)):
            raise HTTPException(404, 'Registro não encontrado no catálogo.')
        existing = db.get(s.Favorite, (user['id'], payload.kind, payload.entity_id))
        if payload.enabled and not existing:
            db.add(s.Favorite(user_id=user['id'], kind=payload.kind, entity_id=payload.entity_id))
        elif not payload.enabled and existing:
            db.delete(existing)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()  # Concurrent identical requests still converge to the requested state.
        return {'enabled': payload.enabled}


class SavedSearchRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    filters: PublicationFilters
    alerts_enabled: bool = False


@router.get('/saved-searches')
def saved_searches(user=Depends(current_user)):
    with Session() as db:
        return [{'id': r.id, 'name': r.name, 'filters': r.filters, 'alerts_enabled': r.alerts_enabled,
                 'created_at': iso(r.created_at)} for r in db.scalars(select(s.SavedSearch).where(
                     s.SavedSearch.user_id == user['id']).order_by(s.SavedSearch.id.desc()))]


@router.post('/saved-searches', status_code=201)
def save_search(payload: SavedSearchRequest, user=Depends(current_user)):
    with Session() as db:
        if db.scalar(select(func.count()).select_from(s.SavedSearch).where(s.SavedSearch.user_id == user['id'])) >= 100:
            raise HTTPException(422, 'Limite de 100 pesquisas salvas por usuário.')
        row = s.SavedSearch(user_id=user['id'], name=payload.name, filters=payload.filters.model_dump(), alerts_enabled=payload.alerts_enabled)
        db.add(row)
        db.flush()
        for identifier in db.scalars(publication_query(db, payload.filters, user['id']).with_only_columns(Publication.id)):
            db.add(s.SavedMatch(search_id=row.id, publication_id=identifier))
        db.commit()
        return {'id': row.id, 'name': row.name}


@router.delete('/saved-searches/{identifier}')
def remove_saved_search(identifier: int, user=Depends(current_user)):
    with Session() as db:
        row = db.scalar(select(s.SavedSearch).where(s.SavedSearch.id == identifier,
            s.SavedSearch.user_id == user['id']).with_for_update())
        if not row or row.user_id != user['id']:
            raise HTTPException(404, 'Pesquisa não encontrada.')
        db.execute(delete(s.SearchAlert).where(s.SearchAlert.search_id == identifier))
        db.execute(delete(s.SavedMatch).where(s.SavedMatch.search_id == identifier))
        db.delete(row)
        db.commit()
        return {'ok': True}


@router.get('/search-alerts')
def search_alerts(user=Depends(current_user)):
    with Session() as db:
        rows = db.execute(select(s.SearchAlert, s.SavedSearch.name, Publication.title).join(s.SavedSearch,
            s.SavedSearch.id == s.SearchAlert.search_id).join(Publication, Publication.id == s.SearchAlert.publication_id).where(
                s.SearchAlert.user_id == user['id']).order_by(s.SearchAlert.id.desc()).limit(100)).all()
        return [{'id': a.id, 'search_name': name, 'publication_id': a.publication_id, 'title': title,
                 'read': a.read, 'created_at': iso(a.created_at)} for a, name, title in rows]


@router.post('/search-alerts/{identifier}/read')
def read_alert(identifier: int, user=Depends(current_user)):
    with Session() as db:
        row = db.get(s.SearchAlert, identifier)
        if not row or row.user_id != user['id']:
            raise HTTPException(404, 'Aviso não encontrado.')
        row.read = True
        db.commit()
        return {'ok': True}


def affiliations(data, category):
    result = []
    for group in ((data.get('activities-summary') or {}).get(category) or {}).get('affiliation-group', []):
        for summary in group.get('summaries', []):
            for entry in summary.values():
                if isinstance(entry, dict):
                    result.append({'organization': (entry.get('organization') or {}).get('name', ''),
                                   'role': entry.get('role-title') or '', 'department': entry.get('department-name') or ''})
    return result


@router.get('/researcher-profile')
def researcher_profile(id: str, user=Depends(current_user)):
    with Session() as db:
        author = db.get(s.Author, id)
        orcid = id.removeprefix('orcid:') if id.startswith('orcid:') else (author.orcid if author else None)
        person = db.get(Researcher, orcid) if orcid else None
        if not person and not author:
            raise HTTPException(404, 'Pesquisador não encontrado no catálogo importado.')
        data = person.data if person else {}
        works = db.scalars(publication_query(db, PublicationFilters(author_id=id), user['id']).limit(25)).all()
        return {'id': id, 'name': person.name if person else author.name, 'orcid': orcid,
                'identity_confirmed': bool(orcid), 'public_profile_imported': person is not None,
                'employments': affiliations(data, 'employments'), 'educations': affiliations(data, 'educations'),
                'works': [publication_item(db, w, user['id']) for w in works],
                'fetched_at': iso(person.fetched_at) if person else None,
                'scope': 'Vínculos públicos do ORCID, quando consultados, e trabalhos disponíveis no catálogo local.'}


@router.get('/dataset')
def dataset(id: str, user=Depends(current_user)):
    from .read_api import serialize
    with Session() as db:
        row = db.get(Dataset, id)
        if not row:
            raise HTTPException(404, 'Conjunto não encontrado.')
        return serialize(row)
