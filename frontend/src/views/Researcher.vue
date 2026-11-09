<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, date, revision, type Publication, type User } from "../api";
import { value } from "../discovery";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
const route = useRoute(),
  router = useRouter(),
  loading = ref(true),
  q = ref(""),
  orcid = ref("");
type Profile = {
  id: string;
  name: string;
  orcid: string | null;
  identity_confirmed: boolean;
  public_profile_imported: boolean;
  employments: { organization: string; role: string; department: string }[];
  educations: { organization: string; role: string; department: string }[];
  works: Publication[];
  fetched_at: string | null;
  scope: string;
};
const profile = ref<Profile | null>(null),
  list = ref<{ orcid: string; name: string; fetched_at: string }[]>([]);
const filtered = computed(() =>
  list.value.filter((p) =>
    p.name.toLocaleLowerCase().includes(q.value.toLocaleLowerCase()),
  ),
);
let controller: AbortController | undefined;
async function load() {
  controller?.abort();
  controller = new AbortController();
  loading.value = true;
  try {
    if (value(route.query, "id"))
      profile.value = await api<Profile>(
        "researcher-profile?id=" + encodeURIComponent(value(route.query, "id")),
        "GET",
        undefined,
        controller.signal,
      );
    else {
      profile.value = null;
      list.value = await api<typeof list.value>(
        "researchers",
        "GET",
        undefined,
        controller.signal,
      );
    }
  } catch (e) {
    if ((e as Error).name !== "AbortError") emit("error", (e as Error).message);
  } finally {
    loading.value = false;
  }
}
async function collect(id: string) {
  try {
    await api("sync", "POST", { source: "orcid", orcid: id });
    emit("notice", "Perfil público adicionado à fila de consulta.");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(() => route.query, load);
watch(revision, load);
onUnmounted(() => controller?.abort());
</script>
<template>
  <p v-if="loading" role="status">Carregando pesquisadores…</p>
  <section v-if="profile" class="panel researcher-profile">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">PERFIL DO PESQUISADOR</p>
        <h2>{{ profile.name }}</h2>
        <p>
          {{
            profile.orcid || "Identidade individual não confirmada por ORCID"
          }}
        </p>
      </div>
      <RouterLink :to="{ name: 'researchers' }" class="text-button"
        >Ver pesquisadores</RouterLink
      >
    </div>
    <div class="detail-body">
      <p class="scope-note">
        {{ profile.scope
        }}<span v-if="!profile.identity_confirmed"
          >Este registro representa uma autoria em uma publicação. Nomes
          semelhantes não foram unidos automaticamente.</span
        >
      </p>
      <div class="action-row">
        <a
          v-if="profile.orcid"
          class="text-button"
          :href="'https://orcid.org/' + profile.orcid"
          target="_blank"
          rel="noopener noreferrer"
          >Abrir ORCID ↗</a
        ><button
          v-if="profile.orcid && user.role !== 'viewer'"
          class="chip-button"
          @click="collect(profile.orcid)"
        >
          {{
            profile.public_profile_imported
              ? "Atualizar registro público"
              : "Consultar vínculos no ORCID"
          }}</button
        ><small>Coleta ORCID: {{ date(profile.fetched_at) }}</small>
      </div>
      <div class="two-columns">
        <section>
          <h3>Vínculos profissionais públicos</h3>
          <article
            v-for="(a, i) in profile.employments"
            :key="i"
            class="affiliation-card"
          >
            <strong>{{ a.organization }}</strong>
            <p>{{ [a.role, a.department].filter(Boolean).join(" · ") }}</p>
            <RouterLink
              :to="{
                name: 'search',
                query: { q: a.organization, kind: 'institution' },
              }"
              class="text-button"
              >Pesquisar instituição →</RouterLink
            >
          </article>
          <p v-if="!profile.employments.length" class="muted">
            Nenhum vínculo disponível nos dados públicos consultados.
          </p>
        </section>
        <section>
          <h3>Formação informada</h3>
          <article
            v-for="(a, i) in profile.educations"
            :key="i"
            class="affiliation-card"
          >
            <strong>{{ a.organization }}</strong>
            <p>{{ [a.role, a.department].filter(Boolean).join(" · ") }}</p>
          </article>
          <p v-if="!profile.educations.length" class="muted">
            Formação não disponibilizada nos dados consultados.
          </p>
        </section>
      </div>
      <h3>Publicações relacionadas no catálogo</h3>
      <article
        v-for="work in profile.works"
        :key="work.id"
        class="related-work"
      >
        <RouterLink
          :to="{
            name: 'publications',
            query: { publication: work.id, author_id: profile.id },
          }"
          >{{ work.title }} →</RouterLink
        ><small>{{ work.year }} · {{ work.source }}</small>
      </article>
      <p v-if="!profile.works.length" class="muted">
        Nenhum trabalho relacionado foi importado até o momento.
      </p>
      <RouterLink
        :to="{ name: 'publications', query: { author_id: profile.id } }"
        class="text-button"
        >Pesquisar todas as publicações desta autoria →</RouterLink
      >
    </div>
  </section>
  <template v-else-if="!loading"
    ><form
      v-if="user.role !== 'viewer'"
      class="filter-row panel padded section-gap"
      @submit.prevent="collect(orcid)"
    >
      <label
        >Consultar pesquisador por ORCID<input
          v-model="orcid"
          placeholder="0000-0000-0000-000X"
          required
          pattern="[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]" /></label
      ><button class="primary-action">Consultar registro público</button>
    </form>
    <section class="panel section-gap">
      <div class="panel-heading">
        <h2>Perfis públicos consultados</h2>
        <input
          v-model="q"
          aria-label="Buscar pesquisador"
          placeholder="Buscar pesquisador"
        />
      </div>
      <article v-for="p in filtered" :key="p.orcid" class="catalog-item">
        <h3>
          <RouterLink
            :to="{ name: 'researchers', query: { id: 'orcid:' + p.orcid } }"
            >{{ p.name }} →</RouterLink
          >
        </h3>
        <small>{{ p.orcid }} · {{ date(p.fetched_at) }}</small>
      </article>
      <p v-if="!filtered.length" class="empty-cell">
        Nenhum perfil público encontrado. Explore autores das publicações ou use
        a busca global.
      </p>
      <p class="scope-caption">
        A busca global também encontra autorias do OpenAlex cujo perfil ORCID
        ainda não foi consultado.
      </p>
    </section></template
  >
</template>
