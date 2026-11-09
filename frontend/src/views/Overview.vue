<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { BookOpen, Building2, Database, ArrowRight } from "@lucide/vue";
import GlobalSearch from "../components/GlobalSearch.vue";
import FirstSteps from "../components/FirstSteps.vue";
import CatalogStatus from "../components/CatalogStatus.vue";
import { api, date, revision, type Run, type User } from "../api";
defineProps<{ user: User }>();
const kind = ref("");
const emit = defineEmits<{ error: [message: string] }>();
const counts = ref<Record<string, number>>({}),
  runs = ref<Run[]>([]),
  loading = ref(true);
async function load() {
  try {
    const d = await api<{ counts: Record<string, number>; executions: Run[] }>(
      "dashboard",
    );
    counts.value = d.counts;
    runs.value = d.executions;
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(revision, load);
const services = [
  {
    route: "institutions",
    title: "Instituições",
    description: "Conheça universidades e explore suas áreas de pesquisa.",
    action: "Consultar instituições",
    icon: Building2,
  },
  {
    route: "publications",
    title: "Publicações científicas",
    description: "Encontre trabalhos por assunto, instituição ou autor.",
    action: "Consultar publicações",
    icon: BookOpen,
  },
  {
    route: "datasets",
    title: "Dados abertos",
    description: "Consulte conjuntos de dados e acesse suas fontes.",
    action: "Consultar dados abertos",
    icon: Database,
  },
];
</script>
<template>
  <CatalogStatus />
  <div class="welcome-layout">
    <section class="research-intro" aria-labelledby="research-title">
      <p class="portal-kicker">CONSULTA ACADÊMICA</p>
      <h1 id="research-title">
        Encontre informações<br class="desktop-break" />
        para sua pesquisa.
      </h1>
      <p class="research-lead">
        Comece com um assunto ou o nome de uma universidade. Você pode refinar a
        pesquisa depois.
      </p>
      <fieldset class="search-kind-picker">
        <legend>O que você quer encontrar?</legend>
        <label
          v-for="option in [
            { id: '', label: 'Tudo' },
            { id: 'publication', label: 'Trabalhos e artigos' },
            { id: 'institution', label: 'Universidades' },
            { id: 'researcher', label: 'Autores' },
            { id: 'dataset', label: 'Dados abertos' },
          ]"
          :key="option.id"
          :class="{ selected: kind === option.id }"
          ><input
            v-model="kind"
            type="radio"
            name="search-kind"
            :value="option.id"
          />{{ option.label }}</label
        >
      </fieldset>
      <label class="search-visible-label" for="catalog-search"
        >O que você procura?</label
      ><GlobalSearch :kind="kind" @error="emit('error', $event)" />
      <div class="search-examples">
        <span>Experimente:</span
        ><RouterLink :to="{ name: 'search', query: { q: 'educação' } }"
          >educação</RouterLink
        ><RouterLink :to="{ name: 'search', query: { q: 'redes' } }"
          >redes</RouterLink
        ><RouterLink :to="{ name: 'search', query: { q: 'UFRN' } }"
          >UFRN</RouterLink
        >
      </div>
      <p class="research-scope">
        A busca consulta os dados já disponíveis neste portal. A fonte de cada
        informação aparece nos resultados.
      </p>
    </section>
    <FirstSteps :user-id="user.id" />
  </div>
  <section class="portal-services" aria-labelledby="services-title">
    <div class="section-title">
      <h2 id="services-title">Explore por tipo de informação</h2>
      <p>Escolha por onde começar.</p>
    </div>
    <div class="service-grid">
      <RouterLink
        v-for="service in services"
        :key="service.route"
        :to="{ name: service.route }"
        class="service-link"
        ><component :is="service.icon" :size="26" aria-hidden="true" />
        <h3>{{ service.title }}</h3>
        <p>{{ service.description }}</p>
        <span>{{ service.action }} <ArrowRight :size="17" /></span
      ></RouterLink>
    </div>
  </section>
  <section class="catalog-summary" aria-labelledby="catalog-title">
    <div>
      <h2 id="catalog-title">Informações disponíveis</h2>
      <p>Quantidade de registros no catálogo local.</p>
    </div>
    <p v-if="loading" role="status">Carregando informações…</p>
    <dl v-else>
      <div
        v-for="item in [
          { key: 'institutions', label: 'Instituições' },
          { key: 'publications', label: 'Publicações' },
          { key: 'datasets', label: 'Conjuntos de dados' },
        ]"
        :key="item.key"
      >
        <dt>{{ item.label }}</dt>
        <dd>{{ (counts[item.key] || 0).toLocaleString("pt-BR") }}</dd>
      </div>
    </dl>
  </section>
  <section class="research-help help-band" aria-labelledby="help-title">
    <div>
      <h2 id="help-title">Precisa de uma orientação?</h2>
      <p>Entenda os resultados, os filtros e de onde vêm as informações.</p>
      <RouterLink to="/help" class="text-button"
        >Ver orientações de pesquisa →</RouterLink
      >
    </div>
    <RouterLink to="/my-research" class="chip-button"
      >Continuar minhas pesquisas →</RouterLink
    >
  </section>
  <div class="catalog-note">
    <strong>Sobre a atualização dos dados</strong>
    <p>
      As fontes são atualizadas pelas rotinas de coleta. O catálogo pode
      representar apenas parte das informações de cada instituição.
    </p>
    <RouterLink
      v-if="runs.length"
      :to="{ name: 'runs', query: { id: String(runs[0].id) } }"
      >Consultar última coleta · {{ date(runs[0].created_at) }} →</RouterLink
    ><RouterLink v-else to="/help">Entenda de onde vêm os dados →</RouterLink>
  </div>
</template>
