<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api, date, labels, revision, type User } from "../api";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Incident = {
  id: number;
  title: string;
  detail: string;
  source: string;
  status: string;
  created_at: string;
  resolved_at: string | null;
};
const items = ref<Incident[]>([]);
async function load() {
  try {
    items.value = await api<Incident[]>("incidents");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function resolve(id: number) {
  try {
    await api(`incidents/${id}/resolve`, "POST");
    emit("notice", "Incidente resolvido e ação registrada na auditoria.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(revision, load);
</script>
<template>
  <div class="scope-note">
    Falhas recorrentes abrem incidentes conforme as regras. Uma coleta completa
    bem-sucedida resolve automaticamente o incidente de falhas consecutivas da
    fonte. Mudanças de contrato exigem revisão.
  </div>
  <section class="panel">
    <div class="panel-heading">
      <h2>Incidentes operacionais</h2>
      <span class="badge"
        >{{ items.filter((i) => i.status === "open").length }} abertos</span
      >
    </div>
    <article v-for="item in items" :key="item.id" class="incident-item">
      <div>
        <div class="tag-row">
          <span class="badge" :class="item.status">{{
            labels[item.status]
          }}</span
          ><small>#{{ item.id }} · {{ item.source.toUpperCase() }}</small>
        </div>
        <h3>{{ item.title }}</h3>
        <p>{{ item.detail }}</p>
        <small
          >{{ date(item.created_at)
          }}<span v-if="item.resolved_at">
            · Resolvido em {{ date(item.resolved_at) }}</span
          ></small
        >
      </div>
      <button
        v-if="user.role !== 'viewer' && item.status === 'open'"
        class="chip-button"
        @click="resolve(item.id)"
      >
        Resolver
      </button>
    </article>
    <div v-if="!items.length" class="empty">
      <strong>Nenhum incidente registrado</strong>
      <p>As regras acompanharão as próximas coletas.</p>
    </div>
  </section>
</template>
