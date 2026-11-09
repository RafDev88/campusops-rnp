import { ref } from "vue";

export type Source = "ror" | "openalex" | "crossref" | "orcid" | "ufrn";
export type User = {
  id: number;
  username: string;
  role: "admin" | "operator" | "viewer";
  active: boolean;
};
export type Institution = {
  id: string;
  name: string;
  country: string;
  watched: boolean;
};
export type Run = {
  id: number;
  source: Source;
  status: string;
  records: number;
  new: number;
  updated: number;
  rejected: number;
  created_at: string;
  finished_at: string | null;
  duration_ms: number;
  attempts: number;
  http_calls: number;
  message: string;
  error_code: string;
  details: Record<string, unknown>;
};
export type Event = {
  id: number;
  kind: string;
  title: string;
  created_at: string;
  payload: Record<string, unknown>;
};
export type Publication = {
  abstract_preview?: string;
  language?: string;
  work_type?: string;
  journal?: string;
  is_retracted?: boolean | null;
  has_abstract?: boolean;
  publication_date?: string;
  issn?: string[];
  landing_url?: string;
  pdf_url?: string;
  oa_status?: string;

  id: string;
  title: string;
  year: number | null;
  doi: string | null;
  is_oa: boolean;
  citations: number;
  topics: { id: string; name: string }[];
  authors: { id: string; name: string; orcid: string | null }[];
  affiliations: { name: string; ror: string | null }[];
  crossref: Record<string, unknown>;
  fetched_at: string;
  crossref_at: string | null;
  source: string;
  favorite: boolean;
  abstract?: string;
  publisher?: string;
  funders?: string[];
  licenses?: string[];
};
export type Page<T> = { total: number; items: T[] };
export const revision = ref(0);
export const refresh = () => revision.value++;
export const labels: Record<string, string> = {
  queued: "Na fila",
  running: "Em andamento",
  success: "Concluída",
  failed: "Falhou",
  partial: "Parcial",
  open: "Aberto",
  resolved: "Resolvido",
  pending: "Pendente",
  sending: "Enviando",
  delivered: "Entregue",
  dead: "Esgotado",
  admin: "Administrador",
  operator: "Operador",
  viewer: "Consulta",
  paused: "Pausada",
  retry_wait: "Retentativa agendada",
  cancelled: "Cancelada",
  waiting: "Aguardando fonte",
  pausing: "Pausando",
  cancelling: "Cancelando",
  ready: "Disponível",
  expired: "Expirado",
  retrying: "Reprocessando",
  ignored: "Ignorado",
  skipped: "Disparo omitido",
  dispatched: "Enfileirado",
};
export const date = (value: string | null) =>
  value ? new Date(value).toLocaleString("pt-BR") : "—";
export function safeUrl(value: string) {
  try {
    const url = new URL(value);
    if (
      url.protocol === "http:" &&
      [
        "creativecommons.org",
        "dados.ufrn.br",
        "doi.org",
        "orcid.org",
        "ror.org",
      ].includes(url.hostname)
    )
      url.protocol = "https:";
    return url.protocol === "https:" ? url.href : "#";
  } catch {
    return "#";
  }
}
let sessionEpoch = 0;
export const advanceSession = () => {
  sessionEpoch++;
};
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const requestEpoch = sessionEpoch;
  const response = await fetch("/api/" + path, {
    signal,
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(method !== "GET" ? { "X-CampusOps": "1" } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let message = `A operação falhou (HTTP ${response.status}).`;
    try {
      const data = await response.json();
      message =
        typeof data.detail === "string"
          ? data.detail
          : "Verifique os campos informados.";
      if (response.status >= 500 && data.request_id)
        message += ` Referência para suporte: ${data.request_id}.`;
    } catch {
      /* retain HTTP status */
    }
    if (
      response.status === 401 &&
      !path.startsWith("auth/") &&
      requestEpoch === sessionEpoch
    )
      window.dispatchEvent(new Event("campusops:expired"));
    throw new Error(message);
  }
  return response.json();
}
