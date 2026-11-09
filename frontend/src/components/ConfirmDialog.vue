<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
const props = defineProps<{
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  busy?: boolean;
}>();
const emit = defineEmits<{ confirm: []; cancel: [] }>();
const dialog = ref<HTMLDialogElement | null>(null);
function sync() {
  if (props.open && !dialog.value?.open) dialog.value?.showModal();
  if (!props.open && dialog.value?.open) dialog.value.close();
}
watch(() => props.open, sync);
onMounted(sync);
</script>
<template>
  <dialog
    ref="dialog"
    class="confirmation-dialog"
    aria-labelledby="confirm-title"
    aria-describedby="confirm-description"
    @cancel.prevent="!busy && emit('cancel')"
  >
    <h2 id="confirm-title">{{ title }}</h2>
    <p id="confirm-description">{{ description }}</p>
    <div class="action-row">
      <button
        class="chip-button"
        autofocus
        :disabled="busy"
        @click="emit('cancel')"
      >
        Voltar sem remover</button
      ><button class="primary-action" :disabled="busy" @click="emit('confirm')">
        {{ busy ? "Removendo…" : confirmLabel }}
      </button>
    </div>
  </dialog>
</template>
