// Centralised API client.
//
// One place to deal with: base URL, X-API-Key header, JSON parsing,
// error unwrapping. Every view imports `useApi()` from `hooks/useApi`
// which in turn calls the helpers exported here.

import type {
  AdminStats,
  AdminUser,
  AssetItem,
  AuditLogItem,
  CurrentUser,
  DashboardData,
  Finding,
  LegalTermsState,
  NotificationItem,
  ScanDetail,
  ScanItem,
  ToolCommand,
  ToolSpec,
} from "../types";

export const API_BASE =
  (import.meta as { env?: { VITE_API_BASE?: string } }).env?.VITE_API_BASE ||
  "http://localhost:8000";

// ─── Low-level helper ─────────────────────────────────────────────────────

export interface ApiError extends Error {
  status: number;
  code?: string;
}

async function request<T>(
  apiKey: string,
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "X-API-Key": apiKey,
    ...((init.headers as Record<string, string>) || {}),
  };
  if (init.body) headers["Content-Type"] = "application/json";

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });

  let data: { ok?: boolean; error?: string; message?: string } & Record<
    string,
    unknown
  > = { ok: false };
  try {
    data = await res.json();
  } catch {
    // body wasn't JSON — fall through to status-based error below
  }

  if (!res.ok || data.ok === false) {
    const err: ApiError = Object.assign(
      new Error(data.error || data.message || `HTTP ${res.status}`),
      { status: res.status, code: data.error as string | undefined },
    );
    throw err;
  }

  return data as unknown as T;
}

// ─── Auth ─────────────────────────────────────────────────────────────────

export interface AuthResponse {
  ok: true;
  user: CurrentUser;
}

export async function login(
  email: string,
  password: string,
): Promise<AuthResponse> {
  return request<AuthResponse>("", "/api/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function register(
  email: string,
  password: string,
): Promise<AuthResponse> {
  return request<AuthResponse>("", "/api/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function me(apiKey: string): Promise<AuthResponse> {
  return request<AuthResponse>(apiKey, "/api/me");
}

// ─── Dashboard ────────────────────────────────────────────────────────────

export interface DashboardResponse {
  ok: true;
  dashboard: DashboardData;
}

export const getDashboard = (apiKey: string) =>
  request<DashboardResponse>(apiKey, "/api/dashboard");

// ─── Scans ────────────────────────────────────────────────────────────────

export interface ScansListResponse {
  ok: true;
  scans: ScanItem[];
  total: number;
  page: number;
  per_page: number;
}

export const listScans = (
  apiKey: string,
  params: {
    page?: number;
    per_page?: number;
    status?: string;
    tool?: string;
    search?: string;
  } = {},
) => {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  if (params.status) qs.set("status", params.status);
  if (params.tool) qs.set("tool", params.tool);
  if (params.search) qs.set("search", params.search);
  return request<ScansListResponse>(apiKey, `/api/scans?${qs}`);
};

export interface ScanCreateResponse {
  ok: true;
  scan_id: number;
  status: string;
  tool: string;
  target: string;
}

export const createScan = (apiKey: string, target: string, tool: string) =>
  request<ScanCreateResponse>(apiKey, "/api/scans", {
    method: "POST",
    body: JSON.stringify({ target, tool }),
  });

export interface ScanDetailResponse {
  ok: true;
  scan: ScanDetail;
}

export const getScan = (apiKey: string, id: number) =>
  request<ScanDetailResponse>(apiKey, `/api/scans/${id}`);

export const deleteScan = (apiKey: string, id: number) =>
  request<{ ok: true }>(apiKey, `/api/scans/${id}`, { method: "DELETE" });

export const cancelScan = (apiKey: string, id: number) =>
  request<{ ok: true; scan_id: number; status: string }>(
    apiKey,
    `/api/scans/${id}/cancel`,
    { method: "POST" },
  );

export interface ScanRawResponse {
  ok: true;
  scan_id: number;
  stdout: string;
  stderr: string;
  error_message: string | null;
}

export const getScanRaw = (apiKey: string, id: number) =>
  request<ScanRawResponse>(apiKey, `/api/scans/${id}/raw`);

// Reports are protected by X-API-Key, so we can't just `window.open` a URL —
// the browser wouldn't attach the header and the request would 401. Instead
// we fetch the report as a blob with the right header, then trigger a
// download client-side via a temporary anchor.
export async function downloadReport(
  apiKey: string,
  scanId: number,
  format: "json" | "html" | "md",
): Promise<void> {
  const res = await fetch(
    `${API_BASE}/api/scans/${scanId}/report?format=${format}`,
    { headers: { "X-API-Key": apiKey } },
  );

  if (!res.ok) {
    // Try to surface the server's error message if it's JSON; otherwise
    // throw a generic error with the status code.
    let msg = `HTTP ${res.status}`;
    try {
      const data = (await res.json()) as { error?: string };
      if (data?.error) msg = data.error;
    } catch {
      /* response wasn't JSON — keep the status-based message */
    }
    const err: ApiError = Object.assign(new Error(msg), {
      status: res.status,
    });
    throw err;
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  try {
    const ext = format === "md" ? "md" : format;
    const a = document.createElement("a");
    a.href = url;
    a.download = `rasid_report_${scanId}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

// ─── Findings / Assets ────────────────────────────────────────────────────

export interface FindingsResponse {
  ok: true;
  findings: Finding[];
  total: number;
  page: number;
  per_page: number;
}

export const listFindings = (
  apiKey: string,
  params: { page?: number; per_page?: number; severity?: string; priority?: string } = {},
) => {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  if (params.severity) qs.set("severity", params.severity);
  if (params.priority) qs.set("priority", params.priority);
  return request<FindingsResponse>(apiKey, `/api/findings?${qs}`);
};

export interface AssetsResponse {
  ok: true;
  assets: AssetItem[];
  total: number;
  page: number;
  per_page: number;
}

export const listAssets = (
  apiKey: string,
  params: { page?: number; per_page?: number } = {},
) => {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  return request<AssetsResponse>(apiKey, `/api/assets?${qs}`);
};

// ─── Tools / Custom commands ─────────────────────────────────────────────

export interface ToolsResponse {
  ok: true;
  tools: ToolSpec[];
}

export const listTools = (apiKey: string) =>
  request<ToolsResponse>(apiKey, "/api/tools");

export interface ToolCommandsResponse {
  ok: true;
  commands: ToolCommand[];
}

export const listToolCommands = (apiKey: string) =>
  request<ToolCommandsResponse>(apiKey, "/api/tools/commands");

export interface ToolCommandResponse {
  ok: true;
  command: ToolCommand;
}

export const upsertToolCommand = (
  apiKey: string,
  tool_name: string,
  args: string[],
  name = "custom",
) =>
  request<ToolCommandResponse>(apiKey, "/api/tools/commands", {
    method: "POST",
    body: JSON.stringify({ tool_name, args, name }),
  });

export const deleteToolCommand = (apiKey: string, id: number) =>
  request<{ ok: true }>(apiKey, `/api/tools/commands/${id}`, {
    method: "DELETE",
  });

export const toggleToolCommand = (apiKey: string, id: number) =>
  request<ToolCommandResponse>(apiKey, `/api/tools/commands/${id}/toggle`, {
    method: "POST",
  });

// ─── Notifications ───────────────────────────────────────────────────────

export interface NotificationsResponse {
  ok: true;
  notifications: NotificationItem[];
  total: number;
  unread_count: number;
  page: number;
  per_page: number;
}

export const listNotifications = (
  apiKey: string,
  unreadOnly = false,
) =>
  request<NotificationsResponse>(
    apiKey,
    `/api/notifications${unreadOnly ? "?unread=1" : ""}`,
  );

export const markNotificationRead = (apiKey: string, id: number) =>
  request<{ ok: true }>(apiKey, `/api/notifications/${id}/read`, {
    method: "PUT",
  });

export const markAllNotificationsRead = (apiKey: string) =>
  request<{ ok: true }>(apiKey, `/api/notifications/read-all`, {
    method: "PUT",
  });

// ─── Legal ───────────────────────────────────────────────────────────────

export interface LegalTermsResponse extends LegalTermsState {
  ok: true;
}

export const getLegalTerms = (apiKey: string) =>
  request<LegalTermsResponse>(apiKey, "/api/legal/terms");

export const acceptLegalTerms = (apiKey: string) =>
  request<{ ok: true; version: string }>(apiKey, "/api/legal/accept", {
    method: "POST",
  });

// ─── Settings ────────────────────────────────────────────────────────────

export const changePassword = (
  apiKey: string,
  current_password: string,
  new_password: string,
) =>
  request<{ ok: true }>(apiKey, "/api/settings/change-password", {
    method: "POST",
    body: JSON.stringify({ current_password, new_password }),
  });

export const rotateApiKey = (apiKey: string) =>
  request<{ ok: true; api_key: string }>(apiKey, "/api/settings/rotate-api-key", {
    method: "POST",
  });

export const deleteAccount = (apiKey: string, password: string) =>
  request<{ ok: true }>(apiKey, "/api/settings/account", {
    method: "DELETE",
    body: JSON.stringify({ password }),
  });

// ─── Admin ───────────────────────────────────────────────────────────────

export interface AdminUsersResponse {
  ok: true;
  users: AdminUser[];
}

export const adminListUsers = (apiKey: string) =>
  request<AdminUsersResponse>(apiKey, "/api/admin/users");

export const adminUpdateUser = (
  apiKey: string,
  id: number,
  patch: Partial<Pick<AdminUser, "role" | "is_active">>,
) =>
  request<{ ok: true; user: AdminUser }>(apiKey, `/api/admin/users/${id}`, {
    method: "PUT",
    body: JSON.stringify(patch),
  });

export interface AdminStatsResponse {
  ok: true;
  stats: AdminStats;
}

export const adminStats = (apiKey: string) =>
  request<AdminStatsResponse>(apiKey, "/api/admin/stats");

export interface AdminAuditLogsResponse {
  ok: true;
  logs: AuditLogItem[];
  total: number;
  page: number;
  per_page: number;
}

export const adminAuditLogs = (
  apiKey: string,
  params: { page?: number; per_page?: number; action?: string } = {},
) => {
  const qs = new URLSearchParams();
  if (params.page) qs.set("page", String(params.page));
  if (params.per_page) qs.set("per_page", String(params.per_page));
  if (params.action) qs.set("action", params.action);
  return request<AdminAuditLogsResponse>(apiKey, `/api/admin/audit-logs?${qs}`);
};
export interface AggregateResponse {
  ok: true;
  target: string;
  summary: Record<string, number>;
  results: {
    subdomain: object[];
    port: object[];
    http_endpoint: object[];
    vulnerability: object[];
  };
}

export async function getAggregate(
  apiKey: string,
  target: string,
  params?: { page?: number; per_page?: number; category?: string },
): Promise<AggregateResponse> {
  const q = new URLSearchParams();
  if (params?.page)     q.set("page",     String(params.page));
  if (params?.per_page) q.set("per_page", String(params.per_page));
  if (params?.category) q.set("category", params.category);
  const qs = q.toString() ? `?${q.toString()}` : "";
  return request<AggregateResponse>(
    apiKey,
    `/api/aggregate/${encodeURIComponent(target)}${qs}`,
  );
}
