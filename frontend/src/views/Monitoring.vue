<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api, date, revision, safeUrl, type User, type Page } from "../api";
import Pager from "../components/Pager.vue";
import {
  monitorKinds,
  monitorStates,
  monitorTone,
  type MonitorTarget,
  type MonitorCheck,
} from "../monitoring";
const props = defineProps<{ user: User }>();
const emit = defineEmits<{
  error: [message: string];
  notice: [message: string];
}>();
const route = useRoute(),
  router = useRouter();
const q = ref(""),
  kind = ref(""),
  status = ref(""),
  problems = ref(false),
  archived = ref(false),
  offset = ref(0),
  busy = ref(""),
  loading = ref(false);
const data = ref<Page<MonitorTarget> & { summary: Record<string, number> }>({
  total: 0,
  items: [],
  summary: {},
});
type Config = {
  enabled: boolean;
  discovery: boolean;
  per_day: number;
  per_host_minute: number;
  retention_days: number;
  next_discovery?: string;
};
const settings = ref<Config>({
    enabled: true,
    discovery: true,
    per_day: 2000,
    per_host_minute: 10,
    retention_days: 30,
  }),
  destinations = ref<{ id: number; name: string }[]>([]);
const selected = computed(() => Number(route.query.id) || 0),
  historyOffset = ref(0),
  referencesOffset = ref(0);
type Reference = {
  kind: string;
  entity_id: string;
  role: string;
  title: string;
};
const detail = ref<{
    target: MonitorTarget;
    checks: Page<MonitorCheck>;
    references: Page<Reference>;
  } | null>(null),
  editing = ref(false),
  preferences = ref({
    enabled: true,
    interval_minutes: 1440,
    alerts: true,
    failure_threshold: 3,
    certificate_days: 30,
    webhook_id: null as number | null,
  });
const form = ref({ name: "", url: "", interval_minutes: 1440 });
const summary = computed(() => {
  const s = data.value.summary,
    total = Object.values(s).reduce((a, b) => a + b, 0),
    good = (s.available || 0) + (s.redirected || 0);
  return {
    total,
    good,
    attention: total - good - (s.not_checked || 0),
    unknown: s.not_checked || 0,
  };
});
let generation = 0;
async function load() {
  const current = ++generation;
  loading.value = true;
  try {
    const p = new URLSearchParams({
      q: q.value,
      kind: kind.value,
      status: status.value,
      problems: String(problems.value),
      include_archived: String(archived.value),
      offset: String(offset.value),
    });
    const result = await api<typeof data.value>("monitors?" + p);
    if (current === generation) data.value = result;
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    if (current === generation) loading.value = false;
  }
}
async function loadSettings() {
  try {
    const result = await api<{
      config: Config;
      destinations: typeof destinations.value;
    }>("monitor-settings");
    settings.value = result.config;
    destinations.value = result.destinations;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function loadDetail() {
  if (!selected.value) {
    detail.value = null;
    return;
  }
  const id = selected.value;
  try {
    const result = await api<typeof detail.value>(
      `monitors/${id}?offset=${historyOffset.value}&references_offset=${referencesOffset.value}`,
    );
    if (selected.value === id) detail.value = result;
  } catch (e) {
    emit("error", (e as Error).message);
  }
}
async function action(
  key: string,
  work: () => Promise<unknown>,
  notice: string,
) {
  busy.value = key;
  try {
    await work();
    await load();
    await loadDetail();
    emit("notice", notice);
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = "";
  }
}
async function check(item: { id: number }) {
  await action(
    "check:" + item.id,
    () => api(`monitors/${item.id}/check`, "POST"),
    "Verificação adicionada à fila. O diagnóstico aparecerá ao concluir.",
  );
}
async function discover() {
  busy.value = "discover";
  try {
    const result = await api<{ created: number; skipped: number }>(
      "monitors/discover",
      "POST",
    );
    await load();
    emit(
      "notice",
      `${result.created} novos endereços encontrados. ${result.skipped} endereços não elegíveis foram omitidos.`,
    );
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = "";
  }
}
async function create() {
  busy.value = "create";
  try {
    const result = await api<MonitorTarget>("monitors", "POST", form.value);
    form.value = { name: "", url: "", interval_minutes: 1440 };
    await load();
    await router.push({ query: { id: String(result.id) } });
    emit(
      "notice",
      "Endereço cadastrado ou localizado no monitoramento existente.",
    );
  } catch (e) {
    emit("error", (e as Error).message);
  } finally {
    busy.value = "";
  }
}
function edit() {
  if (!detail.value) return;
  const t = detail.value.target;
  preferences.value = {
    enabled: t.enabled,
    interval_minutes: t.interval_minutes,
    alerts: t.alerts,
    failure_threshold: t.failure_threshold,
    certificate_days: t.certificate_days,
    webhook_id: t.webhook_id,
  };
  editing.value = !editing.value;
}
async function savePreferences() {
  await action(
    "preferences",
    () => api(`monitors/${selected.value}`, "PATCH", preferences.value),
    "Preferências de monitoramento atualizadas.",
  );
  editing.value = false;
}
async function toggle(item: MonitorTarget) {
  await action(
    "toggle:" + item.id,
    () =>
      api(`monitors/${item.id}`, "PATCH", {
        enabled: !item.enabled,
        interval_minutes: item.interval_minutes,
        alerts: item.alerts,
        failure_threshold: item.failure_threshold,
        certificate_days: item.certificate_days,
        webhook_id: item.webhook_id,
      }),
    "Agendamento do endereço atualizado.",
  );
}
async function saveConfig() {
  await action(
    "settings",
    () => api("monitor-settings", "PUT", settings.value),
    "Limites de monitoramento atualizados.",
  );
  await loadSettings();
}
function destination(ref: Reference) {
  return ref.kind === "publication"
    ? { name: "publications", query: { publication: ref.entity_id } }
    : ref.kind === "institution"
      ? { name: "institutions", query: { id: ref.entity_id } }
      : { name: "search", query: { dataset: ref.entity_id } };
}
const currentCheck = computed(() =>
  detail.value?.checks.items.find(
    (c) =>
      c.state === "completed" &&
      c.outcome !== "deferred" &&
      c.outcome !== "skipped",
  ),
);
watch([kind, status, problems, archived], () => {
  offset.value = 0;
  load();
});
watch(offset, load);
watch([historyOffset, referencesOffset], loadDetail);
watch(selected, () => {
  historyOffset.value = 0;
  referencesOffset.value = 0;
  editing.value = false;
  loadDetail();
});
watch(revision, () => {
  load();
  if (selected.value) loadDetail();
});
let timer: ReturnType<typeof setInterval>;
onMounted(() => {
  load();
  loadSettings();
  loadDetail();
  timer = setInterval(() => {
    if (
      data.value.items.some((t) => t.active_check) ||
      detail.value?.checks.items.some((c) =>
        ["queued", "running"].includes(c.state),
      )
    ) {
      load();
      loadDetail();
    }
  }, 5000);
});
onUnmounted(() => clearInterval(timer));
</script>
<template>
  <p class="scope-note">
    O diagnóstico vale para cada endereço verificado. Um DOI não encontrado, uma
    consulta recusada ou uma exigência de autenticação não significam que toda a
    fonte esteja fora do ar. Nunca desativamos a validação HTTPS para marcar um
    endereço como disponível.
  </p>
  <section
    class="monitor-summary"
    aria-label="Resumo de todos os endereços não arquivados"
  >
    <div>
      <strong>{{ summary.total }}</strong
      ><span>Endereços cadastrados</span>
    </div>
    <div>
      <strong>{{ summary.good }}</strong
      ><span>Disponíveis</span>
    </div>
    <div>
      <strong>{{ summary.attention }}</strong
      ><span>Precisam de atenção</span>
    </div>
    <div>
      <strong>{{ summary.unknown }}</strong
      ><span>Ainda não verificados</span>
    </div>
  </section>
  <div v-if="user.role !== 'viewer'" class="action-row monitor-actions">
    <button
      class="primary-action"
      :disabled="!!busy"
      @click="
        action(
          'apis',
          () => api('monitors/check-apis', 'POST'),
          'APIs adicionadas à verificação; verificações recentes ou já em andamento são preservadas.',
        )
      "
    >
      {{ busy === "apis" ? "Enfileirando…" : "Verificar APIs agora" }}</button
    ><button class="chip-button" :disabled="!!busy" @click="discover">
      Atualizar lista de links do catálogo
    </button>
  </div>
  <section
    v-if="detail"
    class="panel monitor-detail section-gap"
    aria-labelledby="monitor-detail-title"
  >
    <div class="panel-heading">
      <div>
        <p class="eyebrow">DIAGNÓSTICO DO ENDEREÇO</p>
        <h2 id="monitor-detail-title">{{ detail.target.name }}</h2>
        <a
          class="monitor-url"
          :href="safeUrl(detail.target.url)"
          target="_blank"
          rel="noopener noreferrer"
          >{{ detail.target.url }} ↗</a
        >
      </div>
      <button class="text-button" @click="router.push({ query: {} })">
        Fechar diagnóstico
      </button>
    </div>
    <div class="detail-body">
      <div class="tag-row">
        <span class="badge" :class="monitorTone(detail.target.status)">{{
          monitorStates[detail.target.status] || detail.target.status
        }}</span
        ><span>{{ monitorKinds[detail.target.kind] }}</span
        ><span>{{
          detail.target.enabled ? "Agendamento ativo" : "Agendamento pausado"
        }}</span
        ><span v-if="detail.target.archived"
          >Arquivado: sem vínculo atual no catálogo</span
        >
      </div>
      <p v-if="currentCheck">{{ currentCheck.message }}</p>
      <p v-else class="muted">
        Nenhuma verificação concluída. Uma tarefa na fila ainda não comprova
        disponibilidade.
      </p>
      <div class="action-row" v-if="user.role !== 'viewer'">
        <button
          class="chip-button"
          :disabled="
            !!busy ||
            detail.target.archived ||
            detail.checks.items.some((c) =>
              ['queued', 'running'].includes(c.state),
            )
          "
          @click="check(detail.target)"
        >
          Verificar este endereço agora</button
        ><button class="text-button" @click="edit">
          Configurar frequência e alertas</button
        ><RouterLink class="text-button" :to="{ name: 'incidents' }"
          >Consultar incidentes →</RouterLink
        >
      </div>
      <form
        v-if="editing"
        class="form-grid monitor-preferences"
        @submit.prevent="savePreferences"
      >
        <label class="checkbox-label"
          ><input v-model="preferences.enabled" type="checkbox" />Ativar
          verificações automáticas deste endereço</label
        >
        <div class="two-columns">
          <label
            >Intervalo em minutos<input
              v-model.number="preferences.interval_minutes"
              type="number"
              min="15"
              max="10080"
              required /></label
          ><label
            >Falhas consecutivas para incidente<input
              v-model.number="preferences.failure_threshold"
              type="number"
              min="2"
              max="10"
              required /></label
          ><label
            >Avisar certificado a vencer em até (dias)<input
              v-model.number="preferences.certificate_days"
              type="number"
              min="1"
              max="90"
              required /></label
          ><label
            >Notificação externa opcional<select
              v-model="preferences.webhook_id"
            >
              <option :value="null">Somente radar e incidentes internos</option>
              <option v-for="d in destinations" :key="d.id" :value="d.id">
                {{ d.name }}
              </option>
            </select></label
          >
        </div>
        <label class="checkbox-label"
          ><input v-model="preferences.alerts" type="checkbox" />Criar
          incidentes e avisos de recuperação</label
        >
        <p class="muted">
          O incidente de falha é resolvido após duas respostas esperadas
          consecutivas. Certificados renovados resolvem o aviso de vencimento.
          Escolher um destino externo autoriza o envio desses avisos ao webhook
          já cadastrado.
        </p>
        <button class="primary-action" :disabled="!!busy">
          Salvar preferências do endereço
        </button>
      </form>
      <section v-if="currentCheck" class="monitor-diagnostics">
        <h3>Último resultado nesta página do histórico</h3>
        <dl class="bibliographic-facts">
          <div>
            <dt>Resposta HTTP</dt>
            <dd>{{ currentCheck.http_status ?? "Sem resposta HTTP" }}</dd>
          </div>
          <div>
            <dt>Duração total</dt>
            <dd>{{ currentCheck.duration_ms }} ms</dd>
          </div>
          <div>
            <dt>Certificado com menor validade no trajeto</dt>
            <dd>
              {{
                currentCheck.tls.days_remaining === undefined
                  ? "Não disponível"
                  : currentCheck.tls.days_remaining + " dias"
              }}<small v-if="currentCheck.tls.host">{{
                currentCheck.tls.host
              }}</small>
            </dd>
          </div>
          <div>
            <dt>Última conclusão</dt>
            <dd>{{ date(currentCheck.finished_at) }}</dd>
          </div>
        </dl>
        <p v-if="currentCheck.final_url" class="monitor-url">
          Endereço final ou última tentativa:
          <a
            :href="safeUrl(currentCheck.final_url)"
            target="_blank"
            rel="noopener noreferrer"
            >{{ currentCheck.final_url }} ↗</a
          >
        </p>
        <details v-if="currentCheck.tls.certificates?.length">
          <summary>Certificados validados no trajeto</summary>
          <dl
            v-for="cert in currentCheck.tls.certificates"
            :key="cert.host"
            class="monitor-certificate"
          >
            <dt>{{ cert.host }}</dt>
            <dd>
              {{ cert.version }} · Vence em {{ date(cert.expires_at) }} ·
              {{ cert.days_remaining }} dias
            </dd>
            <dd>Emissor: {{ cert.issuer || "Não informado" }}</dd>
          </dl>
        </details>
        <details v-if="currentCheck.redirects.length">
          <summary>Caminho dos redirecionamentos</summary>
          <ol>
            <li
              v-for="(hop, i) in currentCheck.redirects"
              :key="i"
              class="monitor-url"
            >
              HTTP {{ hop.status }} · {{ hop.from }} → {{ hop.to }}
            </li>
          </ol>
        </details>
        <details v-if="Object.keys(currentCheck.timings).length">
          <summary>Tempos da última requisição HTTP</summary>
          <p>
            DNS: {{ currentCheck.timings.dns_ms ?? "—" }} ms · Conexão:
            {{ currentCheck.timings.connect_ms ?? "—" }} ms · TLS:
            {{ currentCheck.timings.tls_ms ?? "—" }} ms · HTTP e leitura
            limitada: {{ currentCheck.timings.http_ms ?? "—" }} ms.
          </p>
        </details>
      </section>
      <h3>
        Registros que utilizam este endereço
        <span class="count">{{ detail.references.total }}</span>
      </h3>
      <ul class="monitor-references">
        <li
          v-for="ref in detail.references.items"
          :key="ref.kind + ref.entity_id + ref.role"
        >
          <RouterLink :to="destination(ref)">{{ ref.title }} →</RouterLink
          ><small
            >{{
              ref.kind === "publication"
                ? "Publicação"
                : ref.kind === "institution"
                  ? "Instituição"
                  : "Conjunto de dados"
            }}
            ·
            {{
              ref.role === "doi"
                ? "DOI"
                : ref.role === "pdf"
                  ? "PDF"
                  : ref.role === "page"
                    ? "Página de origem"
                    : ref.role === "website"
                      ? "Portal"
                      : "Arquivo de dados"
            }}</small
          >
        </li>
      </ul>
      <p v-if="!detail.references.total" class="muted">
        Endpoint de referência ou endereço cadastrado sem vínculo com um
        registro do catálogo.
      </p>
      <Pager
        v-if="detail.references.total > 25"
        :total="detail.references.total"
        :offset="referencesOffset"
        @change="referencesOffset = $event"
      />
      <h3>Histórico de verificações</h3>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>DATA</th>
              <th>RESULTADO</th>
              <th>HTTP</th>
              <th>TEMPO</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in detail.checks.items" :key="c.id">
              <td>{{ date(c.created_at) }}</td>
              <td>
                <span
                  class="badge"
                  :class="
                    monitorTone(c.state === 'completed' ? c.outcome : c.state)
                  "
                  >{{
                    monitorStates[
                      c.state === "completed" ? c.outcome : c.state
                    ] || c.outcome
                  }}</span
                ><small>{{ c.message }}</small>
              </td>
              <td>{{ c.http_status ?? "—" }}</td>
              <td>
                {{ c.state === "completed" ? c.duration_ms + " ms" : "—" }}
              </td>
            </tr>
            <tr v-if="!detail.checks.items.length">
              <td colspan="4" class="empty-cell">
                Nenhuma verificação registrada.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pager
        :total="detail.checks.total"
        :size="20"
        :offset="historyOffset"
        @change="historyOffset = $event"
      />
    </div>
  </section>
  <section class="panel section-gap">
    <div class="panel-heading">
      <div>
        <h2>
          Endereços monitorados <span class="count">{{ data.total }}</span>
        </h2>
        <p>
          APIs a cada 15 minutos e links do catálogo diariamente, com
          distribuição dos horários e limites de consultas.
        </p>
      </div>
      <span v-if="loading" role="status">Atualizando…</span>
    </div>
    <form
      class="monitor-filters"
      @submit.prevent="
        offset = 0;
        load();
      "
    >
      <label
        >Buscar nome ou endereço<input
          v-model="q"
          aria-label="Buscar endereço monitorado"
          placeholder="Ex.: OpenAlex, dados.ufrn.br"
          maxlength="150" /></label
      ><label
        >Categoria<select
          v-model="kind"
          aria-label="Categoria do monitoramento"
        >
          <option value="">Todas as categorias</option>
          <option v-for="(label, key) in monitorKinds" :key="key" :value="key">
            {{ label }}
          </option>
        </select></label
      ><label
        >Diagnóstico<select
          v-model="status"
          aria-label="Diagnóstico do monitoramento"
        >
          <option value="">Todos os diagnósticos</option>
          <option v-for="(label, key) in monitorStates" :key="key" :value="key">
            {{ label }}
          </option>
        </select></label
      ><button class="chip-button">Filtrar endereços</button
      ><label class="checkbox-label"
        ><input v-model="problems" type="checkbox" />Somente os que precisam de
        atenção</label
      ><label class="checkbox-label"
        ><input v-model="archived" type="checkbox" />Incluir arquivados</label
      >
    </form>
    <div class="table-scroll monitor-table">
      <table>
        <thead>
          <tr>
            <th>ENDEREÇO</th>
            <th>DIAGNÓSTICO</th>
            <th>ÚLTIMA VERIFICAÇÃO</th>
            <th>PRÓXIMA AUTOMÁTICA</th>
            <th>AÇÕES</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in data.items" :key="item.id">
            <td>
              <button
                class="row-title"
                @click="router.push({ query: { id: String(item.id) } })"
              >
                {{ item.name }}</button
              ><small class="monitor-url"
                >{{ item.host }} · {{ monitorKinds[item.kind] }} ·
                {{ item.references }} vínculos</small
              ><small v-if="item.archived">Arquivado</small
              ><small v-else-if="!item.enabled">Agendamento pausado</small>
            </td>
            <td>
              <span v-if="item.active_check" class="badge monitor-neutral">{{
                monitorStates[item.active_check.state]
              }}</span
              ><span v-else class="badge" :class="monitorTone(item.status)">{{
                monitorStates[item.status] || item.status
              }}</span
              ><small>{{
                item.last_check?.message ||
                "Disponibilidade ainda não verificada."
              }}</small
              ><small v-if="item.last_attempt?.outcome === 'deferred'"
                >Última tentativa adiada por limite de consultas.</small
              ><small v-if="item.window.observations"
                >Respostas esperadas em 24h: {{ item.window.expected_percent }}%
                · {{ item.window.observations }} verificações</small
              >
            </td>
            <td>
              {{ date(item.checked_at)
              }}<small v-if="item.last_check"
                >{{
                  item.last_check.http_status
                    ? "HTTP " + item.last_check.http_status
                    : "Sem HTTP"
                }}
                · {{ item.last_check.duration_ms }} ms</small
              >
            </td>
            <td>
              {{
                item.enabled && settings.enabled && !item.archived
                  ? date(item.next_at)
                  : "Pausada"
              }}
            </td>
            <td>
              <div class="action-row">
                <button
                  class="text-button"
                  @click="router.push({ query: { id: String(item.id) } })"
                >
                  Ver diagnóstico</button
                ><template v-if="user.role !== 'viewer'"
                  ><button
                    class="text-button"
                    :disabled="!!busy || !!item.active_check || item.archived"
                    @click="check(item)"
                  >
                    Verificar agora</button
                  ><button
                    v-if="!item.archived"
                    class="text-button"
                    :disabled="!!busy"
                    @click="toggle(item)"
                  >
                    {{ item.enabled ? "Pausar agenda" : "Ativar agenda" }}
                  </button></template
                >
              </div>
            </td>
          </tr>
          <tr v-if="!data.items.length">
            <td colspan="5" class="empty-cell">
              Nenhum endereço com estes filtros. Atualize a lista do catálogo ou
              ajuste os critérios.
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <Pager :total="data.total" :offset="offset" @change="offset = $event" />
    <p class="scope-caption">
      Percentuais usam apenas verificações concluídas com diagnóstico no
      período. Pausas, tarefas na fila, adiamentos locais e verificações
      interrompidas não são consideradas sucesso. Não representam um SLA da
      fonte.
    </p>
  </section>
  <details
    v-if="user.role !== 'viewer'"
    class="panel section-gap monitor-options"
  >
    <summary>Cadastrar outro endereço público</summary>
    <form class="form-grid detail-body" @submit.prevent="create">
      <div class="two-columns">
        <label
          >Nome do endereço<input
            v-model="form.name"
            aria-label="Nome do endereço"
            required
            minlength="3"
            maxlength="300" /></label
        ><label
          >URL pública<input
            v-model="form.url"
            aria-label="URL pública para monitorar"
            type="url"
            required
            maxlength="2048"
            placeholder="https://universidade.example/portal" /></label
        ><label
          >Intervalo em minutos<input
            v-model.number="form.interval_minutes"
            type="number"
            min="15"
            max="10080"
            required
        /></label>
      </div>
      <p class="muted">
        Somente HTTP/HTTPS nas portas padrão. Destinos internos, credenciais e
        segredos na URL não são aceitos. PDFs e arquivos não são baixados por
        inteiro; o GET de fallback tem leitura limitada.
      </p>
      <button class="primary-action" :disabled="!!busy">
        Cadastrar endereço
      </button>
    </form>
  </details>
  <details class="panel section-gap monitor-options">
    <summary>Frequência, limites e funcionamento</summary>
    <div class="detail-body">
      <p>
        O catálogo é relido a cada hora para descobrir links de publicações,
        dados abertos e sites das instituições acompanhadas. Endereços iguais
        são verificados uma vez; vínculos antigos são arquivados sem apagar o
        histórico. Links recusados pela política de destino não são cadastrados.
      </p>
      <p>
        O worker verifica os endereços a partir da rede do servidor. Restrições
        dessa rede podem causar um resultado diferente do seu navegador. Nenhum
        diagnóstico corrige automaticamente o certificado de outra instituição
        ou altera os links originais.
      </p>
      <form class="form-grid" @submit.prevent="saveConfig">
        <label class="checkbox-label"
          ><input
            v-model="settings.enabled"
            type="checkbox"
            :disabled="user.role !== 'admin'"
          />Ativar agendamento automático do monitoramento</label
        ><label class="checkbox-label"
          ><input
            v-model="settings.discovery"
            type="checkbox"
            :disabled="user.role !== 'admin'"
          />Atualizar links do catálogo automaticamente</label
        >
        <div class="two-columns">
          <label
            >Chamadas HTTP por dia UTC<input
              v-model.number="settings.per_day"
              type="number"
              min="50"
              max="10000"
              required
              :disabled="user.role !== 'admin'" /></label
          ><label
            >Chamadas por domínio e minuto<input
              v-model.number="settings.per_host_minute"
              type="number"
              min="1"
              max="60"
              required
              :disabled="user.role !== 'admin'" /></label
          ><label
            >Histórico em dias<input
              v-model.number="settings.retention_days"
              type="number"
              min="7"
              max="90"
              required
              :disabled="user.role !== 'admin'"
          /></label>
        </div>
        <p class="muted">
          As APIs também respeitam as políticas de chamadas da fonte. A última
          verificação concluída de cada endereço é preservada mesmo após a
          janela de retenção. A fila de monitoramento funciona separada das
          coletas e dos relatórios.
        </p>
        <button
          v-if="user.role === 'admin'"
          class="primary-action"
          :disabled="!!busy"
        >
          Salvar limites de monitoramento
        </button>
      </form>
    </div>
  </details>
</template>
