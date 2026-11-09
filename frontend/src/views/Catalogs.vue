<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import Pager from "../components/Pager.vue";
import { api, date, revision, safeUrl, type Page, type User } from "../api";
const props = defineProps<{ mode: string; user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Issue = {
  id: string;
  title: string;
  reasons: string[];
  openalex_title: string;
  crossref_title: string;
};
type Dataset = {
  id: string;
  title: string;
  url: string;
  modified: string;
  fetched_at: string;
  resources: { id: string; name: string; format: string; url: string }[];
};
type Researcher = {
  orcid: string;
  name: string;
  fetched_at: string;
  data: Record<string, unknown>;
};
const issues = ref<Page<Issue>>({ total: 0, items: [] }),
  datasets = ref<Page<Dataset>>({ total: 0, items: [] }),
  researchers = ref<Researcher[]>([]),
  counts = ref<Record<string, number>>({}),
  q = ref(""),
  offset = ref(0),
  orcid = ref(""),
  busy = ref(false);
let timer: ReturnType<typeof setTimeout>;
async function load() {
  try {
    if (props.mode === "quality") {
      const d = await api<Page<Issue> & { counts: Record<string, number> }>(
        "quality?limit=25&offset=" + offset.value,
      );
      issues.value = d;
      counts.value = d.counts;
    }
    if (props.mode === "datasets")
      datasets.value = await api<Page<Dataset>>(
        `datasets?q=${encodeURIComponent(q.value)}&offset=${offset.value}`,
      );
    if (props.mode === "researchers")
      researchers.value = await api<Researcher[]>("researchers");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function importOrcid() {
  busy.value = true;
  try {
    await api("sync", "POST", { source: "orcid", orcid: orcid.value });
    emit("notice", "Consulta do registro público adicionada à fila.");
    orcid.value = "";
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
onMounted(load);
watch(revision, load);
watch(offset, load);
watch(q, () => {
  offset.value = 0;
  clearTimeout(timer);
  timer = setTimeout(load, 300);
});
</script>
<template>
  <template v-if="mode === 'quality'"
    ><p class="scope-note">
      Sinalizações para revisão humana. Divergências preservam os valores de
      cada fonte e não provocam sobrescrita automática.
    </p>
    <div class="tag-row section-gap">
      <span v-for="(count, reason) in counts" :key="reason" class="badge"
        >{{ reason }} · {{ count }}</span
      >
    </div>
    <section class="panel">
      <div class="panel-heading">
        <h2>
          Registros para revisão <span class="count">{{ issues.total }}</span>
        </h2>
      </div>
      <article
        v-for="issue in issues.items"
        :key="issue.id"
        class="incident-item"
      >
        <div>
          <h3>{{ issue.title }}</h3>
          <div class="tag-row">
            <span
              v-for="reason in issue.reasons"
              :key="reason"
              class="badge partial"
              >{{ reason }}</span
            >
          </div>
          <details v-if="issue.crossref_title">
            <summary>Comparar títulos</summary>
            <p>OpenAlex: {{ issue.openalex_title }}</p>
            <p>Crossref: {{ issue.crossref_title }}</p>
          </details>
        </div>
      </article>
      <p v-if="!issues.items.length" class="empty-cell">
        Nenhuma sinalização nos dados importados.
      </p>
      <Pager
        :total="issues.total"
        :offset="offset"
        @change="offset = $event"
      /></section
  ></template>
  <template v-if="mode === 'datasets'"
    ><div class="scope-note">
      Catálogo público da UFRN. Exibimos metadados, formatos e links; os
      arquivos não são baixados nem têm seu conteúdo analisado nesta etapa.
    </div>
    <section class="panel">
      <div class="panel-heading">
        <h2>
          Conjuntos de dados <span class="count">{{ datasets.total }}</span>
        </h2>
        <input
          v-model="q"
          aria-label="Buscar conjunto de dados"
          placeholder="Buscar no catálogo local"
        />
      </div>
      <article
        v-for="item in datasets.items"
        :key="item.id"
        class="catalog-item"
      >
        <h3>
          <a :href="safeUrl(item.url)" target="_blank" rel="noopener noreferrer"
            >{{ item.title }} ↗</a
          >
        </h3>
        <small
          >Modificado na fonte: {{ item.modified || "Não informado" }} ·
          Coletado: {{ date(item.fetched_at) }}</small
        >
        <details>
          <summary>{{ item.resources.length }} recursos disponíveis</summary>
          <ul class="resource-list">
            <li v-for="resource in item.resources" :key="resource.id">
              <span class="badge">{{ resource.format || "Arquivo" }}</span
              ><a
                :href="safeUrl(resource.url)"
                target="_blank"
                rel="noopener noreferrer"
                >{{ resource.name || "Abrir recurso" }} ↗</a
              >
            </li>
          </ul>
        </details>
      </article>
      <p v-if="!datasets.items.length" class="empty-cell">
        Importe o catálogo UFRN em Integrações para explorar seus conjuntos.
      </p>
      <Pager
        :total="datasets.total"
        :offset="offset"
        @change="offset = $event"
      /></section
  ></template>
  <template v-if="mode === 'researchers'"
    ><div class="scope-note">
      Perfis públicos consultados por ORCID. Informações ausentes podem ser
      privadas ou não preenchidas; não indicam ausência de vínculo ou produção.
    </div>
    <form
      v-if="user.role !== 'viewer'"
      class="filter-row panel padded section-gap"
      @submit.prevent="importOrcid"
    >
      <label
        >Consultar pesquisador<input
          v-model="orcid"
          placeholder="0000-0000-0000-000X"
          pattern="[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]"
          required /></label
      ><button class="chip-button" :disabled="busy">
        {{ busy ? "Enfileirando…" : "Consultar ORCID" }}
      </button>
    </form>
    <section class="panel">
      <div class="panel-heading">
        <h2>
          Pesquisadores <span class="count">{{ researchers.length }}</span>
        </h2>
      </div>
      <article
        v-for="researcher in researchers"
        :key="researcher.orcid"
        class="catalog-item"
      >
        <h3>{{ researcher.name }}</h3>
        <a
          class="text-button"
          :href="'https://orcid.org/' + researcher.orcid"
          target="_blank"
          rel="noopener noreferrer"
          >{{ researcher.orcid }} ↗</a
        ><small>Coletado em {{ date(researcher.fetched_at) }}</small>
        <details>
          <summary>Registro público: vínculos e trabalhos informados</summary>
          <pre>{{ JSON.stringify(researcher.data, null, 2) }}</pre>
        </details>
      </article>
      <p v-if="!researchers.length" class="empty-cell">
        Consulte um ORCID ou abra o identificador de um autor na tela de
        Publicações.
      </p>
    </section></template
  >
</template>
