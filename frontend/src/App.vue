<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { useRouter, RouterView } from "vue-router";
import Button from "primevue/button";
import { Network } from "@lucide/vue";
import { refresh } from "./api";
import { useSession } from "./composables/useSession";
import PortalLayout from "./components/PortalLayout.vue";
const {
  demo,
  user,
  setup,
  ready,
  busy,
  error,
  username,
  password,
  signIn: authenticate,
  logout: endSession,
} = useSession();
const notice = ref(""),
  router = useRouter();
function report(message: string) {
  error.value = message;
}
function inform(message = "Operação salva.") {
  notice.value = message;
  refresh();
}
async function signIn() {
  notice.value = "";
  await authenticate();
}
async function logout() {
  notice.value = "";
  if (await endSession()) router.push({ name: "overview" });
}
let timer: ReturnType<typeof setInterval>;
onMounted(() => {
  timer = setInterval(() => {
    if (user.value && document.visibilityState === "visible") refresh();
  }, 15000);
});
onUnmounted(() => clearInterval(timer));
</script>
<template>
  <div v-if="demo" class="demo-banner" role="status">
    Ambiente de demonstração · Dados fictícios · Coletas externas desativadas
  </div>
  <div v-if="!ready" class="login-page" role="status">
    Conectando ao CampusOps…
  </div>
  <div v-else-if="!user" class="login-page">
    <section class="login-card">
      <div class="brand">
        <span class="brand-icon"><Network :size="23" /></span>Campus<span
          >Ops</span
        >
      </div>
      <p class="eyebrow">PORTAL DE PESQUISA ACADÊMICA</p>
      <h1>
        {{ setup ? "Crie seu acesso ao portal." : "Bem-vindo de volta." }}
      </h1>
      <p class="subtitle">
        {{
          setup
            ? "Cadastre a primeira conta para organizar as fontes de pesquisa."
            : "Entre para pesquisar e salvar as informações do seu interesse."
        }}
      </p>
      <div v-if="error" class="alert" role="alert">{{ error }}</div>
      <form class="form-grid" @submit.prevent="signIn">
        <label
          >Usuário<input
            v-model="username"
            autocomplete="username"
            minlength="3"
            maxlength="80"
            pattern="[a-zA-Z0-9_.-]+"
            required /></label
        ><label
          >Senha<input
            v-model="password"
            aria-label="Senha"
            type="password"
            :autocomplete="setup ? 'new-password' : 'current-password'"
            minlength="10"
            maxlength="128"
            required
          /><small>Mínimo de 10 caracteres.</small></label
        ><Button
          type="submit"
          :loading="busy"
          :label="setup ? 'Criar acesso' : 'Entrar'"
        />
      </form>
      <p class="login-foot">
        CampusOps · Consulta a dados acadêmicos de fontes públicas.
      </p>
    </section>
  </div>
  <PortalLayout
    v-else
    :user="user"
    :error="error"
    :notice="notice"
    @logout="logout"
    @clear-error="error = ''"
    @clear-notice="notice = ''"
  >
    <RouterView v-slot="{ Component }"
      ><component
        :is="Component"
        :user="user"
        :mode="$route.name"
        @error="report"
        @notice="inform"
        @navigate="router.push({ name: $event })"
    /></RouterView>
  </PortalLayout>
</template>
