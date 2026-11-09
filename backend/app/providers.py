"""Source adapters. Only fixed, trusted API origins are used for ingestion."""
import asyncio
import hashlib
import json
import os
import ssl
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import httpx
import certifi
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class SourceError(Exception):
    def __init__(self, code, message, retry_after=None):
        self.code, self.message = code, message
        self.retry_after = retry_after
        super().__init__(message)


class RorItem(BaseModel):
    id: str = Field(pattern=r'^https://ror\.org/[a-z0-9]+$')
    names: list[dict] = Field(min_length=1)
    locations: list[dict] = []


class OpenAlexWork(BaseModel):
    id: str = Field(pattern=r'^https://openalex\.org/W\d+$')
    display_name: str | None = None
    doi: str | None = None
    publication_year: int | None = None
    cited_by_count: int = 0
    open_access: dict = {}
    topics: list[dict] = []
    authorships: list[dict] = []
    model_config = ConfigDict(extra='allow')


def normalize_doi(value):
    if not value:
        return None
    value = value.strip().lower()
    for prefix in ('https://doi.org/', 'http://doi.org/', 'http://dx.doi.org/', 'https://dx.doi.org/', 'doi:'):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value if value.startswith('10.') and '/' in value else None


def source_ssl_context():
    context=ssl.create_default_context(cafile=os.getenv('SOURCE_CA_BUNDLE') or certifi.where())
    context.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
    context.load_verify_locations(cafile=str(Path(__file__).resolve().parents[1] / 'certificates' / 'rnp-icpedu-2025.pem'))
    return context


class Network:
    def __init__(self, client=None):
        self.client = client
        self.owned = client is None
        self.calls = 0
        self.retries = 0

    async def get(self, url, params=None, headers=None):
        if self.client is None:
            context = source_ssl_context()
            self.client = httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False,
                verify=context,
                headers={'User-Agent': 'CampusOps/0.6 (academic integration demo)'})
        client = self.client
        try:
            for attempt in range(3):
                try:
                    if hasattr(self,'before_request'):
                        await self.before_request()
                    self.calls += 1
                    response = await client.get(url, params=params, headers=headers)
                    if response.status_code in {429, 500, 502, 503, 504}:
                        if attempt == 2:
                            raise SourceError('rate_limited' if response.status_code == 429 else 'unavailable',
                                              f'Fonte respondeu HTTP {response.status_code} após três tentativas.')
                        delay = 2 ** attempt
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                delay = max(delay, float(retry_after))
                            except ValueError:
                                try:
                                    delay = max(delay, (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
                                except (ValueError, TypeError):
                                    pass
                        if delay > 120:
                            raise SourceError('rate_limited', 'Cota da fonte atingida. Aguarde a renovação antes de reprocessar.',retry_after=delay)
                        self.retries += 1
                        await asyncio.sleep(max(0, delay))
                        continue
                    if response.status_code in {401, 403}:
                        raise SourceError('credentials', 'A fonte exige credenciais válidas. Configure o acesso nas variáveis do servidor.')
                    if response.status_code == 404:
                        raise SourceError('not_found', 'Registro não encontrado na fonte consultada.')
                    response.raise_for_status()
                    return response.json()
                except httpx.TransportError as exc:
                    if 'CERTIFICATE_VERIFY_FAILED' in str(exc):
                        raise SourceError('tls_certificate', 'Não foi possível validar a cadeia TLS da fonte. Verifique os certificados do portal ou configure SOURCE_CA_BUNDLE com uma cadeia confiável.') from None
                    if attempt == 2:
                        raise SourceError('network', 'Não foi possível conectar à fonte após três tentativas.') from None
                    self.retries += 1
                    await asyncio.sleep(2 ** attempt)
        except httpx.HTTPStatusError as exc:
            raise SourceError('http_error', f'Fonte respondeu HTTP {exc.response.status_code}.') from None
        except (ValueError, KeyError, TypeError) as exc:
            raise SourceError('schema_change', 'A resposta da fonte não corresponde ao contrato esperado.') from exc

    async def aclose(self):
        if self.owned and self.client:
            await self.client.aclose()


class Providers:
    def __init__(self, network=None):
        self.net = network or Network()

    async def ror(self, params):
        results, total, complete = [], 0, False
        unique, received = {}, 0
        for page in range(1, params.get('max_pages', 500) + 1):
            payload = await self.net.get('https://api.ror.org/v2/organizations',
                params={'filter': 'locations.geonames_details.country_code:BR', 'page': page})
            if not isinstance(payload.get('items'), list):
                raise SourceError('schema_change', 'ROR não retornou a lista de instituições esperada.')
            total = int(payload['number_of_results'])
            for raw in payload['items']:
                try:
                    item = RorItem.model_validate(raw)
                    name = next((n['value'] for n in item.names if 'ror_display' in n['types']), item.names[0]['value'])
                    country = item.locations[0]['geonames_details']['country_name'] if item.locations else 'Não informado'
                    received += 1
                    unique[item.id] = {'id': item.id, 'name': name, 'country': country, 'data': raw}
                except (ValidationError, KeyError, IndexError, TypeError):
                    raise SourceError('schema_change', 'Um registro ROR mudou de estrutura; a importação foi interrompida.') from None
            if page * 20 >= total or not payload['items']:
                complete = len(unique) >= total
                break
            await asyncio.sleep(.12)
        results = list(unique.values())
        return results, {'reported_total': total, 'received_records': received, 'unique_records': len(results),
                         'duplicate_records': received - len(results), 'pages': page, 'complete': complete,
                         'scope': 'Instituições brasileiras no ROR; paginação da API, não snapshot integral.'}

    async def openalex(self, institution_id, params):
        key = os.getenv('OPENALEX_API_KEY', '')
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        identifier = institution_id.rsplit('/', 1)[-1]
        profile = await self.net.get(f'https://api.openalex.org/institutions/ror:{quote(identifier)}', headers=headers)
        if not str(profile.get('id', '')).startswith('https://openalex.org/I'):
            raise SourceError('schema_change', 'Perfil OpenAlex sem identificador institucional válido.')
        results, total, cursor, complete = [], 0, '*', False
        unique, received = {}, 0
        pages = min(params.get('max_pages', 3), 500 if key else 100)
        seen_cursors=set()
        for page in range(1, pages + 1):
            query = {'filter': f"institutions.id:{profile['id']},from_publication_date:{params.get('_since') or str(params.get('year_from', 2024))+'-01-01'}",
                     'per_page': 100, 'sort': 'publication_date:desc'}
            query['cursor' if key else 'page'] = cursor if key else page
            if params.get('query'):query['search']=params['query']
            for name,value in [('to_publication_date',str(params['year_to'])+'-12-31' if params.get('year_to') else ''),('language',params.get('language')),('type',params.get('work_type'))]:
                if value:query['filter']+=f',{name}:{value}'
            payload = await self.net.get('https://api.openalex.org/works', params=query, headers=headers)
            if not isinstance(payload.get('results'), list):
                raise SourceError('schema_change', 'OpenAlex não retornou a lista de publicações esperada.')
            total = int(payload['meta']['count'])
            for raw in payload['results']:
                try:
                    item = OpenAlexWork.model_validate(raw)
                except ValidationError:
                    raise SourceError('schema_change', 'Publicação fora do contrato OpenAlex; importação interrompida.') from None
                authors, affiliations = [], {}
                for authorship in item.authorships:
                    author = authorship.get('author') or {}
                    authors.append({'name': author.get('display_name', ''), 'orcid': author.get('orcid'),'openalex_id':author.get('id')})
                    for inst in authorship.get('institutions', []):
                        affiliations[inst['id']] = {'id': inst['id'], 'ror': inst.get('ror'), 'name': inst.get('display_name', '')}
                received += 1
                unique[item.id] = {'id': item.id, 'openalex_id': item.id, 'doi': normalize_doi(item.doi),
                    'title': item.display_name or '(Sem título)', 'year': item.publication_year,
                    'is_oa': bool(item.open_access.get('is_oa')), 'citations': item.cited_by_count,
                    'topics': [{'id': t['id'], 'name': t['display_name']} for t in item.topics],
                    'authors': authors, 'affiliations': list(affiliations.values()), 'openalex': raw}
            cursor = payload.get('meta', {}).get('next_cursor')
            if key and cursor and cursor in seen_cursors:break
            if cursor:seen_cursors.add(cursor)
            if not payload['results'] or page * 100 >= total or (key and not cursor):
                complete = len(unique) >= total
                break
            await asyncio.sleep(.15)
        results = list(unique.values())
        return profile, results, {'institution_id': institution_id, 'reported_total': total, 'imported': len(results),
            'received_records': received, 'duplicate_records': received - len(results),
            'pages': page, 'complete': complete, 'year_from': params.get('year_from', 2024), 'source': 'OpenAlex',
            'scope': 'Trabalhos associados diretamente à instituição, no período escolhido.'}

    async def crossref(self, doi):
        payload = await self.net.get('https://api.crossref.org/works/' + quote(doi, safe=''),
                                    headers={'User-Agent': 'CampusOps/0.6'})
        item = payload.get('message')
        if not isinstance(item, dict) or normalize_doi(item.get('DOI')) != normalize_doi(doi):
            raise SourceError('schema_change', 'Crossref retornou um DOI diferente do solicitado.')
        return item

    async def orcid(self, identifier):
        headers = {'Accept': 'application/json'}
        token = os.getenv('ORCID_ACCESS_TOKEN')
        if token:
            headers['Authorization'] = f'Bearer {token}'
        payload = await self.net.get(f'https://pub.orcid.org/v3.0/{identifier}/record', headers=headers)
        if not isinstance(payload.get('person'), dict):
            raise SourceError('schema_change', 'ORCID não retornou um registro público válido.')
        name = payload['person'].get('name') or {}
        label = ' '.join((name.get(k) or {}).get('value') or '' for k in ['given-names', 'family-name']).strip()
        return {'orcid': identifier, 'name': label or identifier, 'data': payload}

    async def ufrn(self, params):
        results, total, complete = [], 0, False
        for page in range(params.get('max_pages', 10)):
            payload = await self.net.get('https://dados.ufrn.br/api/3/action/package_search',
                params={'q': params.get('query') or '*:*', 'rows': 50, 'start': page * 50, 'sort': 'id asc'})
            if payload.get('success') is not True or not isinstance(payload.get('result', {}).get('results'), list):
                raise SourceError('schema_change', 'Catálogo UFRN fora do contrato CKAN esperado.')
            total = payload['result']['count']
            for item in payload['result']['results']:
                resources = [{'id': r['id'], 'name': r.get('name') or '', 'format': r.get('format') or '',
                              'url': r.get('url') or '', 'modified': r.get('last_modified') or ''}
                             for r in item.get('resources', [])]
                resources.sort(key=lambda resource: resource['id'])
                signature = {'title': item['title'], 'modified': item.get('metadata_modified', ''), 'resources': resources}
                results.append({'id': item['id'], 'title': item['title'], 'modified': item.get('metadata_modified', ''),
                    'url': 'https://dados.ufrn.br/dataset/' + quote(item['name'], safe=''), 'resources': resources,
                    'fingerprint': hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()})
            if (page + 1) * 50 >= total or not payload['result']['results']:
                complete = True
                break
            await asyncio.sleep(.15)
        return results, {'reported_total': total, 'pages': page + 1, 'complete': complete,
                         'scope': 'Metadados do catálogo UFRN. Conteúdo dos arquivos não é baixado.'}
