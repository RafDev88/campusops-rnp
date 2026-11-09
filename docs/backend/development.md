# Desenvolvimento e configuração

## Docker: ambiente completo

Pré-requisitos: Docker com Compose. Na raiz do projeto, em uma instalação nova:

```powershell
Copy-Item .env.example .env
# Edite .env e configure POSTGRES_PASSWORD antes de iniciar.
docker compose up --build -d
docker compose ps
```

Não substitua um `.env` existente. Use senha alfanumérica para o banco, pois o Compose a interpola diretamente na URL de conexão. Não versione o arquivo. O volume PostgreSQL preserva os dados entre recriações dos contêineres.

| Endereço | Uso |
| --- | --- |
| http://localhost:8080 | Interface via Nginx; encaminha `/api` para FastAPI |
| http://localhost:8000/docs | Swagger interativo |
| http://localhost:8000/redoc | Leitura do contrato HTTP |
| http://localhost:8000/openapi.json | Contrato para ferramentas |
| http://localhost:8000/api/health | Conexão com o banco; não testa fontes, Redis ou workers |

A API aplica Alembic no startup, prepara políticas iniciais e atualiza o inventário local de links. Workers aguardam a saúde da API. Execute uma instância do scheduler. Uma nova implantação com múltiplas réplicas da API deve coordenar a migração antes da expansão: não há lock de migração distribuído implementado.

## Variáveis de ambiente

| Variável | Padrão no código / Compose | Finalidade |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./campus.db` fora do Docker; PostgreSQL no Compose | Banco; configure antes de importar `app.database` |
| `POSTGRES_PASSWORD` | Obrigatória no Compose | Inicialização do PostgreSQL e conexão dos serviços |
| `REDIS_URL` | `redis://localhost:6379/0`; host `redis` no Compose | Broker Celery |
| `COOKIE_SECURE` | `false` | `true` exige HTTPS para transmitir o cookie |
| `OPENALEX_API_KEY` | Vazia | Acesso e cotas da conta OpenAlex; não ativa cobrança automaticamente |
| `ORCID_ACCESS_TOKEN` | Vazia | Autorização para as operações públicas que a exigirem |
| `SOURCE_CA_BUNDLE` | Certifi quando não definido | Caminho interno de bundle confiável; exige disponibilizar o arquivo no contêiner |
| `WEBHOOK_ALLOWED_HOSTS` | Vazia | Domínios HTTPS autorizados, separados por vírgula |
| `WEBHOOK_SIGNING_SECRET` | Vazia | Segredo HMAC compartilhado com destinatários |

Políticas de fontes, agendas e limites de monitoramento são persistidos no banco e administrados pela API; não são variáveis de ambiente. Nunca use credenciais reais nos exemplos ou nos testes. A aplicação também inclui um intermediário público para completar a cadeia TLS UFRN; consulte [certificados](../../backend/certificates/README.md).

## API local para desenvolvimento

Na raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.lock
Set-Location backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Sem `DATABASE_URL`, o SQLite fica relativo ao diretório atual. Use um banco de desenvolvimento separado. SQLite habilita chaves estrangeiras; não oferece trigramas nem reproduz toda a concorrência do PostgreSQL. A busca informa `features.approximate=false` nesse ambiente.

Iniciar somente Uvicorn permite consultar a API, mas não processa tarefas. Prefira os workers Docker no Windows. Para um ambiente de desenvolvimento totalmente separado, configure seu próprio Redis e `DATABASE_URL` e execute em terminais distintos:

```powershell
..\.venv\Scripts\python -m celery -A app.tasks:celery worker -Q ingestion,control,reports,notifications,monitoring --pool=solo --loglevel=INFO
..\.venv\Scripts\python -m celery -A app.tasks:celery beat --schedule=./campusops-dev-beat --loglevel=INFO
```

Esse worker único é uma conveniência local; o Compose usa filas/processos separados. Não conecte uma API de teste ao broker usado pelos workers do banco principal: identificadores de tarefas poderiam ser consumidos no ambiente errado.

## Testes e verificações

Na raiz:

```powershell
Set-Location backend
..\.venv\Scripts\python -m pytest tests -q
Set-Location ..
.\.venv\Scripts\python scripts/document-backend.py --check
```

As fixtures criam bancos SQLite temporários e substituem publicação de tarefas e transportes quando necessário. Os cenários incluem autorização, CSRF, privacidade, migrações, contratos de fontes, busca, retomada, fluxos, relatórios e proteção de rede do monitor. Não usam a conta real do usuário.

Para validar PostgreSQL, o script abaixo cria um banco temporário com nome aleatório, aplica migrações, verifica busca/permissões e o remove ao terminar. Requer o serviço de banco local e autorização de criação de banco que o Compose fornece ao usuário do PostgreSQL:

```powershell
Get-Content -Raw scripts/verify-postgres.py | docker compose exec -T api python -
```

O script usa broker `memory://`, evitando publicar tarefas de QA para os workers reais. O CI também executa build Vue e teste de navegador; consulte [validação](../validation.md). Testes locais não comprovam desempenho de produção ou disponibilidade futura dos provedores.

## Alterar e entregar

1. Identifique o módulo e mantenha a validação de acesso no servidor.
2. Se alterar persistência, crie migração Alembic e teste preservação de registros; não use `create_all` para atualizar produção.
3. Teste o comportamento afetado, com transportes externos simulados.
4. Regenere a referência e execute sua verificação.
5. Antes de migração, faça backup; confira os procedimentos do [runbook](../runbook.md).
6. Reconstrua os serviços Python que compartilham o código com `docker compose up --build -d` e confira saúde/logs.

Não execute `docker compose down -v` para atualizar: remove volumes. Rollback de imagem não equivale a rollback de dados ou schema.
