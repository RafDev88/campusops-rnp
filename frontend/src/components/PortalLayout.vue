<script setup lang="ts">
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  BookOpen,
  LogOut,
  Search,
  FolderHeart,
  ChevronDown,
} from "@lucide/vue";
import { labels, type User } from "../api";
import { pages, pageByName, managementGroups } from "../navigation";
import ContextHelp from "./ContextHelp.vue";
const props = defineProps<{ user: User; error: string; notice: string }>();
const emit = defineEmits<{ logout: []; clearError: []; clearNotice: [] }>();
const route = useRoute(),
  router = useRouter(),
  current = computed(() => pageByName(route.name)),
  managementOpen = ref(current.value.group !== "consult");
const primary = [
  "overview",
  "search",
  "institutions",
  "publications",
  "my-research",
  "help",
];
const moreMenu = ref<HTMLDetailsElement | null>(null);
function closeMore(restore = false) {
  moreMenu.value?.removeAttribute("open");
  if (restore) moreMenu.value?.querySelector("summary")?.focus();
}
function outside(event: PointerEvent) {
  if (moreMenu.value?.open && !moreMenu.value.contains(event.target as Node))
    closeMore();
}
onMounted(() => document.addEventListener("pointerdown", outside));
onUnmounted(() => document.removeEventListener("pointerdown", outside));
const primaryPages = computed(() => primary.map((id) => pageByName(id)));
const morePages = pages.filter((p) =>
  ["researchers", "datasets", "reports", "account"].includes(p.id),
);
const visibleGroups = computed(() =>
  managementGroups
    .map((group) => ({
      ...group,
      pages: pages.filter(
        (p) =>
          p.group === group.id &&
          (p.group !== "admin" || props.user.role === "admin"),
      ),
    }))
    .filter((group) => group.pages.length),
);
watch(
  () => route.name,
  () => {
    if (current.value.group !== "consult") managementOpen.value = true;
    emit("clearError");
    emit("clearNotice");
    document.title = current.value.label + " · CampusOps";
    closeMore();
    nextTick(() =>
      document.getElementById("conteudo")?.focus({ preventScroll: true }),
    );
  },
  { immediate: true },
);
function navigate(id: string) {
  router.push({ name: id });
}
</script>
<template>
  <div class="shell portal portal-friendly">
    <a class="skip-link" href="#conteudo">Ir para o conteúdo</a>
    <div class="portal-topline">
      <div class="portal-width">
        <span>CampusOps · Portal de pesquisa acadêmica</span
        ><span>Informações de fontes públicas</span>
      </div>
    </div>
    <header class="portal-header">
      <div class="portal-width portal-brand-row">
        <RouterLink
          class="portal-brand"
          to="/"
          aria-label="CampusOps, página inicial"
          ><span class="portal-symbol"><BookOpen :size="25" /></span
          ><span
            >CampusOps<small
              >Encontre. Entenda. Continue sua pesquisa.</small
            ></span
          ></RouterLink
        >
        <div class="portal-account">
          <span
            >{{ user.username }}<small>{{ labels[user.role] }}</small></span
          ><button
            class="text-button"
            @click="emit('logout')"
            aria-label="Sair da conta"
          >
            <LogOut :size="17" /> Sair
          </button>
        </div>
      </div>
      <div class="portal-nav-wrap">
        <nav class="portal-width portal-nav" aria-label="Navegação principal">
          <button
            v-for="page in primaryPages"
            :key="page.id"
            :aria-current="route.name === page.id ? 'page' : undefined"
            :class="{ active: route.name === page.id }"
            @click="navigate(page.id)"
          >
            <Search v-if="page.id === 'search'" :size="16" /><FolderHeart
              v-if="page.id === 'my-research'"
              :size="16"
            />{{ page.label }}
          </button>
          <details
            ref="moreMenu"
            class="explore-menu"
            @keydown.esc.prevent="closeMore(true)"
          >
            <summary
              :class="{ active: morePages.some((p) => p.id === route.name) }"
            >
              Outras consultas <ChevronDown :size="14" />
            </summary>
            <div>
              <button
                v-for="page in morePages"
                :key="page.id"
                @click="
                  navigate(page.id);
                  ($event.currentTarget as HTMLElement)
                    .closest('details')
                    ?.removeAttribute('open');
                "
              >
                {{ page.label }}
              </button>
            </div>
          </details>
        </nav>
      </div>
    </header>
    <div class="portal-width management-wrap">
      <details
        class="management-menu"
        :open="managementOpen"
        @toggle="managementOpen = ($event.target as HTMLDetailsElement).open"
      >
        <summary>
          Gestão de dados
          <span>Para quem atualiza e acompanha o funcionamento do portal</span>
        </summary>
        <nav
          aria-label="Gestão de dados"
          class="management-nav management-groups"
        >
          <section v-for="group in visibleGroups" :key="group.id">
            <h2>{{ group.title }}</h2>
            <p>{{ group.description }}</p>
            <div>
              <button
                v-for="page in group.pages"
                :key="page.id"
                :class="{ active: route.name === page.id }"
                :aria-current="route.name === page.id ? 'page' : undefined"
                @click="navigate(page.id)"
              >
                {{ page.label }}
              </button>
            </div>
          </section>
        </nav>
      </details>
    </div>
    <main id="conteudo" class="portal-width" tabindex="-1">
      <nav class="portal-breadcrumb" aria-label="Caminho da página">
        <RouterLink to="/">Início</RouterLink
        ><span v-if="route.name !== 'overview'" aria-hidden="true">/</span
        ><span v-if="route.name !== 'overview'" aria-current="page">{{
          current.label
        }}</span>
      </nav>
      <section
        v-if="route.name !== 'overview'"
        class="page-heading friendly-heading"
      >
        <div>
          <p class="page-category">
            {{
              current.group === "consult"
                ? "CONSULTAR INFORMAÇÕES"
                : "GESTÃO DO PORTAL"
            }}
          </p>
          <h1>{{ current.label }}</h1>
          <p class="subtitle">{{ current.description }}</p>
        </div>
        <ContextHelp :key="current.id" :page="current.id" />
      </section>
      <div v-if="error" class="alert" role="alert">
        <span>{{ error }}</span
        ><button
          @click="emit('clearError')"
          aria-label="Fechar mensagem de erro"
        >
          Fechar
        </button>
      </div>
      <div v-if="notice" class="notice" role="status">
        <span>{{ notice }}</span
        ><button @click="emit('clearNotice')" aria-label="Fechar confirmação">
          Fechar
        </button>
      </div>
      <slot />
      <footer class="portal-footer">
        <div>
          <strong>CampusOps</strong>
          <p>Informações acadêmicas para apoiar sua pesquisa.</p>
          <small
            >Os resultados dependem das fontes e dos dados disponíveis no
            catálogo. Este projeto não é um portal oficial do governo.</small
          >
        </div>
        <div class="footer-links">
          <RouterLink to="/help">Precisa de ajuda? →</RouterLink
          ><RouterLink to="/my-research"
            >Voltar às minhas pesquisas →</RouterLink
          >
        </div>
      </footer>
    </main>
  </div>
</template>
