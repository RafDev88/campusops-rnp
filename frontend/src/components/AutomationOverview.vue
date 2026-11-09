<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import { api, date, labels, revision } from "../api";
const stages: Record<string, string> = {
  queued: "Aguardando início",
  collecting: "Consultando a fonte",
  applying: "Gravando informações",
  completed: "Etapa concluída",
  retry_wait: "Aguardando nova tentativa",
};
type Summary = {
  active_runs: number;
  failed_runs: number;
  enabled_schedules: number;
  scope: string;
  items: {
    id: string;
    kind: string;
    title: string;
    status: string;
    stage: string;
    next_at: string | null;
    message: string;
    action: string;
    route: string;
    resource_id: number | null;
  }[];
};
const data = ref<Summary | null>(null),
  error = ref("");
let controller: AbortController | undefined;
async function load() {
  controller?.abort();
  const current = (controller = new AbortController());
  try {
    const result = await api<Summary>(
      "automation-overview",
      "GET",
      undefined,
      current.signal,
    );
    if (!current.signal.aborted) {
      data.value = result;
      error.value = "";
    }
  } catch (e) {
    if (!current.signal.aborted) error.value = (e as Error).message;
  }
}
onMounted(load);
watch(revision, load);
onUnmounted(() => controller?.abort());
</script>
<template>
  <section class="panel" aria-labelledby="automation-overview-title">
    <h2 id="automation-overview-title">Acompanhe suas automações</h2>
    <p v-if="error" role="alert">
      {{ error }}
      <button class="text-button" @click="load">Tentar novamente</button>
    </p>
    <template v-if="data">
      <p role="status">
        {{ data.active_runs }} coletas em acompanhamento ·
        {{ data.enabled_schedules }} agendas ativas ·
        {{ data.failed_runs }} falhas no histórico
      </p>
      <p>{{ data.scope }}</p>
      <details v-if="data.items.length">
        <summary>
          Ver próximas execuções e itens que precisam de atenção
        </summary>
        <ul class="operation-summary-list">
          <li v-for="item in data.items" :key="item.id">
            <strong>{{ item.title }} · {{ item.kind }}</strong>
            <span
              >{{
                labels[item.status] ||
                (item.status === "scheduled" ? "Programada" : item.status)
              }}<template v-if="item.stage">
                · {{ stages[item.stage] || item.stage }}</template
              ></span
            >
            <span v-if="item.next_at"
              >Próximo horário: {{ date(item.next_at) }}</span
            >
            <p v-if="item.message">{{ item.message }}</p>
            <p>{{ item.action }}</p>
            <RouterLink
              :to="{
                name: item.route,
                query: item.resource_id ? { id: item.resource_id } : {},
              }"
              >Abrir detalhes →</RouterLink
            >
          </li>
        </ul>
      </details>
      <p v-else>
        Nenhuma rotina precisa de acompanhamento agora.
        <RouterLink :to="{ name: 'automation' }"
          >Conheça os agendamentos</RouterLink
        >.
      </p>
    </template>
  </section>
</template>
