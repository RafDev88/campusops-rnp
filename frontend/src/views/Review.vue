<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { api, date, labels, revision, type Page, type User } from "../api";
import Pager from "../components/Pager.vue";
const props = defineProps<{ mode: string; user: User }>(),
  emit = defineEmits<{ error: [message: string]; notice: [message: string] }>(),
  route = useRoute();
type Review = {
  id: number;
  run_id: number;
  source: string;
  entity_id: string;
  reason: string;
  status: string;
  retry_run_id: number | null;
};
type Change = {
  id: number;
  run_id: number;
  source: string;
  entity_id: string;
  field: string;
  before: unknown;
  after: unknown;
  created_at: string;
};
const reviews = ref<Page<Review>>({ total: 0, items: [] }),
  changes = ref<Page<Change>>({ total: 0, items: [] }),
  source = ref(""),
  status = ref("pending"),
  entity = ref(String(route.query.entity_id || "")),
  offset = ref(0);
async function load() {
  try {
    if (props.mode === "reviews")
      reviews.value = await api(
        `record-reviews?source=${source.value}&status=${status.value}&offset=${offset.value}`,
      );
    else
      changes.value = await api(
        `data-changes?source=${source.value}&entity_id=${encodeURIComponent(entity.value)}&offset=${offset.value}`,
      );
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function act(id: number, action: string) {
  try {
    await api(`record-reviews/${id}/${action}`, "POST");
    await load();
    emit(
      "notice",
      action === "retry"
        ? "Registro adicionado ao reprocessamento."
        : "Registro marcado como ignorado.",
    );
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(revision, load);
watch([source, status], () => {
  offset.value = 0;
  load();
});
watch(offset, load);
watch(
  () => [props.mode, route.query.entity_id],
  () => {
    entity.value = String(route.query.entity_id || "");
    offset.value = 0;
    load();
  },
);
const fieldNames: Record<string, string> = {
  name: "Nome",
  country: "País",
  title: "Título",
  year: "Ano",
  doi: "DOI",
  is_oa: "Acesso aberto",
  citations: "Citações",
  topics: "Temas",
  authors: "Autores",
  affiliations: "Instituições",
  crossref: "Metadados Crossref",
  resources: "Recursos",
  modified: "Atualização na fonte",
};
</script>
<template>
  <div class="scope-note">
    {{
      mode === "reviews"
        ? "Registros rejeitados ficam separados para revisão. Reprocessar consulta somente o identificador selecionado; erros de contrato retomam a execução de origem com respostas refeitas."
        : "Alterações são registradas na mesma transação dos dados. Exibimos campo, valor anterior, valor novo e origem."
    }}
  </div>
  <section class="panel">
    <div class="panel-heading">
      <h2>
        {{ mode === "reviews" ? "Fila de revisão" : "Histórico de alterações" }}
      </h2>
      <form
        class="filter-row"
        @submit.prevent="
          offset = 0;
          load();
        "
      >
        <select v-model="source" aria-label="Fonte da revisão">
          <option value="">Todas as fontes</option>
          <option
            v-for="s in ['ror', 'openalex', 'crossref', 'orcid', 'ufrn']"
            :key="s"
          >
            {{ s }}
          </option></select
        ><select
          v-if="mode === 'reviews'"
          v-model="status"
          aria-label="Estado da revisão"
        >
          <option value="">Todos os estados</option>
          <option
            v-for="s in ['pending', 'retrying', 'resolved', 'ignored']"
            :key="s"
            :value="s"
          >
            {{ labels[s] || s }}
          </option></select
        ><template v-else
          ><input
            v-model="entity"
            aria-label="Identificador do registro"
            placeholder="Identificador do registro"
          /><button class="text-button">Filtrar</button></template
        >
      </form>
    </div>
    <template v-if="mode === 'reviews'"
      ><article
        v-for="item in reviews.items"
        :key="item.id"
        class="incident-item"
      >
        <div>
          <div class="tag-row">
            <span class="badge">{{ item.source.toUpperCase() }}</span
            ><span class="badge">{{ labels[item.status] || item.status }}</span>
          </div>
          <h3>{{ item.entity_id }}</h3>
          <p>{{ item.reason }}</p>
          <RouterLink
            class="text-button"
            :to="{
              name: 'runs',
              query: { id: String(item.retry_run_id || item.run_id) },
            }"
            >Ver execução #{{ item.retry_run_id || item.run_id }} →</RouterLink
          >
        </div>
        <div
          v-if="
            user.role !== 'viewer' &&
            ['pending', 'ignored'].includes(item.status)
          "
          class="action-row"
        >
          <button class="chip-button" @click="act(item.id, 'retry')">
            Reprocessar registro</button
          ><button
            v-if="item.status === 'pending'"
            class="text-button"
            @click="act(item.id, 'ignore')"
          >
            Ignorar
          </button>
        </div>
      </article>
      <p v-if="!reviews.items.length" class="empty-cell">
        Nenhum registro com estes filtros.
      </p>
      <Pager
        :total="reviews.total"
        :offset="offset"
        @change="offset = $event" /></template
    ><template v-else
      ><article
        v-for="change in changes.items"
        :key="change.id"
        class="change-card"
      >
        <div class="tag-row">
          <span class="badge">{{ change.source.toUpperCase() }}</span
          ><strong>{{ fieldNames[change.field] || change.field }}</strong
          ><small>{{ date(change.created_at) }}</small
          ><RouterLink
            class="text-button"
            :to="{ name: 'runs', query: { id: String(change.run_id) } }"
            >Execução #{{ change.run_id }}</RouterLink
          >
        </div>
        <p class="muted">{{ change.entity_id }}</p>
        <div class="two-columns">
          <div>
            <h4>Antes</h4>
            <pre>{{
              typeof change.before === "object"
                ? JSON.stringify(change.before, null, 2)
                : String(change.before ?? "Não informado")
            }}</pre>
          </div>
          <div>
            <h4>Depois</h4>
            <pre>{{
              typeof change.after === "object"
                ? JSON.stringify(change.after, null, 2)
                : String(change.after ?? "Não informado")
            }}</pre>
          </div>
        </div>
      </article>
      <p v-if="!changes.items.length" class="empty-cell">
        Nenhuma alteração registrada. O histórico começa nas próximas coletas.
      </p>
      <Pager :total="changes.total" :offset="offset" @change="offset = $event"
    /></template>
  </section>
</template>
