<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import RunProgress from "../components/RunProgress.vue";
import AutomationOverview from "../components/AutomationOverview.vue";
import Pager from "../components/Pager.vue";
import {
  api,
  date,
  labels,
  revision,
  type Page,
  type Run,
  type User,
} from "../api";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
const route = useRoute();
const inspected = ref(Number(route.query.id) || 0);
watch(
  () => route.query.id,
  (id) => {
    inspected.value = Number(id) || 0;
  },
);
const data = ref<Page<Run>>({ total: 0, items: [] }),
  source = ref(""),
  status = ref(""),
  offset = ref(0),
  selected = ref<Run | null>(null),
  legacy = ref<object[] | null>(null);
async function load() {
  try {
    data.value = await api<Page<Run>>(
      `runs?source=${source.value}&status=${status.value}&offset=${offset.value}`,
    );
    if (selected.value)
      selected.value =
        data.value.items.find((r) => r.id === selected.value?.id) ||
        selected.value;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function retry(id: number) {
  try {
    await api(`runs/${id}/retry`, "POST");
    emit(
      "notice",
      "Nova execução adicionada à fila, preservando o histórico anterior.",
    );
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function showLegacy() {
  try {
    legacy.value = await api<object[]>("legacy-executions");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
watch([source, status], () => {
  offset.value = 0;
  load();
});
watch(offset, load);
watch(revision, load);
onMounted(load);
</script>
<template>
  <AutomationOverview />
  <RunProgress
    v-if="inspected"
    :identifier="inspected"
    :user="user"
    @close="inspected = 0"
    @error="emit('error', $event)"
    @notice="emit('notice', $event)"
  />
  <section class="panel">
    <div class="panel-heading">
      <div>
        <h2>
          Histórico operacional <span class="count">{{ data.total }}</span>
        </h2>
        <p>Processamento assíncrono com reprocessamento por fonte.</p>
      </div>
      <form class="filter-row" @submit.prevent="load">
        <select v-model="source" aria-label="Filtrar fonte">
          <option value="">Todas as fontes</option>
          <option
            v-for="s in ['ror', 'openalex', 'crossref', 'orcid', 'ufrn']"
            :key="s"
          >
            {{ s }}
          </option></select
        ><select v-model="status" aria-label="Filtrar estado">
          <option value="">Todos os estados</option>
          <option
            v-for="s in [
              'queued',
              'running',
              'paused',
              'retry_wait',
              'cancelled',
              'success',
              'partial',
              'failed',
            ]"
            :key="s"
            :value="s"
          >
            {{ labels[s] }}
          </option>
        </select>
      </form>
    </div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>EXECUÇÃO</th>
            <th>ESTADO</th>
            <th>REGISTROS</th>
            <th>DURAÇÃO</th>
            <th>CRIADA EM</th>
            <th>AÇÕES</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="run in data.items" :key="run.id">
            <td>#{{ run.id }} · {{ run.source.toUpperCase() }}</td>
            <td>
              <span class="badge" :class="run.status">{{
                labels[run.status]
              }}</span>
            </td>
            <td>{{ run.records }}</td>
            <td>{{ (run.duration_ms / 1000).toFixed(1) }}s</td>
            <td>{{ date(run.created_at) }}</td>
            <td>
              <div class="action-row">
                <button class="text-button" @click="inspected = run.id">
                  Detalhes</button
                ><button
                  v-if="
                    user.role !== 'viewer' &&
                    ['success', 'partial', 'failed', 'cancelled'].includes(
                      run.status,
                    )
                  "
                  class="text-button"
                  @click="retry(run.id)"
                >
                  Reprocessar
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="!data.items.length">
            <td colspan="6" class="empty-cell">
              Nenhuma execução para estes filtros.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <Pager :total="data.total" :offset="offset" @change="offset = $event" />
  </section>
  <details class="section-gap">
    <summary @click="!legacy && showLegacy()">
      Histórico da versão anterior (preservado)
    </summary>
    <pre v-if="legacy">{{ JSON.stringify(legacy, null, 2) }}</pre>
  </details>
</template>
