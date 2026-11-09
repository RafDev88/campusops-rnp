<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { revision } from "../api";
import { destination, kinds } from "../discovery";
import { savedSearchDestination } from "../researchFilters";
import {
  useResearchLibrary,
  type SavedResearch,
  type ResearchAlert,
} from "../composables/useResearchLibrary";
import ConfirmDialog from "../components/ConfirmDialog.vue";
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
const route = useRoute(),
  router = useRouter(),
  library = useResearchLibrary();
const { saved, favorites, favoriteCount, alerts, loading, error } = library;
const section = computed(() =>
  ["saved", "favorites", "alerts"].includes(String(route.query.section))
    ? String(route.query.section)
    : "saved",
);
const removing = ref<SavedResearch | null>(null),
  busy = ref(false),
  unread = computed(() => alerts.value.filter((a) => !a.read).length);
async function remove() {
  if (!removing.value) return;
  busy.value = true;
  try {
    await library.removeSaved(removing.value.id);
    removing.value = null;
    emit("notice", "Pesquisa removida. Seus favoritos continuam guardados.");
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = false;
  }
}
async function openAlert(item: ResearchAlert) {
  try {
    await library.readAlert(item.id);
    router.push({
      name: "publications",
      query: { publication: item.publication_id },
    });
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
watch(revision, library.load);
onMounted(library.load);
</script>
<template>
  <p class="personal-scope">
    Esta área é só sua. Os favoritos e as pesquisas de outras pessoas ficam nas
    contas delas.
  </p>
  <div class="library-tabs" role="group" aria-label="Escolher meus itens">
    <button
      v-for="tab in [
        { id: 'saved', label: 'Pesquisas salvas', count: saved.length },
        { id: 'favorites', label: 'Favoritos', count: favoriteCount },
        { id: 'alerts', label: 'Novidades', count: unread },
      ]"
      :key="tab.id"
      :aria-pressed="section === tab.id"
      :class="{ active: section === tab.id }"
      @click="router.push({ query: { section: tab.id } })"
    >
      {{ tab.label }} <span>{{ tab.count }}</span>
    </button>
  </div>
  <div v-if="error" class="alert" role="alert">
    <span>{{ error }}</span
    ><button class="text-button" @click="library.load">Tentar novamente</button>
  </div>
  <p v-if="loading" class="loading-strip" role="status">
    Carregando suas pesquisas…
  </p>
  <section v-if="section === 'saved'" class="panel library-panel">
    <div class="panel-heading">
      <div>
        <h2>Continue uma pesquisa</h2>
        <p>
          Os assuntos e filtros que você escolheu, prontos para usar de novo.
        </p>
      </div>
      <RouterLink class="chip-button" to="/publications"
        >Fazer nova pesquisa</RouterLink
      >
    </div>
    <article v-for="item in saved" :key="item.id" class="library-item">
      <div>
        <button
          class="row-title"
          @click="router.push(savedSearchDestination(item.filters))"
        >
          {{ item.name }}
        </button>
        <p>
          {{
            item.alerts_enabled
              ? "Você receberá novidades quando as próximas atualizações encontrarem novos resultados."
              : "Filtros salvos para consultar quando quiser."
          }}
        </p>
      </div>
      <div class="action-row">
        <button
          class="chip-button"
          @click="router.push(savedSearchDestination(item.filters))"
        >
          Continuar pesquisa →</button
        ><button
          class="text-button"
          :aria-label="'Remover pesquisa ' + item.name"
          @click="removing = item"
        >
          Remover
        </button>
      </div>
    </article>
    <div v-if="!loading && !saved.length && !error" class="friendly-empty">
      <span aria-hidden="true">⌕</span>
      <h3>Sua próxima pesquisa pode começar aqui.</h3>
      <p>
        Na página Publicações, escolha um assunto e clique em Salvar pesquisa.
        Assim, você volta aos mesmos filtros sem precisar começar de novo.
      </p>
      <RouterLink class="primary-action" to="/publications"
        >Pesquisar publicações →</RouterLink
      >
    </div>
  </section>
  <section v-else-if="section === 'favorites'" class="panel library-panel">
    <div class="panel-heading">
      <div>
        <h2>Informações que você guardou</h2>
        <p>
          Use a estrela ao lado de um resultado para encontrá-lo aqui depois.
        </p>
      </div>
      <RouterLink
        class="text-button"
        :to="{ name: 'search', query: { favorites: 'true' } }"
        >Ver todos os favoritos →</RouterLink
      >
    </div>
    <article
      v-for="item in favorites"
      :key="item.kind + item.id"
      class="library-item"
    >
      <div>
        <small>{{ kinds[item.kind] }} · {{ item.source }}</small
        ><RouterLink class="row-title" :to="destination(item)">{{
          item.title
        }}</RouterLink>
        <p>{{ item.subtitle }}</p>
      </div>
      <RouterLink class="chip-button" :to="destination(item)"
        >Abrir detalhes →</RouterLink
      >
    </article>
    <div v-if="!loading && !favorites.length && !error" class="friendly-empty">
      <span aria-hidden="true">☆</span>
      <h3>Guarde o que for importante para você.</h3>
      <p>
        Encontre uma informação e use a estrela para adicioná-la aos seus
        favoritos.
      </p>
      <RouterLink class="primary-action" to="/search"
        >Encontrar informações →</RouterLink
      >
    </div>
  </section>
  <section v-else class="panel library-panel">
    <div class="panel-heading">
      <div>
        <h2>Novidades para você</h2>
        <p>
          Novos trabalhos encontrados para as pesquisas em que você ativou os
          avisos.
        </p>
      </div>
    </div>
    <article v-for="item in alerts" :key="item.id" class="library-item">
      <div>
        <small
          >{{ item.search_name }} ·
          {{ item.read ? "Já consultado" : "Ainda não consultado" }}</small
        ><button class="row-title" @click="openAlert(item)">
          {{ item.title }}
        </button>
      </div>
      <button class="chip-button" @click="openAlert(item)">
        Conhecer publicação →
      </button>
    </article>
    <div v-if="!loading && !alerts.length && !error" class="friendly-empty">
      <h3>As novidades aparecerão aqui.</h3>
      <p>
        Ao salvar uma pesquisa, marque a opção de receber avisos. Os resultados
        encontrados nas próximas atualizações serão reunidos nesta área.
      </p>
      <RouterLink class="text-button" to="/publications"
        >Criar uma pesquisa com avisos →</RouterLink
      >
    </div>
  </section>
  <div class="library-report-link">
    <div>
      <h2>Precisa de um arquivo para consultar depois?</h2>
      <p>Gere uma planilha a partir de uma pesquisa salva.</p>
    </div>
    <RouterLink class="chip-button" to="/reports"
      >Abrir relatórios →</RouterLink
    >
  </div>
  <ConfirmDialog
    :open="!!removing"
    title="Remover esta pesquisa salva?"
    :description="
      'A pesquisa ' +
      (removing?.name || '') +
      ' e os avisos associados serão removidos. Os registros do catálogo e seus favoritos serão preservados.'
    "
    confirm-label="Remover pesquisa"
    :busy="busy"
    @cancel="removing = null"
    @confirm="remove"
  />
</template>
