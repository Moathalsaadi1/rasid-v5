import { useCallback, useEffect, useState } from "react";
import {
  createScan,
  listScans,
  listTools,
  type ApiError,
} from "../api/client";
import Badge from "../components/Badge";
import Pagination from "../components/Pagination";
import { fmtDate, STATUS_COLOR, toolMeta } from "../utils/format";
import { g } from "../utils/styles";
import type { ScanItem, ScanStatus, ToolSpec } from "../types";

interface Props {
  apiKey: string;
  onOpenScan: (id: number) => void;
  onLegalRequired: () => void; // open the LegalAcceptanceModal
}

const PAGE_SIZE = 20;
const STATUS_FILTERS: (ScanStatus | "")[] = [
  "",
  "PENDING",
  "RUNNING",
  "SUCCESS",
  "FAILED",
];

export default function ScansView({
  apiKey,
  onOpenScan,
  onLegalRequired,
}: Props) {
  const [scans, setScans] = useState<ScanItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  // create-form state
  const [target, setTarget] = useState("");
  const [tool, setTool] = useState("nmap");
  const [createError, setCreateError] = useState("");

  // available tools (fetched once)
  const [tools, setTools] = useState<ToolSpec[]>([]);

  // filtering
  const [statusFilter, setStatusFilter] = useState<ScanStatus | "">("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await listScans(apiKey, {
        page,
        per_page: PAGE_SIZE,
        status: statusFilter || undefined,
        search: search || undefined,
      });
      setScans(d.scans);
      setTotal(d.total);
    } finally {
      setLoading(false);
    }
  }, [apiKey, page, statusFilter, search]);

  useEffect(() => {
    load();
  }, [load]);

  // Load tool catalogue once.
  useEffect(() => {
    listTools(apiKey)
      .then((d) => setTools(d.tools))
      .catch(() => {
        /* non-fatal — tool picker will fall back to default */
      });
  }, [apiKey]);

  // Auto-refresh when any scan is pending/running so the user sees status
  // transitions live without manually hitting refresh.
  useEffect(() => {
    const live = scans.some((s) => s.status === "RUNNING" || s.status === "PENDING");
    if (!live) return;
    const t = setTimeout(load, 4000);
    return () => clearTimeout(t);
  }, [scans, load]);

  async function create() {
    const trimmed = target.trim();
    if (!trimmed) {
      setCreateError("Target is required");
      return;
    }
    setCreating(true);
    setCreateError("");
    try {
      await createScan(apiKey, trimmed, tool);
      setTarget("");
      await load();
    } catch (e: unknown) {
      const err = e as ApiError;
      if (err.code === "legal_acceptance_required") {
        onLegalRequired();
        return;
      }
      setCreateError(err.message || "Failed");
    } finally {
      setCreating(false);
    }
  }

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div style={g.gap}>
      {/* ── New scan form ─────────────────────────────────────────────── */}
      <div style={g.card}>
        <div style={g.cardHead}>New Scan</div>
        <div
          style={{
            padding: 20,
            display: "grid",
            gridTemplateColumns: "1fr auto auto",
            gap: 12,
          }}
        >
          <input
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && create()}
            placeholder="scanme.nmap.org  or  https://example.com"
            style={g.input}
          />
          <select
            value={tool}
            onChange={(e) => setTool(e.target.value)}
            style={g.select}
          >
            {(tools.length > 0
              ? tools
              : [{ name: "nmap", description: "Port scan" }] as ToolSpec[]
            ).map((t) => (
              <option key={t.name} value={t.name}>
                {toolMeta(t.name).emoji} {t.name} — {t.description}
              </option>
            ))}
          </select>
          <button
            onClick={create}
            disabled={creating}
            style={g.btnPrimary}
          >
            {creating ? "Starting…" : "▶ Start Scan"}
          </button>
        </div>
        {createError && (
          <p
            style={{
              color: "#f87171",
              fontSize: 13,
              margin: "-4px 20px 16px",
            }}
          >
            {createError}
          </p>
        )}
      </div>

      {/* ── List + filters + search ───────────────────────────────────── */}
      <div style={g.card}>
        <div
          style={{
            ...g.cardHead,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 12,
            flexWrap: "wrap",
          }}
        >
          <span>Scans ({total})</span>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <input
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search target…"
              style={{ ...g.input, width: 180, padding: "6px 12px" }}
            />
            {STATUS_FILTERS.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setStatusFilter(s);
                  setPage(1);
                }}
                style={{
                  ...g.btnSm,
                  ...(statusFilter === s
                    ? { background: "#14b8a6", color: "#06261f" }
                    : {}),
                }}
              >
                {s || "All"}
              </button>
            ))}
            <button onClick={load} style={g.btnSm}>
              ↻
            </button>
          </div>
        </div>

        <div style={{ padding: "0 20px 20px" }}>
          {loading ? (
            <p style={g.empty}>Loading…</p>
          ) : scans.length === 0 ? (
            <p style={g.empty}>No scans found.</p>
          ) : (
            scans.map((s) => {
              const meta = toolMeta(s.tool);
              return (
                <div
                  key={s.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "14px 0",
                    borderBottom: "1px solid #1e293b",
                    gap: 12,
                  }}
                >
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 8,
                        flexWrap: "wrap",
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 600,
                          color: "#f1f5f9",
                          fontSize: 14,
                        }}
                      >
                        {s.target}
                      </span>
                      <span
                        style={{
                          background: meta.color + "22",
                          color: meta.color,
                          border: `1px solid ${meta.color}44`,
                          borderRadius: 6,
                          padding: "2px 8px",
                          fontSize: 11,
                          fontWeight: 700,
                        }}
                      >
                        {meta.emoji} {s.tool}
                      </span>
                      <Badge
                        label={s.status}
                        color={STATUS_COLOR[s.status] || "#64748b"}
                      />
                      {(s.status === "RUNNING" || s.status === "PENDING") && (
                        <span style={{ fontSize: 11, color: "#fbbf24" }}>
                          ⟳ live
                        </span>
                      )}
                    </div>
                    <p
                      style={{
                        margin: "4px 0 0",
                        fontSize: 12,
                        color: "#64748b",
                      }}
                    >
                      #{s.id} · {fmtDate(s.created_at)}
                    </p>
                    {s.error_message && (
                      <p
                        style={{
                          margin: "4px 0 0",
                          fontSize: 12,
                          color: "#f87171",
                        }}
                      >
                        {s.error_message}
                      </p>
                    )}
                  </div>
                  <button onClick={() => onOpenScan(s.id)} style={g.btnSm}>
                    Details →
                  </button>
                </div>
              );
            })
          )}
        </div>

        <Pagination
          page={page}
          totalPages={totalPages}
          onPage={(p) => setPage(p)}
        />
      </div>
    </div>
  );
}
