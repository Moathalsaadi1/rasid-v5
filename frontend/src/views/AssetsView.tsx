import { useCallback, useEffect, useState } from "react";
import { listAssets } from "../api/client";
import Badge from "../components/Badge";
import Pagination from "../components/Pagination";
import { fmtDate } from "../utils/format";
import { g } from "../utils/styles";
import type { AssetItem } from "../types";

interface Props {
  apiKey: string;
}

const PAGE_SIZE = 25;

export default function AssetsView({ apiKey }: Props) {
  const [assets, setAssets] = useState<AssetItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await listAssets(apiKey, { page, per_page: PAGE_SIZE });
      setAssets(d.assets);
      setTotal(d.total);
    } finally {
      setLoading(false);
    }
  }, [apiKey, page]);

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
          }}
        >
          <span>Discovered Assets ({total})</span>
          <button onClick={load} style={g.btnSm}>
            ↻ Refresh
          </button>
        </div>

        <div style={{ padding: "0 20px 20px", overflowX: "auto" }}>
          {loading ? (
            <p style={g.empty}>Loading…</p>
          ) : assets.length === 0 ? (
            <p style={g.empty}>No assets discovered yet.</p>
          ) : (
            <table
              style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
            >
              <thead>
                <tr>
                  {["Value", "Type", "Risk", "Findings", "First seen"].map(
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
                {assets.map((a) => (
                  <tr key={a.id}>
                    <td style={g.td}>
                      <code style={{ color: "#67e8f9", fontSize: 12 }}>
                        {a.value}
                      </code>
                    </td>
                    <td style={g.td}>
                      <Badge label={a.type} color="#14b8a6" />
                    </td>
                    <td style={g.td}>
                      <span
                        style={{
                          color:
                            a.highest_risk_score > 70 ? "#ef4444" : "#f8fafc",
                          fontWeight: 700,
                        }}
                      >
                        {a.highest_risk_score}
                      </span>
                    </td>
                    <td style={g.td}>{a.findings_count}</td>
                    <td style={g.td}>{fmtDate(a.created_at)}</td>
                  </tr>
                ))}
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
