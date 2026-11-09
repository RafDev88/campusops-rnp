# Runbook

Referências complementares: [configuração do backend](backend/development.md), [contrato HTTP e segurança](backend/api.md) e [filas e integrações](backend/automation.md).

## Diagnóstico inicial

```powershell
docker compose ps
docker compose logs --tail 100 api worker control-worker delivery-worker monitor-worker scheduler
```

`api`, `db` e `redis` têm healthchecks. O worker e o scheduler devem estar em execução. Uma API saudável confirma banco e schema, mas não garante disponibilidade das APIs externas.

## Diagnóstico de fontes e links

Abra **Gestão de dados → Saúde das fontes e links**. Confira se o problema está no endpoint de referência, em uma publicação específica ou em um arquivo. Uma falha é observada a partir da rede do servidor; a mesma URL pode responder de outra forma no navegador do usuário.

Use **Verificar agora** para enfileirar uma consulta leve, com intervalo mínimo de um minuto entre solicitações manuais do mesmo endereço. A agenda pode ser pausada por endereço ou globalmente. Verificações manuais continuam disponíveis quando a agenda está pausada, respeitando quotas e a política da fonte. Uma tarefa pendente não comprova disponibilidade.

- **TLS:** confira validade, domínio e cadeia. O transporte mantém verificação de certificado e usa `SOURCE_CA_BUNDLE` e o intermediário confiável já incluído. Não corrija um erro desligando a validação. Uma cadeia incompleta pode depender da configuração do servidor remoto ou da cadeia confiável local.
- **401/403:** confira credenciais, permissões e restrições da fonte. Tokens só são enviados ao endpoint integrado exato, nunca a links de publicações ou redirecionamentos externos.
- **404:** revise o registro ou endereço afetado; a API pode continuar funcionando normalmente.
- **429/adiamento local:** aguarde o próximo horário indicado. Limites do monitor e políticas da fonte são compartilhados no banco; não dispare repetidamente verificações manuais.
- **Conteúdo inesperado:** o servidor respondeu, mas o JSON de referência ou o tipo de arquivo não corresponde ao esperado. Uma página HTML de login não comprova disponibilidade de um PDF.
- **Destino bloqueado:** o endereço ou algum redirecionamento aponta para rede privada, porta não permitida, credenciais ou segredo na URL. Não remova essas proteções para testar um link externo.

O monitor-worker atende `monitoring`; o ciclo de controle agenda verificações e república tarefas persistidas se o broker falhar. Uma tarefa sem conclusão por três minutos é marcada como interrompida e reagendada, sem ser contada como queda da fonte. O limite de execução do worker é de 90 segundos. Incidentes são deduplicados e recuperações são registradas no radar.

URLs originais dos registros não são alteradas. A descoberta arquiva vínculos removidos e mantém o histórico; usa sites ROR apenas das instituições acompanhadas. A retenção preserva a última verificação de cada endereço mesmo após o prazo configurado.

## Coleta pendente

Verifique Redis e worker. A execução persistida será republicada pelo ciclo periódico, mesmo que a primeira publicação no broker tenha falhado. Se o agendador também estiver parado, inicie-o. Mensagens repetidas são descartadas pela transição atômica do estado da execução.

## Falha na fonte

Abra **Execuções → Detalhes** e confira o código:

| Código | Ação |
| --- | --- |
| credentials | Confira a variável de acesso da fonte e recrie os serviços |
| rate_limited | Aguarde a janela indicada pela fonte; reduza a frequência/páginas |
| not_found | Confira o identificador; um DOI pode pertencer a outra agência |
| schema_change | Revise o adaptador e o contrato; os dados antigos foram preservados |
| tls_certificate | Confira a cadeia do portal e o certificado intermediário confiável |
| network / unavailable | Verifique conectividade e situação da fonte; reprocese depois |
| selection | Selecione uma instituição acompanhada, DOI disponível ou ORCID válido |
| interrupted | Worker interrompido ou limite de duração; confira a causa antes de reprocessar |
| internal | Consulte logs pelo run_id; confira transações e conexão PostgreSQL |

Retentativas HTTP respeitam Retry-After até 120 segundos. Esperas maiores ficam persistidas como nova tentativa de execução e liberam o worker, respeitando o limite configurado. Falhas de autenticação, contrato e certificado não são repetidas automaticamente.

## Checkpoints, limites e recuperação

Abra **Execuções → Detalhes** para ver respostas/páginas confirmadas, etapa atual e histórico. A pausa é aplicada entre consultas. Durante a gravação, aguarde a conclusão da transação. Cancelar libera a fonte, sem desfazer etapas concluídas. Uma execução pausada mantém a fonte reservada.

Retomar pelo checkpoint reutiliza respostas confirmadas e transforma novamente os registros. Depois de corrigir um contrato, marque **Refazer respostas salvas** para consultar novamente a fonte; os contadores de chamadas continuam cumulativos. Amplie a política por execução antes de retomar se ela já foi consumida. Chamadas por minuto/dia usam janelas UTC compartilhadas por fonte. Checkpoints têm um limite de armazenamento por execução; não incluem cabeçalhos ou tokens.

O ciclo recupera tentativas sem heartbeat por dez minutos; transações em gravação mantêm o bloqueio da execução e são ignoradas até liberar esse bloqueio. Uma tentativa substituída perde a autorização de aplicar respostas atrasadas. Coletores anteriores à versão 0.4 mantêm o diagnóstico de interrupção após duas horas. Confira logs se esse ciclo deixar de rodar.

## Fluxos e agendas

Fluxos guardam uma cópia das etapas/parâmetros na inicialização. Pausar aguarda o ponto seguro da etapa; retomar continua a mesma etapa. Resultados parciais só permitem avançar quando essa opção foi habilitada. Se a fonte estiver ocupada, o fluxo aguarda. Cancelar não desfaz etapas anteriores. Desativar uma definição impede novos inícios, mas não cancela execuções existentes.

Agendas por cron mostram os próximos horários no fuso escolhido. Uma agenda atrasada gera uma ocorrência e avança para o futuro, sem reproduzir cada horário perdido. Sobreposição fica registrada como omitida. Agendas por intervalo anteriores continuam disponíveis; evite configurar as duas modalidades para a mesma rotina.

O incremental OpenAlex usa data de publicação, não data de alteração do registro. Só avança com cobertura completa; faça reconciliações sem incremental para mudanças históricas ou inclusão tardia de publicações antigas. Ajuste páginas e orçamento antes de esperar cobertura completa de instituições grandes.

## Relatórios e revisão

Relatórios e seus modelos são privados por conta; favoritos são avaliados para essa conta na geração. Arquivos expiram após 30 dias e têm limite de 10 mil linhas. A fila `reports` e a fila `notifications` são atendidas pelo delivery-worker, separadas da ingestão e do agendamento. A geração interrompida volta à fila após 20 minutos.

Na fila de revisão, reprocessar DOI/ORCID consulta apenas o identificador selecionado. Falhas de contrato retomam a execução original com respostas refeitas. Uma rejeição repetida volta a pendente; sucesso resolve a revisão. O histórico de alterações começa após a atualização, sem inventar diferenças retroativas.

## Incidentes

Falhas consecutivas têm um único incidente aberto por regra/fonte. Um sucesso completo resolve esse tipo automaticamente. Resolva mudanças de contrato somente após revisar e testar o adaptador. Uma coleta parcial não comprova recuperação completa.

## Certificados UFRN

O intermediário incluído está em `backend/certificates`. A cadeia precisa continuar terminando em uma raiz confiável, e o hostname deve corresponder ao portal. Caso a autoridade emissora mude, obtenha o novo intermediário pelo canal oficial, valide a cadeia e atualize a documentação/fingerprint. Não desative a validação TLS.

## Webhook não entregue

Confira a aba Administração, as tentativas e o último resultado. Verifique domínio permitido, segredo, DNS público e resposta 2xx. Após cinco tentativas, a entrega fica esgotada para revisão. Um webhook pausado não recebe novos eventos vinculados a ele; eventos internos continuam no radar.

## Backup e atualização

Para criar um dump e comprovar sua restauração em banco descartável, execute `.\.venv\Scripts\python scripts/verify-backup.py` na raiz. O script preserva o banco principal e mantém o backup/manifesto em `backups/`. Veja [procedimento e limites](reliability.md).

Faça backup antes de alterar o schema. Um exemplo com Docker é executar `pg_dump` no serviço db e guardar o resultado em local protegido. Não use `docker compose down -v`: essa opção remove volumes e apaga os dados.

Atualize com `docker compose up --build -d`. A API executa Alembic antes de aceitar tráfego; workers aguardam sua saúde. A migração inicial preserva instituições e execuções anteriores. Rollback do schema inicial exige restauração de backup.

## Acesso

O primeiro acesso cria o administrador no banco ainda vazio. Depois, somente administradores criam/desativam usuários. Não há senha padrão, cadastro público após o setup ou recuperação por e-mail. Sessões expiram após oito horas; desativar o usuário invalida o acesso em sua próxima requisição.

Em **Outras consultas → Minha conta**, o usuário pode trocar a própria senha, validando a atual, e encerrar outras sessões. A troca gira o cookie atual e invalida os anteriores. Senha atual incorreta mantém a sessão e informa o erro. Não redefine o acesso de outras contas nem substitui recuperação de senha por um administrador.

O Compose publica serviços somente em loopback. Antes de disponibilizar para outras máquinas, configure HTTPS, COOKIE_SECURE=true, uma política de bootstrap administrativo, backup e restrições de rede para os destinos de saída.
