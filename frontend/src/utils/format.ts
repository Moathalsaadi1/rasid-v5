import type { Severity } from "../types";

export const SEV_COLOR: Record<string, string> = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
  info: "#6b7280",
};

export const STATUS_COLOR: Record<string, string> = {
  SUCCESS: "#4ade80",
  FAILED: "#f87171",
  RUNNING: "#fbbf24",
  PENDING: "#cbd5e1",
};

export function severityColor(s: string | null | undefined): string {
  return SEV_COLOR[(s || "").toLowerCase()] || "#6b7280";
}

export function fmtDate(v?: string | null): string {
  if (!v) return "—";
  const d = new Date(v);
  return isNaN(d.getTime()) ? v : d.toLocaleString();
}

export function fmtRelative(v?: string | null): string {
  if (!v) return "";
  const d = new Date(v);
  if (isNaN(d.getTime())) return v;
  const diff = (Date.now() - d.getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function severityLabel(s: Severity): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

// Tool icons / colors — keeps the tool selector visually distinct.
export const TOOL_META: Record<string, { color: string; emoji: string }> = {
  nmap: { color: "#14b8a6", emoji: "🔍" },
  httpx: { color: "#6366f1", emoji: "🌐" },
  nuclei: { color: "#f97316", emoji: "⚡" },
  subfinder: { color: "#a78bfa", emoji: "🌿" },
  amass: { color: "#22d3ee", emoji: "🕸" },
  masscan: { color: "#ec4899", emoji: "💨" },
  massdns: { color: "#84cc16", emoji: "🌍" },
};

export function toolMeta(name: string): { color: string; emoji: string } {
  return TOOL_META[name] || { color: "#64748b", emoji: "🛠" };
}
