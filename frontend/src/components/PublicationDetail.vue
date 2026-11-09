<script setup lang="ts">
import HelpHint from "./HelpHint.vue";
import { useRouter } from "vue-router";
import { languages, workTypes } from "../discovery";
import {
  api,
  date,
  safeUrl,
  refresh,
  type Publication,
  type User,
} from "../api";
const props = defineProps<{ item: Publication; user: User }>();
const emit = defineEmits<{
  close: [];
  error: [message: string];
  notice: [message: string];
}>();
const router = useRouter();
async function favorite() {
  try {
    await api("favorites", "POST", {
      kind: "publication",
      entity_id: props.item.id,
      enabled: !props.item.favorite,
    });
    refresh();
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function orcid(id: string) {
  try {
    await api("sync", "POST", { source: "orcid", orcid: id.split("/").pop() });
    emit("notice", "Consulta ORCID adicionada à fila.");
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
</script>
<template>
  <section class="panel detail-panel publication-detail">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">FICHA DA PUBLICAÇÃO</p>
        <h2>{{ item.title }}</h2>
        <p>{{ item.source }} · Atualizado em {{ date(item.fetched_at) }}</p>
      </div>
      <button class="text-button" @click="emit('close')">
        Fechar publicação
      </button>
    </div>
    <div class="detail-body">
      <p v-if="item.is_retracted" class="scope-note retraction-note">
        A fonte sinaliza esta publicação como retratada. Consulte o registro
        original e o aviso de retratação antes de utilizar o trabalho.
      </p>
      <div class="action-row">
        <span class="badge">{{ item.year || "Ano não informado" }}</span
        ><span class="badge">{{
          item.is_oa ? "Acesso aberto" : "Acesso aberto não identificado"
        }}</span
        ><span class="muted">{{ item.citations }} citações na fonte</span
        ><button
          class="favorite-button"
          :aria-pressed="item.favorite"
          @click="favorite"
        >
          {{ item.favorite ? "★ Favorito" : "☆ Favoritar" }}
        </button>
      </div>
      <p v-if="item.doi">
        <a
          class="text-button"
          :href="safeUrl('https://doi.org/' + item.doi)"
          target="_blank"
          rel="noopener noreferrer"
          >DOI: {{ item.doi }} ↗</a
        >
      </p>
      <dl class="bibliographic-facts">
        <div>
          <dt>Idioma dos metadados</dt>
          <dd>
            {{
              languages[item.language || ""] || item.language || "Não informado"
            }}
          </dd>
        </div>
        <div>
          <dt>Tipo de publicação</dt>
          <dd>
            {{
              workTypes[item.work_type || ""] ||
              item.work_type ||
              "Não informado"
            }}
          </dd>
        </div>
        <div>
          <dt>Data da publicação</dt>
          <dd>{{ item.publication_date || "Não informada" }}</dd>
        </div>
        <div>
          <dt>ISSN</dt>
          <dd>{{ item.issn?.join(", ") || "Não informado" }}</dd>
        </div>
      </dl>
      <div class="action-row">
        <a
          v-if="item.landing_url"
          class="text-button"
          :href="safeUrl(item.landing_url)"
          target="_blank"
          rel="noopener noreferrer"
          >Abrir página na fonte ↗</a
        ><a
          v-if="item.pdf_url"
          class="text-button"
          :href="safeUrl(item.pdf_url)"
          target="_blank"
          rel="noopener noreferrer"
          >Consultar PDF indicado pela fonte ↗</a
        >
      </div>
      <RouterLink
        class="text-button"
        :to="{ name: 'changes', query: { entity_id: item.id } }"
        >Histórico de alterações desta publicação →</RouterLink
      >
      <div class="detail-section-title">
        <h3>Resumo</h3>
        <HelpHint
          label="O que é um resumo?"
          text="É um texto curto que apresenta a pergunta, os métodos e as principais conclusões do trabalho. Quando não está disponível nas fontes, o portal informa a ausência."
        />
      </div>
      <p class="abstract-text">
        {{
          item.abstract ||
          "Resumo não disponibilizado nos metadados importados."
        }}
      </p>
      <h3>Temas relacionados</h3>
      <div class="tag-row">
        <button
          v-for="t in item.topics"
          :key="t.id"
          class="chip-button"
          @click="router.push({ name: 'publications', query: { topic: t.id } })"
        >
          {{ t.name }} →</button
        ><span v-if="!item.topics.length" class="muted"
          >Temas não informados.</span
        >
      </div>
      <h3>Autores e identificadores públicos</h3>
      <div class="author-list">
        <div v-for="(a, i) in item.authors" :key="i">
          <RouterLink :to="{ name: 'researchers', query: { id: a.id } }"
            >{{ a.name }} →</RouterLink
          ><a
            v-if="a.orcid"
            :href="safeUrl(a.orcid)"
            target="_blank"
            rel="noopener noreferrer"
            >ORCID ↗</a
          ><button
            v-if="a.orcid && user.role !== 'viewer'"
            class="text-button"
            @click="orcid(a.orcid)"
          >
            Consultar perfil público
          </button>
        </div>
        <p v-if="!item.authors.length" class="muted">Autores não informados.</p>
      </div>
      <h3>Instituições relacionadas</h3>
      <div class="tag-row">
        <RouterLink
          v-for="(a, i) in item.affiliations"
          :key="i"
          class="chip-button"
          :to="{
            name: 'publications',
            query: { institution_id: a.ror || ('id' in a ? String(a.id) : '') },
          }"
          >{{ a.name }} →</RouterLink
        ><span v-if="!item.affiliations.length" class="muted"
          >Afiliações não informadas.</span
        >
      </div>
      <div class="metadata-grid">
        <section>
          <h3>Periódico e editora</h3>
          <p>
            {{ item.journal || "Periódico não informado" }}<br />{{
              item.publisher || "Editora não informada"
            }}
          </p>
        </section>
        <section>
          <h3>Financiamento informado</h3>
          <ul v-if="item.funders?.length">
            <li v-for="name in item.funders" :key="name">{{ name }}</li>
          </ul>
          <p v-else class="muted">Financiadores não informados.</p>
        </section>
        <section>
          <h3>Licenças informadas</h3>
          <ul v-if="item.licenses?.length">
            <li v-for="url in item.licenses" :key="url">
              <a
                v-if="url.startsWith('https://') || url.startsWith('http://')"
                :href="safeUrl(url)"
                target="_blank"
                rel="noopener noreferrer"
                >{{ url }} ↗</a
              >
              <span v-else>{{ url }}</span>
            </li>
          </ul>
          <p v-else class="muted">Licença não informada nos metadados.</p>
        </section>
      </div>
      <p class="scope-note">
        Os campos refletem os metadados disponíveis em cada fonte. Uma
        informação ausente pode não ter sido publicada ou importada.
        Enriquecimento Crossref: {{ date(item.crossref_at) }}.
      </p>
    </div>
  </section>
</template>
