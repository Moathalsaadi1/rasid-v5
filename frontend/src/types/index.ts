// Shared TypeScript types — kept in one place so views, hooks, and api
// helpers all agree on the shape of objects coming back from the API.

export type UserRole = "admin" | "user" | "guest";

export type ScanStatus = "PENDING" | "RUNNING" | "SUCCESS" | "FAILED";

export type Severity = "info" | "low" | "medium" | "high" | "critical";

export interface CurrentUser {
  id: number;
  email: string;
  api_key: string;
  role: UserRole;
  scan_count: number;
}

export interface ScanItem {
  id: number;
  target: string;
  tool: string;
  status: ScanStatus;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  error_message?: string | null;
}

export interface Finding {
  id: number;
  title: string;
  severity: Severity;
  priority: Severity;
  risk_score: number;
  confidence: string;
  description?: string | null;
  evidence?: string | null;
  recommendation?: string | null;
  asset_id?: number | null;
  service_id?: number | null;
  web_endpoint_id?: number | null;
  created_at: string;
}

export interface ScanAssetRef {
  id: number;
  type: string;
  value: string;
  role: string;
}

export interface ScanServiceRef {
  id: number;
  port: number;
  protocol: string;
  state: string;
  name: string;
}

export interface ScanWebEndpoint {
  id: number;
  url: string;
  status_code?: number;
  title?: string;
  webserver?: string;
}

export interface ScanDetail extends ScanItem {
  findings: Finding[];
  assets: ScanAssetRef[];
  services: ScanServiceRef[];
  web_endpoints: ScanWebEndpoint[];
}

export interface AssetItem {
  id: number;
  type: string;
  value: string;
  findings_count: number;
  highest_risk_score: number;
  created_at: string;
}

export interface TopAsset {
  asset_id: number;
  value: string;
  type: string;
  highest_risk_score: number;
  findings_count: number;
  roles: string[];
}

export interface DashboardData {
  total_scans: number;
  total_findings: number;
  severity: Record<string, number>;
  status_counts: Record<string, number>;
  tool_counts: Record<string, number>;
  top_assets: TopAsset[];
  recent_scans: ScanItem[];
}

export interface AdminUser {
  id: number;
  email: string;
  role: UserRole;
  is_active: boolean;
  scan_count: number;
  created_at: string;
}

export interface AdminStats {
  total_users: number;
  total_scans: number;
  total_findings: number;
  total_assets: number;
  running_scans: number;
}

// ─── Phase 3-5 additions ──────────────────────────────────────────────────

export interface ToolSpec {
  name: string;
  description: string;
  default_args: string[];
  allowed_flags: string[];
  target_position: string;
  timeout_seconds: number;
}

export interface ToolCommand {
  id: number;
  tool_name: string;
  name: string;
  args: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationItem {
  id: number;
  scan_id: number | null;
  severity: Severity;
  title: string;
  message: string | null;
  is_read: boolean;
  created_at: string;
}

export interface AuditLogItem {
  id: number;
  user_id: number | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string;
}

export interface LegalTermsState {
  version: string;
  text: string;
  accepted: boolean;
}

// ─── Generic API envelope ────────────────────────────────────────────────

export interface ApiOk {
  ok: true;
  // The actual payload appears under various keys depending on the endpoint
  // (e.g. `scans`, `user`, `stats`). Use the typed helpers in api/client.ts
  // rather than reading payload fields directly off this base.
  [k: string]: unknown;
}

export interface ApiError {
  ok: false;
  error: string;
  message?: string;
}

export type ApiResponse<T> = (ApiOk & T) | ApiError;
