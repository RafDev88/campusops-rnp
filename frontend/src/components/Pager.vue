<script setup lang="ts">
defineProps<{ total: number; offset: number; size?: number }>();
defineEmits<{ change: [offset: number] }>();
</script>
<template>
  <div class="pager">
    <span
      >{{ total ? offset + 1 : 0 }}–{{
        Math.min(offset + (size || 25), total)
      }}
      de {{ total }}</span
    >
    <div>
      <button
        :disabled="offset === 0"
        @click="$emit('change', Math.max(0, offset - (size || 25)))"
      >
        Anterior</button
      ><button
        :disabled="offset + (size || 25) >= total"
        @click="$emit('change', offset + (size || 25))"
      >
        Próxima
      </button>
    </div>
  </div>
</template>
