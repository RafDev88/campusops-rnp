export const monitorKinds: Record<string, string> = {
  api: "APIs",
  publication: "Publicações e DOI",
  dataset: "Páginas de dados abertos",
  file: "Arquivos",
  portal: "Portais de instituições",
  manual: "Endereços cadastrados",
};
export const monitorStates: Record<string, string> = {
  not_checked: "Não verificado",
  available: "Disponível",
  redirected: "Disponível com redirecionamento",
  slow: "Resposta lenta",
  tls_expiring: "Certificado próximo do vencimento",
  http_insecure: "HTTP sem proteção",
  auth_required: "Exige autenticação",
  forbidden: "Consulta recusada",
  rate_limited: "Limite da fonte atingido",
  not_found: "Endereço não encontrado",
  server_error: "Erro no servidor",
  dns_error: "Domínio não localizado",
  tls_error: "Falha na validação HTTPS",
  timeout: "Tempo de resposta excedido",
  connection_error: "Falha de conexão",
  invalid_content: "Resposta fora do esperado",
  blocked: "Destino bloqueado",
  http_error: "Resposta HTTP inesperada",
  redirect_error: "Problema no redirecionamento",
  deferred: "Adiada por limite local",
  interrupted: "Verificação interrompida",
  internal: "Erro interno",
  skipped: "Verificação omitida",
  queued: "Na fila",
  running: "Verificando",
};
export function monitorTone(status: string) {
  return ["available", "redirected"].includes(status)
    ? "monitor-good"
    : [
          "slow",
          "tls_expiring",
          "http_insecure",
          "auth_required",
          "forbidden",
          "rate_limited",
          "deferred",
        ].includes(status)
      ? "monitor-warning"
      : ["not_checked", "queued", "running", "skipped", "interrupted"].includes(
            status,
          )
        ? "monitor-neutral"
        : "monitor-bad";
}
export type MonitorCheck = {
  id: number;
  target_id: number;
  state: string;
  outcome: string;
  ok: boolean | null;
  message: string;
  http_status: number | null;
  final_url: string;
  method: string;
  duration_ms: number;
  created_at: string;
  finished_at: string | null;
  timings: Record<string, number>;
  redirects: { status: number; from: string; to: string }[];
  tls: {
    expires_at?: string;
    days_remaining?: number;
    version?: string;
    issuer?: string;
    verify_code?: number;
    host?: string;
    certificates?: {
      host: string;
      expires_at: string;
      days_remaining: number;
      issuer: string;
      version: string;
    }[];
  };
};
export type MonitorTarget = {
  id: number;
  name: string;
  url: string;
  kind: string;
  source: string;
  host: string;
  enabled: boolean;
  archived: boolean;
  interval_minutes: number;
  status: string;
  checked_at: string | null;
  next_at: string;
  alerts: boolean;
  failure_threshold: number;
  certificate_days: number;
  webhook_id: number | null;
  failures: number;
  references: number;
  last_check: MonitorCheck | null;
  last_attempt: MonitorCheck | null;
  active_check: MonitorCheck | null;
  window: {
    observations: number;
    expected: number;
    expected_percent: number | null;
  };
};
