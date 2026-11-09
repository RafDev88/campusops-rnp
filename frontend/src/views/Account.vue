<script setup lang="ts">
import { onMounted, ref } from "vue";
import { api, advanceSession, date, type User } from "../api";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
const sessions = ref<{ id: string; current: boolean; expires_at: string }[]>(
  [],
);
const currentPassword = ref(""),
  newPassword = ref(""),
  confirmation = ref(""),
  busy = ref(false);
async function load() {
  try {
    sessions.value = (
      await api<{ items: typeof sessions.value }>("account/sessions")
    ).items;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function revoke(id: string) {
  busy.value = true;
  try {
    await api(`account/sessions/${id}`, "DELETE");
    await load();
    emit("notice", "Sessão encerrada.");
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function password() {
  if (newPassword.value !== confirmation.value) {
    emit("error", "As novas senhas precisam ser iguais.");
    return;
  }
  busy.value = true;
  try {
    await api("account/password", "POST", {
      current_password: currentPassword.value,
      new_password: newPassword.value,
    });
    advanceSession();
    emit("notice", "Senha alterada. As outras sessões foram encerradas.");
    await load();
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
    currentPassword.value = "";
    newPassword.value = "";
    confirmation.value = "";
  }
}
onMounted(load);
</script>
<template>
  <section class="panel">
    <h2>Minha conta · {{ user.username }}</h2>
    <p>
      Altere sua senha e encerre acessos que você não está usando. As senhas não
      são guardadas no navegador.
    </p>
    <form class="account-password-form" @submit.prevent="password">
      <label
        >Senha atual<input
          v-model="currentPassword"
          type="password"
          autocomplete="current-password"
          minlength="10"
          maxlength="128"
          required
      /></label>
      <label
        >Nova senha<input
          v-model="newPassword"
          type="password"
          autocomplete="new-password"
          minlength="10"
          maxlength="128"
          aria-describedby="password-guidance"
          required
      /></label>
      <p id="password-guidance">
        Use uma senha exclusiva com pelo menos 10 caracteres. A alteração
        encerra as sessões anteriores.
      </p>
      <label
        >Confirmar nova senha<input
          v-model="confirmation"
          type="password"
          autocomplete="new-password"
          minlength="10"
          maxlength="128"
          required
      /></label>
      <button class="primary-action" :disabled="busy">
        {{ busy ? "Aguarde…" : "Alterar senha" }}
      </button>
    </form>
  </section>
  <section class="panel">
    <h2>Sessões ativas</h2>
    <ul class="operation-summary-list">
      <li v-for="session in sessions" :key="session.id">
        <strong>{{ session.current ? "Este acesso" : "Outro acesso" }}</strong>
        <span>Expira em {{ date(session.expires_at) }}</span>
        <button
          v-if="!session.current"
          class="text-button"
          :disabled="busy"
          @click="revoke(session.id)"
        >
          Encerrar este acesso
        </button>
      </li>
    </ul>
    <p>
      A lista não identifica dispositivo ou localização. Para encerrar este
      acesso, use Sair.
    </p>
  </section>
</template>
