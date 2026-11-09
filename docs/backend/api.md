# Contrato HTTP e segurança

## Documentação navegável

Use [Swagger](http://localhost:8000/docs), [ReDoc](http://localhost:8000/redoc) e [OpenAPI](http://localhost:8000/openapi.json). Cada operação é agrupada por módulo, informa o perfil mínimo, declara sessão quando necessária e documenta `X-CampusOps: 1` nas escritas. `x-access-level` permite consultar a classificação por ferramenta.

Os requisitos derivam das dependências reais de acesso. Regras internas também podem restringir um recurso: ter perfil de consulta não permite ler o relatório privado de outra conta. A [referência gerada](reference.md) lista todas as operações.

## Sessão e permissões

Não existe senha padrão. `GET /api/auth/status` informa se é necessário o setup. `POST /api/auth/setup` cria o primeiro administrador somente em um banco vazio; depois, administradores gerenciam contas. Para uma instalação existente, faça login, sem tentar executar setup novamente.

O login retorna o usuário público e um cookie `campusops_session`, HttpOnly, SameSite Strict, com validade de oito horas. O banco guarda o hash SHA-256 do token aleatório, não o token original. Senhas usam Argon2. `COOKIE_SECURE=true` habilita a exigência de HTTPS no cookie. Logout remove a sessão, e contas desativadas perdem acesso na próxima requisição.

| Perfil | Acesso geral |
| --- | --- |
| `viewer` | Consultas e biblioteca/relatórios pessoais; algumas agendas pessoais conforme o tipo de destino |
| `operator` | Consulta e operação de coletas, fluxos, regras e monitores |
| `admin` | Operação, usuários e políticas/configurações administrativas |

O perfil mínimo está em cada operação; calendários verificam também tipo de destino e propriedade. Não existe cadastro público após o setup, recuperação por e-mail ou autenticação Bearer/JWT. Login tem limite por combinação IP/usuário: dez tentativas em dez minutos.

## Exemplo seguro com PowerShell

Execute com uma conta existente. A senha é solicitada no terminal e não aparece no comando nem precisa ser gravada em arquivo:

```powershell
$base = 'http://localhost:8000'
$credential = Get-Credential -Message 'Conta existente do CampusOps'
$body = @{
    username = $credential.UserName
    password = $credential.GetNetworkCredential().Password
} | ConvertTo-Json
$headers = @{ 'X-CampusOps' = '1' }
Invoke-RestMethod "$base/api/auth/login" -Method Post -Headers $headers `
    -ContentType 'application/json' -Body $body -SessionVariable campusSession
Remove-Variable body,credential

Invoke-RestMethod "$base/api/auth/me" -WebSession $campusSession
Invoke-RestMethod "$base/api/publications?q=educacao&year_from=2024&limit=10" `
    -WebSession $campusSession

Invoke-RestMethod "$base/api/auth/logout" -Method Post -Headers $headers `
    -WebSession $campusSession
```

No Swagger, execute login com `X-CampusOps=1`; o navegador recebe o cookie automaticamente. Login e Swagger devem usar a mesma origem. O botão Authorize não consegue definir manualmente um cookie HttpOnly no navegador. Não cole tokens de sessão em tickets, logs ou documentação.

O middleware exige o cabeçalho também no login, setup, prévias e demais POSTs. Ele complementa cookies SameSite e a política de mesma origem; não é um segredo de autenticação. A aplicação não habilita CORS permissivo. O frontend usa proxy de mesma origem.

## Pesquisa e paginação

Exemplo: `GET /api/publications?q=redes&mode=all&language=pt&has_doi=true&offset=0&limit=25`.

A lista retorna `total`, `items`, `features.approximate` e `scope`. Itens incluem identidade, título, autores, ano, DOI, acesso aberto, citações, temas, afiliações, fonte, datas de coleta, favorito e resumo curto quando disponível. `GET /api/publication?id=...` fornece a ficha detalhada. IDs externos contendo `/`, `:`, espaços ou parâmetros devem ser codificados com a biblioteca HTTP do cliente, sem concatenação manual insegura.

| Critério | Semântica |
| --- | --- |
| `mode=all/any/phrase/exact` | Todas as palavras, qualquer palavra, frase em ordem ou correspondência exata do campo de título por padrão |
| `search_in=all/title/abstract` | Escopo textual |
| `approximate=true` | Aproximação opcional no PostgreSQL; não substitui correspondência exata de IDs |
| `institution_id`, `topic`, `author_id` | Identidades para relações do catálogo; `author` permite texto |
| `year`, `year_from`, `year_to` | Ano exato e limites; intervalo invertido é inválido |
| `oa`, `has_doi`, `has_abstract`, `retracted` | Ausente não filtra; `true` e `false` são critérios distintos |
| `language` | Idioma informado nos metadados, sem traduzir conteúdo |
| `work_type`, `journal`, `citations_min` | Tipo, veículo e mínimo de citações |
| `source=crossref` | Trabalhos enriquecidos, sem duplicar a publicação OpenAlex |
| `favorites=true` | Apenas itens da conta autenticada |
| `sort` | `relevance`, `recent`, `title` ou `citations` |

Publicações usam `offset` e `limit` de 1 a 100, padrão 25. Outros endpoints possuem limites próprios: confira o OpenAPI em vez de presumir paginação uniforme. Facetas refletem os demais critérios, desconsiderando seu próprio filtro. CSV reutiliza critérios/ordenação e limita a 10 mil resultados; campos potencialmente interpretados como fórmulas são escapados.

`GET /api/search` integra os tipos do catálogo, e `/api/search/suggestions` fornece sugestões. Nenhuma dessas rotas consulta provedores externos ao digitar. A busca não representa toda a produção de uma instituição.

## Comandos assíncronos

`POST /api/sync` aceita `SyncRequest` e retorna 202 com a execução enfileirada. Exemplo de corpo para uma instituição **já cadastrada**, substituindo o identificador pelo valor real:

```json
{
  "source": "openalex",
  "institution_id": "https://ror.org/IDENTIFICADOR_REAL",
  "year_from": 2024,
  "max_pages": 1,
  "incremental": true
}
```

Acompanhe `/api/runs` e `/api/runs/{identifier}/runtime`. `202` não significa coleta concluída. Fonte ocupada pode produzir `409`; uma execução parcial deve ser avaliada pela cobertura e rejeições. Fluxos, relatórios e verificações usam recursos próprios da [referência](reference.md).

## Erros e correlação

| HTTP | Interpretação usual |
| --- | --- |
| 400 | Comando inválido no contexto do recurso |
| 401 | Sessão ausente/expirada ou conta desativada |
| 403 | CSRF ausente/inválido ou perfil insuficiente |
| 404 | Recurso inexistente ou indisponível para a conta |
| 409 | Conflito de estado, fonte ocupada ou identidade duplicada |
| 422 | Validação de campos/parâmetros |
| 429 | Limite de autenticação ou intervalo/limite operacional |
| 500 | Falha interna; correlacione com logs |

Erros HTTP retornam `detail`, `code` e `request_id`. `detail` é uma mensagem nos erros de negócio e uma lista de problemas na validação; os campos `input` e `ctx` não são devolvidos. O código permite distinguir autenticação, permissão, conflito e validação sem analisar a mensagem. Falhas inesperadas retornam 500 genérico. Falhas de uma tarefa ficam registradas na execução; não são necessariamente o status HTTP da consulta que a acompanha.

Respostas que passam pelo middleware recebem `X-Request-ID`, `Cache-Control: no-store` e `X-Content-Type-Options: nosniff`, inclusive rejeições CSRF. Logs não devem receber corpos de login ou cookies. `/api/metrics` oferece formato Prometheus para administradores autenticados; não é um endpoint público de scraping.

## Conta e acompanhamento · 0.8

`GET /api/account/sessions` lista apenas sessões válidas da própria conta com ID não autenticador, expiração e indicação do acesso atual; não expõe cookie ou hash persistido. `DELETE /api/account/sessions/{identifier}` revoga somente sessão própria. `POST /api/account/password` exige senha atual e nova senha de 10–128 caracteres; respeita o limite de autenticação, invalida sessões anteriores e define um novo cookie. Senha atual incorreta retorna 400, preservando o acesso existente. Não há recuperação por e-mail.

`GET /api/catalog-status` fornece a situação das cinco fontes e cobertura explícita; desconhecido não vira completo. `GET /api/automation-overview` reúne amostras limitadas de coletas, agendas, fluxos, monitores e relatórios da conta. As respostas desses endpoints e de publicações são tipadas em `contracts.py`. Os campos bibliográficos adicionais continuam extensíveis.

## Rede e publicação

O Compose publica web/API em loopback. Antes de expor a aplicação, configure HTTPS, cookie seguro, bootstrap administrativo, backup e controle de saída. Não há SSO/MFA ou política completa de produção embutida. Consulte o [runbook](../runbook.md) para operação, sem desabilitar validação TLS para contornar erros externos.
