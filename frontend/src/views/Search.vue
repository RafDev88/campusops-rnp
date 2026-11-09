<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import Pager from "../components/Pager.vue";
import { api, date, refresh, revision, safeUrl } from "../api";
import { destination, kinds, value, type SearchResult } from "../discovery";
import { savedSearchDestination } from "../researchFilters";
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
const route = useRoute(),
  router = useRouter(),
  loading = ref(true),
  q = ref(value(route.query, "q"));
const data = ref<{
  total: number;
  counts: Record<string, number>;
  items: SearchResult[];
  scope: string;
  approximate_supported?: boolean;
}>({ total: 0, counts: {}, items: [], scope: "" });
type Dataset = {
  title: string;
  url: string;
  modified: string;
  resources: { id: string; name: string; format: string; url: string }[];
};
const dataset = ref<Dataset | null>(null),
  offset = computed(() =>
    Math.max(0, Number(value(route.query, "offset")) || 0),
  );
const saved = ref<
  {
    id: number;
    name: string;
    filters: Record<string, string | number | boolean | null>;
    alerts_enabled: boolean;
  }[]
>([]);
const alerts = ref<
  {
    id: number;
    title: string;
    publication_id: string;
    search_name: string;
    read: boolean;
  }[]
>([]);
let controller: AbortController | undefined;
function set(key: string, v: string) {
  router.push({
    name: "search",
    query: {
      ...route.query,
      [key]: v || undefined,
      offset: undefined,
      dataset: undefined,
    },
  });
}
async function load() {
  controller?.abort();
  controller = new AbortController();
  loading.value = true;
  try {
    const p = new URLSearchParams({
      q: value(route.query, "q"),
      kind: value(route.query, "kind"),
      favorites: value(route.query, "favorites") || "false",
      offset: String(offset.value),
      mode: value(route.query, "mode") || "all",
      approximate: value(route.query, "approximate") || "false",
    });
    data.value = await api("search?" + p, "GET", undefined, controller.signal);
    [saved.value, alerts.value] = await Promise.all([
      api<typeof saved.value>("saved-searches"),
      api<typeof alerts.value>("search-alerts"),
    ]);
    dataset.value = value(route.query, "dataset")
      ? await api<Dataset>(
          "dataset?id=" + encodeURIComponent(value(route.query, "dataset")),
        )
      : null;
  } catch (e) {
    if ((e as Error).name !== "AbortError") emit("error", (e as Error).message);
  } finally {
    loading.value = false;
  }
}
async function favorite(item: SearchResult) {
  try {
    await api("favorites", "POST", {
      kind: item.kind,
      entity_id: item.id,
      enabled: !item.favorite,
    });
    item.favorite = !item.favorite;
    refresh();
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function remove(id: number) {
  try {
    await api("saved-searches/" + id, "DELETE");
    await load();
    emit("notice", "Pesquisa removida.");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
function openSaved(filters: Record<string, string | number | boolean | null>) {
  router.push(savedSearchDestination(filters));
}
async function openAlert(item: (typeof alerts.value)[number]) {
  try {
    await api(`search-alerts/${item.id}/read`, "POST");
    router.push({
      name: "publications",
      query: { publication: item.publication_id },
    });
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(
  () => route.query,
  () => {
    q.value = value(route.query, "q");
    load();
  },
);
watch(revision, load);
onUnmounted(() => controller?.abort());
</script>
<template>
  <section class="panel discovery-hero">
    <p class="eyebrow">BUSCA NO CATÁLOGO</p>
    <h2>O que você procura?</h2>
    <p>Pesquise por assunto, universidade ou autor nos dados já importados.</p>
    <form class="filter-row" @submit.prevent="set('q', q)">
      <input
        v-model="q"
        aria-label="Termos da pesquisa global"
        placeholder="Ex.: UFRN, redes, nome do autor ou DOI"
        maxlength="150"
      /><button class="primary-action">Buscar informações</button>
    </form>
    <details class="search-advanced">
      <summary>Mais opções para combinar as palavras</summary>
      <div class="search-options">
        <label
          >Combinar palavras<select
            :value="value(route.query, 'mode') || 'all'"
            aria-label="Combinar palavras da pesquisa"
            @change="set('mode', ($event.target as HTMLSelectElement).value)"
          >
            <option value="all">Todas as palavras</option>
            <option value="phrase">Frase na mesma ordem</option>
            <option value="any">Qualquer palavra</option>
            <option value="exact">Título completo exato</option>
          </select></label
        ><label v-if="data.approximate_supported" class="checkbox-label"
          ><input
            type="checkbox"
            :checked="value(route.query, 'approximate') === 'true'"
            @change="
              set(
                'approximate',
                ($event.target as HTMLInputElement).checked ? 'true' : '',
              )
            "
          />Incluir títulos parecidos</label
        >
      </div>
      <p class="search-precision-note">
        Palavras completas por padrão. Cole um DOI, ORCID ou endereço
        ROR/OpenAlex para localizar o identificador exato.
      </p>
    </details>
    <div class="filter-tabs">
      <button
        :class="{ selected: !value(route.query, 'kind') }"
        @click="set('kind', '')"
      >
        Todos</button
      ><button
        v-for="(label, key) in kinds"
        :key="key"
        :class="{ selected: value(route.query, 'kind') === key }"
        @click="set('kind', key)"
      >
        {{ label }} <span>{{ data.counts[key] || 0 }}</span></button
      ><button
        :class="{ selected: value(route.query, 'favorites') === 'true' }"
        @click="
          set(
            'favorites',
            value(route.query, 'favorites') === 'true' ? '' : 'true',
          )
        "
      >
        ★ Meus favoritos
      </button>
    </div>
  </section>
  <section v-if="dataset" class="panel detail-panel">
    <div class="panel-heading">
      <h2>{{ dataset.title }}</h2>
      <button class="text-button" @click="set('dataset', '')">
        Fechar conjunto
      </button>
    </div>
    <div class="detail-body">
      <a
        :href="safeUrl(dataset.url)"
        target="_blank"
        rel="noopener noreferrer"
        class="text-button"
        >Abrir no portal de origem ↗</a
      >
      <p class="muted">Atualização na fonte: {{ dataset.modified }}</p>
      <ul class="resource-list">
        <li v-for="r in dataset.resources" :key="r.id">
          <span class="badge">{{ r.format || "Arquivo" }}</span
          ><a :href="safeUrl(r.url)" target="_blank" rel="noopener noreferrer"
            >{{ r.name || "Recurso" }} ↗</a
          >
        </li>
      </ul>
    </div>
  </section>
  <div class="discovery-layout">
    <section class="panel">
      <div class="panel-heading">
        <h2>
          {{ data.total }} resultados
          {{
            value(route.query, "q")
              ? "para “" + value(route.query, "q") + "”"
              : ""
          }}
        </h2>
        <span v-if="loading" role="status" class="muted">Atualizando…</span>
      </div>
      <article
        v-for="item in data.items"
        :key="item.kind + item.id"
        class="search-result"
      >
        <div>
          <span class="badge">{{ kinds[item.kind] }}</span>
          <h3>
            <RouterLink :to="destination(item)">{{ item.title }}</RouterLink>
          </h3>
          <p>{{ item.subtitle }}</p>
          <small
            >{{ item.source }} · Coletado em
            {{ date(item.collected_at) }}</small
          >
        </div>
        <button
          class="favorite-button"
          :aria-label="
            (item.favorite ? 'Remover dos favoritos: ' : 'Favoritar: ') +
            item.title
          "
          :aria-pressed="item.favorite"
          @click="favorite(item)"
        >
          {{ item.favorite ? "★" : "☆" }}
        </button>
      </article>
      <div v-if="!loading && !data.items.length" class="empty">
        <strong>Nenhum resultado com estes critérios</strong>
        <p>Tente um termo mais curto ou remova a seleção de tipo/favoritos.</p>
        <button class="text-button" @click="router.push({ name: 'search' })">
          Limpar pesquisa e explorar o catálogo
        </button>
      </div>
      <Pager
        :total="data.total"
        :offset="offset"
        :size="20"
        @change="
          router.push({
            query: { ...route.query, offset: $event || undefined },
          })
        "
      />
      <p class="scope-caption">{{ data.scope }}</p>
    </section>
    <div class="research-sidebar" role="complementary">
      <section class="panel">
        <div class="panel-heading"><h2>Pesquisas salvas</h2></div>
        <div v-for="s in saved" :key="s.id" class="saved-item">
          <button class="text-button" @click="openSaved(s.filters)">
            {{ s.name }}</button
          ><small>{{
            s.alerts_enabled ? "Novidades ativadas" : "Sem avisos de novidades"
          }}</small
          ><button
            class="text-button"
            @click="remove(s.id)"
            :aria-label="'Excluir pesquisa ' + s.name"
          >
            Excluir
          </button>
        </div>
        <p v-if="!saved.length" class="empty-cell">
          Salve uma combinação de filtros em Publicações para retomá-la aqui.
        </p>
      </section>
      <section class="panel section-gap">
        <div class="panel-heading"><h2>Novidades para você</h2></div>
        <div v-for="a in alerts" :key="a.id" class="saved-item">
          <span class="badge">{{ a.read ? "Lido" : "Novo" }}</span
          ><button class="text-button" @click="openAlert(a)">
            {{ a.title }}</button
          ><small>{{ a.search_name }}</small>
        </div>
        <p v-if="!alerts.length" class="empty-cell">
          Ative avisos ao salvar uma pesquisa. Novos resultados aparecem após as
          próximas coletas.
        </p>
      </section>
    </div>
  </div>
</template>
