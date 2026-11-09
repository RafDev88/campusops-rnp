<script setup lang="ts">
import { languages, workTypes } from "../discovery";
import { date, type Publication } from "../api";
defineProps<{ items: Publication[]; loading: boolean }>();
const emit = defineEmits<{
  open: [item: Publication];
  favorite: [item: Publication];
  topic: [id: string];
}>();
</script>
<template>
  <div class="publication-card-list" :aria-busy="loading">
    <article v-for="item in items" :key="item.id" class="publication-card">
      <div class="publication-card-top">
        <div class="tag-row">
          <span class="result-kind">{{
            workTypes[item.work_type || ""] || "Publicação científica"
          }}</span
          ><span>{{ item.year || "Ano não informado" }}</span
          ><span v-if="item.language">{{
            languages[item.language] || item.language
          }}</span>
        </div>
        <button
          class="save-result"
          :aria-pressed="item.favorite"
          :aria-label="
            (item.favorite ? 'Remover dos favoritos: ' : 'Favoritar: ') +
            item.title
          "
          @click="emit('favorite', item)"
        >
          <span aria-hidden="true">{{ item.favorite ? "★" : "☆" }}</span>
          {{ item.favorite ? "Salvo" : "Salvar" }}
        </button>
      </div>
      <h3>
        <button class="row-title" @click="emit('open', item)">
          {{ item.title }}
        </button>
      </h3>
      <p v-if="item.authors.length" class="result-authors">
        {{
          item.authors
            .slice(0, 3)
            .map((a) => a.name)
            .join(" · ")
        }}<span v-if="item.authors.length > 3">
          e mais {{ item.authors.length - 3 }}</span
        >
      </p>
      <p v-if="item.journal" class="result-journal">{{ item.journal }}</p>
      <p v-if="item.abstract_preview" class="result-preview">
        {{ item.abstract_preview }}
      </p>
      <p v-else class="result-preview muted">
        Abra os detalhes para conhecer as informações disponíveis e consultar a
        fonte.
      </p>
      <p v-if="item.is_retracted" class="result-retraction">
        A fonte indica retratação deste trabalho. Consulte o aviso nos detalhes.
      </p>
      <div class="result-topics">
        <button
          v-for="topic in item.topics.slice(0, 2)"
          :key="topic.id"
          class="text-button"
          @click="emit('topic', topic.id)"
        >
          {{ topic.name }} →
        </button>
      </div>
      <div class="publication-card-footer">
        <div>
          <span class="access-label" :class="{ open: item.is_oa }">{{
            item.is_oa
              ? "Leitura gratuita identificada"
              : "Leitura gratuita não identificada"
          }}</span
          ><small
            >Fonte: {{ item.source }} · Atualizado em
            {{ date(item.fetched_at) }}</small
          >
        </div>
        <button
          class="chip-button"
          :aria-label="'Ver detalhes de ' + item.title"
          @click="emit('open', item)"
        >
          Ver detalhes →
        </button>
      </div>
    </article>
  </div>
</template>
