<script setup lang="ts">
import { languages, workTypes } from "../discovery";
import type { PublicationFacets } from "../researchFilters";
import HelpHint from "./HelpHint.vue";
defineProps<{
  values: Record<string, string>;
  facets: PublicationFacets;
  advanced: boolean;
  approximateSupported: boolean;
}>();
const emit = defineEmits<{
  change: [key: string, value: string];
  type: [key: string, value: string];
  submit: [];
  toggle: [];
}>();
</script>
<template>
  <form class="publication-filters" @submit.prevent="emit('submit')">
    <label class="wide-filter"
      >Assunto ou título do trabalho<input
        :value="values.q"
        aria-label="Buscar título"
        placeholder="Ex.: redes, educação, nome do autor…"
        maxlength="150"
        @input="
          emit('type', 'q', ($event.target as HTMLInputElement).value)
        " /></label
    ><label
      >Instituição<select
        :value="values.institution_id"
        aria-label="Instituição"
        @change="
          emit(
            'change',
            'institution_id',
            ($event.target as HTMLSelectElement).value,
          )
        "
      >
        <option value="">Todas as instituições</option>
        <option
          v-for="i in facets.institutions"
          :key="i.id + i.name"
          :value="i.id"
        >
          {{ i.name }}
        </option>
        <option
          v-if="
            values.institution_id &&
            !facets.institutions.some((i) => i.id === values.institution_id)
          "
          :value="values.institution_id"
        >
          {{ values.institution_id }}
        </option>
      </select></label
    ><label
      >Tema<select
        :value="values.topic"
        aria-label="Tema"
        @change="
          emit('change', 'topic', ($event.target as HTMLSelectElement).value)
        "
      >
        <option value="">Todos os temas</option>
        <option v-for="t in facets.topics" :key="t.id" :value="t.id">
          {{ t.name }} ({{ t.count }})
        </option>
        <option
          v-if="
            values.topic && !facets.topics.some((t) => t.id === values.topic)
          "
          :value="values.topic"
        >
          {{ values.topic }}
        </option>
      </select></label
    ><label v-show="advanced"
      >Autor ou ORCID<input
        :value="values.author"
        aria-label="Autor ou ORCID"
        @input="
          emit('type', 'author', ($event.target as HTMLInputElement).value)
        "
        placeholder="Nome ou identificador"
        maxlength="150" /></label
    ><label
      >Ano inicial<input
        :value="values.year_from"
        aria-label="Ano inicial"
        type="number"
        min="1900"
        max="2100"
        @input="
          emit('type', 'year_from', ($event.target as HTMLInputElement).value)
        "
        @change="
          emit(
            'change',
            'year_from',
            ($event.target as HTMLSelectElement).value,
          )
        " /></label
    ><label v-show="advanced"
      >Ano final<input
        :value="values.year_to"
        aria-label="Ano final"
        type="number"
        min="1900"
        max="2100"
        @input="
          emit('type', 'year_to', ($event.target as HTMLInputElement).value)
        "
        @change="
          emit('change', 'year_to', ($event.target as HTMLSelectElement).value)
        " /></label
    ><label
      >Acesso aberto<select
        :value="values.oa"
        aria-label="Acesso aberto"
        @change="
          emit('change', 'oa', ($event.target as HTMLSelectElement).value)
        "
      >
        <option value="">Qualquer condição</option>
        <option value="true">Identificado como aberto</option>
        <option value="false">Aberto não identificado</option>
      </select></label
    ><label v-show="advanced"
      >Metadados<select
        :value="values.source"
        aria-label="Metadados"
        @change="
          emit('change', 'source', ($event.target as HTMLSelectElement).value)
        "
      >
        <option value="">Todas as publicações</option>
        <option value="openalex">OpenAlex</option>
        <option value="crossref">Enriquecidas pelo Crossref</option>
      </select></label
    ><label v-show="advanced"
      >Ordenar por<select
        :value="values.sort"
        aria-label="Ordenar por"
        @change="
          emit('change', 'sort', ($event.target as HTMLSelectElement).value)
        "
      >
        <option value="">Relevância</option>
        <option value="recent">Mais recentes</option>
        <option value="title">Título</option>
        <option value="citations">Mais citadas</option>
      </select></label
    >
    <template v-if="advanced">
      <label
        >Como combinar as palavras<select
          :value="values.mode || 'all'"
          aria-label="Como combinar as palavras"
          @change="
            emit('change', 'mode', ($event.target as HTMLSelectElement).value)
          "
        >
          <option value="all">Todas as palavras</option>
          <option value="phrase">Frase na mesma ordem</option>
          <option value="any">Qualquer palavra</option>
          <option value="exact">Título completo exato</option>
        </select></label
      >
      <label
        >Onde pesquisar<select
          :value="values.search_in || 'all'"
          aria-label="Onde pesquisar"
          @change="
            emit(
              'change',
              'search_in',
              ($event.target as HTMLSelectElement).value,
            )
          "
        >
          <option value="all">Todos os campos</option>
          <option value="title">Somente no título</option>
          <option value="abstract">Somente no resumo</option>
        </select></label
      >
      <label
        >Idioma dos metadados<select
          :value="values.language"
          aria-label="Idioma dos metadados"
          @change="
            emit(
              'change',
              'language',
              ($event.target as HTMLSelectElement).value,
            )
          "
        >
          <option value="">Todos os idiomas</option>
          <option v-for="l in facets.languages" :key="l.id" :value="l.id">
            {{ languages[l.id] || l.id }} ({{ l.count }})
          </option>
        </select></label
      >
      <label
        >Tipo de publicação<select
          :value="values.work_type"
          aria-label="Tipo de publicação"
          @change="
            emit(
              'change',
              'work_type',
              ($event.target as HTMLSelectElement).value,
            )
          "
        >
          <option value="">Todos os tipos</option>
          <option v-for="t in facets.work_types" :key="t.id" :value="t.id">
            {{ workTypes[t.id] || t.id }} ({{ t.count }})
          </option>
        </select></label
      >
      <label
        >Periódico ou veículo<input
          :value="values.journal"
          aria-label="Periódico ou veículo"
          placeholder="Nome da revista ou publicação"
          @input="
            emit('type', 'journal', ($event.target as HTMLInputElement).value)
          "
          maxlength="200"
      /></label>
      <label
        >Mínimo de citações<input
          :value="values.citations_min"
          aria-label="Mínimo de citações"
          type="number"
          min="0"
          max="100000000"
          @change="
            emit(
              'change',
              'citations_min',
              ($event.target as HTMLSelectElement).value,
            )
          "
      /></label>
      <label
        >Disponibilidade de resumo<select
          :value="values.has_abstract"
          aria-label="Disponibilidade de resumo"
          @change="
            emit(
              'change',
              'has_abstract',
              ($event.target as HTMLSelectElement).value,
            )
          "
        >
          <option value="">Qualquer</option>
          <option value="true">Com resumo importado</option>
          <option value="false">Sem resumo importado</option>
        </select></label
      >
      <label
        >Identificador DOI<select
          :value="values.has_doi"
          aria-label="Identificador DOI"
          @change="
            emit(
              'change',
              'has_doi',
              ($event.target as HTMLSelectElement).value,
            )
          "
        >
          <option value="">Qualquer</option>
          <option value="true">Com DOI</option>
          <option value="false">Sem DOI</option>
        </select></label
      >
      <label
        >Retratação na fonte<select
          :value="values.retracted"
          aria-label="Retratação na fonte"
          @change="
            emit(
              'change',
              'retracted',
              ($event.target as HTMLSelectElement).value,
            )
          "
        >
          <option value="">Todos, inclusive não informado</option>
          <option value="false">Fonte informa: não retratado</option>
          <option value="true">Retratado na fonte</option>
        </select></label
      >
      <label v-if="approximateSupported" class="checkbox-label"
        ><input
          type="checkbox"
          :checked="values.approximate === 'true'"
          @change="
            emit(
              'change',
              'approximate',
              ($event.target as HTMLInputElement).checked ? 'true' : '',
            )
          "
        />Incluir títulos parecidos</label
      >
      <p class="filter-explanation">
        A busca exige palavras completas por padrão. DOI, ORCID e
        identificadores são comparados exatamente. A aproximação é opcional e
        funciona no modo Todas as palavras. Campos ausentes não são presumidos.
      </p>
    </template>
    <button
      class="text-button filter-more"
      type="button"
      :aria-expanded="advanced"
      @click="emit('toggle')"
    >
      {{ advanced ? "Menos opções de pesquisa" : "Mais opções de pesquisa" }}
      {{ advanced ? "−" : "+" }}
    </button>
    <div class="search-form-help">
      <HelpHint
        label="Não conhece esses termos?"
        text="Resumo é uma apresentação curta do trabalho. DOI identifica uma publicação; ORCID identifica um pesquisador. Você pode pesquisar só por assunto, sem conhecer esses códigos."
      /><span
        >Os resultados são atualizados conforme você digita ou escolhe um
        filtro.</span
      >
    </div>
    <button type="submit" class="primary-action publication-submit">
      Pesquisar publicações
    </button>
  </form>
</template>
