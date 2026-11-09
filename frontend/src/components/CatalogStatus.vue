<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import { api, date, labels, revision } from "../api";
type Status = {
  total_publications: number;
  scope: string;
  sources: {
    source: string;
    status: string;
    collected_at: string | null;
    coverage: string;
    message: string;
  }[];
};
const data = ref<Status | null>(null),
  error = ref("");
let controller: AbortController | undefined;
async function load() {
  controller?.abort();
  const current = (controller = new AbortController());
  try {
    const result = await api<Status>(
      "catalog-status",
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
  <details class="catalog-status panel">
    <summary>De onde vêm estes dados e quando foram atualizados?</summary>
    <p v-if="error" role="status">
      Não foi possível consultar a atualização.
      <button class="text-button" @click="load">Tentar novamente</button>
    </p>
    <template v-if="data">
      <p>{{ data.scope }}</p>
      <ul class="status-source-list">
        <li v-for="item in data.sources" :key="item.source">
          <strong>{{ item.source.toUpperCase() }}</strong>
          <span
            >Última coleta bem-sucedida ou parcial:
            {{ date(item.collected_at) }}</span
          >
          <span
            >Última execução:
            {{ labels[item.status] || "Ainda não coletada" }}</span
          >
          <span>{{
            item.coverage === "partial"
              ? "Cobertura parcial"
              : item.coverage === "complete"
                ? "Escopo da execução completo"
                : "Cobertura não comprovada"
          }}</span>
        </li>
      </ul>
      <RouterLink :to="{ name: 'sources' }"
        >Ver fontes e limites do catálogo →</RouterLink
      >
    </template>
  </details>
</template>
