<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, type User } from "../api";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Policy = {
  source: string;
  enabled: boolean;
  per_run: number;
  per_minute: number;
  per_day: number;
  cache_mb: number;
  auto_retries: number;
  overlap_days: number;
};
const items = ref<Policy[]>([]),
  busy = ref("");
async function load() {
  try {
    items.value = await api("source-policies");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function save(item: Policy) {
  busy.value = item.source;
  try {
    await api("source-policies/" + item.source, "PUT", item);
    emit("notice", "Limites e recuperação atualizados.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = "";
  }
}
onMounted(load);
</script>
<template>
  <div class="scope-note">
    Estes são limites locais de chamadas do CampusOps, não o saldo financeiro
    nem a cota restante do provedor. As janelas diária e por minuto usam UTC.
    Checkpoints economizam chamadas durante a retomada.
  </div>
  <div class="source-grid">
    <section v-for="item in items" :key="item.source" class="panel">
      <div class="panel-heading">
        <h2>{{ item.source.toUpperCase() }}</h2>
        <span class="badge">{{ item.enabled ? "Habilitada" : "Pausada" }}</span>
      </div>
      <form class="form-grid detail-body" @submit.prevent="save(item)">
        <label class="checkbox-label"
          ><input
            v-model="item.enabled"
            type="checkbox"
            :disabled="user.role !== 'admin'"
          />Habilitar novas consultas da fonte</label
        >
        <div class="two-columns">
          <label
            >Chamadas por execução<input
              v-model.number="item.per_run"
              type="number"
              min="1"
              max="5000"
              required
              :disabled="user.role !== 'admin'" /></label
          ><label
            >Chamadas por minuto<input
              v-model.number="item.per_minute"
              type="number"
              min="1"
              max="600"
              required
              :disabled="user.role !== 'admin'" /></label
          ><label
            >Chamadas por dia<input
              v-model.number="item.per_day"
              type="number"
              min="1"
              max="100000"
              required
              :disabled="user.role !== 'admin'" /></label
          ><label
            >Checkpoint máximo (MB)<input
              v-model.number="item.cache_mb"
              type="number"
              min="1"
              max="500"
              required
              :disabled="user.role !== 'admin'" /></label
          ><label
            >Retentativas automáticas<input
              v-model.number="item.auto_retries"
              type="number"
              min="0"
              max="5"
              required
              :disabled="user.role !== 'admin'" /></label
          ><label v-if="item.source === 'openalex'"
            >Sobreposição incremental (dias)<input
              v-model.number="item.overlap_days"
              type="number"
              min="0"
              max="30"
              required
              :disabled="user.role !== 'admin'"
          /></label>
        </div>
        <p class="muted">
          Erros de credencial, contrato e certificado exigem revisão. Limites
          diários aguardam a próxima janela; limites da execução pausam o
          trabalho para ajuste.
        </p>
        <button
          v-if="user.role === 'admin'"
          class="primary-action"
          :disabled="busy === item.source"
        >
          Salvar política {{ item.source.toUpperCase() }}
        </button>
      </form>
    </section>
  </div>
</template>
