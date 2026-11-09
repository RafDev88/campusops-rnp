/** Shared page language and navigation. Route names remain stable for links. */
export type PortalPage = {
  id: string;
  label: string;
  description: string;
  group: "consult" | "update" | "automate" | "follow" | "admin";
  steps: string[];
};
export const pages: PortalPage[] = [
  {
    id: "account",
    label: "Minha conta",
    description: "Cuide da sua senha e dos acessos à sua conta.",
    group: "consult",
    steps: [
      "Use uma senha exclusiva.",
      "Revise os acessos ativos.",
      "Encerre sessões que não está usando.",
    ],
  },
  {
    id: "overview",
    label: "Início",
    description:
      "Encontre um assunto, conheça uma instituição ou retome sua pesquisa.",
    group: "consult",
    steps: [
      "Escolha o tipo de informação que procura.",
      "Digite um assunto ou nome.",
      "Abra um resultado para conhecer os detalhes.",
    ],
  },
  {
    id: "search",
    label: "Pesquisar",
    description:
      "Procure por assunto, universidade, autor ou título. Depois, escolha o tipo de resultado.",
    group: "consult",
    steps: [
      "Digite uma palavra ou um nome.",
      "Escolha Publicações, Instituições, Pesquisadores ou Dados abertos.",
      "Abra os detalhes ou use a estrela para guardar um resultado.",
    ],
  },
  {
    id: "institutions",
    label: "Instituições",
    description:
      "Conheça universidades, suas áreas de pesquisa e as publicações disponíveis.",
    group: "consult",
    steps: [
      "Pesquise pelo nome ou sigla da universidade.",
      "Use localização e tipo para reduzir a lista.",
      "Selecione Explorar para conhecer temas, autores e publicações.",
    ],
  },
  {
    id: "publications",
    label: "Publicações",
    description:
      "Encontre artigos, livros e outros trabalhos científicos. Comece por um assunto.",
    group: "consult",
    steps: [
      "Digite o assunto no campo de pesquisa.",
      "Se precisar, refine por instituição, tema ou ano.",
      "Abra um trabalho para ler o resumo, consultar a fonte ou guardar nos favoritos.",
    ],
  },
  {
    id: "researchers",
    label: "Pesquisadores",
    description:
      "Encontre autores e conheça os trabalhos disponíveis no catálogo.",
    group: "consult",
    steps: [
      "Pesquise pelo nome do autor.",
      "Use o identificador ORCID para distinguir pessoas com nomes parecidos.",
      "Abra o perfil para consultar trabalhos e vínculos públicos disponíveis.",
    ],
  },
  {
    id: "datasets",
    label: "Dados abertos",
    description:
      "Encontre conjuntos de informações e acesse os arquivos no portal de origem.",
    group: "consult",
    steps: [
      "Procure um assunto, como cursos ou matrículas.",
      "Abra o conjunto para ver os arquivos disponíveis.",
      "Confira o formato e a atualização no portal de origem antes de usar os dados.",
    ],
  },
  {
    id: "my-research",
    label: "Minhas pesquisas",
    description:
      "Seus favoritos, pesquisas salvas e novidades, reunidos em um só lugar.",
    group: "consult",
    steps: [
      "Reabra uma pesquisa salva para continuar com os mesmos filtros.",
      "Consulte os registros que guardou com a estrela.",
      "Veja novidades encontradas nas próximas atualizações do catálogo.",
    ],
  },
  {
    id: "reports",
    label: "Relatórios",
    description:
      "Baixe resultados em planilha e programe novos arquivos a partir das suas pesquisas.",
    group: "consult",
    steps: [
      "Salve os filtros desejados na página Publicações.",
      "Crie um modelo de relatório usando essa pesquisa.",
      "Gere o arquivo e baixe quando estiver pronto. Seus relatórios são privados.",
    ],
  },
  {
    id: "help",
    label: "Ajuda",
    description:
      "Orientações para começar, entender os resultados e usar o portal.",
    group: "consult",
    steps: [
      "Escolha a dúvida que corresponde ao que você precisa.",
      "Leia a orientação e use os links para abrir a página indicada.",
      "Consulte o glossário para entender termos da pesquisa.",
    ],
  },
  {
    id: "sources",
    label: "Integrações",
    description:
      "Escolha de onde vêm as informações e solicite atualizações do catálogo.",
    group: "update",
    steps: [
      "Escolha a fonte de informação.",
      "Confira a cobertura e as permissões disponíveis.",
      "Configure uma coleta e acompanhe sua conclusão em Execuções.",
    ],
  },
  {
    id: "runs",
    label: "Execuções",
    description: "Veja o andamento e o resultado das atualizações do catálogo.",
    group: "update",
    steps: [
      "Localize uma atualização pelo período, fonte ou situação.",
      "Abra Detalhes para ver o andamento e a cobertura.",
      "Se houver falha, leia o motivo antes de retomar ou repetir a tarefa.",
    ],
  },
  {
    id: "reviews",
    label: "Revisão de registros",
    description:
      "Confira informações que não puderam ser importadas e decida como tratá-las.",
    group: "update",
    steps: [
      "Leia o motivo da rejeição.",
      "Confira o identificador na fonte original.",
      "Reprocesse após corrigir a causa ou marque como ignorado.",
    ],
  },
  {
    id: "changes",
    label: "Alterações",
    description:
      "Compare os valores anteriores e atuais das informações atualizadas.",
    group: "update",
    steps: [
      "Escolha a fonte ou o identificador do registro.",
      "Compare os campos Antes e Depois.",
      "Abra a execução para entender de onde veio a mudança.",
    ],
  },
  {
    id: "quality",
    label: "Qualidade",
    description:
      "Identifique informações ausentes, possíveis duplicações e dados que precisam de revisão.",
    group: "update",
    steps: [
      "Leia a sinalização de cada registro.",
      "Compare as informações nas fontes originais.",
      "Considere que uma sinalização precisa de avaliação humana.",
    ],
  },
  {
    id: "automation",
    label: "Automações",
    description:
      "Programe tarefas e avisos para acompanhar os assuntos e fontes do seu interesse.",
    group: "automate",
    steps: [
      "Escolha a tarefa ou o aviso desejado.",
      "Defina os horários e teste as regras antes de ativar.",
      "Acompanhe os resultados em Execuções, Incidentes ou Radar e resumo.",
    ],
  },
  {
    id: "flows",
    label: "Fluxos",
    description:
      "Conecte várias tarefas para executá-las em sequência, sem cliques intermediários.",
    group: "automate",
    steps: [
      "Escolha as etapas da rotina.",
      "Defina limites e como tratar resultados parciais.",
      "Inicie agora ou programe uma agenda.",
    ],
  },
  {
    id: "policies",
    label: "Limites e recuperação",
    description:
      "Defina quantas consultas podem ser feitas e como as falhas serão tratadas.",
    group: "automate",
    steps: [
      "Confira os limites locais e os da fonte.",
      "Ajuste chamadas, tentativas e espaço para retomada.",
      "Salve a política antes de retomar uma tarefa pausada por limite.",
    ],
  },
  {
    id: "monitoring",
    label: "Saúde das fontes e links",
    description:
      "Confira se os endereços respondem e entenda problemas de acesso ou HTTPS.",
    group: "follow",
    steps: [
      "Comece por Verificar APIs agora ou filtre os endereços que precisam de atenção.",
      "Abra Ver diagnóstico para entender o problema.",
      "Confira os registros afetados antes de decidir o que fazer.",
    ],
  },
  {
    id: "incidents",
    label: "Incidentes",
    description:
      "Acompanhe problemas detectados e confira quais já foram resolvidos.",
    group: "follow",
    steps: [
      "Leia o problema e a fonte afetada.",
      "Confira o histórico ou diagnóstico correspondente.",
      "Resolva manualmente quando necessário, após verificar a causa.",
    ],
  },
  {
    id: "radar",
    label: "Radar e resumo",
    description:
      "Veja os avisos gerados pelas regras e as recuperações das fontes.",
    group: "follow",
    steps: [
      "Leia os avisos mais recentes.",
      "Abra os registros relacionados quando estiverem disponíveis.",
      "Ajuste as regras se os avisos não correspondem ao que deseja acompanhar.",
    ],
  },
  {
    id: "settings",
    label: "Administração",
    description:
      "Gerencie o acesso das pessoas e os destinos das notificações.",
    group: "admin",
    steps: [
      "Escolha a configuração que deseja alterar.",
      "Conceda apenas as permissões necessárias.",
      "Confira a auditoria para acompanhar as mudanças.",
    ],
  },
];
export const pageByName = (name: unknown) =>
  pages.find((p) => p.id === String(name)) || pages[0];
export const managementGroups = [
  {
    id: "update",
    title: "Atualizar informações",
    description: "Fontes, atualizações e qualidade dos dados.",
  },
  {
    id: "automate",
    title: "Programar rotinas",
    description: "Horários, etapas e limites de consultas.",
  },
  {
    id: "follow",
    title: "Acompanhar problemas",
    description: "Links, avisos e diagnósticos.",
  },
  {
    id: "admin",
    title: "Administrar acesso",
    description: "Pessoas e notificações.",
  },
];
