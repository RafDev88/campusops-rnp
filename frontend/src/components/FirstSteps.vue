<script setup lang="ts">
import { computed, ref, watch } from "vue";
const props = defineProps<{ userId: number }>();
const key = computed(() => `campusops:first-steps:v1:${props.userId}`),
  dismissed = ref(false),
  step = ref(0);
function restore() {
  try {
    dismissed.value = localStorage.getItem(key.value) === "done";
  } catch {
    dismissed.value = false;
  }
}
restore();
watch(
  () => props.userId,
  () => {
    step.value = 0;
    restore();
  },
);
function finish() {
  dismissed.value = true;
  try {
    localStorage.setItem(key.value, "done");
  } catch {
    /* Guidance remains usable without browser storage. */
  }
}
const steps = [
  {
    title: "Comece com uma pergunta",
    text: "Pense no assunto que deseja conhecer. Pode ser educação, redes, saúde ou o nome de uma universidade.",
    action: "Fazer minha primeira pesquisa",
    to: "/search",
  },
  {
    title: "Abra e entenda o resultado",
    text: "Nos detalhes você encontra um resumo, os autores e o endereço da fonte. Alguns campos podem não estar disponíveis.",
    action: "Conhecer as publicações",
    to: "/publications",
  },
  {
    title: "Guarde para continuar depois",
    text: "Use a estrela para guardar um resultado. Salve uma pesquisa para voltar aos mesmos filtros. Tudo fica em Minhas pesquisas.",
    action: "Abrir minhas pesquisas",
    to: "/my-research",
  },
];
</script>
<template>
  <section
    v-if="!dismissed"
    class="first-steps"
    aria-labelledby="first-steps-title"
  >
    <div class="first-steps-top">
      <span>PRIMEIRA VEZ AQUI?</span
      ><button
        class="text-button"
        @click="finish"
        aria-label="Ocultar primeiros passos"
      >
        Agora não
      </button>
    </div>
    <p class="guide-position">Passo {{ step + 1 }} de {{ steps.length }}</p>
    <h2 id="first-steps-title" aria-live="polite">{{ steps[step].title }}</h2>
    <p>{{ steps[step].text }}</p>
    <RouterLink class="guide-action" :to="steps[step].to"
      >{{ steps[step].action }} →</RouterLink
    >
    <div class="guide-controls">
      <button v-if="step > 0" class="text-button" @click="step--">Voltar</button
      ><button
        v-if="step < steps.length - 1"
        class="chip-button"
        @click="step++"
      >
        Próximo passo →</button
      ><button v-else class="chip-button" @click="finish">
        Entendi, começar
      </button>
    </div>
  </section>
  <div v-else class="guide-reopen">
    <strong>Continue de onde parou.</strong>
    <p>Suas pesquisas e favoritos ficam guardados na sua conta.</p>
    <RouterLink to="/my-research">Abrir minhas pesquisas →</RouterLink
    ><button
      class="text-button"
      @click="
        dismissed = false;
        step = 0;
      "
    >
      Rever os primeiros passos
    </button>
  </div>
</template>
