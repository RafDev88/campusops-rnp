<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import { api, date, labels, refresh, type Run, type User } from "../api";
const props = defineProps<{ identifier: number; user: User }>();
const emit = defineEmits<{
  close: [];
  error: [message: string];
  notice: [message: string];
}>();
type Runtime = {
  stage: string;
  responses: number;
  pages: number;
  cache_bytes: number;
  requested: string;
  next_at: string | null;
  retries: number;
  heartbeat: string;
};
const data = ref<{
    run: Run;
    runtime: Runtime | null;
    log: { id: number; kind: string; message: string; created_at: string }[];
  } | null>(null),
  reset = ref(false),
  busy = ref(false);
const stages: Record<string, string> = {
  queued: "Na fila",
  collecting: "Consultando a fonte",
  applying: "Gravando dados e índices",
  completed: "Etapa concluída",
  paused: "Pausada",
  waiting_retry: "Aguardando nova tentativa",
  failed: "Falha",
  cancelled: "Cancelada",
};
async function load() {
  try {
    data.value = await api("runs/" + props.identifier + "/runtime");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function command(action: string) {
  busy.value = true;
  try {
    await api(`runs/${props.identifier}/control`, "POST", {
      action,
      reset_checkpoint: reset.value,
    });
    refresh();
    await load();
    emit(
      "notice",
      action === "resume"
        ? "Retomada registrada."
        : "Solicitação registrada; aplicada entre consultas.",
    );
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
let timer: ReturnType<typeof setInterval>;
onMounted(() => {
  load();
  timer = setInterval(load, 5000);
});
watch(
  () => props.identifier,
  () => {
    reset.value = false;
    load();
  },
);
onUnmounted(() => clearInterval(timer));
</script>
<template>
  <section v-if="data" class="panel detail-panel">
    <div class="panel-heading">
      <div>
        <h2>
          Execução #{{ data.run.id }} · {{ data.run.source.toUpperCase() }}
        </h2>
        <p>{{ data.run.message }}</p>
      </div>
      <button class="text-button" @click="emit('close')">
        Fechar progresso
      </button>
    </div>
    <div class="detail-body">
      <div class="progress-strip">
        <span class="badge" :class="data.run.status">{{
          labels[data.run.status] || data.run.status
        }}</span
        ><strong>{{ stages[data.runtime?.stage || "queued"] }}</strong
        ><span v-if="data.runtime?.requested" class="muted"
          >Comando pendente: {{ data.runtime.requested }}</span
        >
      </div>
      <div class="runtime-counters">
        <div>
          <strong>{{ data.run.http_calls }}</strong
          ><small>Chamadas HTTP</small>
        </div>
        <div>
          <strong>{{ data.runtime?.pages || 0 }}</strong
          ><small>Páginas confirmadas</small>
        </div>
        <div>
          <strong>{{ data.runtime?.responses || 0 }}</strong
          ><small>Respostas em checkpoint</small>
        </div>
        <div>
          <strong
            >{{
              ((data.runtime?.cache_bytes || 0) / 1048576).toFixed(1)
            }}
            MB</strong
          ><small>Dados para retomada</small>
        </div>
      </div>
      <p v-if="data.runtime?.next_at" class="scope-note">
        Próxima tentativa: {{ date(data.runtime.next_at) }} ·
        {{ data.runtime.retries }} retentativas automáticas de execução.
      </p>
      <div v-if="user.role !== 'viewer'" class="action-row">
        <button
          v-if="['queued', 'running', 'retry_wait'].includes(data.run.status)"
          class="chip-button"
          :disabled="busy"
          @click="command('pause')"
        >
          Pausar execução</button
        ><button
          v-if="['paused', 'failed', 'retry_wait'].includes(data.run.status)"
          class="chip-button"
          :disabled="busy"
          @click="command('resume')"
        >
          Retomar pelo checkpoint</button
        ><button
          v-if="
            ['queued', 'running', 'paused', 'retry_wait'].includes(
              data.run.status,
            )
          "
          class="text-button danger-text"
          :disabled="busy"
          @click="command('cancel')"
        >
          Cancelar execução</button
        ><label
          v-if="['paused', 'failed'].includes(data.run.status)"
          class="checkbox-label"
          ><input v-model="reset" type="checkbox" />Refazer respostas salvas
          (após corrigir o contrato)</label
        >
      </div>
      <p class="muted">
        Pausa e cancelamento são cooperativos. Respostas já confirmadas
        permanecem salvas; os dados são aplicados ao concluir uma coleta válida.
        A etapa de gravação não é interrompida.
      </p>
      <details>
        <summary>Cobertura e resultado da coleta</summary>
        <pre>{{ JSON.stringify(data.run.details, null, 2) }}</pre>
      </details>
      <h3>Histórico da execução</h3>
      <div v-for="entry in data.log" :key="entry.id" class="job-log">
        <span>{{ date(entry.created_at) }}</span
        ><strong>{{ entry.message }}</strong>
      </div>
      <p v-if="!data.log.length" class="muted">
        Execução anterior ao histórico de checkpoints.
      </p>
    </div>
  </section>
</template>
