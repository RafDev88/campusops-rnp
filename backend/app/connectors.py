import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


def transient(exc):
    return isinstance(exc, httpx.TransportError) or (
        isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {429, 500, 502, 503, 504}
    )


class RorConnector:
    """Bounded import of the first page; no arbitrary user-supplied URLs."""

    @retry(retry=retry_if_exception(transient), stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8), reraise=True)
    async def fetch(self):
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get('https://api.ror.org/v2/organizations', params={'filter': 'locations.geonames_details.country_code:BR', 'page': 1})
            response.raise_for_status()
            items = response.json()['items']
            result = []
            for item in items:
                names = item['names']
                name = next((n['value'] for n in names if 'ror_display' in n['types']), names[0]['value'])
                locations = item.get('locations', [])
                country = locations[0]['geonames_details']['country_name'] if locations else 'Não informado'
                result.append({'id': item['id'], 'name': name, 'country': country})
            return result
