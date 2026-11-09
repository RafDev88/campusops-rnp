# Validação da entrega

## Confiabilidade e experiência · 0.8

- Backend: **110 testes aprovados** na execução completa final, com cenários de cobertura desconhecida/parcial, privacidade de resumos, erros correlacionados sem eco de dados sensíveis, falha interna sanitizada, troca de senha/rotação e propriedade das sessões. Os resultados anteriores abaixo permanecem históricos.
- Navegador: fluxo completo de pesquisa e administração aprovado, incluindo painel de cobertura por teclado, troca de senha, formulário de conta no celular e ausência de erros JavaScript. O teste de título da ficha passou a distinguir seu heading dos títulos dos resultados; a navegação dos filtros aguarda a URL correspondente.
- PostgreSQL temporário: migrações, busca, automações, novos resumos, sessões e permissões verificados com broker em memória; banco descartado ao final. Job equivalente adicionado ao CI, sem alegar execução remota.
- Backup: pg_dump restaurado com sucesso em banco descartável, revisão `0007`, 1.693 instituições, 100 publicações e 1 conta. Dump e manifesto mantidos em `backups/`, fora do versionamento.
- Benchmark SQLite isolado: 5 mil registros fictícios, 20 amostras após aquecimento, mediana 57,37 ms e p95 75,84 ms para contagem + primeira página; não é teste de carga HTTP/PostgreSQL.
- Demonstração Docker separada: login, banner, cookie próprio, instituição e três trabalhos fictícios, cobertura parcial e layout desktop/celular verificados. Nenhum worker externo é iniciado na demonstração.
- Tipagem/build de interface aprovados. Permanecem o aviso conhecido de bundle de gráficos acima de 500 kB e a depreciação TestClient/HTTPX. Não foi realizada auditoria completa com leitor de tela.

Procedimentos e limites detalhados em [Confiabilidade](reliability.md).

## Documentação do backend · 0.7

O guia em `docs/backend` descreve módulos, configuração, identidade dos dados, segurança, contratos HTTP, filas, recuperação e monitoramento. A referência gerada inventaria 82 operações HTTP, modelos persistidos e parâmetros de publicações. `scripts/document-backend.py --check` verifica divergências no CI, sem startup, migração ou consultas ao banco.

O OpenAPI informa o nível mínimo de acesso derivado das dependências, cookie de sessão e cabeçalho CSRF nas operações de escrita. Dois testes verificam a cobertura de todas as operações, inclusive routers incluídos, e que a documentação pública não altera os bloqueios reais de autenticação/CSRF.

Validação local desta atualização: **104 testes Python aprovados**, referência e dicionário de dados regenerados e conferidos com `--check`, links locais dos guias verificados e imagem Docker da API construída. O aviso de depreciação do TestClient/HTTPX permanece conhecido. A configuração do CI foi atualizada; isso não comprova execução em um provedor remoto.

As evidências das entregas anteriores abaixo são históricas; quantidades de registros e versões nelas não representam necessariamente o estado atual do catálogo.

## Pesquisa integrada · 0.3

- 41 testes Python, incluindo nove cenários novos de busca: acentos/siglas, links DOI/ORCID, filtros combinados, paridade CSV, relações de temas e autorias, identidade ORCID, privacidade, avisos deduplicados e apresentação de vínculos públicos.
- A integridade de chaves estrangeiras também foi ativada no SQLite usado em desenvolvimento e testes.
- PostgreSQL isolado: extensão pg_trgm, índices de busca, gravação de relações com chaves estrangeiras, filtros e notificações privadas verificados sem alterar contas do banco principal.
- Chrome: navegação entre publicação/autor/instituição, sugestões por teclado, filtros combinados, exportação filtrada, favoritos, pesquisas salvas, URL compartilhável, recarregar e Voltar/Avançar.
- Layout do celular com resultados organizados em blocos e sem transbordamento horizontal da página.
- As buscas consultam dados já importados. A tolerância por trigramas está disponível no PostgreSQL; o SQLite usa a normalização textual sem acentos.

O registro abaixo descreve a validação anterior das integrações; os dados de origem são preservados durante a migração de pesquisa.

- 32 testes Python aprovados: permissões, sessões, CSRF, limitação de login, paginação, cobertura parcial, duplicatas, validação contratual, idempotência, regras, resumo semanal, recuperação, webhook HMAC/outbox e migrações.
- Build Vue/TypeScript aprovado, com módulos carregados sob demanda. O bundle de gráficos ainda supera o aviso de 500 kB do Vite, mas só é carregado nas telas que o usam.
- Teste Chrome aprovado: setup, instituição acompanhada, perfil/gráficos, publicação, regra, agendamento, criação de usuário e restrições do perfil de consulta. Verificada ausência de rolagem horizontal global em viewport de 390 px.
- Electron carregou a interface em janela oculta, com sandbox e contextIsolation ativos, nodeIntegration desativado e `require` indisponível no renderer.
- PostgreSQL temporário separado: migrações, criação inicial de administrador, sequência de usuários, login e bloqueios do perfil de consulta verificados. Banco temporário removido ao fim; nenhum usuário de teste foi criado no banco principal.
- Fluxo Docker real com API, worker, scheduler, Redis e PostgreSQL. Coletas de ROR, UFRN, OpenAlex, Crossref e ORCID persistidas pelo worker.

## Dados reais usados para verificação

O catálogo local ficou com 1.693 instituições únicas. O ROR reportou/processou 2.222 registros em 112 páginas, mas repetiu identificadores; a execução está marcada como parcial e a revisão da cobertura registrada na auditoria. Não há exclusão automática de instituições ausentes em páginas parciais.

UFRN: 11 conjuntos de dados relacionados à busca por cursos. OpenAlex: 100 trabalhos da UFRN no período desde 2025, uma página, portanto cobertura parcial. Crossref: cinco DOIs consultados, quatro enriquecidos e um não encontrado, sem apagar o trabalho. ORCID: um perfil público encontrado nos autores dos trabalhos importados.

Webhooks foram testados com transporte HTTP simulado, incluindo falha e recuperação; nenhum destino externo foi cadastrado ou recebeu mensagens. O usuário deverá configurar seus destinos autorizados.

O portal UFRN passou na verificação TLS após completar a cadeia com o intermediário público RNP ICPEdu; a validação até raiz confiável e de hostname permaneceu ativa.

Os testes em CI estão configurados, mas não foram executados em um provedor remoto nesta sessão. O pipeline foi adicionado ao repositório local.
