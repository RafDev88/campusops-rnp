<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from "vue";
import Button from "primevue/button";
import { useRoute, useRouter } from "vue-router";
import { value } from "../discovery";
import Pager from "../components/Pager.vue";
import SyncForm from "../components/SyncForm.vue";
import {
  api,
  date,
  revision,
  safeUrl,
  type Institution,
  type Page,
  type User,
} from "../api";
const Chart = defineAsyncComponent(() => import("../components/Chart.vue"));
const route = useRoute(),
  router = useRouter();
const props = defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Detail = {
  institution: Institution;
  profile: {
    watched: boolean;
    fetched_at: string;
    data: {
      coverage?: {
        complete: boolean;
        year_from: number;
        reported_total: number;
        imported: number;
      };
      ror?: {
        locations?: {
          geonames_details: { name: string; country_name: string };
        }[];
      };
    };
  } | null;
  metrics: {
    imported: number;
    open_access: number;
    citations: number;
    years: [number, number][];
    topics: [string, number][];
    collaborations: [string, number][];
  };
  scope: string;
};
const q = ref(value(route.query, "q")),
  watched = ref(value(route.query, "watched") === "true"),
  offset = ref(Number(value(route.query, "offset")) || 0),
  data = ref<Page<Institution>>({ total: 0, items: [] }),
  detail = ref<Detail | null>(null),
  selected = ref(value(route.query, "id")),
  collecting = ref(false),
  loading = ref(true);
const institutionFilters = [
  "country",
  "region",
  "city",
  "institution_type",
  "status",
];
const extra = ref<Record<string, string>>(
  Object.fromEntries(institutionFilters.map((k) => [k, value(route.query, k)])),
);
const options = ref<
  Record<string, { id: string; name: string; count: number }[]>
>({});
async function loadFacets() {
  try {
    options.value = await api("institution-facets");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
function setExtra(key: string, v: string) {
  router.push({
    query: { ...route.query, [key]: v || undefined, offset: undefined },
  });
}
let searchTimer: ReturnType<typeof setTimeout>,
  generation = 0;
let restoring = false;
async function load() {
  const current = ++generation;
  try {
    const result = await api<Page<Institution>>(
      `institutions?q=${encodeURIComponent(q.value)}&watched=${watched.value}&offset=${offset.value}&${new URLSearchParams(extra.value)}`,
    );
    if (current === generation) data.value = result;
    if (selected.value)
      detail.value = await api<Detail>(
        "institution-profile?id=" + encodeURIComponent(selected.value),
      );
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    loading.value = false;
  }
}
async function open(id: string) {
  await router.push({ query: { ...route.query, id } });
  selected.value = id;
  collecting.value = false;
  try {
    detail.value = await api<Detail>(
      "institution-profile?id=" + encodeURIComponent(id),
    );
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function toggle(item: Institution) {
  try {
    await api("watch", "POST", {
      institution_id: item.id,
      watched: !item.watched,
    });
    emit(
      "notice",
      item.watched
        ? "Instituição removida do acompanhamento."
        : "Instituição adicionada ao acompanhamento.",
    );
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
const yearChart = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 45, right: 20, top: 20, bottom: 30 },
  xAxis: {
    type: "category",
    data: detail.value?.metrics.years.map((x) => x[0]) || [],
  },
  yAxis: { type: "value", minInterval: 1 },
  series: [
    {
      type: "line",
      smooth: true,
      areaStyle: { color: "#e7f3ef" },
      itemStyle: { color: "#167c72" },
      data: detail.value?.metrics.years.map((x) => x[1]) || [],
    },
  ],
}));
const topicChart = computed(() => ({
  tooltip: {},
  grid: { left: 160, right: 25, top: 10, bottom: 25 },
  xAxis: { type: "value", minInterval: 1 },
  yAxis: {
    type: "category",
    inverse: true,
    axisLabel: { width: 145, overflow: "truncate" },
    data: detail.value?.metrics.topics.slice(0, 8).map((x) => x[0]) || [],
  },
  series: [
    {
      type: "bar",
      itemStyle: { color: "#167c72", borderRadius: [0, 4, 4, 0] },
      data: detail.value?.metrics.topics.slice(0, 8).map((x) => x[1]) || [],
    },
  ],
}));
const networkChart = computed(() => ({
  tooltip: {},
  series: [
    {
      type: "graph",
      layout: "force",
      roam: true,
      force: { repulsion: 240, edgeLength: 100 },
      label: { show: true, width: 95, overflow: "truncate", fontSize: 10 },
      data: [
        {
          id: "center",
          name: detail.value?.institution.name,
          symbolSize: 45,
          itemStyle: { color: "#167c72" },
        },
        ...(detail.value?.metrics.collaborations || []).map(
          ([name, count], i) => ({
            id: String(i),
            name,
            value: count,
            symbolSize: Math.min(35, 12 + count),
            itemStyle: { color: "#82b9ad" },
          }),
        ),
      ],
      links: (detail.value?.metrics.collaborations || []).map(
        ([_, count], i) => ({
          source: "center",
          target: String(i),
          value: count,
        }),
      ),
      lineStyle: { color: "#b8d4cf" },
    },
  ],
}));
watch(
  [q, watched],
  () => {
    if (restoring) return;
    restoring = true;
    offset.value = 0;
    restoring = false;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(
      () =>
        router.push({
          query: {
            ...route.query,
            q: q.value || undefined,
            watched: watched.value ? "true" : undefined,
            offset: undefined,
          },
        }),
      300,
    );
  },
  { flush: "sync" },
);
watch(
  offset,
  () => {
    if (!restoring)
      router.push({
        query: { ...route.query, offset: offset.value || undefined },
      });
  },
  { flush: "sync" },
);
watch(
  () => route.query,
  () => {
    restoring = true;
    extra.value = Object.fromEntries(
      institutionFilters.map((k) => [k, value(route.query, k)]),
    );
    q.value = value(route.query, "q");
    watched.value = value(route.query, "watched") === "true";
    offset.value = Number(value(route.query, "offset")) || 0;
    restoring = false;
    selected.value = value(route.query, "id");
    if (!selected.value) detail.value = null;
    load();
  },
);
watch(revision, load);
onMounted(() => {
  load();
  loadFacets();
});
onUnmounted(() => clearTimeout(searchTimer));
</script>
<template>
  <section v-if="detail" class="panel detail-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">PERFIL DA INSTITUIÇÃO</p>
        <h2>{{ detail.institution.name }}</h2>
        <p>
          {{ detail.institution.country }} ·
          {{
            detail.profile?.data.ror?.locations?.[0]?.geonames_details.name ||
            "Localização não informada"
          }}
        </p>
      </div>
      <button
        class="text-button"
        @click="
          detail = null;
          selected = '';
          router.push({ query: { ...route.query, id: undefined } });
        "
      >
        Fechar perfil
      </button>
    </div>
    <div class="detail-body">
      <div class="action-row">
        <RouterLink
          class="chip-button"
          :to="{
            name: 'publications',
            query: { institution_id: detail.institution.id },
          }"
          >Pesquisar publicações desta instituição →</RouterLink
        >
        <a
          class="text-button"
          :href="safeUrl(detail.institution.id)"
          target="_blank"
          rel="noopener noreferrer"
          >Registro ROR ↗</a
        ><Button
          v-if="user.role !== 'viewer'"
          size="small"
          @click="collecting = !collecting"
          >Coletar publicações</Button
        ><small
          >Última coleta cadastral:
          {{ date(detail.profile?.fetched_at || null) }}</small
        >
      </div>
      <SyncForm
        v-if="collecting"
        source="openalex"
        :institution-id="detail.institution.id"
        @done="
          collecting = false;
          emit('notice', 'Coleta de publicações adicionada à fila.');
        "
        @error="emit('error', $event)"
      />
      <p class="scope-note">
        {{ detail.scope }}
        <span v-if="detail.profile?.data.coverage"
          >Período: desde {{ detail.profile.data.coverage.year_from }}.
          Cobertura:
          {{
            detail.profile.data.coverage.complete
              ? "completa no período consultado"
              : "parcial"
          }}. Fonte reporta
          {{ detail.profile.data.coverage.reported_total }} trabalhos.</span
        >
      </p>
      <section class="stats compact-stats">
        <article>
          <div>Publicações importadas</div>
          <strong>{{ detail.metrics.imported }}</strong>
        </article>
        <article>
          <div>Acesso aberto</div>
          <strong>{{
            detail.metrics.imported
              ? Math.round(
                  (detail.metrics.open_access / detail.metrics.imported) * 100,
                ) + "%"
              : "—"
          }}</strong>
        </article>
        <article>
          <div>Citações na fonte</div>
          <strong>{{ detail.metrics.citations }}</strong>
        </article>
      </section>
      <div v-if="detail.metrics.imported" class="two-columns">
        <article>
          <h3>Publicações por ano</h3>
          <Chart
            :option="yearChart"
            @select="
              router.push({
                name: 'publications',
                query: { institution_id: selected, year: $event.name },
              })
            "
          />
          <div class="tag-row">
            <RouterLink
              v-for="[year, count] in detail.metrics.years"
              :key="year"
              class="chip-button"
              :to="{
                name: 'publications',
                query: { institution_id: selected, year: String(year) },
              }"
              >{{ year }} · {{ count }}</RouterLink
            >
          </div>
        </article>
        <article>
          <h3>Temas mais presentes</h3>
          <Chart
            :option="topicChart"
            @select="
              router.push({
                name: 'publications',
                query: { institution_id: selected, topic: $event.name },
              })
            "
          />
          <div class="tag-row">
            <RouterLink
              v-for="[topic] in detail.metrics.topics.slice(0, 5)"
              :key="topic"
              class="text-button"
              :to="{
                name: 'publications',
                query: { institution_id: selected, topic },
              }"
              >{{ topic }} →</RouterLink
            >
          </div>
        </article>
        <article class="full-width">
          <h3>Rede de colaboração</h3>
          <p class="muted">
            Instituições que aparecem nas mesmas publicações importadas.
          </p>
          <Chart
            :option="networkChart"
            @select="
              $event.dataType === 'node' &&
              router.push({
                name: 'search',
                query: { q: $event.name, kind: 'institution' },
              })
            "
          />
          <details>
            <summary>Ver colaborações em texto</summary>
            <ul>
              <li
                v-for="[name, count] in detail.metrics.collaborations"
                :key="name"
              >
                {{ name }} — {{ count }} trabalhos
              </li>
            </ul>
          </details>
        </article>
      </div>
      <p v-else class="empty-cell">
        Colete publicações desta instituição para explorar os indicadores.
      </p>
    </div>
  </section>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <h2>
          Catálogo institucional <span class="count">{{ data.total }}</span>
        </h2>
        <p>
          Marque instituições para incluir nas coletas agendadas do OpenAlex.
        </p>
      </div>
      <form class="filter-row" @submit.prevent="load">
        <input
          v-model="q"
          aria-label="Buscar instituição"
          placeholder="Buscar instituição"
        /><label class="checkbox-label"
          ><input v-model="watched" type="checkbox" />Acompanhadas</label
        >
      </form>
    </div>
    <form class="institution-filters" @submit.prevent="load">
      <label
        v-for="f in [
          { key: 'country', option: 'country', label: 'País' },
          { key: 'region', option: 'region', label: 'Estado ou região' },
          { key: 'city', option: 'city', label: 'Cidade' },
          {
            key: 'institution_type',
            option: 'type',
            label: 'Tipo de instituição',
          },
          { key: 'status', option: 'status', label: 'Situação no ROR' },
        ]"
        :key="f.key"
        >{{ f.label
        }}<select
          :value="extra[f.key]"
          :aria-label="f.label"
          @change="setExtra(f.key, ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Todos</option>
          <option
            v-for="item in options[f.option] || []"
            :key="item.id"
            :value="item.id"
          >
            {{ item.name }} ({{ item.count }})
          </option>
        </select></label
      ><button
        v-if="institutionFilters.some((k) => extra[k])"
        class="text-button"
        type="button"
        @click="
          router.push({
            name: 'institutions',
            query: { q: q || undefined, watched: watched ? 'true' : undefined },
          })
        "
      >
        Limpar localização e tipo
      </button>
    </form>
    <p v-if="loading" class="empty-cell" role="status">
      Carregando instituições…
    </p>
    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>INSTITUIÇÃO</th>
            <th>PAÍS</th>
            <th>ACOMPANHAMENTO</th>
            <th>PERFIL</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in data.items" :key="item.id">
            <td>{{ item.name }}</td>
            <td>{{ item.country }}</td>
            <td>
              <button
                v-if="user.role !== 'viewer'"
                class="chip-button"
                :class="{ selected: item.watched }"
                :aria-pressed="item.watched"
                @click="toggle(item)"
              >
                {{ item.watched ? "✓ Acompanhando" : "+ Acompanhar" }}</button
              ><span v-else>{{
                item.watched ? "Acompanhada" : "Não acompanhada"
              }}</span>
            </td>
            <td>
              <button class="text-button" @click="open(item.id)">
                Explorar →
              </button>
            </td>
          </tr>
          <tr v-if="!data.items.length">
            <td colspan="4" class="empty-cell">
              Nenhuma instituição encontrada. Ajuste a busca ou importe o ROR em
              Integrações.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <Pager :total="data.total" :offset="offset" @change="offset = $event" />
  </section>
</template>
