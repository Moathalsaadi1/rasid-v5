import { useCallback, useEffect, useState } from "react";
import { listFindings } from "../api/client";
import Badge from "../components/Badge";
import Pagination from "../components/Pagination";
import { fmtDate, SEV_COLOR } from "../utils/format";
import { g } from "../utils/styles";
import type { Finding, Severity } from "../types";

interface Props {
  apiKey: string;
}

const PAGE_SIZE = 25;
const SEVERITIES: (Severity | "")[] = ["", "critical", "high", "medium", "low", "info"];

export default function FindingsView({ apiKey }: Props) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [severity, setSeverity] = useState<Severity | "">("");
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await listFindings(apiKey, {
        page,
        per_page: PAGE_SIZE,
        severity: severity || undefined,
      });
      setFindings(d.findings);
      setTotal(d.total);
    } finally {
      setLoading(false);
    }
  }, [apiKey, page, severity]);

  useEffect(() => {
    load();
  }, [load]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div style={g.gap}>
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
          <span>Findings ({total})</span>
          <div style={{ display: "flex", gap: 8 }}>
            {SEVERITIES.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setSeverity(s);
                  setPage(1);
                }}
                style={{
                  ...g.btnSm,
                  ...(severity === s
                    ? { background: "#14b8a6", color: "#06261f" }
                    : {}),
                }}
              >
                {s ? s.charAt(0).toUpperCase() + s.slice(1) : "All"}
              </button>
            ))}
          </div>
        </div>

        <div style={{ padding: "0 20px 20px", overflowX: "auto" }}>
          {loading ? (
            <p style={g.empty}>Loading…</p>
          ) : findings.length === 0 ? (
            <p style={g.empty}>No findings.</p>
          ) : (
            <table
              style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
            >
              <thead>
                <tr>
                  {["Title", "Severity", "Risk", "Confidence", "When"].map(
                    (h) => (
                      <th
                        key={h}
                        style={{
                          textAlign: "left",
                          padding: "8px 10px",
                          color: "#64748b",
                          borderBottom: "1px solid #1e293b",
                        }}
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {findings.map((f) => {
                  const c = SEV_COLOR[f.severity] || "#6b7280";
                  return (
                    <tr key={f.id}>
                      <td style={g.td}>
                        <div style={{ fontWeight: 600, color: "#f1f5f9" }}>
                          {f.title}
                        </div>
                        {f.description && (
                          <div
                            style={{
                              color: "#64748b",
                              fontSize: 12,
                              marginTop: 3,
                              maxWidth: 420,
                              whiteSpace: "nowrap",
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                            }}
                          >
                            {f.description}
                          </div>
                        )}
                      </td>
                      <td style={g.td}>
                        <Badge label={f.severity.toUpperCase()} color={c} />
                      </td>
                      <td style={g.td}>
                        <span
                          style={{
                            color: f.risk_score > 70 ? "#ef4444" : "#f8fafc",
                            fontWeight: 700,
                          }}
                        >
                          {f.risk_score}
                        </span>
                      </td>
                      <td style={g.td}>{f.confidence}</td>
                      <td style={g.td}>{fmtDate(f.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
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
