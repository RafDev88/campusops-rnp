# Backend CampusOps · 0.8

API Python para consultar um catálogo universitário local e operar integrações públicas, automações e monitoramento de links. O backend é um **monólito modular**: API e processos Celery compartilham o código e o banco; filas separam os tipos de trabalho.

## Comece aqui

1. [Guia do backend](../docs/backend/README.md): visão geral e sequência de leitura.
2. [Desenvolvimento e configuração](../docs/backend/development.md): Docker, ambiente local, variáveis e testes.
3. [Arquitetura e dados](../docs/backend/architecture.md): responsabilidades, persistência, transações e concorrência.
4. [Contrato HTTP e segurança](../docs/backend/api.md): sessão, permissões, filtros e exemplos executáveis.
5. [Integrações e tarefas](../docs/backend/automation.md): fontes, filas, recuperação e monitoramento.
6. [Referência gerada](../docs/backend/reference.md): todas as rotas, tabelas e filtros extraídos do código.
7. [Operação e diagnóstico](../docs/runbook.md): incidentes, backup e atualização.

O [dicionário de dados](../docs/backend/data-dictionary.md) detalha colunas, tipos, nulabilidade, chaves e índices declarados no ORM.

Veja também [confiabilidade e experiência 0.8](../docs/reliability.md), com restauração de backup, benchmark, acompanhamento e demonstração isolada.

Com o Docker iniciado na raiz do repositório, abra [Swagger](http://localhost:8000/docs), [ReDoc](http://localhost:8000/redoc) ou [OpenAPI JSON](http://localhost:8000/openapi.json). Não existe senha padrão: use sua conta existente; o setup cria o administrador somente em um banco vazio.

Esta documentação descreve o que está implementado. Não pressupõe cobertura completa das fontes, processamento exatamente uma vez ou prontidão de produção sem configuração operacional.
