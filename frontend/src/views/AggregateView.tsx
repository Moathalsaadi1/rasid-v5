import { useCallback, useState } from "react";
import { getAggregate } from "../api/client";
import { g } from "../utils/styles";

interface AggEntry {
  value: string; sources: string[]; confidence: "low"|"medium"|"high";
  first_seen: string|null; last_seen: string|null; service?: string;
  state?: string; status_code?: number; title?: string; webserver?: string;
  severity?: string; description?: string;
}
interface Pagination { page:number; per_page:number; total:number; total_pages:number; category:string|null; }
interface AggregateData {
  target:string; summary:Record<string,number>; pagination:Pagination;
  results:{ subdomain:AggEntry[]; port:AggEntry[]; http_endpoint:AggEntry[]; vulnerability:AggEntry[]; };
}
interface Props { apiKey: string; }

const CONF_COLOR: Record<string,string> = { high:"#22c55e", medium:"#f59e0b", low:"#64748b" };
const SEV_COLOR: Record<string,string> = { critical:"#ef4444", high:"#f97316", medium:"#f59e0b", low:"#22c55e", info:"#64748b" };
const COL_HEAD: React.CSSProperties = { padding:"10px 14px", textAlign:"left", fontSize:11, fontWeight:700, color:"#64748b", textTransform:"uppercase", letterSpacing:0.6, borderBottom:"1px solid rgba(255,255,255,0.05)", whiteSpace:"nowrap" };
const COL_CELL: React.CSSProperties = { padding:"11px 14px", fontSize:13, color:"#cbd5e1", borderBottom:"1px solid rgba(255,255,255,0.03)", verticalAlign:"middle" };
const CODE: React.CSSProperties = { fontFamily:"monospace", fontSize:12, color:"#e2e8f0", background:"rgba(0,0,0,0.25)", padding:"2px 7px", borderRadius:6 };

function SourceTags({ sources }: { sources: string[] }) {
  return <span style={{ display:"flex", gap:4, flexWrap:"wrap" }}>{sources.map(s=>(
    <span key={s} style={{ background:"rgba(20,184,166,0.12)", color:"#99f6e4", fontSize:11, borderRadius:6, padding:"2px 8px", border:"1px solid rgba(20,184,166,0.2)" }}>{s}</span>
  ))}</span>;
}
function ConfDot({ level }: { level: string }) {
  return <span style={{ display:"inline-flex", alignItems:"center", gap:5, fontSize:12, color:CONF_COLOR[level]??"#64748b", fontWeight:600 }}>
    <span style={{ width:8, height:8, borderRadius:"50%", background:CONF_COLOR[level]??"#64748b", display:"inline-block" }}/>{level}
  </span>;
}
function SummaryCard({ icon, label, count, color }: { icon:string; label:string; count:number; color:string }) {
  return <div style={{ ...g.card, padding:"18px 22px", display:"flex", alignItems:"center", gap:14, flex:1, minWidth:160 }}>
    <div style={{ width:44, height:44, borderRadius:12, background:`${color}18`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:20, flexShrink:0 }}>{icon}</div>
    <div><p style={{ margin:0, fontSize:26, fontWeight:700, color:"#f8fafc" }}>{count.toLocaleString()}</p><p style={{ margin:"2px 0 0", fontSize:12, color:"#64748b" }}>{label}</p></div>
  </div>;
}

type TabKey = "subdomain"|"port"|"http_endpoint"|"vulnerability";
const TABS: {key:TabKey;icon:string;label:string}[] = [
  {key:"subdomain",icon:"📡",label:"Subdomains"},{key:"port",icon:"🔌",label:"Ports"},
  {key:"http_endpoint",icon:"🌐",label:"HTTP"},{key:"vulnerability",icon:"🔴",label:"Vulns"},
];
const PER_PAGE = 50;

export default function AggregateView({ apiKey }: Props) {
  const [target,setTarget]       = useState("");
  const [data,setData]           = useState<AggregateData|null>(null);
  const [loading,setLoading]     = useState(false);
  const [error,setError]         = useState("");
  const [activeTab,setActiveTab] = useState<TabKey>("subdomain");
  const [page,setPage]           = useState(1);
  const [summary,setSummary]     = useState<Record<string,number>>({});

  const load = useCallback(async (t:string, tab:TabKey, p:number, keepSummary=false) => {
    if (!t.trim()) return;
    setLoading(true); setError("");
    try {
      const d = await getAggregate(apiKey, t.trim(), { page:p, per_page:PER_PAGE, category:tab });
      setData(d);
      if (!keepSummary) setSummary(d.summary);
    } catch(e:unknown) { setError(e instanceof Error ? e.message : "Failed to load"); }
    finally { setLoading(false); }
  }, [apiKey]);

  const handleSearch = useCallback(async () => {
    if (!target.trim()) return;
    setLoading(true); setError(""); setData(null); setSummary({});
    try {
      const d = await getAggregate(apiKey, target.trim(), { page:1, per_page:PER_PAGE });
      const s = d.summary; setSummary(s);
      const best = (["subdomain","port","http_endpoint","vulnerability"] as TabKey[])
        .reduce((a,b)=>(s[b]??0)>(s[a]??0)?b:a);
      setActiveTab(best); setPage(1);
      const d2 = await getAggregate(apiKey, target.trim(), { page:1, per_page:PER_PAGE, category:best });
      setData(d2);
    } catch(e:unknown) { setError(e instanceof Error ? e.message : "Failed to load"); }
    finally { setLoading(false); }
  }, [apiKey, target]);

  const handleTabChange = (tab:TabKey) => { setActiveTab(tab); setPage(1); load(target,tab,1,true); };
  const handlePageChange = (p:number) => { setPage(p); load(target,activeTab,p,true); };
  const rows = data?.results[activeTab] ?? [];
  const pag  = data?.pagination;

  return (
    <div style={g.gap}>
      <div style={g.card}><div style={{ padding:"18px 20px" }}>
        <p style={{ margin:"0 0 12px", fontWeight:700, color:"#f8fafc", fontSize:15 }}>⬡ Aggregated Intelligence</p>
        <div style={{ display:"flex", gap:10 }}>
          <input value={target} onChange={e=>setTarget(e.target.value)} onKeyDown={e=>e.key==="Enter"&&handleSearch()}
            placeholder="Enter target (e.g. example.com)" style={{ ...g.input, flex:1, maxWidth:420 }}/>
          <button onClick={handleSearch} disabled={loading||!target.trim()} style={{ ...g.btn, opacity:loading||!target.trim()?0.5:1 }}>
            {loading?"Loading…":"Load Results"}
          </button>
        </div>
        {error&&<p style={{ margin:"10px 0 0", color:"#f87171", fontSize:13 }}>{error}</p>}
      </div></div>

      {Object.keys(summary).length>0&&(
        <div style={{ display:"flex", gap:14, flexWrap:"wrap" }}>
          <SummaryCard icon="📡" label="Subdomains"      count={summary.subdomain??0}     color="#14b8a6"/>
          <SummaryCard icon="🔌" label="Open Ports"      count={summary.port??0}           color="#6366f1"/>
          <SummaryCard icon="🌐" label="HTTP Endpoints"  count={summary.http_endpoint??0} color="#0ea5e9"/>
          <SummaryCard icon="🔴" label="Vulnerabilities" count={summary.vulnerability??0} color="#ef4444"/>
        </div>
      )}

      {data&&(
        <div style={g.card}>
          <div style={{ display:"flex", borderBottom:"1px solid rgba(255,255,255,0.05)", padding:"0 20px", gap:4 }}>
            {TABS.map(({key,icon,label})=>{
              const active=activeTab===key;
              return <button key={key} onClick={()=>handleTabChange(key)} style={{ background:"none", border:"none",
                borderBottom:active?"2px solid #14b8a6":"2px solid transparent",
                color:active?"#99f6e4":"#64748b", cursor:"pointer", padding:"14px 16px 12px",
                fontSize:13, fontWeight:active?700:400, display:"flex", alignItems:"center", gap:6 }}>
                {icon} {label}
                <span style={{ background:active?"rgba(20,184,166,0.2)":"rgba(255,255,255,0.05)",
                  color:active?"#99f6e4":"#64748b", fontSize:11, borderRadius:99, padding:"1px 8px", fontWeight:700 }}>
                  {(summary[key]??0).toLocaleString()}
                </span>
              </button>;
            })}
          </div>
          <div style={{ overflowX:"auto" }}>
            {loading?(<p style={g.empty}>Loading…</p>):rows.length===0?(<p style={g.empty}>No results.</p>):
            activeTab==="subdomain"?(
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead><tr><th style={COL_HEAD}>Subdomain</th><th style={COL_HEAD}>Sources</th><th style={COL_HEAD}>Confidence</th><th style={COL_HEAD}>Last Seen</th></tr></thead>
                <tbody>{rows.map((r,i)=><tr key={i}>
                  <td style={COL_CELL}><span style={CODE}>{r.value}</span></td>
                  <td style={COL_CELL}><SourceTags sources={r.sources}/></td>
                  <td style={COL_CELL}><ConfDot level={r.confidence}/></td>
                  <td style={{...COL_CELL,fontSize:12,color:"#475569"}}>{r.last_seen?new Date(r.last_seen).toLocaleDateString():"—"}</td>
                </tr>)}</tbody>
              </table>
            ):activeTab==="port"?(
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead><tr><th style={COL_HEAD}>Host:Port/Proto</th><th style={COL_HEAD}>Service</th><th style={COL_HEAD}>State</th><th style={COL_HEAD}>Sources</th><th style={COL_HEAD}>Confidence</th></tr></thead>
                <tbody>{rows.map((r,i)=><tr key={i}>
                  <td style={COL_CELL}><span style={CODE}>{r.value}</span></td>
                  <td style={COL_CELL}>{r.service??"—"}</td>
                  <td style={COL_CELL}><span style={{color:r.state==="open"?"#22c55e":"#94a3b8"}}>{r.state??"—"}</span></td>
                  <td style={COL_CELL}><SourceTags sources={r.sources}/></td>
                  <td style={COL_CELL}><ConfDot level={r.confidence}/></td>
                </tr>)}</tbody>
              </table>
            ):activeTab==="http_endpoint"?(
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead><tr><th style={COL_HEAD}>URL</th><th style={COL_HEAD}>Status</th><th style={COL_HEAD}>Title</th><th style={COL_HEAD}>Server</th><th style={COL_HEAD}>Sources</th></tr></thead>
                <tbody>{rows.map((r,i)=><tr key={i}>
                  <td style={COL_CELL}><a href={r.value} target="_blank" rel="noreferrer" style={{color:"#38bdf8",fontSize:13}}>{r.value}</a></td>
                  <td style={COL_CELL}>{r.status_code?<span style={{...CODE,color:(r.status_code??0)<400?"#22c55e":"#f87171"}}>{r.status_code}</span>:"—"}</td>
                  <td style={COL_CELL}>{r.title??"—"}</td>
                  <td style={COL_CELL}>{r.webserver??"—"}</td>
                  <td style={COL_CELL}><SourceTags sources={r.sources}/></td>
                </tr>)}</tbody>
              </table>
            ):(
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead><tr><th style={COL_HEAD}>Title</th><th style={COL_HEAD}>Severity</th><th style={COL_HEAD}>Description</th><th style={COL_HEAD}>Sources</th></tr></thead>
                <tbody>{rows.map((r,i)=><tr key={i}>
                  <td style={COL_CELL}>{r.value}</td>
                  <td style={COL_CELL}>{r.severity?<span style={{...CODE,color:SEV_COLOR[r.severity]??"#94a3b8"}}>{r.severity}</span>:"—"}</td>
                  <td style={{...COL_CELL,maxWidth:320,fontSize:12,color:"#94a3b8"}}>{r.description??"—"}</td>
                  <td style={COL_CELL}><SourceTags sources={r.sources}/></td>
                </tr>)}</tbody>
              </table>
            )}
          </div>
          {pag&&pag.total_pages>1&&(
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
              padding:"14px 20px", borderTop:"1px solid rgba(255,255,255,0.05)" }}>
              <span style={{ fontSize:12, color:"#475569" }}>
                Showing {((page-1)*PER_PAGE)+1}–{Math.min(page*PER_PAGE,pag.total)} of {pag.total.toLocaleString()}
              </span>
              <div style={{ display:"flex", gap:8, alignItems:"center" }}>
                <button onClick={()=>handlePageChange(page-1)} disabled={page===1||loading}
                  style={{...g.btnSm,opacity:page===1?0.4:1}}>← Prev</button>
                <span style={{ fontSize:13, color:"#94a3b8", minWidth:80, textAlign:"center" }}>{page} / {pag.total_pages}</span>
                <button onClick={()=>handlePageChange(page+1)} disabled={page>=pag.total_pages||loading}
                  style={{...g.btnSm,opacity:page>=pag.total_pages?0.4:1}}>Next →</button>
              </div>
            </div>
          )}
        </div>
      )}

      {!data&&!loading&&!error&&(
        <div style={{...g.card,padding:40,textAlign:"center"}}>
          <p style={{fontSize:32,margin:"0 0 12px"}}>⬡</p>
          <p style={{color:"#475569",fontSize:14,margin:0}}>Enter a target above to see merged results from all tools.</p>
        </div>
      )}
    </div>
  );
}
