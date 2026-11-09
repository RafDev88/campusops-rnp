<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from "vue";
import { api, date, labels, revision, type User } from "../api";
import CronForm from "../components/CronForm.vue";
import CalendarList from "../components/CalendarList.vue";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Template = { id: number; name: string; filters: Record<string, unknown> };
const templates = ref<Template[]>([]),
  saved = ref<{ id: number; name: string; filters: Record<string, unknown> }[]>(
    [],
  ),
  reports = ref<
    {
      id: number;
      name: string;
      status: string;
      created_at: string;
      rows: number;
      total: number;
      message: string;
    }[]
  >([]),
  name = ref(""),
  search = ref(""),
  agenda = ref<Template | null>(null),
  busy = ref(false);
async function load() {
  try {
    [templates.value, saved.value, reports.value] = await Promise.all([
      api<Template[]>("report-templates"),
      api<typeof saved.value>("saved-searches"),
      api<typeof reports.value>("reports"),
    ]);
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function create() {
  busy.value = true;
  try {
    await api("report-templates", "POST", {
      name: name.value,
      filters:
        saved.value.find((s) => String(s.id) === search.value)?.filters || {},
    });
    name.value = "";
    await load();
    emit("notice", "Modelo privado criado. Gere agora ou escolha uma agenda.");
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function generate(id: number) {
  try {
    await api(`report-templates/${id}/generate`, "POST");
    await load();
    emit("notice", "Relatório na fila de geração.");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
let timer: ReturnType<typeof setInterval>;
onMounted(() => {
  load();
  timer = setInterval(() => {
    if (reports.value.some((r) => ["queued", "running"].includes(r.status)))
      load();
  }, 5000);
});
watch(revision, load);
onUnmounted(() => clearInterval(timer));
</script>
<template>
  <p class="scope-note">
    Relatórios CSV usam uma cópia dos filtros escolhidos, respeitam seus
    favoritos e ficam disponíveis só para sua conta. Até 10 mil resultados por
    arquivo; disponibilidade de 30 dias.
  </p>
  <section class="panel">
    <div class="panel-heading"><h2>Novo modelo de relatório</h2></div>
    <form class="form-grid detail-body" @submit.prevent="create">
      <div class="two-columns">
        <label
          >Nome do relatório<input
            v-model="name"
            minlength="3"
            maxlength="100"
            required /></label
        ><label
          >Critérios do relatório<select
            v-model="search"
            aria-label="Critérios do relatório"
          >
            <option value="">Todo o catálogo de publicações</option>
            <option v-for="s in saved" :key="s.id" :value="String(s.id)">
              {{ s.name }}
            </option>
          </select></label
        >
      </div>
      <p class="muted">
        Para escolher critérios específicos, salve uma pesquisa na tela de
        Publicações e selecione-a aqui.
      </p>
      <button class="primary-action" :disabled="busy">
        Criar modelo de relatório
      </button>
    </form>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Seus modelos</h2></div>
    <article v-for="item in templates" :key="item.id" class="workflow-card">
      <h3>{{ item.name }}</h3>
      <div class="action-row">
        <button class="chip-button" @click="generate(item.id)">
          Gerar relatório agora</button
        ><button
          class="text-button"
          @click="agenda = agenda?.id === item.id ? null : item"
        >
          Programar relatório
        </button>
      </div>
    </article>
    <p v-if="!templates.length" class="empty-cell">
      Nenhum modelo privado criado.
    </p>
  </section>
  <section v-if="agenda" class="panel section-gap">
    <div class="panel-heading">
      <h2>Programar: {{ agenda.name }}</h2>
      <button class="text-button" @click="agenda = null">Fechar</button>
    </div>
    <div class="detail-body">
      <CronForm
        :key="agenda.id"
        target="report"
        :target-id="agenda.id"
        :title="agenda.name + ' · agenda'"
        @done="
          agenda = null;
          emit('notice', 'Relatório programado.');
        "
        @error="emit('error', $event)"
      />
    </div>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Arquivos gerados</h2></div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>RELATÓRIO</th>
            <th>ESTADO</th>
            <th>RESULTADOS</th>
            <th>CRIADO EM</th>
            <th>ARQUIVO</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in reports" :key="item.id">
            <td>
              {{ item.name }}<small>{{ item.message }}</small>
            </td>
            <td>
              <span class="badge" :class="item.status">{{
                labels[item.status] || item.status
              }}</span>
            </td>
            <td>{{ item.rows }} / {{ item.total }}</td>
            <td>{{ date(item.created_at) }}</td>
            <td>
              <a
                v-if="item.status === 'ready'"
                class="text-button"
                :href="`/api/reports/${item.id}/download`"
                download
                >Baixar CSV ↓</a
              ><span v-else>—</span>
            </td>
          </tr>
          <tr v-if="!reports.length">
            <td colspan="5" class="empty-cell">
              Os arquivos aparecerão aqui após a geração.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
  <CalendarList
    :user="user"
    @error="emit('error', $event)"
    @notice="emit('notice', $event)"
  />
</template>
