<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { api, labels, revision, type User } from "../api";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Calendar = {
  id: number;
  name: string;
  target: string;
  cron: string;
  timezone: string;
  next_at: string;
  enabled: boolean;
};
const targets: Record<string, string> = {
  source: "Coleta",
  workflow: "Fluxo",
  report: "Relatório",
};
const items = ref<Calendar[]>([]),
  fires = ref<
    {
      id: number;
      schedule_id: number;
      status: string;
      scheduled_at: string;
      job_id: number | null;
      message: string;
    }[]
  >([]);
async function load() {
  try {
    const data = await api<{ items: Calendar[]; fires: typeof fires.value }>(
      "calendar-schedules",
    );
    items.value = data.items;
    fires.value = data.fires;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function toggle(item: Calendar) {
  try {
    await api("calendar-schedules/" + item.id, "PATCH", {
      enabled: !item.enabled,
    });
    await load();
    emit("notice", "Agenda atualizada.");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(revision, load);
</script>
<template>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Agendas por horário</h2></div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>AGENDA</th>
            <th>DESTINO</th>
            <th>PRÓXIMO HORÁRIO</th>
            <th>ESTADO</th>
            <th>AÇÃO</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>
              {{ item.name
              }}<small>{{ item.cron }} · {{ item.timezone }}</small>
            </td>
            <td>{{ targets[item.target] }}</td>
            <td>
              {{
                new Date(item.next_at).toLocaleString("pt-BR", {
                  timeZone: item.timezone,
                })
              }}
            </td>
            <td>{{ item.enabled ? "Ativa" : "Pausada" }}</td>
            <td>
              <button
                v-if="user.role !== 'viewer' || item.target === 'report'"
                class="text-button"
                @click="toggle(item)"
              >
                {{ item.enabled ? "Pausar agenda" : "Ativar agenda" }}
              </button>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="5" class="empty-cell">
              Nenhuma agenda por horário foi criada.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <details v-if="fires.length" class="detail-body">
      <summary>Últimos disparos</summary>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>AGENDA</th>
              <th>HORÁRIO</th>
              <th>RESULTADO</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="fire in fires" :key="fire.id">
              <td>#{{ fire.schedule_id }}</td>
              <td>{{ new Date(fire.scheduled_at).toLocaleString("pt-BR") }}</td>
              <td>
                {{ labels[fire.status] || fire.status
                }}<small>{{ fire.message }}</small>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </details>
  </section>
</template>
