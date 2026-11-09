# Integrações, tarefas e monitoramento

## Adaptadores e cobertura

| Fonte | O que importa / enriquece | Limites e interpretação |
| --- | --- | --- |
| ROR | Instituições, nomes alternativos, localização e perfil | Teto do conector de 500 páginas; repetição de identificadores impede afirmar cobertura completa |
| OpenAlex | Publicações, autores, afiliações, temas, citações e acesso aberto | Até 50 instituições por execução; sem chave usa paginação básica, com chave usa cursor conforme cota/política |
| Crossref | Metadados bibliográficos por DOI já existente | Até 200 DOIs por execução; DOI não encontrado não apaga o trabalho |
| ORCID | Campos públicos de um perfil identificado | Não associa pessoas por semelhança de nome; não escreve no ORCID |
| UFRN / CKAN | Conjuntos, recursos e formatos de dados abertos | Importa metadados; não transforma automaticamente arquivos em tabelas de cursos |

Limites acima são do código atual; contratos e cotas externos podem mudar. Um novo conector exige validar documentação oficial da fonte, permissões e exemplos reais. Respostas inesperadas devem gerar diagnóstico, não um falso catálogo vazio.

## Separação das filas

| Fila | Tarefa Celery | Serviço | Limite soft / hard |
| --- | --- | --- | --- |
| `ingestion` | `campusops.execute` | worker | 7000 / 7100 segundos |
| `control` | `campusops.tick` | control-worker | Sem limite específico por tarefa configurado |
| `reports` | `campusops.report` | delivery-worker | 300 / 360 segundos |
| `notifications` | `campusops.webhook` | delivery-worker | 60 / 90 segundos |
| `monitoring` | `campusops.monitor` | monitor-worker | 70 / 90 segundos |

O Beat publica o ciclo de controle a cada 60 segundos. Ele executa rotinas operacionais, automações e monitoramento, com blocos `finally` para tentar os ciclos seguintes mesmo após falha anterior. Mensagens JSON, confirmação tardia e prefetch 1 reduzem retenção de trabalhos por processo. O Compose usa concorrência 2 para ingestão/entregas/monitor e 1 para controle.

## Estados e retomada

Uma coleta pode ficar `queued`, `running`, `paused`, `success`, `partial`, `failed` ou `cancelled`. Consulte também runtime, etapa, horário da próxima tentativa, cobertura e mensagens; apenas o status não explica o motivo de uma espera.

Checkpoint confirma respostas/páginas recebidas e permite retomar a transformação sem consultar tudo novamente. A opção explícita de refazer respostas é adequada após corrigir um contrato. Pausar mantém a fonte reservada; cancelar libera o próximo trabalho sem desfazer etapas já concluídas.

Quotas por execução, minuto e dia são compartilhadas por fonte no banco; janelas de minuto/dia usam UTC. Retentativas transitórias usam espera crescente/jitter e Retry-After. Esperas HTTP maiores que 120 segundos viram nova tentativa persistida, liberando o worker. Autenticação, certificado e mudança de contrato exigem revisão. Não configure retentativas indiscriminadas para toda exceção.

O ciclo recupera tentativas sem heartbeat por dez minutos, respeitando bloqueios de gravação; execuções legadas sem o runtime atual possuem diagnóstico de interrupção após duas horas. Identidade da tentativa evita aplicar respostas atrasadas. Consulte o [runbook](../runbook.md) antes de reprocessar.

## Agendas e fluxos

Agendas cron aceitam fuso e prévia dos próximos horários; o intervalo mínimo é de 15 minutos. Horários perdidos são condensados em uma ocorrência, avançando para o futuro. Fonte/fluxo ocupado registra omissão em vez de iniciar sobreposição. Intervalos antigos continuam disponíveis; evite duplicar agendas equivalentes.

Um fluxo guarda cópia da definição e parâmetros no início e encadeia coletas/enriquecimento/relatório. Cobertura parcial só permite avançar quando a definição autoriza. O relatório pertence ao criador, mesmo quando a definição do fluxo é compartilhada. Desativar uma definição não cancela execuções já iniciadas.

O incremental OpenAlex usa **data de publicação**, com sobreposição padrão de dois dias e marcador por escopo. Só avança após cobertura completa; não detecta toda alteração histórica ou publicação antiga cadastrada tardiamente. Execute reconciliação sem incremental periodicamente e dimensione páginas/orçamento.

## Regras, incidentes e notificações

Regras geram eventos internos deduplicados, incidentes e entregas opcionais. A prévia não envia notificações nem cria eventos. Pesquisas salvas estabelecem uma base inicial: resultados já existentes não geram alertas retroativos.

Webhooks exigem domínio HTTPS permitido, porta 443, DNS público e segredo configurado. Não seguem redirecionamentos. O corpo possui `id`, `kind`, `title` e `payload`; `X-CampusOps-Signature` contém `sha256=<HMAC-SHA256 do corpo original>`. O destinatário compara em tempo constante e deduplica `Idempotency-Key`. A entrega é pelo menos uma vez, com até cinco tentativas; resposta perdida pode causar repetição. Nenhum destino externo é criado automaticamente.

Relatórios usam a mesma semântica de pesquisa, pertencem à conta, têm limite de 10 mil linhas e retenção de 30 dias. Geração interrompida é reenfileirada após 20 minutos. Favoritos são avaliados para o proprietário na geração.

## Monitoramento de URLs

O inventário reúne cinco endpoints de referência, links de publicações/DOIs, recursos CKAN e sites de instituições acompanhadas. Descoberta é uma operação local de banco; verificar uma URL é tarefa de rede. URLs iguais compartilham monitor e referências. Vínculos removidos são arquivados, preservando histórico e preferências do operador.

O transporte valida todos os IPs resolvidos, conecta ao IP público aprovado e mantém Host/SNI do domínio. Cada redirecionamento é validado novamente; são bloqueadas redes privadas, credenciais/segredos na URL, portas não permitidas e downgrade HTTPS para HTTP. Tokens só podem seguir para o endpoint integrado exato. TLS mantém validação de cadeia e hostname, inclusive com o intermediário documentado da UFRN.

APIs recebem GET com validação de JSON; links recebem HEAD, com fallback GET para 405/501 e leitura limitada a 256 KiB + um byte. Arquivos conhecidos que respondem HTML geram conteúdo inesperado. Isso não comprova integridade completa de um PDF ou CSV.

| Parâmetro inicial | Valor |
| --- | --- |
| Endpoints de APIs | Intervalo de 15 minutos |
| Demais links | Distribuídos ao longo de 24 horas |
| Tentativas HTTP globais | 2000 por dia UTC |
| Limite por domínio | 10 por minuto |
| Manual no mesmo alvo | Intervalo mínimo de 60 segundos |
| Retenção do histórico | 30 dias, preservando a última verificação |
| Incidente de disponibilidade | 3 falhas consecutivas; recuperação com 2 respostas esperadas |
| Aviso de certificado | Até 30 dias restantes |
| Redirecionamentos | Até 5 |
| Rede | Até 8 segundos por operação dentro de orçamento de 40 segundos |

Configurações administrativas podem alterar os limites persistidos. Endpoints também debitam quotas de sua fonte. Adiamentos por quota não contam como queda; pendentes e tarefas interrompidas não contam como sucesso. Lease vencido de três minutos marca interrupção e permite reagendar. Certificado próximo do vencimento tem incidente separado, mesmo se HTTP funcionar.

Percentuais representam respostas esperadas nas verificações observadas em 24 horas, não SLA. Um 401/403 pode representar autenticação/restrição; um DOI 404 não comprova queda da API. O diagnóstico é observado da rede do servidor. Nenhuma verificação corrige automaticamente a URL original ou desabilita TLS.

## Adicionar uma integração

1. Defina a identidade canônica, campos importados e o significado de cobertura completa/parcial.
2. Implemente adaptador e transformação com timeout, validação e fixtures representativas.
3. Registre a fonte nos tipos/validações, políticas, seleção operacional e interface; evite registrar somente no worker.
4. Preserve metadados de origem e atualize projeções/alterações na mesma transação de aplicação.
5. Teste paginação repetida, contrato inválido, ausência de dados, autenticação, quota e retomada sem publicar tarefas reais.
6. Se incluir endpoint de monitoramento, mantenha allowlist exata de credenciais e transporte com DNS/IP validado.
7. Atualize documentação, referência gerada e runbook. Faça coleta pequena controlada antes de aumentar a cobertura.
