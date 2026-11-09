<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import Pager from "../components/Pager.vue";
import PublicationFilters from "../components/PublicationFilters.vue";
import PublicationResults from "../components/PublicationResults.vue";
import CatalogStatus from "../components/CatalogStatus.vue";
import {
  advancedFilterKeys,
  filterLabels,
  filtersFromQuery,
  type PublicationFacets,
} from "../researchFilters";
import PublicationDetail from "../components/PublicationDetail.vue";
import {
  api,
  date,
  refresh,
  revision,
  type Page,
  type Publication,
  type User,
} from "../api";
import {
  params,
  publicationKeys,
  value,
  languages,
  workTypes,
} from "../discovery";
const props = defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
const route = useRoute(),
  router = useRouter(),
  filters = reactive<Record<string, string>>({}),
  loading = ref(true),
  error = ref("");
const data = ref<Page<Publication> & { features?: { approximate: boolean } }>({
    total: 0,
    items: [],
  }),
  selected = ref<Publication | null>(null);
const facets = ref<PublicationFacets>({
  topics: [],
  institutions: [],
  languages: [],
  work_types: [],
});
const saveName = ref(""),
  saveAlerts = ref(false),
  saving = ref(false),
  showSave = ref(false);
const advanced = ref(advancedFilterKeys.some((k) => value(route.query, k)));
watch(
  () => route.query,
  () => {
    if (advancedFilterKeys.some((k) => value(route.query, k)))
      advanced.value = true;
  },
);
const offset = computed(() =>
  Math.max(0, Number(value(route.query, "offset")) || 0),
);
const query = computed(() => params(route.query, publicationKeys));
const descriptions = filterLabels;
const chips = computed(() =>
  publicationKeys
    .filter(
      (k) =>
        k !== "sort" &&
        value(route.query, k) &&
        !(k === "favorites" && value(route.query, k) === "false"),
    )
    .map((key) => ({
      key,
      label: descriptions[key],
      value:
        key === "language"
          ? languages[value(route.query, key)] || value(route.query, key)
          : key === "work_type"
            ? workTypes[value(route.query, key)] || value(route.query, key)
            : key === "mode"
              ? {
                  all: "Todas as palavras",
                  any: "Qualquer palavra",
                  phrase: "Frase na mesma ordem",
                  exact: "Título completo exato",
                }[value(route.query, key)] || value(route.query, key)
              : key === "search_in"
                ? { all: "Todos", title: "Título", abstract: "Resumo" }[
                    value(route.query, key)
                  ] || value(route.query, key)
                : [
                      "has_doi",
                      "has_abstract",
                      "retracted",
                      "approximate",
                    ].includes(key)
                  ? value(route.query, key) === "true"
                    ? "Sim"
                    : "Não"
                  : key === "institution_id"
                    ? facets.value.institutions.find(
                        (i) => i.id === value(route.query, key),
                      )?.name || value(route.query, key)
                    : key === "topic"
                      ? facets.value.topics.find(
                          (t) => t.id === value(route.query, key),
                        )?.name || value(route.query, key)
                      : key === "oa"
                        ? value(route.query, key) === "true"
                          ? "Aberto"
                          : "Não identificado"
                        : key === "favorites"
                          ? "Somente meus favoritos"
                          : key === "author_id"
                            ? "Autor selecionado"
                            : value(route.query, key),
    })),
);
let controller: AbortController | undefined,
  detailController: AbortController | undefined,
  timer: ReturnType<typeof setTimeout>,
  generation = 0;
function syncForm() {
  for (const key of publicationKeys) filters[key] = value(route.query, key);
}
function set(key: string, v: string) {
  clearTimeout(timer);
  filters[key] = v;
  router.push({
    name: "publications",
    query: {
      ...route.query,
      [key]: v || undefined,
      offset: undefined,
      publication: undefined,
    },
  });
}
function editField(key: string, v: string) {
  filters[key] = v;
  typing(key, v);
}
function typing(key: string, v: string) {
  clearTimeout(timer);
  timer = setTimeout(() => set(key, v), 350);
}
async function load() {
  controller?.abort();
  controller = new AbortController();
  const current = ++generation;
  loading.value = true;
  error.value = "";
  try {
    const [d, f] = await Promise.all([
      api<Page<Publication>>(
        "publications?" + query.value + "&offset=" + offset.value,
        "GET",
        undefined,
        controller.signal,
      ),
      api<typeof facets.value>(
        "publication-facets?" + query.value,
        "GET",
        undefined,
        controller.signal,
      ),
    ]);
    if (current === generation) {
      data.value = d;
      facets.value = f;
    }
  } catch (e) {
    if ((e as Error).name !== "AbortError" && current === generation) {
      error.value = (e as Error).message;
      data.value = { total: 0, items: [] };
    }
  } finally {
    if (current === generation) loading.value = false;
  }
}
async function loadDetail() {
  detailController?.abort();
  detailController = new AbortController();
  const id = value(route.query, "publication");
  if (!id) {
    selected.value = null;
    return;
  }
  try {
    selected.value = await api<Publication>(
      "publication?id=" + encodeURIComponent(id),
      "GET",
      undefined,
      detailController.signal,
    );
  } catch (e) {
    if ((e as Error).name !== "AbortError") emit("error", (e as Error).message);
  }
}
function open(item: Publication) {
  router.push({ query: { ...route.query, publication: item.id } });
}
function close() {
  router.push({ query: { ...route.query, publication: undefined } });
}
async function favorite(item: Publication) {
  try {
    await api("favorites", "POST", {
      kind: "publication",
      entity_id: item.id,
      enabled: !item.favorite,
    });
    item.favorite = !item.favorite;
    refresh();
    emit(
      "notice",
      item.favorite
        ? "Guardado nos favoritos. Você encontra este trabalho em Minhas pesquisas."
        : "Trabalho removido dos favoritos.",
    );
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function save() {
  saving.value = true;
  try {
    const parsed = filtersFromQuery(route.query);
    await api("saved-searches", "POST", {
      name: saveName.value,
      filters: parsed,
      alerts_enabled: saveAlerts.value,
    });
    showSave.value = false;
    saveName.value = "";
    emit(
      "notice",
      "Pesquisa salva. Ela está disponível em Pesquisar → Pesquisas salvas.",
    );
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    saving.value = false;
  }
}
async function share() {
  try {
    await navigator.clipboard.writeText(location.href);
    emit(
      "notice",
      "Link da pesquisa copiado. Quem abrir precisará de acesso ao portal.",
    );
  } catch {
    emit(
      "notice",
      "Copie o endereço da barra do navegador para compartilhar esta pesquisa.",
    );
  }
}
watch(
  () => route.query,
  () => {
    syncForm();
    load();
    loadDetail();
  },
);
watch(revision, () => {
  load();
  loadDetail();
});
onMounted(() => {
  syncForm();
  load();
  loadDetail();
});
onUnmounted(() => {
  clearTimeout(timer);
  controller?.abort();
  detailController?.abort();
});
</script>
<template>
  <PublicationDetail
    v-if="selected"
    :item="selected"
    :user="user"
    @close="close"
    @error="emit('error', $event)"
    @notice="emit('notice', $event)"
  />
  <section class="panel">
    <div class="panel-heading">
      <div>
        <h2>
          Produção científica <span class="count">{{ data.total }}</span>
        </h2>
        <p>Digite um assunto e use os filtros para refinar sua pesquisa.</p>
      </div>
      <div class="action-row">
        <button class="text-button" @click="showSave = !showSave">
          Salvar pesquisa</button
        ><button class="text-button" @click="share">Copiar link</button
        ><a
          class="text-button"
          :href="'/api/exports/publications.csv?' + query"
          download
          >Baixar planilha (CSV) ↓</a
        >
      </div>
    </div>
    <CatalogStatus />
    <PublicationFilters
      :values="filters"
      :facets="facets"
      :advanced="advanced"
      :approximate-supported="data.features?.approximate ?? false"
      @change="set"
      @type="editField"
      @submit="set('q', filters.q)"
      @toggle="advanced = !advanced"
    />
    <div class="active-filters">
      <button
        class="chip-button"
        :aria-pressed="filters.favorites === 'true'"
        @click="set('favorites', filters.favorites === 'true' ? '' : 'true')"
      >
        ★ Meus favoritos</button
      ><button
        v-for="chip in chips"
        :key="chip.key"
        class="filter-chip"
        @click="set(chip.key, '')"
        :aria-label="'Remover filtro ' + chip.label"
      >
        {{ chip.label }}: {{ chip.value }} ×</button
      ><button
        v-if="chips.length"
        class="text-button"
        @click="router.push({ name: 'publications' })"
      >
        Limpar todos
      </button>
    </div>
    <form v-if="showSave" class="save-search-form" @submit.prevent="save">
      <label
        >Nome da pesquisa<input
          v-model="saveName"
          required
          minlength="2"
          maxlength="100"
          placeholder="Ex.: Redes na UFRN" /></label
      ><label class="checkbox-label"
        ><input v-model="saveAlerts" type="checkbox" />Avisar sobre novos
        resultados após as próximas coletas</label
      ><button class="primary-action" :disabled="saving">
        {{ saving ? "Salvando…" : "Salvar combinação de filtros" }}
      </button>
    </form>
    <p v-if="error" class="inline-error" role="alert">
      {{ error }} Ajuste os filtros para continuar.
    </p>
    <p v-if="loading" class="loading-strip" role="status">
      Pesquisando no catálogo…
    </p>
    <PublicationResults
      :items="data.items"
      :loading="loading"
      @open="open"
      @favorite="favorite"
      @topic="set('topic', $event)"
    />
    <div
      v-if="!loading && !error && !data.items.length"
      class="empty search-empty"
    >
      <strong>Nenhuma publicação corresponde a esta combinação</strong>
      <p v-if="chips.length">
        Remova um filtro ou amplie o período. Os dados pesquisados são os já
        importados.
      </p>
      <ul v-if="chips.length">
        <li v-if="filters.year || filters.year_from || filters.year_to">
          Amplie o período para incluir publicações de outros anos.
        </li>
        <li v-if="filters.favorites === 'true'">
          A opção Meus favoritos mostra apenas trabalhos que você guardou.
        </li>
        <li v-if="filters.q">
          Experimente uma palavra principal do assunto, sem combinar tantos
          termos.
        </li>
      </ul>
      <p v-else>
        Acompanhe uma instituição e colete suas publicações em Integrações.
      </p>
      <button
        v-if="chips.length"
        class="text-button"
        @click="router.push({ name: 'publications' })"
      >
        Remover todos os filtros</button
      ><RouterLink v-else class="text-button" :to="{ name: 'sources' }"
        >Ver fontes e cobertura →</RouterLink
      >
    </div>
    <Pager
      :total="data.total"
      :offset="offset"
      @change="
        router.push({ query: { ...route.query, offset: $event || undefined } })
      "
    />
    <p class="scope-caption">
      Resultados limitados à cobertura das coletas realizadas. Exportação
      respeita os filtros e a ordenação, até 10 mil registros.
    </p>
  </section>
</template>
