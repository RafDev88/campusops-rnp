<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import Button from "primevue/button";
import { api, date, labels, revision, type User } from "../api";
const props = defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type Hook = { id: number; name: string; url: string; enabled: boolean };
type Delivery = {
  id: number;
  webhook_id: number;
  event_id: number;
  status: string;
  attempts: number;
  message: string;
  next_at: string;
};
type Audit = {
  id: number;
  actor: string;
  action: string;
  created_at: string;
  detail: Record<string, unknown>;
};
const users = ref<User[]>([]),
  hooks = ref<Hook[]>([]),
  deliveries = ref<Delivery[]>([]),
  audit = ref<Audit[]>([]),
  signing = ref(false),
  hosts = ref(""),
  busy = ref(false);
const account = ref({ username: "", password: "", role: "viewer" }),
  hook = ref({ name: "", url: "" });
async function load() {
  try {
    const [u, h, a] = await Promise.all([
      api<User[]>("users"),
      api<{
        items: Hook[];
        deliveries: Delivery[];
        signing_configured: boolean;
        allowed_hosts: string;
      }>("webhooks"),
      api<Audit[]>("audit"),
    ]);
    users.value = u;
    hooks.value = h.items;
    deliveries.value = h.deliveries;
    signing.value = h.signing_configured;
    hosts.value = h.allowed_hosts;
    audit.value = a;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function createUser() {
  busy.value = true;
  try {
    await api("users", "POST", account.value);
    account.value = { username: "", password: "", role: "viewer" };
    emit("notice", "Usuário criado.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function createHook() {
  busy.value = true;
  try {
    await api("webhooks", "POST", hook.value);
    hook.value = { name: "", url: "" };
    emit("notice", "Webhook cadastrado. Vincule seu ID a uma regra.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function toggleUser(user: User) {
  try {
    await api(`users/${user.id}`, "PATCH", { enabled: !user.active });
    emit("notice", "Acesso atualizado.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function toggleHook(h: Hook) {
  try {
    await api(`webhooks/${h.id}/enabled`, "PATCH", { enabled: !h.enabled });
    emit("notice", "Webhook atualizado.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(revision, load);
</script>
<template>
  <div class="two-columns">
    <section class="panel">
      <div class="panel-heading"><h2>Criar acesso</h2></div>
      <form class="form-grid detail-body" @submit.prevent="createUser">
        <label
          >Usuário<input
            v-model="account.username"
            autocomplete="off"
            pattern="[a-zA-Z0-9_.-]+"
            minlength="3"
            maxlength="80"
            required /></label
        ><label
          >Senha inicial<input
            v-model="account.password"
            type="password"
            autocomplete="new-password"
            minlength="10"
            maxlength="128"
            required /></label
        ><label
          >Perfil<select v-model="account.role">
            <option value="viewer">Consulta: leitura dos dados</option>
            <option value="operator">Operador: coletas e automações</option>
            <option value="admin">
              Administrador: usuários e destinos externos
            </option>
          </select></label
        ><Button type="submit" :loading="busy" label="Criar usuário" />
      </form>
    </section>
    <section class="panel">
      <div class="panel-heading"><h2>Cadastrar webhook</h2></div>
      <form class="form-grid detail-body" @submit.prevent="createHook">
        <p class="muted">
          Domínios autorizados: {{ hosts || "Nenhum configurado no servidor" }}.
          Assinatura HMAC: {{ signing ? "configurada" : "não configurada" }}.
        </p>
        <label
          >Nome do destino<input
            v-model="hook.name"
            minlength="3"
            maxlength="100"
            required /></label
        ><label
          >URL HTTPS<input
            v-model="hook.url"
            type="url"
            placeholder="https://dominio-autorizado/eventos"
            required /></label
        ><Button
          type="submit"
          :loading="busy"
          label="Cadastrar destino"
        /><small
          >O servidor valida o domínio e os endereços públicos.
          Redirecionamentos são recusados.</small
        >
      </form>
    </section>
  </div>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Usuários e permissões</h2></div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>USUÁRIO</th>
            <th>PERFIL</th>
            <th>ACESSO</th>
            <th>AÇÃO</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }}</td>
            <td>{{ labels[u.role] }}</td>
            <td>{{ u.active ? "Ativo" : "Desativado" }}</td>
            <td>
              <button
                v-if="u.id !== props.user.id"
                class="text-button"
                @click="toggleUser(u)"
              >
                {{ u.active ? "Desativar" : "Ativar" }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Destinos externos</h2></div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>NOME</th>
            <th>URL</th>
            <th>ESTADO</th>
            <th>AÇÃO</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="h in hooks" :key="h.id">
            <td>#{{ h.id }}</td>
            <td>{{ h.name }}</td>
            <td>{{ h.url }}</td>
            <td>{{ h.enabled ? "Ativo" : "Pausado" }}</td>
            <td>
              <button class="text-button" @click="toggleHook(h)">
                {{ h.enabled ? "Pausar" : "Ativar" }}
              </button>
            </td>
          </tr>
          <tr v-if="!hooks.length">
            <td colspan="5" class="empty-cell">
              Nenhum destino externo cadastrado.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Entregas de webhook</h2></div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>ENTREGA</th>
            <th>DESTINO / EVENTO</th>
            <th>ESTADO</th>
            <th>TENTATIVAS</th>
            <th>RESULTADO</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in deliveries" :key="d.id">
            <td>#{{ d.id }}</td>
            <td>#{{ d.webhook_id }} / #{{ d.event_id }}</td>
            <td>{{ labels[d.status] }}</td>
            <td>{{ d.attempts }}</td>
            <td>{{ d.message || "Aguardando envio" }}</td>
          </tr>
          <tr v-if="!deliveries.length">
            <td colspan="5" class="empty-cell">
              Entregas serão registradas quando uma regra vinculada a webhook
              gerar um evento.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading"><h2>Auditoria recente</h2></div>
    <div class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>DATA</th>
            <th>USUÁRIO</th>
            <th>AÇÃO</th>
            <th>DETALHES</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in audit" :key="a.id">
            <td>{{ date(a.created_at) }}</td>
            <td>{{ a.actor }}</td>
            <td>{{ a.action }}</td>
            <td>{{ JSON.stringify(a.detail) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
