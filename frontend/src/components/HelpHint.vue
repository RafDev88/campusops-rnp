<script setup lang="ts">
import { ref, useId } from "vue";
defineProps<{ label: string; text: string }>();
const open = ref(false),
  id = useId();
</script>
<template>
  <span class="help-hint"
    ><button
      type="button"
      :aria-expanded="open"
      :aria-controls="id"
      @click="open = !open"
      @keydown.esc="open = false"
    >
      {{ label }} <span aria-hidden="true">ⓘ</span></button
    ><span v-show="open" :id="id" class="help-hint-text" role="note">{{
      text
    }}</span></span
  >
</template>
