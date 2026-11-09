<script setup lang="ts">
import { ref } from "vue";
import Button from "primevue/button";
import { api, refresh, type Source } from "../api";
const props = defineProps<{ source: Source; institutionId?: string }>();
const emit = defineEmits<{ done: []; error: [message: string] }>();
const pages = ref(
    props.source === "ror" ? 500 : props.source === "openalex" ? 3 : 10,
  ),
  year = ref(2024),
  limit = ref(25),
  orcid = ref(""),
  query = ref(""),
  busy = ref(false);
const lastYear = ref<number | null>(null),
  language = ref(""),
  workType = ref("");
const incremental = ref(true),
  since = ref(""),
  pending = ref(false);
async function submit() {
  busy.value = true;
  try {
    await api("sync", "POST", {
      source: props.source,
      max_pages: pages.value,
      year_from: year.value,
      year_to: lastYear.value || null,
      language: language.value,
      work_type: workType.value,
      limit: limit.value,
      orcid: orcid.value,
      query: query.value,
      institution_id: props.institutionId || "",
      incremental: incremental.value,
      since_date: since.value,
      only_pending: pending.value,
    });
    refresh();
    emit("done");
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <form class="form-grid sync-form" @submit.prevent="submit">
    <label v-if="source === 'ror' || source === 'openalex' || source === 'ufrn'"
      >Máximo de páginas<input
        v-model.number="pages"
        type="number"
        min="1"
        max="500"
        required
      /><small>{{
        source === "ror"
          ? "Até 20 instituições por página. 500 cobre o limite da API."
          : source === "openalex"
            ? "Até 100 trabalhos por página e instituição."
            : "Até 50 conjuntos por página."
      }}</small></label
    >
    <label v-if="source === 'openalex'"
      >Publicações a partir de<input
        v-model.number="year"
        type="number"
        min="1900"
        max="2100"
        required
      /><small>{{
        institutionId
          ? "Coleta desta instituição."
          : "Coleta das instituições acompanhadas (até 50)."
      }}</small></label
    >
    <label v-if="source === 'crossref'"
      >Máximo de DOIs<input
        v-model.number="limit"
        type="number"
        min="1"
        max="200"
        required
      /><small>Prioriza publicações ainda não enriquecidas.</small></label
    >
    <label v-if="source === 'orcid'"
      >ORCID público<input
        v-model="orcid"
        placeholder="0000-0000-0000-000X"
        pattern="[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]"
        required
    /></label>
    <label v-if="source === 'ufrn'"
      >Busca no catálogo<input
        v-model="query"
        maxlength="150"
        placeholder="Ex.: cursos (opcional)"
      /><small>Importa metadados e links, sem baixar os arquivos.</small></label
    >
    <template v-if="source === 'openalex'">
      <label
        >Assunto da coleta (opcional)<input
          v-model="query"
          maxlength="150"
          placeholder="Ex.: educação, redes, saúde"
        /><small
          >Pesquisa na fonte. Vazio: todas as publicações do escopo
          escolhido.</small
        ></label
      >
      <label
        >Ano final opcional<input
          v-model.number="lastYear"
          type="number"
          min="1900"
          max="2100"
      /></label>
      <label
        >Idioma da coleta<select v-model="language">
          <option value="">Todos</option>
          <option value="pt">Português</option>
          <option value="en">Inglês</option>
          <option value="es">Espanhol</option>
        </select></label
      >
      <label
        >Tipo da coleta<select v-model="workType">
          <option value="">Todos</option>
          <option value="article">Artigo</option>
          <option value="review">Revisão</option>
          <option value="dissertation">Dissertação ou tese</option>
          <option value="book">Livro</option>
          <option value="book-chapter">Capítulo de livro</option>
          <option value="preprint">Preprint</option>
        </select></label
      >
      <label>Data inicial opcional<input v-model="since" type="date" /></label
      ><label class="checkbox-label"
        ><input v-model="incremental" type="checkbox" />Usar marcador
        incremental quando disponível</label
      ><small
        >Coletas completas avançam o marcador por data de publicação. Desmarque
        para reconciliar dados históricos.</small
      ></template
    >
    <label v-if="source === 'crossref'" class="checkbox-label"
      ><input v-model="pending" type="checkbox" />Somente DOIs ainda não
      consultados</label
    >
    <Button type="submit" :loading="busy" label="Adicionar à fila" />
  </form>
</template>
