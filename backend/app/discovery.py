"""Shared query building for results, facets, export and saved-search alerts."""
from typing import Literal
import re
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import and_, case, exists, func, literal, literal_column, or_, select
from . import discovery_models as s
from .domain import Publication, utcnow
from .search_index import fold


class PublicationFilters(BaseModel):
    q: str = Field(default='', max_length=150)
    institution_id: str = Field(default='', max_length=200)
    topic: str = Field(default='', max_length=200)
    author: str = Field(default='', max_length=150)
    author_id: str = Field(default='', max_length=200)
    year: int | None = Field(default=None, ge=1900, le=2100)
    year_from: int | None = Field(default=None, ge=1900, le=2100)
    year_to: int | None = Field(default=None, ge=1900, le=2100)
    oa: bool | None = None
    source: Literal['', 'openalex', 'crossref'] = ''
    favorites: bool = False
    mode: Literal['all','any','phrase','exact']='all'
    approximate: bool=False
    search_in: Literal['all','title','abstract']='all'
    language: str=Field(default='',max_length=20)
    work_type: str=Field(default='',max_length=80)
    journal: str=Field(default='',max_length=200)
    has_abstract: bool | None=None
    has_doi: bool | None=None
    retracted: bool | None=None
    citations_min: int | None=Field(default=None,ge=0,le=100000000)
    sort: Literal['relevance', 'recent', 'title', 'citations'] = 'relevance'

    @model_validator(mode='after')
    def valid_range(self):
        if self.year_from and self.year_to and self.year_from > self.year_to:
            raise ValueError('O ano inicial deve ser menor ou igual ao final.')
        return self


def matching(db,q,mode='all',approximate=False,column=None,prefix=False):
    from .metadata import identifier
    term=fold(q).strip('"')
    if not term:return literal(True),literal(0)
    canonical=identifier(term)
    is_identifier=bool(re.match(r'^10\.\d{4,9}/\S+$',canonical) or re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dx]',canonical) or re.match(r'^https?://(?:ror\.org|openalex\.org)/',term) or re.fullmatch(r'[wia]\d+',canonical))
    if is_identifier:
        condition=exists(select(s.SearchIdentifier.value).where(s.SearchIdentifier.kind==s.SearchDocument.kind,s.SearchIdentifier.entity_id==s.SearchDocument.entity_id,s.SearchIdentifier.value==canonical))
        return condition,literal(100)
    text=column if column is not None else s.SearchDocument.body
    tokens=re.findall(r'\w+',term)[:20]
    if not tokens:return literal(False),literal(0)
    postgres=db.bind.dialect.name=='postgresql'
    def word(token,last=False):
        pattern=('(^|[^[:alnum:]_])'+re.escape(token)+('' if prefix and last else '([^[:alnum:]_]|$)')) if postgres else (r'(?<!\w)'+re.escape(token)+('' if prefix and last else r'(?!\w)'))
        return text.regexp_match(pattern)
    if mode=='exact':predicate=(column if column is not None else s.SearchDocument.normalized_title)==term
    elif mode=='phrase':predicate=word(term)
    else:
        parts=[word(token,i==len(tokens)-1) for i,token in enumerate(tokens)]
        predicate=or_(*parts) if mode=='any' else and_(*parts)
    rank=case((s.SearchDocument.normalized_title==term,20),(s.SearchDocument.normalized_title.contains(term,autoescape=True),12),else_=2)
    rank=rank+case((predicate,30),else_=0)
    if approximate and postgres and len(term)>=4 and mode=='all':
        target=column if column is not None else s.SearchDocument.normalized_title
        predicate=or_(predicate,target.op('%')(term),literal(term).op('<%')(target))
        rank=rank+func.word_similarity(term,target)
    return predicate,rank


def active_document():
    from .domain import Researcher
    return or_(s.SearchDocument.kind!='researcher',exists(select(s.WorkAuthor.author_id).where(s.WorkAuthor.author_id==s.SearchDocument.entity_id)),
        exists(select(Researcher.orcid).where(literal('orcid:')+Researcher.orcid==s.SearchDocument.entity_id)))


def publication_query(db, filters, user_id):
    from .domain import WorkInstitution
    query = select(Publication).join(s.SearchDocument, and_(s.SearchDocument.kind == 'publication', s.SearchDocument.entity_id == Publication.id))
    query=query.outerjoin(s.WorkMetadata,s.WorkMetadata.publication_id==Publication.id)
    column={'title':s.SearchDocument.normalized_title,'abstract':s.WorkMetadata.normalized_abstract}.get(filters.search_in)
    predicate, rank = matching(db,filters.q,filters.mode,filters.approximate,column)
    for key in ('language','work_type'):
        if getattr(filters,key):query=query.where(getattr(s.WorkMetadata,key)==getattr(filters,key).strip().lower())
    if filters.journal:query=query.where(s.WorkMetadata.normalized_journal.contains(fold(filters.journal),autoescape=True))
    for field,key in [('has_abstract','has_abstract'),('has_doi','has_doi'),('is_retracted','retracted')]:
        if getattr(filters,key) is not None:query=query.where(getattr(s.WorkMetadata,field).is_(getattr(filters,key)))
    if filters.citations_min is not None:query=query.where(Publication.citations>=filters.citations_min)
    query = query.where(predicate)
    if filters.institution_id:
        query = query.where(or_(exists(select(s.WorkAffiliation.publication_id).where(
            s.WorkAffiliation.publication_id == Publication.id, s.WorkAffiliation.institution_id == filters.institution_id)),
            exists(select(WorkInstitution.publication_id).where(WorkInstitution.publication_id == Publication.id,
                       WorkInstitution.institution_id == filters.institution_id))))
    if filters.topic:
        query = query.where(exists(select(s.WorkTopic.publication_id).join(s.Topic).where(s.WorkTopic.publication_id == Publication.id,
            or_(s.Topic.id == filters.topic, s.Topic.normalized_name == fold(filters.topic)))))
    if filters.author or filters.author_id:
        authors = select(s.WorkAuthor.publication_id).join(s.Author).where(s.WorkAuthor.publication_id == Publication.id)
        if filters.author:
            from .metadata import identifier
            token=identifier(filters.author)
            if re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dx]',token):authors=authors.where(func.lower(s.Author.orcid)==token)
            else:
                condition,_=matching(db,filters.author,column=s.Author.normalized_name)
                authors=authors.where(condition)
        if filters.author_id:
            authors = authors.where(s.Author.id == filters.author_id)
        query = query.where(exists(authors))
    if filters.year:
        query = query.where(Publication.year == filters.year)
    if filters.year_from:
        query = query.where(Publication.year >= filters.year_from)
    if filters.year_to:
        query = query.where(Publication.year <= filters.year_to)
    if filters.oa is not None:
        query = query.where(Publication.is_oa.is_(filters.oa))
    if filters.source == 'crossref':
        query = query.where(Publication.crossref_at.is_not(None))
    if filters.favorites:
        query = query.where(exists(select(s.Favorite.entity_id).where(s.Favorite.user_id == user_id,
            s.Favorite.kind == 'publication', s.Favorite.entity_id == Publication.id)))
    orders = {'relevance': [rank.desc(), Publication.year.desc().nullslast()],
              'recent': [Publication.year.desc().nullslast(), Publication.fetched_at.desc()],
              'title': [s.SearchDocument.normalized_title], 'citations': [Publication.citations.desc()]}
    return query.order_by(*orders[filters.sort], Publication.id)


def evaluate_saved_searches(db):
    db.flush()
    for saved in db.scalars(select(s.SavedSearch).where(s.SavedSearch.alerts_enabled.is_(True)).order_by(s.SavedSearch.id).with_for_update()):
        filters = PublicationFilters.model_validate(saved.filters)
        ids = db.scalars(publication_query(db, filters, saved.user_id).with_only_columns(Publication.id).where(
            ~exists(select(s.SavedMatch.publication_id).where(s.SavedMatch.search_id == saved.id,
                s.SavedMatch.publication_id == Publication.id)))).all()
        for identifier in ids:
            db.add(s.SavedMatch(search_id=saved.id, publication_id=identifier))
            db.add(s.SearchAlert(user_id=saved.user_id, search_id=saved.id, publication_id=identifier))
