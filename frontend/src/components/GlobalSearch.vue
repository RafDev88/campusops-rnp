<script setup lang="ts">
import { onUnmounted, ref, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Search } from "@lucide/vue";
import { api } from "../api";
import { destination, kinds, type SearchResult } from "../discovery";
const emit = defineEmits<{ error: [message: string] }>();
const props = withDefaults(defineProps<{ kind?: string }>(), { kind: "" });
const router = useRouter(),
  q = ref(""),
  suggestions = ref<SearchResult[]>([]),
  opened = ref(false),
  active = ref(-1),
  loading = ref(false);
const route = useRoute();
watch(
  () => route.fullPath,
  () => {
    opened.value = false;
    active.value = -1;
    clearTimeout(timer);
    controller?.abort();
  },
);
let timer: ReturnType<typeof setTimeout>,
  controller: AbortController | undefined;
function changed() {
  clearTimeout(timer);
  controller?.abort();
  active.value = -1;
  if (q.value.trim().length < 2) {
    suggestions.value = [];
    return;
  }
  timer = setTimeout(async () => {
    controller = new AbortController();
    loading.value = true;
    try {
      suggestions.value = await api<SearchResult[]>(
        "search/suggestions?q=" +
          encodeURIComponent(q.value) +
          "&kind=" +
          encodeURIComponent(props.kind),
        "GET",
        undefined,
        controller.signal,
      );
      opened.value = true;
    } catch (e) {
      if ((e as Error).name !== "AbortError")
        emit("error", (e as Error).message);
    } finally {
      loading.value = false;
    }
  }, 250);
}
function select(item: SearchResult) {
  opened.value = false;
  active.value = -1;
  router.push(destination(item));
}
function submit() {
  if (active.value >= 0 && suggestions.value[active.value])
    select(suggestions.value[active.value]);
  else {
    opened.value = false;
    const name =
      props.kind === "publication"
        ? "publications"
        : props.kind === "institution"
          ? "institutions"
          : "search";
    router.push({
      name,
      query: {
        ...(q.value ? { q: q.value } : {}),
        ...(["dataset", "researcher"].includes(props.kind)
          ? { kind: props.kind }
          : {}),
      },
    });
  }
}
watch(
  () => props.kind,
  () => {
    opened.value = false;
    active.value = -1;
    suggestions.value = [];
    clearTimeout(timer);
    controller?.abort();
  },
);
function arrow(step: number) {
  opened.value = true;
  active.value = Math.max(
    -1,
    Math.min(suggestions.value.length - 1, active.value + step),
  );
}
onUnmounted(() => {
  clearTimeout(timer);
  controller?.abort();
});
</script>
<template>
  <form
    class="global-search"
    role="search"
    @submit.prevent="submit"
    @focusout="
      (e) => {
        if (!(e.currentTarget as HTMLElement).contains(e.relatedTarget as Node))
          opened = false;
      }
    "
  >
    <Search :size="18" aria-hidden="true" /><input
      id="catalog-search"
      v-model="q"
      @input="changed"
      @focus="opened = true"
      @keydown.down.prevent="arrow(1)"
      @keydown.up.prevent="arrow(-1)"
      @keydown.esc="
        opened = false;
        active = -1;
      "
      role="combobox"
      aria-label="Pesquisar em todo o catálogo"
      aria-autocomplete="list"
      :aria-expanded="opened && suggestions.length > 0"
      aria-controls="global-suggestions"
      :aria-activedescendant="active >= 0 ? 'suggestion-' + active : undefined"
      placeholder="Busque instituições, publicações, autores ou temas…"
      maxlength="150"
    /><button type="submit" aria-label="Pesquisar no catálogo">
      Pesquisar
    </button>
    <ul
      v-if="opened && suggestions.length"
      id="global-suggestions"
      class="suggestions"
      role="listbox"
    >
      <li
        v-for="(item, i) in suggestions"
        :id="'suggestion-' + i"
        :key="item.kind + item.id"
        role="option"
        :aria-selected="active === i"
        @mousedown.prevent
        @click="select(item)"
      >
        <strong>{{ item.title }}</strong
        ><small>{{ kinds[item.kind] }} · {{ item.source }}</small>
      </li>
    </ul>
    <span v-if="loading" class="sr-only" role="status"
      >Buscando sugestões…</span
    >
  </form>
</template>
