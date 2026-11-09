# CampusOps · 0.8

Central de integrações e operações universitárias com Python, Vue 3, PostgreSQL, Redis, Celery e Electron. Importa dados públicos, acompanha instituições, gera indicadores com cobertura explícita e automatiza rotinas operacionais.

## Confiabilidade e acompanhamento · 0.8

Início e Publicações mostram a atualização e cobertura por fonte em um painel expansível. Execuções reúne próximas agendas, etapas, falhas e orientações; relatórios pessoais permanecem restritos à conta. **Outras consultas → Minha conta** permite trocar a senha e encerrar outros acessos. Respostas de publicações possuem contratos Pydantic e os erros incluem código e identificador de requisição sem ecoar corpos sensíveis.

A entrega inclui restauração de backup em banco temporário, benchmark com dados fictícios, integração PostgreSQL no CI e demonstração isolada em outra porta. Veja [procedimentos, resultados e limites](docs/reliability.md). Nenhuma migração ou alteração da senha existente é necessária.

## Experiência para quem está começando

A versão 0.7 reúne no menu principal Início, Pesquisar, Instituições, Publicações, Minhas pesquisas e Ajuda. Pesquisadores, dados abertos e relatórios ficam em **Outras consultas**; a gestão se organiza por atualizar informações, programar rotinas, acompanhar problemas e administrar acesso.

Na página inicial, escolha o tipo de informação e use o guia em três passos. Ele pode ser ocultado e reaberto; apenas essa preferência de apresentação fica no navegador, separada por usuário. **Como usar esta página** oferece ajuda contextual. A lista de publicações mostra resumo curto quando disponível, autores, origem, indicação de leitura gratuita e ações claras para guardar ou abrir os detalhes.

**Minhas pesquisas** reúne pesquisas salvas, favoritos e novidades privados da conta. A remoção de uma pesquisa exige confirmação e pode ser cancelada com Escape. Reabrir pesquisas preserva valores negativos de critérios, como sem DOI, sem resumo e acesso aberto não identificado. Os resultados continuam usando os mesmos filtros na URL e na exportação.

O frontend separa o ciclo de sessão (`useSession`), a estrutura visual (`PortalLayout`), a linguagem e os grupos de navegação (`navigation.ts`), os critérios de pesquisa (`researchFilters.ts`), os controles de filtro e os resultados de publicações. A biblioteca pessoal tem carregamento com cancelamento de requisições antigas. Componentes comuns tratam ajuda e confirmação; tokens CSS centralizam cores e espaçamentos. As proteções de acesso continuam no backend. Esta atualização não exige migração do banco.

## Saúde das fontes e links

Em **Gestão de dados → Saúde das fontes e links**, confira o diagnóstico de cada endereço, HTTP, tempo total, vencimento HTTPS, redirecionamentos, histórico e registros que utilizam o link. **Verificar APIs agora** enfileira os cinco endpoints de referência; **Atualizar lista de links do catálogo** faz descoberta local, sem consultar endereços externos. Operadores podem cadastrar URLs públicas e configurar intervalos, incidentes e destino opcional de webhook. Contas de consulta apenas visualizam.

As APIs têm intervalo inicial de 15 minutos; DOI, páginas de publicação, PDFs, conjuntos/arquivos UFRN e sites das instituições acompanhadas são distribuídos ao longo de 24 horas. A descoberta roda a cada hora e em cada inicialização da API, preservando preferências existentes. URLs iguais compartilham uma verificação. Links sem vínculo atual são arquivados e saem da agenda, mantendo o histórico. Links que voltam ao catálogo ficam disponíveis para reativação, sem desfazer pausas do operador.

O monitor usa GET limitado para validar o JSON dos endpoints de referência; para links usa HEAD e, em 405/501, GET com leitura de até 256 KiB + um byte. Não baixa arquivos por inteiro nem comprova a integridade completa de um PDF/CSV. Detecta HTML quando o link deveria entregar um arquivo conhecido. Diagnósticos distinguem DNS, timeout, conexão, TLS, autenticação, acesso recusado, 404, 429, 5xx, conteúdo inesperado e redirecionamentos. Um DOI ausente não implica queda da API, e 401/403/429 não são classificados como falha de conexão.

O transporte conecta ao IP público validado, mantendo Host e SNI do domínio original; repete a validação a cada redirecionamento, bloqueia redes internas e downgrade HTTPS→HTTP. Segredos e credenciais na URL não são aceitos. As credenciais das APIs só são anexadas ao endereço de referência exato e não seguem para outro destino. A validação HTTPS usa a mesma cadeia confiável das coletas, sem desativar verificação. São permitidos até cinco redirecionamentos, oito segundos por operação de rede dentro de um orçamento de 40 segundos e limite de tarefa no worker.

Limites iniciais: 2 mil tentativas HTTP por dia UTC e dez por domínio/minuto, configuráveis por administrador. Endpoints das APIs também debitam os limites compartilhados de sua fonte. Falhas recebem espera crescente; 429 respeita Retry-After, limitado a um dia. Limites locais adiam a verificação sem registrar queda. Mensagens duplicadas não repetem a consulta; tarefas interrompidas ficam indeterminadas e voltam à agenda.

Três falhas consecutivas abrem um incidente interno por endereço; duas respostas esperadas consecutivas resolvem o incidente e registram recuperação. Certificados válidos com até 30 dias restantes geram aviso separado, resolvido quando a validade supera o limite. Vencimentos de qualquer domínio HTTPS no trajeto são considerados. Notificações externas ficam desativadas até selecionar explicitamente um webhook já cadastrado. Pausar a agenda de um endereço não pausa a integração de dados.

A migração aditiva `0007` cria as tabelas de monitoramento. O serviço `monitor-worker` consome a fila `monitoring`, separado de ingestão, controle e entregas. O histórico tem retenção inicial de 30 dias, preservando a última verificação de cada endereço. Percentuais mostram respostas esperadas nas verificações observadas em 24 horas; não representam um SLA nem contam tarefas pendentes, adiadas ou interrompidas como sucesso.

## Navegação do portal

A página **Início** prioriza a consulta, com campo de busca, exemplos e atalhos para instituições, publicações e dados abertos. O menu principal reúne as áreas de consulta; as telas operacionais ficam em **Gestão de dados**, uma seção expansível no topo. **Ajuda** explica os filtros, favoritos, relatórios, fontes e limites do catálogo. Nas publicações, autor, ano final, origem dos metadados e ordenação ficam em **Mais opções de pesquisa**; links com esses critérios abrem as opções automaticamente.

O visual usa fundo branco, azul institucional, tipografia de sistema, bordas discretas, navegação por teclado, link para pular ao conteúdo e menu completo em grade no celular. A identidade é própria do CampusOps e não representa vínculo com o governo.

## Pesquisa e descoberta

A versão 0.5 usa palavras completas como padrão; a tolerância a erros no PostgreSQL é **opcional**, não entra silenciosamente nos resultados. Há modos de todas as palavras, qualquer palavra, frase na mesma ordem e título completo exato. DOI, ORCID e endereços ROR/OpenAlex usam identificadores normalizados e correspondência exata, inclusive quando a aproximação está ativada. As sugestões permitem completar a última palavra digitada.

As publicações permitem escolher título, resumo ou todos os campos, idioma dos metadados, tipo, periódico/veículo, presença de resumo/DOI, mínimo de citações e retratação informada pela fonte. Valor ausente é distinto de falso. Temas selecionados por ID e autores por ORCID mantêm a identidade; a busca por nome não confunde uma palavra com parte de outra. Facetas são calculadas no contexto dos filtros, desconsiderando o próprio filtro para permitir trocar de opção. Os mesmos critérios valem para URL, pesquisa salva, CSV, avisos e relatórios.

A migração aditiva `0006` reindexa as respostas já armazenadas, sem alterar os metadados originais. Periódico, editora, idioma, tipo, data, ISSN, resumo e links de leitura usam os campos disponíveis do OpenAlex e Crossref; autores Crossref são aproveitados quando os autores OpenAlex estão ausentes. Não se fundem pesquisadores apenas por nome. A ficha mostra alertas de retratação quando informados e mantém campos desconhecidos como não informados. A exportação inclui os principais campos bibliográficos e links.

Em Instituições, filtre país, estado/região, cidade, tipo e situação no ROR. Em Integrações, confira a disponibilidade de DOI, resumo, idioma, periódico e enriquecimento no catálogo local. A coleta manual OpenAlex pode ser delimitada por assunto, idioma, tipo e ano final; os marcadores incrementais ficam separados para cada escopo. Paginação repetida por cursor não produz um falso sucesso. Nenhuma combinação de APIs garante todos os registros: resultados parciais e limites continuam explícitos.

- A barra global pesquisa instituições, siglas, publicações, autores e conjuntos do catálogo já importado. Sugestões podem ser selecionadas com as setas e Enter; Escape fecha a lista.
- **Pesquisar** agrupa resultados por tipo e reúne favoritos, pesquisas salvas e avisos privados de novos resultados.
- **Publicações** combina texto, instituição, tema, autor/ORCID, período, acesso aberto, enriquecimento Crossref e favoritos. A ordenação pode usar relevância, ano, título ou citações.
- Os filtros, a página e a publicação selecionada ficam na URL. Recarregar, compartilhar o endereço e usar Voltar/Avançar preserva o contexto; o destinatário precisa de acesso ao mesmo workspace.
- A exportação CSV usa os mesmos critérios e ordenação da tela, limitada a 10 mil resultados.
- As fichas mostram resumo quando disponível, autores, instituições, periódico, editora, financiadores e licenças como campos legíveis. Os links permitem continuar por autor, instituição ou tema.
- Os gráficos de ano e tema abrem as publicações correspondentes. Há links em texto equivalentes para navegação por teclado.
- Uma pesquisa salva pode avisar sobre novos resultados encontrados nas próximas coletas. Os registros já presentes ao salvar formam a base inicial e não geram notificações retroativas. Os avisos ficam em **Pesquisar → Novidades para você**.

Favoritos, pesquisas e avisos são individuais, inclusive para contas de consulta. Essa personalização não concede permissão para disparar integrações ou alterar configurações compartilhadas. Perfis de autoria sem ORCID são mantidos separados; nomes iguais não comprovam identidade.

A migração `0004` cria as relações de temas/autorias e indexa os dados existentes. O PostgreSQL usa busca textual e índices GIN/pg_trgm sobre projeções sem acentos; o SQLite de desenvolvimento oferece correspondência textual sem acentos, sem a tolerância por trigramas. A busca consulta o catálogo local, sem chamar fontes externas a cada digitação.

## Automação na versão 0.4

- **Fluxos** encadeia ROR, OpenAlex, Crossref, ORCID, UFRN e relatório. Escolha etapas, instituição, limites e se uma coleta parcial permite continuar. As definições ficam compartilhadas; o relatório pertence ao criador do fluxo. Cada execução guarda uma cópia da configuração e o histórico das etapas.
- **Automações** permite agendas diárias, semanais, horárias ou cron com fuso e prévia dos próximos cinco horários. O intervalo mínimo é de 15 minutos. O ciclo roda a cada minuto; horários perdidos são condensados em um disparo e a próxima ocorrência fica no futuro. Fontes ou fluxos ocupados geram um disparo omitido, sem acumular coletas concorrentes.
- **Execuções** mostra etapa, chamadas, páginas, respostas confirmadas, próximas tentativas e histórico. Pausa/cancelamento são cooperativos entre consultas; a gravação é transacional e não é interrompida. A retomada reutiliza respostas JSON confirmadas e a seleção original, repetindo a transformação local; respostas inválidas podem ser refeitas explicitamente após corrigir o adaptador.
- **Limites e recuperação** configura chamadas por execução, minuto e dia UTC, espaço por checkpoint, tentativas de execução e sobreposição incremental. Administradores alteram políticas. Limite por execução ou armazenamento pausa a coleta até ajuste; janela por minuto/dia agenda nova tentativa. Pausar mantém a exclusividade da fonte até retomar ou cancelar.
- O OpenAlex usa **data de publicação**, com sobreposição padrão de dois dias. O marcador só avança para janelas completas, usando a data inicial da coleta, inclusive após retomadas. Essa estratégia pode não encontrar registros antigos adicionados tardiamente ou revisões históricas: desmarque o incremental periodicamente para reconciliar. Não utiliza filtros de atualização exclusivos de planos pagos. Crossref prioriza DOIs pendentes; ORCID descobre identificadores públicos dos autores, com limite por etapa.
- **Revisão de registros** permite reprocessar um DOI/ORCID rejeitado ou retomar uma falha de contrato após correção. **Alterações** registra campo, valor anterior, valor novo, fonte e execução na mesma transação dos dados; começa nas próximas coletas.
- **Relatórios** gera CSV privado com filtros de pesquisas salvas, manualmente ou por agenda. Arquivos têm limite de 10 mil resultados e expiram após 30 dias. A prévia das regras consulta o catálogo sem criar eventos ou enviar webhooks.

A migração aditiva `0005` cria as tabelas operacionais. Nenhuma agenda nova é ativada automaticamente. Os serviços `worker` (ingestão), `control-worker` (agendas/recuperação) e `delivery-worker` (relatórios/webhooks) consomem filas separadas; notificações lentas não bloqueiam o ciclo de agendamento. O banco persiste as intenções antes de publicar no Redis. Mensagens repetidas são descartadas pela transição de estado e por chaves de disparo. Falhas transitórias usam espera crescente com jitter e Retry-After; autenticação, TLS e contrato exigem revisão. Heartbeats e identificação da tentativa evitam que respostas atrasadas de um worker substituído sejam aplicadas.

## Iniciar os serviços

Para trabalhar no servidor Python, consulte o [guia completo do backend](backend/README.md): arquitetura, configuração, segurança, contratos HTTP, filas, integrações e referência gerada das rotas e tabelas.

O ambiente local já usa `http://localhost:8080`. Para iniciar novamente:

```powershell
docker compose up --build -d
```

Em uma instalação nova, copie `.env.example` para `.env` e configure POSTGRES_PASSWORD antes do comando. Use uma senha alfanumérica para evitar caracteres reservados na URL do banco. Defina também WEBHOOK_SIGNING_SECRET se for usar notificações externas.

No primeiro acesso, **crie o administrador pela interface**. Não existe usuário/senha padrão. Os dados anteriores permanecem no volume PostgreSQL. O histórico da versão anterior está disponível em **Execuções → Histórico da versão anterior**.

- Painel: http://localhost:8080
- API e OpenAPI: http://localhost:8000/docs
- Saúde: http://localhost:8080/api/health

As operações de escrita exigem sessão e cabeçalho `X-CampusOps: 1`, enviado automaticamente pela interface. A documentação OpenAPI descreve os corpos de entrada; chamadas manuais devem incluir esse cabeçalho e o cookie obtido no login.

## O que está implementado

| Módulo | Comportamento |
| --- | --- |
| Instituições | ROR paginado, busca, seleção de instituições acompanhadas e perfil individual |
| Publicações | OpenAlex por instituição/ROR, período e páginas; títulos, autores, temas, citações e acesso aberto |
| Enriquecimento | Crossref por DOI; preserva os valores originais de cada fonte |
| Pesquisadores | Consulta de registro público individual no ORCID, também acessível pelos autores de publicações |
| Dados abertos | Catálogo CKAN da UFRN, recursos e formatos; detecção de alterações nos metadados |
| Indicadores | Publicações por ano, temas, acesso aberto e rede de colaboração sobre o catálogo importado |
| Qualidade | DOI ausente/repetido, ausência de afiliação, título divergente e coleta antiga |
| Operação | Fila Celery/Redis persistida, execuções, reprocessamento e bloqueio de sobreposição por fonte |
| Automação | Agendamentos, falhas consecutivas, alteração de contrato, novo trabalho por tema, dados desatualizados e resumo semanal |
| Incidentes | Abertura deduplicada, resolução manual e recuperação automática para falhas consecutivas |
| Notificações | Radar interno, resumo dos últimos sete dias e webhooks com assinatura HMAC e retentativas |
| Acesso | Administrador, operador e consulta; sessões HttpOnly, senha Argon2, CSRF e auditoria |
| Entrega | Docker Compose, migrações Alembic, testes, CI e scripts Bash |
| Desktop | Cliente Electron local com sandbox, isolamento de contexto e Node desativado no renderer |

## Fluxo recomendado

1. Em **Integrações → ROR**, importe as instituições brasileiras. O limite de 500 páginas cobre o teto da API; a coleta informa se o resultado foi parcial.
2. Em **Instituições**, busque uma universidade e clique em **Acompanhar**.
3. Abra seu perfil e selecione **Coletar publicações**, ou faça uma coleta OpenAlex das instituições acompanhadas em Integrações.
4. Consulte gráficos e trabalhos em **Instituições / Publicações**. O limite de páginas e o período aparecem na cobertura da execução.
5. Execute **Crossref** para enriquecer os DOIs já cadastrados. Registros mais antigos/sem enriquecimento têm prioridade.
6. Crie uma regra de nova publicação por tema **antes** da próxima coleta para receber eventos de novos registros. As regras não geram retroativamente notificações para todo o histórico existente.
7. Configure agendamentos e acompanhe **Execuções / Incidentes / Radar**.

ROR inclui organizações de pesquisa de vários tipos, além de universidades. Contagens locais não devem ser confundidas com produção total de uma instituição ou ranking de qualidade. OpenAlex considera nesta versão a afiliação direta, sem agregar automaticamente toda a hierarquia de unidades subordinadas.

Quando a fonte repete identificadores entre páginas, o conector deduplica os registros e compara a quantidade única com o total reportado. Uma coleta com lacunas permanece parcial, mesmo depois de percorrer todas as páginas. Os detalhes registram recebidos, únicos e repetidos.

## Credenciais e integrações externas

Configure variáveis no `.env` e recrie os serviços com `docker compose up -d`:

| Variável | Finalidade |
| --- | --- |
| OPENALEX_API_KEY | Opcional para consultas básicas; habilita cursor nas páginas seguintes e acesso conforme a cota da conta |
| ORCID_ACCESS_TOKEN | Token público caso a operação consultada exija autenticação |
| WEBHOOK_ALLOWED_HOSTS | Lista de domínios HTTPS autorizados, separados por vírgula |
| WEBHOOK_SIGNING_SECRET | Segredo compartilhado para autenticar os eventos enviados |
| COOKIE_SECURE | Use `true` quando o acesso ocorrer por HTTPS |
| SOURCE_CA_BUNDLE | Bundle confiável opcional dentro do contêiner; exige montar o arquivo se usado |

Não é necessário configurar serviços de IA. As chaves das fontes não são armazenadas no navegador nem incluídas nos logs da aplicação.

O portal UFRN apresentou uma cadeia TLS incompleta na validação. Incluímos o intermediário público RNP ICPEdu, obtido no domínio oficial da autoridade emissora, para completar a cadeia até uma raiz confiável. Hostname e verificação TLS continuam ativos. Veja [a origem e o fingerprint](backend/certificates/README.md).

## Webhooks

1. Defina os domínios permitidos e o segredo de assinatura no servidor.
2. Cadastre um destino em **Administração**.
3. Informe seu ID ao criar uma regra em **Automações**.

O worker envia JSON com `id`, `kind`, `title` e `payload`. O cabeçalho `X-CampusOps-Signature` contém `sha256=<HMAC-SHA256 do corpo original>`. O destinatário deve comparar a assinatura em tempo constante e deduplicar `Idempotency-Key`. A entrega é **pelo menos uma vez**, com até cinco tentativas e intervalo crescente, sem seguir redirecionamentos.

Destinos precisam ser HTTPS, porta 443, pertencer à lista autorizada e resolver apenas para IPs públicos. Um ambiente corporativo deve complementar isso com controle de saída de rede. A aplicação não cadastra nem envia mensagens para destinos externos automaticamente.

## Agendamentos e recuperação

O Celery Beat verifica agendamentos a cada minuto. O intervalo mínimo é de 15 minutos; o primeiro disparo ocorre no próximo ciclo. Agendamentos usam as instituições atualmente acompanhadas. Se a fonte já estiver ocupada, aquele disparo é omitido para evitar sobreposição.

A regra **Resumo semanal** gera um evento às segundas-feiras a partir das 9h no horário de Brasília, uma vez por semana, durante a disponibilidade do agendador. O resumo também está disponível a qualquer momento na tela Radar. Ele conta publicações coletadas/atualizadas no período, não somente publicadas nele. Eventos de resumo incluem até 50 títulos.

Uma execução é persistida antes de publicar na fila. Se a publicação falhar, permanece pendente para o próximo ciclo do agendador. A atualização atômica de estado impede que mensagens duplicadas executem o mesmo trabalho simultaneamente. Execuções interrompidas por mais de duas horas são finalizadas como falha e podem ser reprocessadas manualmente.

Use uma instância do scheduler. O worker pode ser ampliado; o bloqueio por fonte está no banco. Redis usa AOF e volume persistente.

## Electron

Com o Docker iniciado:

```powershell
cd desktop
npm ci
npm start
```

O cliente abre somente `http://localhost:8080`; a sessão é independente do navegador. O backend continua nos contêineres. Não foi gerado instalador assinado nem mecanismo de atualização automática.

## Desenvolvimento e testes

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.lock
cd backend
..\.venv\Scripts\python -m pytest tests -q
```

Para o backend local: `python -m uvicorn app.main:app --reload` no diretório backend. Sem DATABASE_URL usa SQLite. A API aplica Alembic no início. Para processamento local, configure um Redis e execute, em terminais separados, `celery -A app.tasks:celery worker -Q ingestion,control,reports,notifications,monitoring --pool=solo --loglevel=INFO` e `celery -A app.tasks:celery beat --schedule=<caminho-gravavel> --loglevel=INFO`. No Windows, prefira os workers Docker. Use banco e broker separados para desenvolvimento.

Frontend:

```powershell
cd frontend
npm ci
npm run dev
npm run build
```

Teste de navegador isolado:

```powershell
$env:QA_PYTHON='C:\caminho\do\projeto\.venv\Scripts\python.exe'
$env:PLAYWRIGHT_CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
npm run test:e2e
```

Alternativamente instale o Chromium com `npx playwright install chromium` e omita PLAYWRIGHT_CHROME_PATH. O teste usa banco temporário, dados explicitamente fictícios de QA e nenhum worker externo; não altera o banco do usuário. Screenshots ficam em `frontend/artifacts`.

O CI executa testes Python, build TypeScript/Vue e teste de navegador. Validação do cliente Electron: `node scripts/verify-desktop.cjs` a partir da raiz, após instalar dependências de frontend/desktop e iniciar Docker. A janela de validação fica oculta.

## Limites operacionais

- ROR: teto de 500 páginas/10 mil resultados da API; uma paginação não é um snapshot consistente.
- OpenAlex: até 50 instituições por execução. Sem chave, até 100 páginas por instituição; com chave usa cursor, respeitando o teto configurado. Não ativa pagamentos automaticamente.
- Crossref: até 200 DOIs por execução. Nem todo DOI pertence ao Crossref. Ausências são registradas como rejeições, sem apagar o trabalho.
- UFRN: catálogo de metadados; o conteúdo dos arquivos CSV/PDF não é importado como tabela de cursos nesta versão.
- ORCID: leitura de campos públicos, sem escrita ou associação automática por nomes semelhantes.
- Qualidade e perfis calculam agregados em memória; para grandes volumes, mover esses cálculos para consultas agregadas/materializadas.
- Exportação CSV: até 10 mil registros. Histórico e listas têm limites/paginação informados na interface.

Veja [arquitetura](docs/architecture.md) e [runbook](docs/runbook.md).
