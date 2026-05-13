import { useEffect, useState } from "react";
import {
  cancelScan,
  deleteScan,
  downloadReport as downloadReportApi,
  getScan,
  getScanRaw,
} from "../api/client";
import Badge from "../components/Badge";
import Modal from "../components/Modal";
import { fmtDate, SEV_COLOR, STATUS_COLOR } from "../utils/format";
import { g } from "../utils/styles";
import type { ScanDetail } from "../types";

interface Props {
  apiKey: string;
  scanId: number | null;
  onClose: () => void;
  onChanged: () => void; // tell the parent to refresh its scans list
}

// Detail view for a single scan: assets, services, web endpoints,
// findings, plus cancel/delete/raw-output controls and report downloads.
export default function ScanModal({ apiKey, scanId, onClose, onChanged }: Props) {
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // raw stdout viewer (toggleable)
  const [showRaw, setShowRaw] = useState(false);
  const [raw, setRaw] = useState<{ stdout: string; stderr: string } | null>(null);

  // confirm-delete state
  const [confirmDelete, setConfirmDelete] = useState(false);

  // Fetch on open / scanId change.
  useEffect(() => {
    if (scanId == null) {
      setScan(null);
      return;
    }
    setLoading(true);
    setError("");
    getScan(apiKey, scanId)
      .then((d) => setScan(d.scan))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [apiKey, scanId]);

  // Auto-refresh while running.
  useEffect(() => {
    if (!scan || (scan.status !== "RUNNING" && scan.status !== "PENDING")) return;
    const t = setTimeout(() => {
      if (scan.id != null) {
        getScan(apiKey, scan.id)
          .then((d) => setScan(d.scan))
          .catch(() => {});
      }
    }, 4000);
    return () => clearTimeout(t);
  }, [scan, apiKey]);

  async function downloadReport(fmt: "json" | "html" | "md") {
    if (!scan) return;
    try {
      await downloadReportApi(apiKey, scan.id, fmt);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Download failed");
    }
  }

  async function loadRaw() {
    if (!scan) return;
    try {
      const d = await getScanRaw(apiKey, scan.id);
      setRaw({ stdout: d.stdout, stderr: d.stderr });
      setShowRaw(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load raw output");
    }
  }

  async function cancel() {
    if (!scan) return;
    try {
      await cancelScan(apiKey, scan.id);
      const d = await getScan(apiKey, scan.id);
      setScan(d.scan);
      onChanged();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    }
  }

  async function doDelete() {
    if (!scan) return;
    try {
      await deleteScan(apiKey, scan.id);
      onChanged();
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
      setConfirmDelete(false);
    }
  }

  if (scanId == null) return null;

  return (
    <Modal open onClose={onClose} maxWidth={820}>
      {error && <div style={{ ...g.errorBox, marginBottom: 14 }}>{error}</div>}

      {loading ? (
        <p style={g.empty}>Loading scan…</p>
      ) : !scan ? (
        <p style={g.empty}>Scan not found.</p>
      ) : (
        <>
          {/* ── Header ────────────────────────────────────────────────── */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: 12,
              marginBottom: 14,
              flexWrap: "wrap",
            }}
          >
            <div>
              <p
                style={{
                  margin: 0,
                  fontWeight: 700,
                  color: "#f8fafc",
                  fontSize: 16,
                }}
              >
                {scan.target} — {scan.tool}
              </p>
              <p
                style={{
                  margin: "4px 0 0",
                  fontSize: 12,
                  color: "#64748b",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                #{scan.id} · {fmtDate(scan.created_at)} ·{" "}
                <Badge
                  label={scan.status}
                  color={STATUS_COLOR[scan.status] || "#64748b"}
                />
              </p>
            </div>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
              {scan.status === "SUCCESS" && (
                <>
                  <button onClick={() => downloadReport("json")} style={g.btnSm}>
                    ⬇ JSON
                  </button>
                  <button onClick={() => downloadReport("html")} style={g.btnSm}>
                    ⬇ HTML
                  </button>
                  <button onClick={() => downloadReport("md")} style={g.btnSm}>
                    ⬇ MD
                  </button>
                </>
              )}
              <button onClick={loadRaw} style={g.btnSm}>
                ⌘ Raw
              </button>
              {(scan.status === "RUNNING" || scan.status === "PENDING") && (
                <button
                  onClick={cancel}
                  style={{ ...g.btnSm, color: "#fbbf24" }}
                >
                  ⏹ Cancel
                </button>
              )}
              {scan.status !== "RUNNING" && (
                <button
                  onClick={() => setConfirmDelete(true)}
                  style={{ ...g.btnSm, color: "#f87171" }}
                >
                  ✕ Delete
                </button>
              )}
            </div>
          </div>

          {/* ── Confirm delete ────────────────────────────────────────── */}
          {confirmDelete && (
            <div
              style={{
                ...g.errorBox,
                marginBottom: 14,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 10,
              }}
            >
              <span>Delete this scan and all its findings?</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={() => setConfirmDelete(false)} style={g.btnSm}>
                  Cancel
                </button>
                <button
                  onClick={doDelete}
                  style={{ ...g.btnSm, color: "#ef4444", fontWeight: 700 }}
                >
                  Confirm
                </button>
              </div>
            </div>
          )}

          {/* ── Raw output (toggleable) ──────────────────────────────── */}
          {showRaw && raw && (
            <div style={{ marginBottom: 16 }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <span style={{ color: "#94a3b8", fontSize: 13, fontWeight: 600 }}>
                  Raw output
                </span>
                <button onClick={() => setShowRaw(false)} style={g.btnSm}>
                  Hide
                </button>
              </div>
              <pre
                style={{
                  background: "#020617",
                  color: "#67e8f9",
                  borderRadius: 8,
                  padding: 14,
                  fontSize: 11,
                  maxHeight: 240,
                  overflow: "auto",
                  whiteSpace: "pre-wrap",
                  fontFamily:
                    "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                  margin: 0,
                }}
              >
                {raw.stdout || "(empty)"}
              </pre>
              {raw.stderr && (
                <pre
                  style={{
                    background: "#1f0c0c",
                    color: "#fca5a5",
                    borderRadius: 8,
                    padding: 14,
                    fontSize: 11,
                    maxHeight: 160,
                    overflow: "auto",
                    whiteSpace: "pre-wrap",
                    fontFamily:
                      "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                    margin: "8px 0 0",
                  }}
                >
                  {raw.stderr}
                </pre>
              )}
            </div>
          )}

          {/* ── Findings ─────────────────────────────────────────────── */}
          {scan.findings.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <p
                style={{
                  margin: "0 0 12px",
                  fontSize: 13,
                  color: "#94a3b8",
                }}
              >
                {scan.findings.length} finding(s)
              </p>
              {scan.findings.map((f) => {
                const c = SEV_COLOR[f.severity] || "#6b7280";
                return (
                  <div
                    key={f.id}
                    style={{
                      border: `1px solid ${c}44`,
                      borderLeft: `3px solid ${c}`,
                      borderRadius: 8,
                      padding: "12px 16px",
                      marginBottom: 10,
                      background: "#0f172a",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        marginBottom: 6,
                        gap: 10,
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 600,
                          color: "#f1f5f9",
                          fontSize: 14,
                        }}
                      >
                        {f.title}
                      </span>
                      <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                        <Badge label={f.severity.toUpperCase()} color={c} />
                        <span
                          style={{
                            fontSize: 11,
                            color: "#64748b",
                            padding: "3px 8px",
                            background: "#1e293b",
                            borderRadius: 6,
                          }}
                        >
                          Risk {f.risk_score}
                        </span>
                      </div>
                    </div>
                    {f.description && (
                      <p
                        style={{
                          color: "#94a3b8",
                          fontSize: 13,
                          margin: "0 0 6px",
                        }}
                      >
                        {f.description}
                      </p>
                    )}
                    {f.evidence && (
                      <pre
                        style={{
                          background: "#020617",
                          color: "#67e8f9",
                          borderRadius: 6,
                          padding: "8px 12px",
                          fontSize: 12,
                          overflowX: "auto",
                          margin: "6px 0",
                        }}
                      >
                        {f.evidence}
                      </pre>
                    )}
                    {f.recommendation && (
                      <p
                        style={{
                          color: "#4ade80",
                          fontSize: 12,
                          margin: "6px 0 0",
                        }}
                      >
                        💡 {f.recommendation}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {scan.findings.length === 0 && scan.status === "SUCCESS" && (
            <div style={{ textAlign: "center", padding: "30px 0" }}>
              <p style={{ fontSize: 32 }}>✅</p>
              <p style={{ color: "#4ade80", fontWeight: 600 }}>
                No findings detected
              </p>
              <p style={{ color: "#64748b", fontSize: 13 }}>
                The scan completed without identifying any issues.
              </p>
            </div>
          )}

          {scan.error_message && (
            <div style={{ ...g.errorBox, marginBottom: 14 }}>
              <b>Error:</b> {scan.error_message}
            </div>
          )}

          {/* ── Services ─────────────────────────────────────────────── */}
          {scan.services.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <p
                style={{
                  fontWeight: 600,
                  color: "#94a3b8",
                  fontSize: 13,
                  marginBottom: 8,
                }}
              >
                Open Services ({scan.services.length})
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {scan.services.map((svc) => (
                  <span
                    key={svc.id}
                    style={{
                      background: "#1e293b",
                      border: "1px solid #334155",
                      borderRadius: 6,
                      padding: "4px 10px",
                      fontSize: 12,
                      color: "#e2e8f0",
                    }}
                  >
                    {svc.port}/{svc.protocol} {svc.name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ── Web endpoints ────────────────────────────────────────── */}
          {scan.web_endpoints.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <p
                style={{
                  fontWeight: 600,
                  color: "#94a3b8",
                  fontSize: 13,
                  marginBottom: 8,
                }}
              >
                Web Endpoints ({scan.web_endpoints.length})
              </p>
              {scan.web_endpoints.slice(0, 10).map((ep) => (
                <div
                  key={ep.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    padding: "6px 0",
                    borderBottom: "1px solid #1e293b",
                    fontSize: 13,
                  }}
                >
                  <span
                    style={{
                      color:
                        ep.status_code && ep.status_code < 400
                          ? "#4ade80"
                          : "#f87171",
                      fontWeight: 700,
                      minWidth: 36,
                    }}
                  >
                    {ep.status_code || "?"}
                  </span>
                  <a
                    href={ep.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      color: "#67e8f9",
                      textDecoration: "none",
                      flex: 1,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {ep.url}
                  </a>
                  {ep.title && (
                    <span style={{ color: "#64748b", fontSize: 11 }}>
                      {ep.title}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* ── Assets ───────────────────────────────────────────────── */}
          {scan.assets.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <p
                style={{
                  fontWeight: 600,
                  color: "#94a3b8",
                  fontSize: 13,
                  marginBottom: 8,
                }}
              >
                Discovered Assets ({scan.assets.length})
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {scan.assets.map((a) => (
                  <span
                    key={`${a.id}-${a.role}`}
                    style={{
                      background: "#1e293b",
                      border: "1px solid #334155",
                      borderRadius: 6,
                      padding: "4px 10px",
                      fontSize: 12,
                      color: "#e2e8f0",
                    }}
                    title={a.role}
                  >
                    <span style={{ color: "#14b8a6", marginRight: 6 }}>
                      {a.type}
                    </span>
                    {a.value}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </Modal>
  );
}
