<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import Pager from "../components/Pager.vue";
import { api, date, revision, type Event, type Page } from "../api";
const emit = defineEmits<{ error: [message: string] }>();
type Digest = {
  period_from: string;
  period_to: string;
  updated_publications: number;
  open_access: number;
  topics: [string, number][];
  scope: string;
};
const digest = ref<Digest | null>(null),
  events = ref<Page<Event>>({ total: 0, items: [] }),
  offset = ref(0);
async function load() {
  try {
    [digest.value, events.value] = await Promise.all([
      api<Digest>("digest"),
      api<Page<Event>>("events?offset=" + offset.value),
    ]);
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
onMounted(load);
watch(revision, load);
watch(offset, load);
</script>
<template>
  <section v-if="digest" class="panel detail-panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">RESUMO DOS ÚLTIMOS SETE DIAS</p>
        <h2>O que mudou no seu catálogo</h2>
        <p>{{ date(digest.period_from) }} — {{ date(digest.period_to) }}</p>
      </div>
    </div>
    <div class="detail-body">
      <div class="stats compact-stats">
        <article>
          <div>Publicações coletadas / atualizadas</div>
          <strong>{{ digest.updated_publications }}</strong>
        </article>
        <article>
          <div>Com acesso aberto identificado</div>
          <strong>{{ digest.open_access }}</strong>
        </article>
      </div>
      <p class="scope-note">{{ digest.scope }}</p>
      <h3>Temas presentes na coleta</h3>
      <div class="tag-row">
        <span class="badge" v-for="[topic, count] in digest.topics" :key="topic"
          >{{ topic }} · {{ count }}</span
        ><span v-if="!digest.topics.length" class="muted"
          >Sem dados no período.</span
        >
      </div>
    </div>
  </section>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <h2>
          Radar de eventos <span class="count">{{ events.total }}</span>
        </h2>
        <p>Novas publicações, mudanças no catálogo e alertas das regras.</p>
      </div>
    </div>
    <article v-for="event in events.items" :key="event.id" class="feed-item">
      <span class="badge">{{ event.kind }}</span>
      <div>
        <strong>{{ event.title }}</strong
        ><small>{{ date(event.created_at) }}</small>
        <details>
          <summary>Detalhes do evento</summary>
          <pre>{{ JSON.stringify(event.payload, null, 2) }}</pre>
        </details>
      </div>
    </article>
    <p v-if="!events.items.length" class="empty-cell">
      Crie uma regra de nova publicação ou alteração de dados para alimentar o
      radar.
    </p>
    <Pager :total="events.total" :offset="offset" @change="offset = $event" />
  </section>
</template>
