# Guia do backend

O CampusOps separa **consulta local** de **atualização externa**. Uma pesquisa lê o catálogo já importado; uma coleta solicita trabalho aos workers. Isso permite consultar registros mesmo quando uma fonte externa está indisponível. Fonte, data de coleta e cobertura acompanham os resultados.

## Mapa de leitura

| Necessidade | Documento |
| --- | --- |
| Instalar, configurar e executar testes | [Desenvolvimento](development.md) |
| Entender módulos, dados e decisões | [Arquitetura](architecture.md) |
| Integrar um cliente, autenticar e pesquisar | [API e segurança](api.md) |
| Entender coletas, filas e recuperação | [Integrações e automações](automation.md) |
| Encontrar um endpoint, tabela ou filtro | [Referência gerada](reference.md) |
| Consultar colunas, nulabilidade, chaves e índices | [Dicionário de dados](data-dictionary.md) |
| Diagnosticar e atualizar o ambiente | [Runbook](../runbook.md) |
| Consultar evidências e limites dos testes | [Validação](../validation.md) |
| Backup verificado, benchmark e demonstração isolada | [Confiabilidade 0.8](../reliability.md) |

## Stack e responsabilidades

| Tecnologia | Papel |
| --- | --- |
| Python 3.13 / FastAPI / Pydantic | Servidor HTTP, dependências de acesso e validação de entrada |
| SQLAlchemy 2 / psycopg | Consultas parametrizadas, transações e conexão PostgreSQL |
| PostgreSQL 17 | Persistência compartilhada, constraints, índices GIN e pg_trgm |
| Alembic | Evolução versionada do schema |
| Celery / Redis 7 com AOF | Transporte de tarefas e execução em processos separados |
| HTTPX / Tenacity / certifi | Integrações HTTP, retentativas e cadeia TLS confiável |
| croniter | Calendários cron com fuso horário |
| pwdlib / Argon2 | Hash de senhas |
| structlog | Logs JSON com correlação de requisição |
| pytest / TestClient | Testes isolados de contratos, segurança e comportamento |

`backend/requirements.lock` fixa as versões utilizadas pela imagem; `requirements.txt` expressa faixas de dependências. Não há serviço de IA obrigatório nem chave de IA para executar o sistema.

## Como manter os documentos

Na raiz, execute `.\.venv\Scripts\python scripts/document-backend.py` após alterar rotas, dependências de acesso, modelos ou filtros. `--check` detecta divergências sem gravar arquivos. A referência usa o OpenAPI e os modelos locais; não inicializa a aplicação nem consulta fontes externas. O CI verifica essa referência.

Mudanças de comportamento também exigem atualizar o guia correspondente e seus testes. O schema OpenAPI ainda possui respostas dinâmicas sem modelos completos em vários handlers; parâmetros e corpos de entrada são descritos, mas não se deve inferir tipagem completa das respostas. A referência gerada não substitui exemplos e regras de negócio.
