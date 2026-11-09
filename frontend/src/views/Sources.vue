<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import SyncForm from "../components/SyncForm.vue";
import {
  api,
  date,
  labels,
  revision,
  type Run,
  type Source,
  type User,
} from "../api";
defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
type SourceState = {
  id: Source;
  last_run: Run | null;
  last_success: string | null;
  success_rate: number | null;
  average_ms: number | null;
  retries: number;
  sample_size: number;
};
const completeness = ref<{
  total: number;
  available: Record<string, number>;
} | null>(null);
const fieldNames: Record<string, string> = {
  doi: "Com DOI",
  abstract: "Com resumo",
  language: "Com idioma",
  journal: "Com periódico",
  crossref: "Enriquecidas no Crossref",
};
const states = ref<SourceState[]>([]),
  credentials = ref({ openalex: false, orcid: false }),
  selected = ref<Source | null>(null);
const descriptions: Record<
  Source,
  { name: string; text: string; url: string }
> = {
  ror: {
    name: "ROR",
    text: "Cadastro de instituições brasileiras com paginação até o limite configurado.",
    url: "https://ror.readme.io/docs/rest-api",
  },
  openalex: {
    name: "OpenAlex",
    text: "Publicações, temas, acesso aberto e colaboração das instituições acompanhadas.",
    url: "https://help.openalex.org/api/",
  },
  crossref: {
    name: "Crossref",
    text: "Enriquecimento por DOI: títulos, periódicos, financiadores e licenças, quando disponíveis.",
    url: "https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
  },
  orcid: {
    name: "ORCID",
    text: "Consulta individual de perfis públicos. A fonte pode exigir token de acesso.",
    url: "https://info.orcid.org/what-is-orcid/services/public-api/",
  },
  ufrn: {
    name: "Dados Abertos UFRN",
    text: "Catálogo CKAN, formatos e links de arquivos. Detecta alterações nos metadados.",
    url: "https://dados.ufrn.br/",
  },
};
async function load() {
  try {
    const data = await api<{
      items: SourceState[];
      credentials: { openalex: boolean; orcid: boolean };
    }>("sources");
    completeness.value = await api("catalog-coverage");
    states.value = data.items;
    credentials.value = data.credentials;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(revision, load);
</script>
<template>
  <div class="action-row section-gap">
    <RouterLink class="chip-button" :to="{ name: 'monitoring' }"
      >Ver saúde das fontes, HTTPS e links →</RouterLink
    >
  </div>
  <div class="scope-note">
    Indicadores por fonte consideram até 50 execuções. “Parcial” indica que o
    limite de coleta foi atingido ou houve registros rejeitados; os detalhes
    ficam no histórico.
  </div>
  <section v-if="completeness" class="panel section-gap">
    <div class="panel-heading">
      <div>
        <h2>Completude dos metadados</h2>
        <p>
          Campos disponíveis nas {{ completeness.total }} publicações do
          catálogo local. Valores ausentes não são preenchidos por suposição.
        </p>
      </div>
    </div>
    <dl class="coverage-metrics">
      <div v-for="(count, key) in completeness.available" :key="key">
        <dt>{{ fieldNames[key] || key }}</dt>
        <dd>{{ count }} / {{ completeness.total }}</dd>
      </div>
    </dl>
    <p class="detail-body muted">
      Para ampliar a cobertura, ajuste o período e o limite de páginas no
      OpenAlex; depois, enriqueça os DOIs pendentes no Crossref. Consulte os
      detalhes da coleta para conferir a cobertura. Uma janela parcial não
      representa toda a produção de uma instituição.
    </p>
  </section>
  <section class="source-grid section-gap">
    <article
      v-for="source in states"
      :key="source.id"
      class="panel source-card"
    >
      <div class="panel-heading">
        <div>
          <p class="eyebrow">INTEGRAÇÃO</p>
          <h2>{{ descriptions[source.id].name }}</h2>
        </div>
        <span class="badge" :class="source.last_run?.status">{{
          source.last_run ? labels[source.last_run.status] : "Não executada"
        }}</span>
      </div>
      <div class="detail-body">
        <p class="source-description">{{ descriptions[source.id].text }}</p>
        <dl class="source-metrics">
          <div>
            <dt>Último sucesso completo</dt>
            <dd>{{ date(source.last_success) }}</dd>
          </div>
          <div>
            <dt>Taxa de sucesso</dt>
            <dd>
              {{
                source.success_rate === null ? "—" : source.success_rate + "%"
              }}
            </dd>
          </div>
          <div>
            <dt>Duração média / retentativas</dt>
            <dd>
              {{
                source.average_ms === null
                  ? "—"
                  : (source.average_ms / 1000).toFixed(1) + "s"
              }}
              / {{ source.retries }}
            </dd>
          </div>
        </dl>
        <p v-if="source.id === 'openalex'" class="muted">
          {{
            credentials.openalex
              ? "Chave configurada no servidor."
              : "Sem chave: consultas sujeitas à cota pública e limite de paginação básica."
          }}
        </p>
        <p v-if="source.id === 'orcid'" class="muted">
          {{
            credentials.orcid
              ? "Token configurado no servidor."
              : "Token não configurado. Se a fonte exigir autenticação, configure ORCID_ACCESS_TOKEN."
          }}
        </p>
        <div class="action-row">
          <a
            class="text-button"
            :href="descriptions[source.id].url"
            target="_blank"
            rel="noopener noreferrer"
            >Documentação ↗</a
          ><button
            v-if="user.role !== 'viewer'"
            class="chip-button"
            @click="selected = selected === source.id ? null : source.id"
          >
            {{ selected === source.id ? "Fechar" : "Configurar coleta" }}
          </button>
        </div>
        <SyncForm
          v-if="selected === source.id"
          :source="source.id"
          @done="
            selected = null;
            emit('notice', 'Coleta adicionada à fila. Acompanhe em Execuções.');
          "
          @error="emit('error', $event)"
        />
      </div>
    </article>
  </section>
</template>
