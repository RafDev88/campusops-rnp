import asyncio

import httpx
import pytest

from app.providers import Network, Providers, SourceError, normalize_doi


def ror_record(identifier='01abcde12'):
    return {'id': 'https://ror.org/' + identifier, 'names': [{'value': 'Universidade Teste', 'types': ['ror_display']}],
            'locations': [{'geonames_details': {'country_name': 'Brazil'}}]}


def test_ror_pagination_and_explicit_partial_coverage(monkeypatch):
    async def no_wait(_): pass
    monkeypatch.setattr('app.providers.asyncio.sleep', no_wait)
    requests = []
    def handler(request):
        page = int(request.url.params['page'])
        requests.append(page)
        return httpx.Response(200, json={'number_of_results': 21,
            'items': [ror_record(f'{page}{i}') for i in range(20 if page == 1 else 1)]})
    async def collect(pages):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await Providers(Network(client)).ror({'max_pages': pages})
    rows, coverage = asyncio.run(collect(2))
    assert len(rows) == 21 and requests == [1, 2] and coverage['complete'] is True
    _, coverage = asyncio.run(collect(1))
    assert coverage['complete'] is False and coverage['reported_total'] == 21


def test_duplicate_ror_pages_never_claim_complete_coverage(monkeypatch):
    async def no_wait(_): pass
    monkeypatch.setattr('app.providers.asyncio.sleep', no_wait)
    async def run():
        payload = {'number_of_results': 21, 'items': [ror_record()]}
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))) as client:
            rows, coverage = await Providers(Network(client)).ror({'max_pages': 2})
            assert len(rows) == 1
            assert coverage['complete'] is False
            assert coverage['received_records'] == 2 and coverage['duplicate_records'] == 1
    asyncio.run(run())


def test_transient_errors_retry_but_permanent_errors_do_not(monkeypatch):
    async def no_wait(_): pass
    monkeypatch.setattr('app.providers.asyncio.sleep', no_wait)
    calls = []
    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={'Retry-After': '0'}) if len(calls) == 1 else httpx.Response(200, json={'ok': True})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            net = Network(client)
            assert await net.get('https://example.com') == {'ok': True}
            assert net.calls == 2 and net.retries == 1
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(401))) as client:
            net = Network(client)
            with pytest.raises(SourceError, match='credenciais'):
                await net.get('https://example.com')
            assert net.calls == 1
    asyncio.run(run())


def test_malformed_source_is_not_silently_accepted():
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'unexpected': []}))) as client:
            with pytest.raises(SourceError) as error:
                await Providers(Network(client)).ror({'max_pages': 1})
            assert error.value.code == 'schema_change'
    asyncio.run(run())


def test_crossref_normalization_and_identifier_validation():
    assert normalize_doi('HTTPS://DOI.ORG/10.1000/ABC') == '10.1000/abc'
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'message': {'DOI': '10.1000/other'}}))) as client:
            with pytest.raises(SourceError):
                await Providers(Network(client)).crossref('10.1000/abc')
    asyncio.run(run())


def test_openalex_pages_and_affiliation_mapping(monkeypatch):
    monkeypatch.delenv('OPENALEX_API_KEY', raising=False)
    async def no_wait(_): pass
    monkeypatch.setattr('app.providers.asyncio.sleep', no_wait)
    def work(identifier):
        return {'id': f'https://openalex.org/W{identifier}', 'display_name': 'Research', 'doi': 'https://doi.org/10.1000/ABC',
                'publication_year': 2025, 'topics': [{'id': 'T1', 'display_name': 'Networks'}],
                'authorships': [{'author': {'display_name': 'Ana', 'orcid': 'https://orcid.org/0000-0002-1825-0097'},
                    'institutions': [{'id': 'I1', 'ror': 'https://ror.org/01abcde12', 'display_name': 'University'}]}]}
    def handler(request):
        if '/institutions/' in request.url.path:
            return httpx.Response(200, json={'id': 'https://openalex.org/I1'})
        page = int(request.url.params['page'])
        return httpx.Response(200, json={'meta': {'count': 101},
            'results': [work(i) for i in range(1, 101)] if page == 1 else [work(101)]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            _, rows, scope = await Providers(Network(client)).openalex('https://ror.org/01abcde12', {'max_pages': 2, 'year_from': 2025})
            assert len(rows) == 101 and scope['complete'] is True
            assert rows[0]['doi'] == '10.1000/abc'
            assert rows[0]['affiliations'][0]['ror'] == 'https://ror.org/01abcde12'
    asyncio.run(run())


def test_ufrn_fingerprint_does_not_change_for_resource_order():
    calls = []
    def handler(request):
        calls.append(1)
        resources = [{'id': 'a', 'name': 'CSV', 'format': 'CSV', 'url': 'https://dados.ufrn.br/a.csv'},
                     {'id': 'b', 'name': 'PDF', 'format': 'PDF', 'url': 'https://dados.ufrn.br/b.pdf'}]
        if len(calls) == 2:
            resources.reverse()
        return httpx.Response(200, json={'success': True, 'result': {'count': 1, 'results': [
            {'id': 'courses', 'name': 'courses', 'title': 'Cursos', 'metadata_modified': '2026-01-01', 'resources': resources}]}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = Providers(Network(client))
            first, scope = await provider.ufrn({'max_pages': 1})
            second, _ = await provider.ufrn({'max_pages': 1})
            assert first[0]['fingerprint'] == second[0]['fingerprint'] and scope['complete'] is True
    asyncio.run(run())


def test_orcid_public_name_is_parsed_and_original_payload_is_retained():
    payload = {'person': {'name': {'given-names': {'value': 'Ana'}, 'family-name': {'value': 'Silva'}}}}
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload))) as client:
            result = await Providers(Network(client)).orcid('0000-0002-1825-0097')
            assert result['name'] == 'Ana Silva' and result['data'] == payload
    asyncio.run(run())


def test_invalid_tls_chain_is_not_retried():
    def handler(request):
        raise httpx.ConnectError('CERTIFICATE_VERIFY_FAILED', request=request)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            net = Network(client)
            with pytest.raises(SourceError) as result:
                await net.get('https://dados.ufrn.br')
            assert result.value.code == 'tls_certificate' and net.calls == 1
    asyncio.run(run())
