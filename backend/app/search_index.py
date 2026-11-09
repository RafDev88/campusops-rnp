"""Transactional search projection; accent folding is identical on SQLite and PG."""
import hashlib
import html
import re
import unicodedata
from sqlalchemy import event, select
from sqlalchemy.orm import Session as OrmSession
from . import discovery_models as s
from .domain import Dataset, Profile, Publication, Researcher, utcnow
from .models import Institution


def fold(text):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', str(text or ''))
                           if not unicodedata.combining(c)).casefold().split())


def plain(text):
    return html.unescape(re.sub(r'<[^>]*>', ' ', str(text or ''))).strip()


def abstract(work):
    crossref = plain((work.crossref or {}).get('abstract'))
    if crossref:
        return crossref[:30000]
    inverted = (work.openalex or {}).get('abstract_inverted_index') or {}
    positions = {p: word for word, indexes in inverted.items() for p in indexes if isinstance(p, int) and 0 <= p < 5000}
    return ' '.join(positions[p] for p in sorted(positions))[:30000]


def author_identity(publication_id, index, author):
    orcid = str(author.get('orcid') or '').rsplit('/', 1)[-1]
    if re.fullmatch(r'\d{4}-\d{4}-\d{4}-\d{3}[\dX]', orcid):
        return 'orcid:' + orcid, orcid
    # Names alone cannot establish that two authors are the same person.
    return 'unverified:' + hashlib.sha256(f'{publication_id}:{index}'.encode()).hexdigest(), None


def document(db, kind, identifier, title, body, source, subtitle='', collected_at=None):
    item = db.get(s.SearchDocument, (kind, identifier)) or next((o for o in db.new if isinstance(o, s.SearchDocument)
        and o.kind == kind and o.entity_id == identifier), None)
    if not item:
        item = s.SearchDocument(kind=kind, entity_id=identifier)
        db.add(item)
    item.title, item.normalized_title = title, fold(title)
    item.body, item.source, item.subtitle = fold(title + ' ' + body), source, subtitle
    item.collected_at = collected_at or utcnow()


def sync_record(db, item):
    from .metadata import sync_metadata,upsert_identifiers,bibliographic,effective_authors
    sync_metadata(db,item)
    if isinstance(item, Institution):
        profile = db.get(Profile, item.id) or next((p for p in db.new if isinstance(p, Profile) and p.institution_id == item.id), None)
        data = (profile.data or {}).get('ror', {}) if profile else {}
        aliases = ' '.join(n.get('value', '') for n in data.get('names', []))
        places = ' '.join(str(loc.get('geonames_details', {}).get('name') or '') for loc in data.get('locations', []))
        document(db, 'institution', item.id, item.name, f'{aliases} {places} {item.country} {item.id}', 'ROR', item.country,
                 profile.fetched_at if profile else None)
    elif isinstance(item, Profile):
        institution = db.get(Institution, item.institution_id) or next((i for i in db.new if isinstance(i, Institution) and i.id == item.institution_id), None)
        if institution:
            data = (item.data or {}).get('ror', {})
            aliases = ' '.join(n.get('value', '') for n in data.get('names', []))
            places = ' '.join(str(loc.get('geonames_details', {}).get('name') or '') for loc in data.get('locations', []))
            document(db, 'institution', institution.id, institution.name, f'{aliases} {places} {institution.country} {institution.id}',
                     'ROR', institution.country, item.fetched_at)
    elif isinstance(item, Publication):
        old_topics = {l.topic_id: l for l in db.scalars(select(s.WorkTopic).where(s.WorkTopic.publication_id == item.id))}
        old_authors = {l.author_id: l for l in db.scalars(select(s.WorkAuthor).where(s.WorkAuthor.publication_id == item.id))}
        old_affiliations = {l.institution_id: l for l in db.scalars(select(s.WorkAffiliation).where(s.WorkAffiliation.publication_id == item.id))}
        topic_ids, author_ids, affiliation_ids = set(), set(), set()
        for topic in item.topics or []:
            if topic['id'] in topic_ids:
                continue
            topic_ids.add(topic['id'])
            entity = db.get(s.Topic, topic['id']) or next((t for t in db.new if isinstance(t, s.Topic) and t.id == topic['id']), None)
            if not entity:
                entity = s.Topic(id=topic['id'])
                db.add(entity)
            entity.name, entity.normalized_name = topic['name'], fold(topic['name'])
            if topic['id'] not in old_topics:
                db.add(s.WorkTopic(publication_id=item.id, topic_id=topic['id']))
        for i, author in enumerate(effective_authors(item)):
            identifier, orcid = author_identity(item.id, i, author)
            if identifier in author_ids:
                continue
            author_ids.add(identifier)
            entity = db.get(s.Author, identifier) or next((a for a in db.new if isinstance(a, s.Author) and a.id == identifier), None)
            if not entity:
                entity = s.Author(id=identifier)
                db.add(entity)
            entity.name, entity.normalized_name, entity.orcid = author.get('name') or 'Nome não informado', fold(author.get('name')), orcid
            document(db, 'researcher', identifier, entity.name, f'{entity.name} {orcid or ""}', 'OpenAlex',
                     'Identificado por ORCID' if orcid else f'Autoria em {item.title[:100]} · identidade não confirmada', item.fetched_at)
            upsert_identifiers(db,'researcher',identifier,[orcid] if orcid else [])
            person = db.get(Researcher, orcid) if orcid else None
            if person:
                sync_record(db, person)
            if identifier not in old_authors:
                db.add(s.WorkAuthor(publication_id=item.id, author_id=identifier))
        for affiliation in item.affiliations or []:
            identifier = affiliation.get('ror') or affiliation.get('id')
            if identifier and identifier not in affiliation_ids:
                affiliation_ids.add(identifier)
                if identifier not in old_affiliations:
                    db.add(s.WorkAffiliation(publication_id=item.id, institution_id=identifier, name=affiliation.get('name') or identifier))
                else:
                    old_affiliations[identifier].name = affiliation.get('name') or identifier
        for key, link in old_topics.items():
            if key not in topic_ids:
                db.delete(link)
        for key, link in old_authors.items():
            if key not in author_ids:
                db.delete(link)
        for key, link in old_affiliations.items():
            if key not in affiliation_ids:
                db.delete(link)
        meta=bibliographic(item)
        body = ' '.join([item.id,item.doi or '', abstract(item),meta['journal'],meta['publisher'],' '.join(meta['funders']), ' '.join(t['name'] for t in item.topics or []),
                         ' '.join(a.get('name') or '' for a in effective_authors(item)),
                         ' '.join(a.get('name') or '' for a in item.affiliations or [])])
        document(db, 'publication', item.id, item.title, body, 'OpenAlex + Crossref' if item.crossref_at else 'OpenAlex',
                 str(item.year or 'Ano não informado'), item.fetched_at)
    elif isinstance(item, Researcher):
        data = item.data or {}
        organizations = []
        for category in ('employments', 'educations'):
            for group in ((data.get('activities-summary') or {}).get(category) or {}).get('affiliation-group', []):
                for entry in group.get('summaries', []):
                    organizations.extend((v.get('organization') or {}).get('name', '') for v in entry.values() if isinstance(v, dict))
        document(db, 'researcher', 'orcid:' + item.orcid, item.name, item.orcid + ' ' + ' '.join(organizations),
                 'ORCID', 'Perfil público consultado', item.fetched_at)
    elif isinstance(item, Dataset):
        document(db, 'dataset', item.id, item.title,
                 ' '.join(f"{r.get('name', '')} {r.get('format', '')}" for r in item.resources or []), item.portal or 'UFRN',
                 f'{len(item.resources or [])} recursos', item.fetched_at)


@event.listens_for(OrmSession, 'before_flush')
def index_changed_entities(db, flush_context, instances):
    candidates = [o for o in list(db.new) + list(db.dirty) if isinstance(o, (Institution, Profile, Publication, Researcher, Dataset))]
    for item in candidates:
        sync_record(db, item)
