<script setup lang="ts">
import { computed, ref } from "vue";
import { api, refresh } from "../api";
const props = defineProps<{
  target: "source" | "workflow" | "report";
  targetId?: number;
  title?: string;
}>();
const emit = defineEmits<{ done: []; error: [message: string] }>();
const name = ref(props.title || ""),
  frequency = ref("daily"),
  time = ref("08:00"),
  days = ref(["1"]),
  zone = ref("America/Sao_Paulo"),
  custom = ref("0 8 * * *"),
  source = ref("openalex"),
  pages = ref(1),
  year = ref(2024),
  since = ref(""),
  orcid = ref(""),
  next = ref<string[]>([]),
  busy = ref(false);
const cron = computed(() => {
  const [h, m] = time.value.split(":");
  return frequency.value === "custom"
    ? custom.value
    : frequency.value === "hourly"
      ? `${m} * * * *`
      : `${m} ${h} * * ${frequency.value === "weekly" ? days.value.join(",") : "*"}`;
});
function payload() {
  return {
    name: name.value || "Agenda de automação",
    target: props.target,
    target_id: props.targetId || null,
    source: props.target === "source" ? source.value : "",
    params: {
      source: source.value,
      max_pages: pages.value,
      year_from: year.value,
      since_date: since.value,
      incremental: true,
      orcid: orcid.value,
      auto_discover: source.value === "orcid" && !orcid.value,
    },
    cron: cron.value,
    timezone: zone.value,
  };
}
async function preview() {
  try {
    next.value = (
      await api<{ next: string[] }>("calendar-preview", "POST", payload())
    ).next;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function save() {
  busy.value = true;
  try {
    await api("calendar-schedules", "POST", payload());
    refresh();
    emit("done");
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
const weekdays = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
</script>
<template>
  <form class="form-grid calendar-form" @submit.prevent="save">
    <label
      >Nome da agenda<input
        v-model="name"
        minlength="3"
        maxlength="100"
        required
    /></label>
    <div class="two-columns">
      <label
        >Frequência<select
          v-model="frequency"
          aria-label="Frequência da agenda"
        >
          <option value="daily">Todos os dias</option>
          <option value="weekly">Dias da semana</option>
          <option value="hourly">A cada hora</option>
          <option value="custom">Cron personalizado</option>
        </select></label
      ><label v-if="frequency !== 'custom'"
        >Horário local<input v-model="time" type="time" required /></label
      ><label
        >Fuso horário<select v-model="zone" aria-label="Fuso horário">
          <option>America/Sao_Paulo</option>
          <option>America/Manaus</option>
          <option>America/Recife</option>
          <option>UTC</option>
          <option>Europe/Lisbon</option>
        </select></label
      >
    </div>
    <fieldset v-if="frequency === 'weekly'" class="weekday-picker">
      <legend>Dias de execução</legend>
      <label v-for="(label, i) in weekdays" :key="i"
        ><input v-model="days" type="checkbox" :value="String(i)" />{{
          label
        }}</label
      >
    </fieldset>
    <label v-if="frequency === 'custom'"
      >Expressão cron<input
        v-model="custom"
        required
        placeholder="0 8 * * 1-5"
      /><small>Cinco campos. Intervalo mínimo de 15 minutos.</small></label
    ><template v-if="target === 'source'"
      ><label
        >Fonte agendada<select v-model="source" aria-label="Fonte agendada">
          <option
            v-for="s in ['ror', 'openalex', 'crossref', 'orcid', 'ufrn']"
            :key="s"
          >
            {{ s }}
          </option>
        </select></label
      >
      <div class="two-columns">
        <label
          >Máximo de páginas<input
            v-model.number="pages"
            type="number"
            min="1"
            max="500" /></label
        ><label
          >Ano inicial<input
            v-model.number="year"
            type="number"
            min="1900"
            max="2100"
        /></label>
      </div>
      <label v-if="source === 'openalex'"
        >Data inicial opcional<input v-model="since" type="date" /><small
          >Novas publicações; o marcador só avança quando a janela foi coletada
          por completo.</small
        ></label
      ><label v-if="source === 'orcid'"
        >ORCID opcional<input
          v-model="orcid"
          placeholder="Vazio: descobrir identificadores novos dos autores" /></label
    ></template>
    <div class="action-row">
      <button class="text-button" type="button" @click="preview">
        Prévia dos próximos horários</button
      ><button class="primary-action" :disabled="busy">
        {{ busy ? "Salvando…" : "Salvar agenda" }}
      </button>
    </div>
    <ul v-if="next.length" class="schedule-preview">
      <li v-for="value in next" :key="value">
        {{ new Date(value).toLocaleString("pt-BR", { timeZone: zone }) }} ·
        {{ zone }}
      </li>
    </ul>
    <p class="muted">
      O ciclo verifica horários a cada minuto. Disparos sobrepostos são
      registrados e omitidos; uma pausa não desfaz etapas já concluídas.
    </p>
  </form>
</template>
