<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import Button from "primevue/button";
import CronForm from "../components/CronForm.vue";
import CalendarList from "../components/CalendarList.vue";
import { api, date, revision, type Source, type User } from "../api";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Schedule = {
  id: number;
  source: Source;
  interval_minutes: number;
  next_at: string;
  enabled: boolean;
  params: Record<string, unknown>;
};
type Rule = {
  id: number;
  name: string;
  kind: string;
  source: string;
  threshold: number;
  topic: string;
  enabled: boolean;
  webhook_id: number | null;
};
const schedules = ref<Schedule[]>([]),
  rules = ref<Rule[]>([]),
  busy = ref(false);
const preview = ref<{
  matched_count: number;
  samples: { id: string; title: string }[];
  explanation: string;
} | null>(null);
async function previewRule() {
  try {
    preview.value = await api("rules/preview", "POST", {
      ...rule.value,
      name: rule.value.name || "Prévia da regra",
      webhook_id: rule.value.webhook_id || null,
    });
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
const schedule = ref({
  source: "ror" as Source,
  interval_minutes: 1440,
  pages: 500,
  year: 2024,
  limit: 25,
  orcid: "",
  query: "",
});
const rule = ref({
  name: "",
  kind: "new_publication",
  source: "openalex",
  threshold: 3,
  topic: "",
  webhook_id: null as number | null,
});
const kinds: Record<string, string> = {
  failure_streak: "Falhas consecutivas",
  new_publication: "Nova publicação",
  schema_change: "Mudança de contrato",
  dataset_changed: "Conjunto de dados alterado",
  stale_source: "Dados desatualizados",
  weekly_digest: "Resumo semanal (segunda, 9h Brasília)",
};
async function load() {
  try {
    [schedules.value, rules.value] = await Promise.all([
      api<Schedule[]>("schedules"),
      api<Rule[]>("rules"),
    ]);
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function createSchedule() {
  busy.value = true;
  try {
    await api("schedules", "POST", {
      source: schedule.value.source,
      interval_minutes: schedule.value.interval_minutes,
      params: {
        source: schedule.value.source,
        max_pages: schedule.value.pages,
        year_from: schedule.value.year,
        limit: schedule.value.limit,
        orcid: schedule.value.orcid,
        query: schedule.value.query,
      },
    });
    emit(
      "notice",
      "Agendamento criado. Primeira execução ocorre no próximo ciclo de até um minuto.",
    );
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function createRule() {
  busy.value = true;
  try {
    await api("rules", "POST", {
      ...rule.value,
      webhook_id: rule.value.webhook_id || null,
    });
    rule.value.name = "";
    emit("notice", "Regra criada. Será aplicada às próximas execuções.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function toggle(collection: string, id: number, enabled: boolean) {
  try {
    await api(`${collection}/${id}/enabled`, "PATCH", { enabled: !enabled });
    emit("notice", enabled ? "Configuração pausada." : "Configuração ativada.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(revision, load);
watch(
  () => schedule.value.source,
  (source) => {
    schedule.value.pages =
      source === "ror" ? 500 : source === "openalex" ? 3 : 10;
  },
);
</script>
<template>
  <div class="automation-links">
    <RouterLink class="chip-button" :to="{ name: 'flows' }"
      >Criar fluxos encadeados →</RouterLink
    ><RouterLink class="chip-button" :to="{ name: 'reports' }"
      >Programar relatórios →</RouterLink
    ><RouterLink class="chip-button" :to="{ name: 'policies' }"
      >Limites e recuperação →</RouterLink
    >
  </div>
  <details v-if="user.role !== 'viewer'" class="panel calendar-panel">
    <summary>Agendar coleta por dia, horário e fuso</summary>
    <div class="detail-body">
      <CronForm
        target="source"
        @done="emit('notice', 'Agenda por horário criada.')"
        @error="emit('error', $event)"
      />
    </div>
  </details>
  <div class="scope-note">
    O agendador verifica tarefas a cada minuto. Pause uma configuração para
    interromper futuras execuções; tarefas que já começaram continuam no
    histórico.
  </div>
  <div v-if="user.role !== 'viewer'" class="two-columns">
    <section class="panel">
      <div class="panel-heading"><h2>Novo agendamento</h2></div>
      <form class="form-grid detail-body" @submit.prevent="createSchedule">
        <div class="two-columns">
          <label
            >Fonte<select v-model="schedule.source">
              <option
                v-for="s in ['ror', 'openalex', 'crossref', 'orcid', 'ufrn']"
                :key="s"
              >
                {{ s }}
              </option>
            </select></label
          ><label
            >Intervalo (minutos)<input
              v-model.number="schedule.interval_minutes"
              type="number"
              min="15"
              max="525600"
              required
          /></label>
        </div>
        <label v-if="['ror', 'openalex', 'ufrn'].includes(schedule.source)"
          >Limite de páginas<input
            v-model.number="schedule.pages"
            type="number"
            min="1"
            max="500"
            required
          /><small>OpenAlex: limite por instituição acompanhada.</small></label
        ><label v-if="schedule.source === 'openalex'"
          >Ano inicial<input
            v-model.number="schedule.year"
            type="number"
            min="1900"
            max="2100"
            required /></label
        ><label v-if="schedule.source === 'crossref'"
          >DOIs por execução<input
            v-model.number="schedule.limit"
            type="number"
            min="1"
            max="200"
            required /></label
        ><label v-if="schedule.source === 'orcid'"
          >ORCID<input
            v-model="schedule.orcid"
            required
            placeholder="0000-0000-0000-000X" /></label
        ><label v-if="schedule.source === 'ufrn'"
          >Busca no catálogo<input
            v-model="schedule.query"
            placeholder="Opcional"
            maxlength="150" /></label
        ><Button type="submit" :loading="busy" label="Criar agendamento" />
      </form>
    </section>
    <section class="panel">
      <div class="panel-heading"><h2>Nova regra de automação</h2></div>
      <form class="form-grid detail-body" @submit.prevent="createRule">
        <label
          >Nome da regra<input
            v-model="rule.name"
            minlength="3"
            maxlength="100"
            required
        /></label>
        <div class="two-columns">
          <label
            >Condição<select v-model="rule.kind">
              <option v-for="(label, key) in kinds" :key="key" :value="key">
                {{ label }}
              </option>
            </select></label
          ><label
            >Fonte<select v-model="rule.source">
              <option value="all">Todas</option>
              <option
                v-for="s in ['ror', 'openalex', 'crossref', 'orcid', 'ufrn']"
                :key="s"
              >
                {{ s }}
              </option>
            </select></label
          >
        </div>
        <label v-if="['failure_streak', 'stale_source'].includes(rule.kind)"
          >{{
            rule.kind === "stale_source"
              ? "Minutos sem atualização completa"
              : "Quantidade de falhas consecutivas"
          }}<input
            v-model.number="rule.threshold"
            type="number"
            min="1"
            max="10080"
            required /></label
        ><label v-if="rule.kind === 'new_publication'"
          >Tema ou trecho do título<input
            v-model="rule.topic"
            maxlength="150"
            placeholder="Ex.: computer networks (vazio acompanha todos)"
          /><small
            >Comparação textual com os temas e títulos recebidos da
            fonte.</small
          ></label
        ><label
          >ID do webhook (opcional)<input
            v-model.number="rule.webhook_id"
            type="number"
            min="1"
            placeholder="Sem webhook: notificar apenas no radar" /></label
        ><button class="text-button" type="button" @click="previewRule">
          Testar regra sem executar
        </button>
        <div v-if="preview" class="rule-preview">
          <strong>{{ preview.matched_count }} registros compatíveis</strong>
          <p>{{ preview.explanation }}</p>
          <ul>
            <li v-for="item in preview.samples" :key="item.id">
              {{ item.title }}
            </li>
          </ul>
        </div>
        <Button type="submit" :loading="busy" label="Criar regra" />
      </form>
    </section>
  </div>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Agendamentos</h2></div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>FONTE</th>
            <th>INTERVALO</th>
            <th>PRÓXIMA EXECUÇÃO</th>
            <th>ESTADO</th>
            <th>AÇÃO</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in schedules" :key="s.id">
            <td>{{ s.source.toUpperCase() }}</td>
            <td>{{ s.interval_minutes }} min</td>
            <td>{{ date(s.next_at) }}</td>
            <td>{{ s.enabled ? "Ativo" : "Pausado" }}</td>
            <td>
              <button
                v-if="user.role !== 'viewer'"
                class="text-button"
                @click="toggle('schedules', s.id, s.enabled)"
              >
                {{ s.enabled ? "Pausar" : "Ativar" }}
              </button>
            </td>
          </tr>
          <tr v-if="!schedules.length">
            <td colspan="5" class="empty-cell">Nenhum agendamento criado.</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Regras configuradas</h2></div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>REGRA</th>
            <th>CONDIÇÃO</th>
            <th>FONTE</th>
            <th>DESTINO</th>
            <th>AÇÃO</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rules" :key="r.id">
            <td>
              {{ r.name }}<small>{{ r.enabled ? "Ativa" : "Pausada" }}</small>
            </td>
            <td>
              {{ kinds[r.kind]
              }}<small>{{
                r.topic ||
                (["failure_streak", "stale_source"].includes(r.kind)
                  ? "Limite: " + r.threshold
                  : "")
              }}</small>
            </td>
            <td>{{ r.source }}</td>
            <td>
              {{
                r.webhook_id
                  ? "Radar + webhook #" + r.webhook_id
                  : "Radar interno"
              }}
            </td>
            <td>
              <button
                v-if="user.role !== 'viewer'"
                class="text-button"
                @click="toggle('rules', r.id, r.enabled)"
              >
                {{ r.enabled ? "Pausar" : "Ativar" }}
              </button>
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
