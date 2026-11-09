<script setup lang="ts">
import { computed } from "vue";
import { pageByName } from "../navigation";
const props = defineProps<{ page: string }>();
const content = computed(() => pageByName(props.page));
</script>
<template>
  <details class="context-help">
    <summary>Como usar esta página</summary>
    <ol>
      <li v-for="step in content.steps" :key="step">{{ step }}</li>
    </ol>
    <RouterLink to="/help">Abrir a central de ajuda →</RouterLink>
  </details>
</template>
