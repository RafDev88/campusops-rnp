"""Bounded HTTP probes pinned to validated public IPs on every redirect."""
import hashlib
import http.client
import ipaddress
import json
import os
import socket
import ssl
from datetime import datetime,timezone
from time import perf_counter
from urllib.parse import parse_qsl,quote,urljoin,urlsplit,urlunsplit
from .providers import source_ssl_context

API_ENDPOINTS={
    'ror':('ROR','https://api.ror.org/v2/organizations?filter=locations.geonames_details.country_code:BR&page=1'),
    'openalex':('OpenAlex','https://api.openalex.org/works?per_page=1'),
    'crossref':('Crossref','https://api.crossref.org/works?rows=0'),
    'orcid':('ORCID','https://pub.orcid.org/v3.0/0000-0002-1825-0097/person'),
    'ufrn':('Dados abertos UFRN','https://dados.ufrn.br/api/3/action/package_search?rows=0'),
}
MAX_BODY=262144


class ProbeError(Exception):
    def __init__(self,code,message,retry_after=None):
        self.code,self.message,self.retry_after=code,message,retry_after
        super().__init__(message)


def normalize_url(url):
    try:
        if not isinstance(url,str) or len(url)>2048 or any(ord(c)<32 for c in url):raise ValueError()
        parts=urlsplit(url.strip())
        if parts.scheme not in ('https','http') or not parts.hostname or parts.username or parts.password:raise ValueError()
        host=parts.hostname.encode('idna').decode().lower().rstrip('.')
        if len(host)>253 or host=='localhost' or host.endswith(('.localhost','.local','.internal')):raise ValueError()
        port=parts.port or (443 if parts.scheme=='https' else 80)
        if port!=(443 if parts.scheme=='https' else 80):raise ValueError()
        try:
            if not public_ip(host):raise ValueError()
        except ValueError:
            # Distinguish a DNS name from a prohibited literal address.
            try:ipaddress.ip_address(host)
            except ValueError:pass
            else:raise ValueError()
        secret_keys={'key','api_key','apikey','token','access_token','authorization','signature','x-amz-signature','x-goog-signature'}
        if any(k.casefold() in secret_keys for k,_ in parse_qsl(parts.query)):raise ValueError('Não monitore endereços com segredos ou assinaturas na URL.')
        authority='['+host+']' if ':' in host else host
        return urlunsplit((parts.scheme,authority,quote(parts.path or '/',safe="/%:@!$&'()*+,;=-._~"),quote(parts.query,safe="=&%/:?@!$'()*+,;~-._"),''))
    except (ValueError,UnicodeError) as exc:
        raise ValueError(str(exc) or 'Use um endereço HTTP/HTTPS público, sem credenciais e na porta padrão.') from None


def url_key(url):return hashlib.sha256(url.encode()).hexdigest()


def public_ip(value):
    address=ipaddress.ip_address(value)
    return address.is_global and not (address.is_multicast or address.is_reserved or address.is_unspecified)


def resolve_public(host,port):
    try:addresses=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    except socket.gaierror:raise ProbeError('dns_error','Não foi possível localizar o domínio no DNS.') from None
    if not addresses or any(not public_ip(row[4][0]) for row in addresses):
        raise ProbeError('blocked','O domínio resolve para rede privada ou endereço reservado; a consulta foi bloqueada.')
    # Docker deployments may resolve AAAA records without an IPv6 route.
    addresses.sort(key=lambda row:ipaddress.ip_address(row[4][0]).version)
    return addresses[0][4][0]


class PinnedConnection(http.client.HTTPConnection):
    def __init__(self,host,ip,secure,timeout,context):
        super().__init__(host,443 if secure else 80,timeout=timeout)
        self.ip,self.secure,self.context=ip,secure,context
        self.timings,self.tls={},{}

    def connect(self):
        start=perf_counter()
        raw=socket.create_connection((self.ip,self.port),self.timeout)
        self.timings['connect_ms']=round((perf_counter()-start)*1000)
        try:
            if self.secure:
                start=perf_counter()
                self.sock=self.context.wrap_socket(raw,server_hostname=self.host)
                self.timings['tls_ms']=round((perf_counter()-start)*1000)
                peer=self.sock.getpeercert()
                expiry=ssl.cert_time_to_seconds(peer['notAfter'])
                self.tls={'expires_at':datetime.fromtimestamp(expiry,timezone.utc).isoformat(),
                    'days_remaining':int((expiry-datetime.now(timezone.utc).timestamp())//86400),
                    'version':self.sock.version(),'issuer':', '.join(value for part in peer.get('issuer',[]) for name,value in part if name=='commonName')}
            else:self.sock=raw
        except BaseException:
            raw.close();raise


def request_once(url,method,headers,reserve,timeout):
    parts=urlsplit(url);host=parts.hostname;port=443 if parts.scheme=='https' else 80
    reserve(host)  # Reserve even failed DNS/connect attempts; do not exceed budgets.
    start=perf_counter();ip=resolve_public(host,port);dns_ms=round((perf_counter()-start)*1000)
    connection=PinnedConnection(host,ip,parts.scheme=='https',timeout,source_ssl_context())
    try:
        connection.connect()
        start=perf_counter()
        connection.request(method,parts.path+('?' + parts.query if parts.query else ''),headers={'User-Agent':'CampusOps-Monitor/0.6','Connection':'close',**headers})
        response=connection.getresponse()
        body=response.read(MAX_BODY+1) if method=='GET' else b''
        return {'status':response.status,'headers':{k.lower():v for k,v in response.getheaders()},'body':body,
            'timings':{'dns_ms':dns_ms,**connection.timings,'http_ms':round((perf_counter()-start)*1000)},'tls':connection.tls}
    finally:connection.close()


def valid_contract(source,payload):
    if not isinstance(payload,dict):return False
    if source=='ror':return isinstance(payload.get('items'),list)
    if source=='openalex':return isinstance(payload.get('results'),list) and isinstance(payload.get('meta'),dict)
    if source=='crossref':return isinstance(payload.get('message'),dict) and isinstance(payload['message'].get('items'),list)
    if source=='orcid':return isinstance(payload.get('name'),dict)
    if source=='ufrn':return payload.get('success') is True and isinstance(payload.get('result'),dict)
    return True


def probe(url,source='',kind='manual',reserve=lambda host:None,requester=request_once,certificate_days=30,expected_type=''):
    start=perf_counter();current=url;redirects=[];timings={};tls={};method='GET' if kind=='api' else 'HEAD'
    code=None;certificates={}
    result={'ok':False,'final_url':url,'http_status':None,'method':method,'redirects':redirects,'tls':tls,'timings':timings}
    try:
        current=normalize_url(url);original=current;seen={current}
        for hop in range(6):
            result.update(final_url=current,http_status=None)
            remaining=40-(perf_counter()-start)
            if remaining<=0:raise ProbeError('timeout','A verificação excedeu o limite total de 40 segundos.')
            headers={'Accept':'application/json' if kind=='api' else '*/*','Accept-Encoding':'identity'}
            # Credentials are only attached to the exact built-in reference URL.
            if kind=='api' and source in API_ENDPOINTS and current==normalize_url(API_ENDPOINTS[source][1]):
                token=os.getenv('OPENALEX_API_KEY' if source=='openalex' else 'ORCID_ACCESS_TOKEN' if source=='orcid' else '_CAMPUSOPS_NO_TOKEN','')
                if token:headers['Authorization']='Bearer '+token
            response=requester(current,method,headers,reserve,min(8,remaining))
            timings.update(response.get('timings') or {});tls=response.get('tls') or {}
            if tls:certificates[urlsplit(current).hostname]={**tls,'host':urlsplit(current).hostname}
            code=response['status'];result.update(http_status=code,tls=tls,final_url=current,method=method)
            if code in (301,302,303,307,308):
                destination=response.get('headers',{}).get('location')
                if not destination:raise ProbeError('redirect_error','Redirecionamento sem endereço de destino.')
                try:destination=normalize_url(urljoin(current,destination))
                except ValueError:raise ProbeError('blocked','O redirecionamento apontou para um destino não permitido.') from None
                if current.startswith('https:') and destination.startswith('http:'):raise ProbeError('redirect_error','O endereço HTTPS redireciona para uma conexão HTTP sem proteção.')
                if destination in seen or hop==5:raise ProbeError('redirect_error','Redirecionamento circular ou com mais de cinco etapas.')
                redirects.append({'status':code,'from':current,'to':destination});seen.add(destination);current=destination
                continue
            if method=='HEAD' and code in (405,501):
                method='GET'
                remaining=40-(perf_counter()-start)
                if remaining<=0:raise ProbeError('timeout','Tempo limite de verificação atingido.')
                response=requester(current,method,headers,reserve,min(8,remaining));code=response['status']
                tls=response.get('tls') or tls;timings.update(response.get('timings') or {})
                if tls:certificates[urlsplit(current).hostname]={**tls,'host':urlsplit(current).hostname}
                result.update(http_status=code,method=method,tls=tls)
                # A GET fallback may redirect too; process it through the next hop.
                if code in (301,302,303,307,308):
                    destination=response.get('headers',{}).get('location')
                    if not destination:raise ProbeError('redirect_error','GET de fallback retornou redirecionamento sem destino.')
                    try:destination=normalize_url(urljoin(current,destination))
                    except ValueError:raise ProbeError('blocked','Destino do redirecionamento não permitido.') from None
                    if current.startswith('https:') and destination.startswith('http:'):raise ProbeError('redirect_error','Redirecionamento de HTTPS para HTTP bloqueado.')
                    if destination in seen or hop==5:raise ProbeError('redirect_error','Redirecionamento circular ou excessivo.')
                    redirects.append({'status':code,'from':current,'to':destination});seen.add(destination);current=destination;continue
            if 200<=code<300:
                wanted=expected_type or ('pdf' if urlsplit(original).path.casefold().endswith('.pdf') else '')
                content_type=response.get('headers',{}).get('content-type','').casefold()
                if wanted and ('text/html' in content_type or 'application/xhtml' in content_type):
                    raise ProbeError('invalid_content',f'O endereço respondeu HTML quando se esperava um arquivo {wanted.upper()}. Pode ser uma página de acesso ou erro; confira a origem.')
                if kind=='api':
                    if len(response.get('body',b''))>MAX_BODY:raise ProbeError('invalid_content','A resposta excedeu o limite de leitura do monitor. A estrutura do endpoint não foi validada.')
                    try:payload=json.loads(response.get('body',b''))
                    except (ValueError,UnicodeError):raise ProbeError('invalid_content','O endpoint respondeu, mas o conteúdo não é um JSON válido dentro do limite de leitura.') from None
                    if not valid_contract(source,payload):raise ProbeError('invalid_content','O JSON recebido não tem a estrutura esperada para este endpoint de referência.')
                message='Endpoint respondeu com JSON na estrutura esperada.' if kind=='api' else f'Endereço respondeu HTTP {code}; o conteúdo completo não foi validado.'
                if redirects:message+=' Houve redirecionamento; o endereço original foi preservado.'
                result.update(ok=True,outcome='redirected' if redirects else 'available',message=message)
                if current.startswith('http:'):result.update(outcome='http_insecure',message='O endereço respondeu por HTTP, sem proteção HTTPS.')
                elif tls.get('days_remaining',9999)<=certificate_days:result.update(outcome='tls_expiring',message=f"Certificado válido, mas vence em {tls['days_remaining']} dias.")
                elif perf_counter()-start>3:result.update(outcome='slow',message='Resposta esperada recebida, com duração superior a três segundos.')
            else:
                outcome,message={401:('auth_required','O endpoint exige credenciais válidas; isso não comprova indisponibilidade da API.'),403:('forbidden','A fonte recusou esta consulta. Pode haver restrição de acesso ou proteção contra robôs.'),404:('not_found','Este endereço ou registro não foi encontrado; isso não indica falha de toda a fonte.'),429:('rate_limited','Limite de consultas da fonte atingido. A próxima verificação respeitará Retry-After.')}.get(code,('server_error','O servidor da fonte retornou um erro.') if code>=500 else ('http_error',f'Resposta HTTP {code} não esperada.'))
                result.update(outcome=outcome,message=message)
                if code==429:
                    from email.utils import parsedate_to_datetime
                    value=response.get('headers',{}).get('retry-after','')
                    try:delay=float(value)
                    except ValueError:
                        try:delay=(parsedate_to_datetime(value)-datetime.now(timezone.utc)).total_seconds()
                        except (ValueError,TypeError,OverflowError):delay=900
                    result['retry_after']=max(60,min(86400,delay))
            break
    except ssl.SSLCertVerificationError as exc:
        explanation={10:'O certificado HTTPS está vencido.',9:'O certificado HTTPS ainda não é válido.',18:'O certificado é autoassinado e não é confiável.',19:'A cadeia contém um certificado autoassinado não confiável.',20:'Não foi possível completar a cadeia até uma autoridade confiável.',21:'Não foi possível verificar a cadeia do certificado.',62:'O certificado não corresponde ao domínio solicitado.',64:'O certificado não corresponde ao endereço solicitado.'}.get(exc.verify_code,'Não foi possível validar o certificado ou a cadeia HTTPS.')
        result.update(outcome='tls_error',message=explanation+' A validação HTTPS foi mantida.',tls={'verify_code':exc.verify_code})
    except ssl.SSLError:result.update(outcome='tls_error',message='Falha na negociação TLS. Verifique a compatibilidade e a cadeia HTTPS.')
    except (TimeoutError,socket.timeout):result.update(outcome='timeout',message='A fonte não respondeu dentro do limite de tempo.')
    except ProbeError as exc:result.update(outcome=exc.code,message=exc.message,retry_after=exc.retry_after)
    except ValueError:result.update(outcome='blocked',message='O endereço não atende às regras de destino público permitido.')
    except (OSError,http.client.HTTPException):result.update(outcome='connection_error',message='Não foi possível concluir a conexão com o endereço.')
    result['duration_ms']=round((perf_counter()-start)*1000)
    if certificates:
        shortest=min(certificates.values(),key=lambda item:item.get('days_remaining',99999))
        if result.get('ok') and shortest.get('days_remaining',9999)<=certificate_days:
            result.update(outcome='tls_expiring',message=f"Certificado de {shortest['host']} válido, com vencimento em {shortest['days_remaining']} dias.")
        result['tls']={**result.get('tls',{}),'certificates':list(certificates.values())}
        if 'verify_code' not in result['tls']:result['tls'].update(shortest)
    return result
