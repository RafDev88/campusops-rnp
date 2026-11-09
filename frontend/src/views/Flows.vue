<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { api, date, labels, revision, type User } from "../api";
import CronForm from "../components/CronForm.vue";
import CalendarList from "../components/CalendarList.vue";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Workflow = {
  id: number;
  name: string;
  steps: string[];
  enabled: boolean;
  allow_partial: boolean;
};
type FlowRun = {
  id: number;
  workflow_id: number;
  status: string;
  step: number;
  child_id: number | null;
  message: string;
  history: {
    step: string;
    run_id?: number;
    report_id?: number;
    status: string;
    records?: number;
  }[];
  snapshot: { name: string; steps: string[] };
  created_at: string;
};
const items = ref<Workflow[]>([]),
  runs = ref<FlowRun[]>([]),
  watched = ref<{ id: string; name: string }[]>([]),
  agenda = ref<Workflow | null>(null),
  busy = ref(false);
const form = ref({
  name: "",
  institution_id: "",
  max_pages: 1,
  year_from: 2024,
  since_date: "",
  incremental: true,
  limit: 25,
  orcid_limit: 5,
  allow_partial: true,
});
const selected = ref(["openalex", "crossref", "orcid", "report"]),
  reset = ref<Record<number, boolean>>({});
const stages = [
  { id: "ror", name: "Atualizar cadastro ROR" },
  { id: "openalex", name: "Coletar publicações OpenAlex" },
  { id: "crossref", name: "Enriquecer DOIs novos no Crossref" },
  { id: "orcid", name: "Consultar ORCIDs ainda não importados" },
  { id: "ufrn", name: "Atualizar catálogo de dados UFRN" },
  { id: "report", name: "Gerar relatório privado do catálogo" },
];
const sequence = computed(() =>
  stages.filter((s) => selected.value.includes(s.id)).map((s) => s.id),
);
async function load() {
  try {
    const [d, i] = await Promise.all([
      api<{ items: Workflow[]; runs: FlowRun[] }>("workflows"),
      api<{ items: { id: string; name: string }[] }>(
        "institutions?watched=true&limit=100",
      ),
    ]);
    items.value = d.items;
    runs.value = d.runs;
    watched.value = i.items;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function create() {
  busy.value = true;
  try {
    await api("workflows", "POST", {
      name: form.value.name,
      steps: sequence.value,
      params: { source: "openalex", ...form.value },
      allow_partial: form.value.allow_partial,
    });
    form.value.name = "";
    await load();
    emit("notice", "Fluxo criado. Inicie manualmente ou configure uma agenda.");
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function start(id: number) {
  try {
    await api(`workflows/${id}/start`, "POST");
    await load();
    emit("notice", "Fluxo iniciado. As etapas serão executadas em sequência.");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function control(item: FlowRun, action: string) {
  try {
    await api(`workflow-runs/${item.id}/control`, "POST", {
      action,
      reset_checkpoint: !!reset.value[item.id],
    });
    await load();
    emit("notice", "Comando do fluxo registrado.");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function toggle(item: Workflow) {
  try {
    await api(`workflows/${item.id}`, "PATCH", { enabled: !item.enabled });
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
    Um fluxo conecta as etapas sem cliques intermediários. A coleta incremental
    do OpenAlex usa data de publicação e só avança seu marcador com cobertura
    completa. Limites de páginas e chamadas continuam valendo.
  </div>
  <section v-if="user.role !== 'viewer'" class="panel">
    <div class="panel-heading"><h2>Novo fluxo de automação</h2></div>
    <form class="form-grid detail-body" @submit.prevent="create">
      <label
        >Nome do fluxo<input
          v-model="form.name"
          required
          minlength="3"
          maxlength="100"
      /></label>
      <fieldset class="workflow-step-picker">
        <legend>Etapas, na ordem de execução</legend>
        <label v-for="(stage, index) in stages" :key="stage.id"
          ><input v-model="selected" type="checkbox" :value="stage.id" /><span
            >{{ index + 1 }}. {{ stage.name }}</span
          ></label
        >
      </fieldset>
      <div class="two-columns">
        <label
          >Instituição do fluxo<select
            v-model="form.institution_id"
            aria-label="Instituição do fluxo"
          >
            <option value="">Todas as acompanhadas</option>
            <option v-for="i in watched" :key="i.id" :value="i.id">
              {{ i.name }}
            </option>
          </select></label
        ><label
          >Máximo de páginas por instituição<input
            v-model.number="form.max_pages"
            type="number"
            min="1"
            max="500" /></label
        ><label
          >Ano inicial da coleta<input
            v-model.number="form.year_from"
            type="number"
            min="1900"
            max="2100" /></label
        ><label
          >Data inicial opcional<input
            v-model="form.since_date"
            type="date" /></label
        ><label
          >DOIs por etapa<input
            v-model.number="form.limit"
            type="number"
            min="1"
            max="200" /></label
        ><label
          >Perfis ORCID por etapa<input
            v-model.number="form.orcid_limit"
            type="number"
            min="1"
            max="25"
        /></label>
      </div>
      <label class="checkbox-label"
        ><input v-model="form.incremental" type="checkbox" />Usar marcador
        incremental quando disponível</label
      ><label class="checkbox-label"
        ><input v-model="form.allow_partial" type="checkbox" />Continuar o fluxo
        quando a etapa terminar com cobertura parcial</label
      >
      <p class="muted">
        O enriquecimento usa publicações da etapa OpenAlex e respeita os limites
        configurados. Relatórios ficam disponíveis para o criador do fluxo. A
        rotina não ativa planos pagos.
      </p>
      <button class="primary-action" :disabled="busy || !sequence.length">
        {{ busy ? "Criando…" : "Criar fluxo" }}
      </button>
    </form>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Fluxos configurados</h2></div>
    <article v-for="item in items" :key="item.id" class="workflow-card">
      <div>
        <h3>
          {{ item.name }}
          <span class="badge">{{ item.enabled ? "Ativo" : "Pausado" }}</span>
        </h3>
        <div class="stage-chain">
          <span v-for="(stage, i) in item.steps" :key="stage"
            >{{ i + 1 }}. {{ stage }}
            <span v-if="i < item.steps.length - 1">→</span></span
          >
        </div>
      </div>
      <div v-if="user.role !== 'viewer'" class="action-row">
        <button
          class="chip-button"
          :disabled="!item.enabled"
          @click="start(item.id)"
        >
          Iniciar fluxo</button
        ><button
          class="text-button"
          @click="agenda = agenda?.id === item.id ? null : item"
        >
          Agendar fluxo</button
        ><button class="text-button" @click="toggle(item)">
          {{ item.enabled ? "Pausar definição" : "Ativar definição" }}
        </button>
      </div>
    </article>
    <p v-if="!items.length" class="empty-cell">
      Nenhum fluxo criado. Escolha as etapas que devem trabalhar juntas.
    </p>
  </section>
  <section v-if="agenda" class="panel section-gap">
    <div class="panel-heading">
      <h2>Agendar: {{ agenda.name }}</h2>
      <button class="text-button" @click="agenda = null">Fechar agenda</button>
    </div>
    <div class="detail-body">
      <CronForm
        :key="agenda.id"
        target="workflow"
        :target-id="agenda.id"
        :title="agenda.name + ' · agenda'"
        @done="
          agenda = null;
          emit('notice', 'Agenda do fluxo criada.');
        "
        @error="emit('error', $event)"
      />
    </div>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Execuções dos fluxos</h2></div>
    <article v-for="run in runs" :key="run.id" class="workflow-card">
      <div>
        <div class="tag-row">
          <span class="badge" :class="run.status">{{
            labels[run.status] || run.status
          }}</span
          ><small>#{{ run.id }} · {{ date(run.created_at) }}</small>
        </div>
        <h3>
          {{ run.snapshot.name }} · etapa
          {{ Math.min(run.step + 1, run.snapshot.steps.length) }} de
          {{ run.snapshot.steps.length }}
        </h3>
        <p>{{ run.message }}</p>
        <div class="stage-chain">
          <span
            v-for="(stage, i) in run.snapshot.steps"
            :key="stage"
            :class="{ done: i < run.step, current: i === run.step }"
            >{{ i + 1 }}. {{ stage }}</span
          >
        </div>
        <RouterLink
          v-if="run.child_id"
          class="text-button"
          :to="{ name: 'runs', query: { id: String(run.child_id) } }"
          >Ver progresso da etapa #{{ run.child_id }} →</RouterLink
        >
        <details v-if="run.history.length">
          <summary>Etapas concluídas</summary>
          <ul>
            <li v-for="(h, i) in run.history" :key="i">
              {{ h.step }} · {{ labels[h.status] || h.status }} ·
              {{
                h.records === undefined
                  ? "relatório #" + h.report_id
                  : h.records + " registros"
              }}
            </li>
          </ul>
        </details>
      </div>
      <div v-if="user.role !== 'viewer'" class="workflow-actions">
        <button
          v-if="['running', 'waiting'].includes(run.status)"
          class="chip-button"
          @click="control(run, 'pause')"
        >
          Pausar fluxo</button
        ><button
          v-if="['paused', 'failed'].includes(run.status)"
          class="chip-button"
          @click="control(run, 'resume')"
        >
          Retomar fluxo</button
        ><label v-if="run.status === 'failed'" class="checkbox-label"
          ><input v-model="reset[run.id]" type="checkbox" />Refazer checkpoint
          da etapa</label
        ><button
          v-if="
            ['running', 'waiting', 'paused', 'pausing'].includes(run.status)
          "
          class="text-button danger-text"
          @click="control(run, 'cancel')"
        >
          Cancelar fluxo
        </button>
      </div>
    </article>
    <p v-if="!runs.length" class="empty-cell">Nenhum fluxo foi iniciado.</p>
  </section>
  <CalendarList
    :user="user"
    @error="emit('error', $event)"
    @notice="emit('notice', $event)"
  />
</template>
