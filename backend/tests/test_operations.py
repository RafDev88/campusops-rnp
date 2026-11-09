import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.domain import Dataset, Event, Incident, Profile, Publication, Rule, Run, WorkInstitution
from app.models import Institution
from app.operations import enqueue, perform
from app.providers import SourceError


class FakeProvider:
    net = SimpleNamespace(calls=1, retries=0)
    fail = False
    fingerprint = 'first'

    async def ror(self, params):
        if self.fail:
            raise SourceError('network', 'Fonte indisponível.')
        return [{'id': 'https://ror.org/01abcde12', 'name': 'Universidade', 'country': 'Brazil', 'data': {}}], {'complete': True}

    async def openalex(self, institution_id, params):
        work = {'id': 'https://openalex.org/W123', 'openalex_id': 'https://openalex.org/W123', 'doi': '10.1000/abc',
                'title': 'Computer networks', 'year': 2025, 'is_oa': True, 'citations': 4,
                'topics': [{'id': 'T1', 'name': 'Networks'}], 'authors': [], 'affiliations': [], 'openalex': {'id': 'W123'}}
        return {'id': 'https://openalex.org/I1'}, [work], {'complete': False, 'institution_id': institution_id, 'year_from': 2024}

    async def ufrn(self, params):
        return [{'id': 'dataset1', 'title': 'Cursos', 'url': 'https://dados.ufrn.br/dataset/cursos', 'modified': '',
                 'resources': [], 'fingerprint': self.fingerprint}], {'complete': True}


def run(factory, source, provider=None, params=None):
    identifier = enqueue(source, params or {})
    asyncio.run(perform(identifier, provider or FakeProvider()))
    with factory() as db:
        result = db.get(Run, identifier)
        db.expunge(result)
        return result


def test_durable_queue_prevents_overlapping_source_runs(database):
    factory, published = database
    identifier = enqueue('ror', {})
    assert published == [identifier]
    with pytest.raises(ValueError):
        enqueue('ror', {})
    asyncio.run(perform(identifier, FakeProvider()))
    assert enqueue('ror', {}) != identifier


def test_repeated_source_import_and_partial_coverage(database):
    factory, _ = database
    first = run(factory, 'ror')
    second = run(factory, 'ror')
    assert first.new == 1 and second.new == 0 and second.updated == 0
    with factory() as db:
        db.get(Profile, 'https://ror.org/01abcde12').watched = True
        db.add(Rule(name='Networks radar', kind='new_publication', source='openalex', topic='networks'))
        db.commit()
    first = run(factory, 'openalex')
    second = run(factory, 'openalex')
    assert first.status == 'partial' and first.new == 1
    assert second.new == 0
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Publication)) == 1
        assert db.scalar(select(func.count()).select_from(WorkInstitution)) == 1
        assert db.scalar(select(func.count()).select_from(Event)) == 1


def test_failure_streak_deduplicates_and_recovery_resolves(database):
    factory, _ = database
    with factory() as db:
        db.add(Rule(name='Three failures', kind='failure_streak', source='ror', threshold=3))
        db.commit()
    provider = FakeProvider()
    provider.fail = True
    for _ in range(4):
        assert run(factory, 'ror', provider).status == 'failed'
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Incident)) == 1
        assert db.scalar(select(Incident)).status == 'open'
    run(factory, 'ror')
    with factory() as db:
        assert db.scalar(select(Incident)).status == 'resolved'


def test_dataset_change_creates_one_event_per_fingerprint(database):
    factory, _ = database
    with factory() as db:
        db.add(Rule(name='Dataset changes', kind='dataset_changed', source='ufrn'))
        db.commit()
    run(factory, 'ufrn')
    provider = FakeProvider()
    provider.fingerprint = 'changed'
    assert run(factory, 'ufrn', provider).updated == 1
    run(factory, 'ufrn', provider)
    with factory() as db:
        assert db.scalar(select(func.count()).select_from(Dataset)) == 1
        assert db.scalar(select(func.count()).select_from(Event)) == 1


def test_schema_failure_does_not_overwrite_existing_catalog(database):
    factory, _ = database
    run(factory, 'ror')
    class Broken(FakeProvider):
        async def ror(self, params):
            raise SourceError('schema_change', 'Contrato mudou.')
    assert run(factory, 'ror', Broken()).error_code == 'schema_change'
    with factory() as db:
        assert db.get(Institution, 'https://ror.org/01abcde12').name == 'Universidade'


def test_crossref_missing_doi_is_rejected_without_overwriting_work(database):
    factory, _ = database
    with factory() as db:
        db.add(Publication(id='https://openalex.org/W1', openalex_id='https://openalex.org/W1',
                           title='Original title', doi='10.1000/abc'))
        db.commit()
    class MissingDoi(FakeProvider):
        async def crossref(self, doi):
            raise SourceError('not_found', 'Missing DOI')
    result = run(factory, 'crossref', MissingDoi())
    assert result.status == 'partial' and result.rejected == 1
    with factory() as db:
        work = db.get(Publication, 'https://openalex.org/W1')
        assert work.title == 'Original title' and work.crossref == {}


def test_missing_crossref_doi_does_not_starve_unqueried_works(database):
    factory, _ = database
    with factory() as db:
        db.add_all([Publication(id=f'W{i}', openalex_id=f'W{i}', title=f'Work {i}', doi=f'10.1000/{i}') for i in (1, 2)])
        db.commit()
    class Mixed(FakeProvider):
        async def crossref(self, doi):
            if doi == '10.1000/1':
                raise SourceError('not_found', 'Missing DOI')
            return {'DOI': doi, 'title': ['Enriched']}
    assert run(factory, 'crossref', Mixed(), {'limit': 1}).rejected == 1
    assert run(factory, 'crossref', Mixed(), {'limit': 1}).records == 1
    with factory() as db:
        assert db.get(Publication, 'W1').crossref_at is None
        assert db.get(Publication, 'W2').crossref['title'] == ['Enriched']
