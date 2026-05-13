import Badge from "../components/Badge";
import { fmtDate, SEV_COLOR, STATUS_COLOR } from "../utils/format";
import { g } from "../utils/styles";
import type { DashboardData } from "../types";

interface Props {
  data: DashboardData | null;
  loading: boolean;
}

export default function DashboardView({ data, loading }: Props) {
  if (loading || !data) {
    return <p style={{ color: "#64748b" }}>Loading dashboard...</p>;
  }

  const bars = [
    { label: "Critical", val: data.severity.critical || 0, color: SEV_COLOR.critical },
    { label: "High", val: data.severity.high || 0, color: SEV_COLOR.high },
    { label: "Medium", val: data.severity.medium || 0, color: SEV_COLOR.medium },
    { label: "Low", val: data.severity.low || 0, color: SEV_COLOR.low },
  ];
  const maxSev = Math.max(...bars.map((b) => b.val), 1);

  const tools = Object.entries(data.tool_counts || {});

  return (
    <div style={g.gap}>
      {/* Stat cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
        {[
          { label: "Total Scans", val: data.total_scans, icon: "◉" },
          { label: "Total Findings", val: data.total_findings, icon: "▲" },
          { label: "Critical", val: data.severity.critical || 0, icon: "⚠" },
          { label: "Successful", val: data.status_counts?.SUCCESS || 0, icon: "✓" },
        ].map(({ label, val, icon }) => (
          <div key={label} style={g.card}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                padding: 16,
              }}
            >
              <div>
                <p style={{ margin: 0, fontSize: 13, color: "#64748b" }}>{label}</p>
                <p
                  style={{
                    margin: "6px 0 0",
                    fontSize: 28,
                    fontWeight: 700,
                    color: "#14b8a6",
                  }}
                >
                  {val}
                </p>
              </div>
              <div style={g.iconBox}>
                <span style={{ fontSize: 18 }}>{icon}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Severity + tool usage */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <div style={g.card}>
          <div style={g.cardHead}>Findings by Severity</div>
          <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 10 }}>
            {bars.map((b) => (
              <div key={b.label}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 12,
                    marginBottom: 4,
                    color: "#94a3b8",
                  }}
                >
                  <span>{b.label}</span>
                  <span style={{ color: b.color, fontWeight: 700 }}>{b.val}</span>
                </div>
                <div style={{ background: "#0f172a", borderRadius: 4, height: 8 }}>
                  <div
                    style={{
                      background: b.color,
                      width: `${(b.val / maxSev) * 100}%`,
                      height: "100%",
                      borderRadius: 4,
                      transition: "width 0.3s",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={g.card}>
          <div style={g.cardHead}>Tool Usage</div>
          <div style={{ padding: 20 }}>
            {tools.length === 0 ? (
              <p style={g.empty}>No scans yet</p>
            ) : (
              tools.map(([name, count]) => (
                <div
                  key={name}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "8px 0",
                    borderBottom: "1px solid #1e293b",
                    fontSize: 13,
                  }}
                >
                  <span style={{ color: "#e2e8f0", fontFamily: "monospace" }}>
                    {name}
                  </span>
                  <span style={{ color: "#14b8a6", fontWeight: 700 }}>
                    {count}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent scans */}
      <div style={g.card}>
        <div style={g.cardHead}>Recent Scans</div>
        <div style={{ padding: "0 20px 20px" }}>
          {data.recent_scans.length === 0 ? (
            <p style={g.empty}>No scans yet</p>
          ) : (
            data.recent_scans.map((s) => (
              <div
                key={s.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "12px 0",
                  borderBottom: "1px solid #1e293b",
                }}
              >
                <div>
                  <p
                    style={{
                      margin: 0,
                      fontWeight: 600,
                      color: "#f1f5f9",
                      fontSize: 14,
                    }}
                  >
                    {s.target}
                  </p>
                  <p
                    style={{
                      margin: "4px 0 0",
                      fontSize: 12,
                      color: "#64748b",
                    }}
                  >
                    {s.tool} · {fmtDate(s.created_at)}
                  </p>
                </div>
                <Badge label={s.status} color={STATUS_COLOR[s.status] || "#64748b"} />
              </div>
            ))
          )}
        </div>
      </div>

      {/* Top risky assets */}
      {data.top_assets.length > 0 && (
        <div style={g.card}>
          <div style={g.cardHead}>Top Risky Assets</div>
          <div style={{ padding: 20, overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>
                  {["Asset", "Type", "Risk Score", "Findings", "Roles"].map((h) => (
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
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.top_assets.map((a) => (
                  <tr key={a.asset_id}>
                    <td style={g.td}>{a.value}</td>
                    <td style={g.td}>
                      <Badge label={a.type} color="#14b8a6" />
                    </td>
                    <td style={g.td}>
                      <span
                        style={{
                          color: a.highest_risk_score > 70 ? "#ef4444" : "#f8fafc",
                          fontWeight: 700,
                        }}
                      >
                        {a.highest_risk_score}
                      </span>
                    </td>
                    <td style={g.td}>{a.findings_count}</td>
                    <td style={g.td}>{a.roles.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
