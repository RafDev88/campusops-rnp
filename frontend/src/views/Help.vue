<template>
  <section class="help-page">
    <p class="scope-note">
      Você não precisa conhecer as ferramentas de coleta para consultar as
      informações. Comece pelo campo de pesquisa ou escolha um tipo de conteúdo
      no menu.
    </p>
    <h2>Como encontrar o que você precisa</h2>
    <details open>
      <summary>Quero pesquisar um assunto</summary>
      <p>
        Abra <RouterLink to="/search">Pesquisar</RouterLink>, digite uma
        palavra, como “educação” ou “redes”, e selecione Buscar informações.
        Escolha o tipo de informação para reduzir os resultados.
      </p>
    </details>
    <details>
      <summary>Quero encontrar trabalhos de uma universidade</summary>
      <p>
        Abra <RouterLink to="/institutions">Instituições</RouterLink>, procure a
        universidade e abra seus detalhes. Os links de temas e anos levam às
        publicações correspondentes. Você também pode selecionar uma instituição
        nos filtros de <RouterLink to="/publications">Publicações</RouterLink>.
      </p>
    </details>
    <details>
      <summary>Quero refinar ou salvar uma pesquisa</summary>
      <p>
        Em Publicações, combine assunto, instituição, tema, ano e acesso aberto.
        Use Mais opções de pesquisa para autor, idioma, tipo de publicação,
        periódico, disponibilidade de resumo ou DOI, citações e ordenação. A
        busca exige palavras completas por padrão. Você pode escolher uma frase
        na mesma ordem, qualquer palavra ou o título completo exato. A opção de
        títulos parecidos pode ajudar com erros de escrita. Os filtros aplicados
        aparecem acima dos resultados e podem ser removidos individualmente.
      </p>
      <p>
        Salvar pesquisa guarda os critérios na sua conta. A estrela guarda um
        registro nos seus favoritos. Encontre ambos em Minhas pesquisas. Copiar
        link permite compartilhar os critérios; a outra pessoa precisa ter
        acesso ao mesmo portal.
      </p>
    </details>
    <details>
      <summary>Quero baixar os resultados</summary>
      <p>
        Em Publicações, selecione Baixar planilha (CSV). O arquivo abre em
        programas de planilha e considera os filtros atuais, com até 10 mil
        resultados. Em <RouterLink to="/reports">Relatórios</RouterLink>, você
        pode gerar arquivos a partir de pesquisas salvas e programar novas
        gerações. Os relatórios são privados para a sua conta.
      </p>
    </details>
    <details>
      <summary>Minha pesquisa não encontrou resultados</summary>
      <p>
        Revise a escrita, tente uma palavra mais simples ou remova os filtros. A
        busca consulta apenas os dados já importados no portal. Um resultado
        vazio não significa que o trabalho ou a instituição não existe na fonte
        original.
      </p>
    </details>
    <details>
      <summary>É minha primeira vez usando o portal</summary>
      <p>
        Na página Início, escolha o que deseja encontrar e siga os primeiros
        passos. Você pode avançar no seu ritmo, ocultar as orientações ou
        reabri-las em Rever os primeiros passos.
      </p>
      <p>
        Use Como usar esta página, ao lado do título de cada seção, para ver as
        ações mais importantes. Em Outras consultas ficam pesquisadores, dados
        abertos e relatórios. Os termos DOI e ORCID são opcionais: você pode
        começar pesquisando só pelo assunto ou nome.
      </p>
    </details>
    <h2>Entenda as informações</h2>
    <dl class="help-glossary">
      <div>
        <dt>Fonte</dt>
        <dd>
          Serviço de origem da informação: ROR para instituições, OpenAlex para
          publicações, Crossref para informações de trabalhos, ORCID para
          pesquisadores e portal UFRN para dados abertos.
        </dd>
      </div>
      <div>
        <dt>Acesso aberto</dt>
        <dd>
          Indicação da fonte de que uma publicação pode estar disponível para
          leitura gratuita. Consulte o endereço original para confirmar a
          disponibilidade.
        </dd>
      </div>
      <div>
        <dt>DOI e ORCID</dt>
        <dd>
          DOI identifica um trabalho científico. ORCID identifica um
          pesquisador. Esses identificadores ajudam a distinguir registros com
          nomes semelhantes.
        </dd>
      </div>
      <div>
        <dt>Coleta parcial</dt>
        <dd>
          Uma atualização que trouxe apenas parte dos dados disponíveis. Os
          limites de páginas e consultas podem restringir a cobertura.
        </dd>
      </div>
    </dl>
    <h2>Para quem atualiza o catálogo</h2>
    <p>
      Em Início e Publicações, abra “De onde vêm estes dados e quando foram
      atualizados?” para conferir a última coleta e seus limites. Cobertura
      completa vale somente para o escopo da execução.
    </p>
    <p>
      Em Execuções, “Acompanhe suas automações” reúne agendas, etapas, falhas e
      ações recomendadas. Em Outras consultas → Minha conta, você pode trocar a
      senha e encerrar outros acessos.
    </p>
    <p>
      Abra Gestão de dados no topo da página para acessar fontes, coletas,
      automações e qualidade. Sua conta precisa de permissão de operador ou
      administrador para alterar essas configurações.
    </p>
    <p class="muted">
      CampusOps é um projeto de consulta acadêmica. Não representa um órgão
      governamental.
    </p>
  </section>
</template>
