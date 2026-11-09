# Confiabilidade e experiência · 0.8

Esta versão aprimora a operação existente sem nova migração e sem redefinir contas do catálogo principal.

## O que mudou

| Área | Implementação | Limite da evidência |
| --- | --- | --- |
| Atualização e cobertura | Painel expansível em Início/Publicações; última coleta aplicada, estado e cobertura por fonte | Completo refere-se ao escopo de uma execução; não afirma cobertura de toda a fonte ou do filtro atual |
| Automações | Resumo em Execuções com coletas, agendas por intervalo/cron, fluxos, relatórios pessoais e links com diagnóstico | Lista limitada com contadores SQL; falhas podem ser históricas, não incidentes novos |
| Contratos HTTP | Modelos Pydantic para publicações, resumos operacionais e conta; envelope de erro com detail/code/request_id | Metadados adicionais das publicações continuam extensíveis; rotas anteriores ainda podem ter respostas dinâmicas |
| Backup | Script cria pg_dump e restaura em banco descartável; verifica schema e contagens | Não replica uma estratégia de recuperação fora da máquina ou restauração contínua |
| Desempenho | Benchmark repetível de consulta/contagem com 5 mil registros fictícios | SQLite isolado, sem HTTP, concorrência ou promessa de SLA |
| PostgreSQL no CI | Job com PostgreSQL 17 executa o script de integração em banco temporário | CI configurado; a execução remota depende do provedor |
| Pesquisa sem resultados | Orientações por período, favoritos e termo; valores digitados dos filtros são preservados antes da navegação | Sugestões são locais; não inventam resultados externos |
| Acessibilidade | Navegação por teclado no painel de cobertura; formulários com labels, autocomplete e mensagens; verificação mobile | Não constitui certificação WCAG ou avaliação completa com leitor de tela |
| Conta | Troca de senha com validação da atual e rotação de sessões; listagem e revogação de acessos próprios | Não identifica dispositivo/localização, não inclui recuperação de senha ou MFA |
| Demonstração | Compose separado com dados fictícios, banner, banco/volumes/portas/cookie próprios e fontes pausadas | Iniciar apenas os quatro serviços documentados, sem workers externos |

## Acessar as melhorias

- Em **Início/Publicações**, abra “De onde vêm estes dados e quando foram atualizados?”.
- Em **Gestão de dados → Execuções**, consulte “Acompanhe suas automações”.
- Em **Outras consultas → Minha conta**, troque a senha ou encerre outro acesso. Trocar a senha invalida os cookies anteriores e mantém um novo acesso no navegador atual.
- Erros de validação não devolvem o corpo recebido, evitando eco de senhas. Falhas internas oferecem um identificador para suporte.

## Backup com restauração verificada

Na raiz, com os serviços principais iniciados:

```powershell
.\.venv\Scripts\python scripts/verify-backup.py
```

O script gera arquivo `.dump` e manifesto `.json` em `backups/`, ignorado pelo Git. Esses arquivos contêm dados do sistema e devem ficar em armazenamento protegido. A restauração usa um nome gerado e validado, com prefixo `campusops_restore_`, e remove apenas esse banco temporário ao final. Não sobrescreve o banco principal. O snapshot é consistente; contagens atuais do banco em uso podem mudar durante a validação.

Verificação executada nesta entrega: restauração da revisão `0007`, 1.693 instituições, 100 publicações e 1 usuário. A conferência de schema/contagens não substitui uma simulação de recuperação de toda a infraestrutura. O script não cria um agendamento do sistema operacional; pode ser acionado pelo mecanismo de agenda adotado na operação.

## Benchmark local

```powershell
.\.venv\Scripts\python scripts/benchmark-search.py --records 5000
```

Banco temporário e broker em memória são configurados antes dos imports. O teste cria registros fictícios, executa uma amostra de aquecimento e mede 20 amostras de contagem + primeira página usando o construtor real de consultas. O relatório fica em `frontend/artifacts/search-benchmark.json`.

Medição local desta entrega: mediana de 57,37 ms e p95 de 75,84 ms para 5 mil registros. Esse resultado depende da máquina e do cenário. Não inclui serialização de resposta, HTTP, PostgreSQL ou usuários simultâneos. A próxima otimização deve ser orientada por um benchmark representativo do ambiente de destino.

## Demonstração isolada

Requer Docker Compose com suporte a `!override` (2.24.4 ou superior). Na raiz:

```powershell
docker compose -p campusops-demo -f compose.yaml -f compose.demo.yaml up --build -d db redis api web
Get-Content -Raw scripts/seed-demo.py | docker compose -p campusops-demo -f compose.yaml -f compose.demo.yaml exec -T api python -
```

Abra http://localhost:8081. Conta **somente da demonstração**: `demonstracao`, senha `CampusOps-Demo-2026`. São credenciais públicas de exemplo para uso local; não são as credenciais da instalação principal. API/Swagger: http://localhost:8002/docs.

O seed exige `CAMPUSOPS_DEMO=true` e banco `campusops_demo`; recusa banco principal ou demonstração já inicializada. Os registros são explicitamente fictícios. Não há workers/scheduler nessa inicialização; fontes são pausadas e o monitor automático é desativado. Não inicie as demais filas com esse override. O cookie `campusops_demo_session` não substitui o cookie principal.

Para parar somente a demonstração, preservando seus volumes:

```powershell
docker compose -p campusops-demo -f compose.yaml -f compose.demo.yaml stop
```

O projeto principal continua em http://localhost:8080. Não use `down -v` para atualizar ou parar os serviços.

## Manutenção

Regere referências com `scripts/document-backend.py`; execute testes no diretório backend e o build/teste de navegador em frontend. O painel de automações filtra relatórios e agendas de relatório pela conta; sua privacidade deve permanecer coberta por teste ao adicionar novos destinos. Não atualizar silenciosamente o PDF da prova: ele registra evidências e afirmações da versão na qual foi produzido.
