import { useCallback, useEffect, useState } from "react";
import { listFindings } from "../api/client";
import Badge from "../components/Badge";
import Pagination from "../components/Pagination";
import { fmtDate, SEV_COLOR } from "../utils/format";
import { g } from "../utils/styles";
import type { Finding, Severity } from "../types";

interface Props { apiKey: string; }
interface VulnIntel {
  cve_id: string; description: string; score: number | null;
  severity: string | null; vector: string | null; cwes: string[];
  references: string[]; published: string | null; source: string;
}

const PAGE_SIZE = 25;
const SEVERITIES: (Severity | "")[] = ["", "critical", "high", "medium", "low", "info"];

function extractCVE(f: Finding): string | null {
  const text = f.title + " " + (f.description ?? "");
  const match = text.match(/CVE-\d{4}-\d+/i);
  return match ? match[0].toUpperCase() : null;
}

function VulnIntelPanel({ cveId, apiKey, onClose }: { cveId: string; apiKey: string; onClose: () => void; }) {
  const [intel, setIntel] = useState<VulnIntel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const SEV_C: Record<string, string> = { CRITICAL:"#ef4444", HIGH:"#f97316", MEDIUM:"#f59e0b", LOW:"#22c55e" };

  useEffect(() => {
    setLoading(true);
    fetch("http://localhost:8000/api/vuln-intel/" + encodeURIComponent(cveId), { headers: { "X-API-Key": apiKey } })
      .then(r => r.json())
      .then(d => { if (d.ok) setIntel(d.intel); else setError(d.error ?? "Not found"); })
      .catch(() => setError("Failed to fetch"))
      .finally(() => setLoading(false));
  }, [cveId, apiKey]);

  return (
    <div style={{ position:"fixed", inset:0, background:"rgba(0,0,0,0.7)", display:"flex",
      alignItems:"center", justifyContent:"center", zIndex:1000, padding:20 }}>
      <div style={{ background:"#0f172a", border:"1px solid rgba(255,255,255,0.1)", borderRadius:18,
        width:"100%", maxWidth:680, maxHeight:"85vh", overflow:"auto", padding:28 }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:20 }}>
          <div>
            <p style={{ margin:0, fontSize:11, color:"#14b8a6", fontWeight:700, letterSpacing:1 }}>VULNERABILITY INTELLIGENCE</p>
            <h2 style={{ margin:"4px 0 0", color:"#f8fafc", fontSize:20 }}>{cveId}</h2>
          </div>
          <button onClick={onClose} style={{ background:"rgba(255,255,255,0.06)", border:"none",
            color:"#94a3b8", width:34, height:34, borderRadius:8, cursor:"pointer", fontSize:16 }}>✕</button>
        </div>
        {loading ? <p style={{ color:"#64748b", textAlign:"center", padding:40 }}>Fetching from NVD…</p>
        : error ? <p style={{ color:"#f87171", textAlign:"center" }}>{error}</p>
        : intel ? (
          <div style={{ display:"flex", flexDirection:"column", gap:18 }}>
            <div style={{ background:"rgba(255,255,255,0.04)", borderRadius:12, padding:"16px 20px", display:"flex", gap:24, flexWrap:"wrap" }}>
              {intel.score !== null && <div>
                <p style={{ margin:0, fontSize:11, color:"#64748b" }}>CVSS SCORE</p>
                <p style={{ margin:"4px 0 0", fontSize:32, fontWeight:800, color:SEV_C[intel.severity?.toUpperCase()??""]??"#f8fafc" }}>{intel.score}</p>
              </div>}
              {intel.severity && <div>
                <p style={{ margin:0, fontSize:11, color:"#64748b" }}>SEVERITY</p>
                <p style={{ margin:"4px 0 0", fontSize:16, fontWeight:700, color:SEV_C[intel.severity.toUpperCase()]??"#f8fafc" }}>{intel.severity.toUpperCase()}</p>
              </div>}
              {intel.published && <div>
                <p style={{ margin:0, fontSize:11, color:"#64748b" }}>PUBLISHED</p>
                <p style={{ margin:"4px 0 0", fontSize:14, color:"#cbd5e1" }}>{intel.published}</p>
              </div>}
            </div>
            <div>
              <p style={{ margin:"0 0 8px", fontSize:12, fontWeight:700, color:"#64748b" }}>📖 DESCRIPTION</p>
              <p style={{ margin:0, fontSize:14, color:"#cbd5e1", lineHeight:1.7 }}>{intel.description}</p>
            </div>
            {intel.cwes.length > 0 && <div>
              <p style={{ margin:"0 0 8px", fontSize:12, fontWeight:700, color:"#64748b" }}>🔗 WEAKNESS TYPES (CWE)</p>
              <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                {intel.cwes.map(c => (
                  <a key={c} href={"https://cwe.mitre.org/data/definitions/"+c.replace("CWE-","")+".html"}
                    target="_blank" rel="noreferrer" style={{ background:"rgba(99,102,241,0.15)", color:"#a5b4fc",
                    fontSize:12, padding:"4px 12px", borderRadius:8, border:"1px solid rgba(99,102,241,0.3)", textDecoration:"none" }}>{c}</a>
                ))}
              </div>
            </div>}
            <div style={{ background:"rgba(20,184,166,0.08)", border:"1px solid rgba(20,184,166,0.2)", borderRadius:12, padding:"14px 18px" }}>
              <p style={{ margin:"0 0 6px", fontSize:12, fontWeight:700, color:"#14b8a6" }}>🎓 EDUCATIONAL NOTE</p>
              <p style={{ margin:0, fontSize:13, color:"#94a3b8", lineHeight:1.6 }}>
                This information is provided for educational and awareness purposes only. Understanding vulnerabilities helps defenders implement proper mitigations. Always obtain proper authorization before testing any system.
              </p>
            </div>
            {intel.references.length > 0 && <div>
              <p style={{ margin:"0 0 8px", fontSize:12, fontWeight:700, color:"#64748b" }}>📚 REFERENCES</p>
              <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
                {intel.references.map((r,i) => <a key={i} href={r} target="_blank" rel="noreferrer" style={{ color:"#38bdf8", fontSize:12, wordBreak:"break-all" }}>{r}</a>)}
              </div>
            </div>}
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function FindingsView({ apiKey }: Props) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [severity, setSeverity] = useState<Severity | "">("");
  const [page, setPage] = useState(1);
  const [selectedCVE, setSelectedCVE] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const d = await listFindings(apiKey, { page, per_page: PAGE_SIZE, severity: severity || undefined });
      setFindings(d.findings); setTotal(d.total);
    } finally { setLoading(false); }
  }, [apiKey, page, severity]);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={g.gap}>
      <div style={g.card}>
        <div style={{ ...g.cardHead, display:"flex", justifyContent:"space-between", alignItems:"center", gap:12, flexWrap:"wrap" }}>
          <span>Findings ({total})</span>
          <div style={{ display:"flex", gap:8 }}>
            {SEVERITIES.map(s => (
              <button key={s} onClick={() => { setSeverity(s); setPage(1); }}
                style={{ ...g.btnSm, ...(severity===s?{background:"#14b8a6",color:"#06261f"}:{}) }}>
                {s ? s.charAt(0).toUpperCase()+s.slice(1) : "All"}
              </button>
            ))}
          </div>
        </div>
        <div style={{ padding:"0 20px 20px", overflowX:"auto" }}>
          {loading ? <p style={g.empty}>Loading…</p>
          : findings.length===0 ? <p style={g.empty}>No findings.</p>
          : (
            <table style={{ width:"100%", borderCollapse:"collapse", fontSize:13 }}>
              <thead><tr>
                {["Title","Severity","Risk","Confidence","Intel","When"].map(h => (
                  <th key={h} style={{ textAlign:"left", padding:"8px 10px", color:"#64748b", borderBottom:"1px solid #1e293b" }}>{h}</th>
                ))}
              </tr></thead>
              <tbody>{findings.map(f => {
                const c = SEV_COLOR[f.severity]||"#6b7280";
                const cve = extractCVE(f);
                return <tr key={f.id}>
                  <td style={g.td}>
                    <div style={{ fontWeight:600, color:"#f1f5f9" }}>{f.title}</div>
                    {f.description && <div style={{ color:"#64748b", fontSize:12, marginTop:3, maxWidth:420, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>{f.description}</div>}
                  </td>
                  <td style={g.td}><Badge label={f.severity.toUpperCase()} color={c}/></td>
                  <td style={g.td}><span style={{ color:f.risk_score>70?"#ef4444":"#f8fafc", fontWeight:700 }}>{f.risk_score}</span></td>
                  <td style={g.td}>{f.confidence}</td>
                  <td style={g.td}>{cve
                    ? <button onClick={() => setSelectedCVE(cve)} style={{ background:"rgba(20,184,166,0.12)", border:"1px solid rgba(20,184,166,0.25)", color:"#99f6e4", fontSize:11, borderRadius:7, padding:"3px 10px", cursor:"pointer", fontWeight:600 }}>🔍 {cve}</button>
                    : <span style={{ color:"#334155", fontSize:12 }}>—</span>}
                  </td>
                  <td style={g.td}>{fmtDate(f.created_at)}</td>
                </tr>;
              })}</tbody>
            </table>
          )}
        </div>
        <Pagination page={page} totalPages={Math.ceil(total/PAGE_SIZE)} onPage={p => setPage(p)}/>
      </div>
      {selectedCVE && <VulnIntelPanel cveId={selectedCVE} apiKey={apiKey} onClose={() => setSelectedCVE(null)}/>}
    </div>
  );
}