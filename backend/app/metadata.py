"""Derived metadata with explicit fallbacks; raw provider responses stay intact."""
import re
from . import discovery_models as s
from .domain import Publication,Profile,Researcher
from .models import Institution


def effective_authors(work):
    if work.authors:return work.authors
    result=[]
    for raw in (work.crossref or {}).get('author',[]):
        name=' '.join(str(raw.get(k) or '').strip() for k in ('given','family')).strip() or raw.get('name') or ''
        orcid=raw.get('ORCID') or ''
        if name:result.append({'name':name,'orcid':orcid if re.fullmatch(r'(?:https?://orcid.org/)?\d{4}-\d{4}-\d{4}-\d{3}[\dX]',orcid) else None})
    return result


def bibliographic(work):
    from .search_index import abstract,plain
    oa,cr=work.openalex or {},work.crossref or {}
    location=oa.get('primary_location') or {}
    source=location.get('source') or {}
    best=oa.get('best_oa_location') or {}
    titles=cr.get('container-title') or []
    return {'language':str(oa.get('language') or cr.get('language') or '').lower().replace('_','-').split('-')[0],
        'work_type':oa.get('type') or cr.get('type') or '',
        'journal':plain(titles[0] if titles else source.get('display_name') or ''),
        'publisher':cr.get('publisher') or source.get('host_organization_name') or '',
        'abstract':abstract(work),'publication_date':oa.get('publication_date') or '',
        'issn':cr.get('ISSN') or source.get('issn') or [],
        'is_retracted':oa.get('is_retracted') if isinstance(oa.get('is_retracted'),bool) else None,
        'landing_url':best.get('landing_page_url') or location.get('landing_page_url') or '',
        'pdf_url':best.get('pdf_url') or (location.get('pdf_url') if location.get('is_oa') else '') or '',
        'oa_status':(oa.get('open_access') or {}).get('oa_status') or '',
        'funders':list(dict.fromkeys([f.get('name','') for f in cr.get('funder',[])]+[f.get('display_name','') for f in oa.get('funders',[]) if isinstance(f,dict)])),
        'licenses':list(dict.fromkeys([entry.get('URL','') for entry in cr.get('license',[])]+([best['license']] if best.get('license') else [])))}


def identifier(value):
    value=str(value or '').strip().casefold()
    value=re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*|https?://orcid\.org/|orcid:|https?://(?:www\.)?ror\.org/|https?://openalex.org/)', '',value)
    return value


def upsert_identifiers(db,kind,key,values):
    from sqlalchemy import select
    wanted={identifier(v) for v in values if v}
    old={r.value:r for r in db.scalars(select(s.SearchIdentifier).where(s.SearchIdentifier.kind==kind,s.SearchIdentifier.entity_id==key))}
    pending={(r.kind,r.entity_id,r.value) for r in db.new if isinstance(r,s.SearchIdentifier)}
    for value in wanted:
        if value not in old and (kind,key,value) not in pending:db.add(s.SearchIdentifier(kind=kind,entity_id=key,value=value))
    for value,row in old.items():
        if value not in wanted:db.delete(row)


def sync_metadata(db,item):
    from sqlalchemy import select
    from .search_index import fold
    if isinstance(item,Publication):
        data=bibliographic(item)
        row=db.get(s.WorkMetadata,item.id) or next((r for r in db.new if isinstance(r,s.WorkMetadata) and r.publication_id==item.id),None)
        if not row:row=s.WorkMetadata(publication_id=item.id);db.add(row)
        for key in ('language','work_type','journal','is_retracted'):setattr(row,key,data[key])
        row.normalized_journal=fold(data['journal']);row.normalized_abstract=fold(data['abstract'])
        row.has_abstract=bool(data['abstract']);row.has_doi=bool(item.doi)
        upsert_identifiers(db,'publication',item.id,[item.id,item.openalex_id,item.doi])
    elif isinstance(item,(Institution,Profile)):
        inst=item if isinstance(item,Institution) else db.get(Institution,item.institution_id)
        if not inst:inst=next((r for r in db.new if isinstance(r,Institution) and r.id==item.institution_id),None)
        if not inst:return
        profile=item if isinstance(item,Profile) else db.get(Profile,inst.id)
        if not profile:profile=next((r for r in db.new if isinstance(r,Profile) and r.institution_id==inst.id),None)
        raw=(profile.data or {}).get('ror',{}) if profile else {}
        pairs={('country',fold(inst.country)):inst.country}
        for loc in raw.get('locations',[]):
            place=loc.get('geonames_details') or {}
            for field,value in [('city',place.get('name')),('region',place.get('country_subdivision_name')),('country_code',place.get('country_code'))]:
                if value:pairs[(field,fold(value))]=value
        for value in raw.get('types',[]):pairs[('type',fold(value))]=value
        if raw.get('status'):pairs[('status',fold(raw['status']))]=raw['status']
        old={(r.field,r.value):r for r in db.scalars(select(s.InstitutionField).where(s.InstitutionField.institution_id==inst.id))}
        for key,label in pairs.items():
            pending=next((r for r in db.new if isinstance(r,s.InstitutionField) and (r.institution_id,r.field,r.value)==(inst.id,*key)),None)
            row=old.get(key) or pending
            if not row:row=s.InstitutionField(institution_id=inst.id,field=key[0],value=key[1],label=label);db.add(row)
            row.label=label
        for key,row in old.items():
            if key not in pairs:db.delete(row)
        upsert_identifiers(db,'institution',inst.id,[inst.id])
    elif isinstance(item,Researcher):upsert_identifiers(db,'researcher','orcid:'+item.orcid,[item.orcid])
