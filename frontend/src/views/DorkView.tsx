import { useCallback, useEffect, useRef, useState } from "react";
import { g } from "../utils/styles";

interface Category { key:string; label:string; icon:string; description:string; count:number; }
interface DorkResult { dork:string; count:number; results:{title:string;url:string;snippet:string}[]; }
interface DorkData { target:string; category:string; total:number; dorks:DorkResult[]; }
interface Props { apiKey: string; }

const API = "http://localhost:8000";

// Sample dorks per category for the chips display
const SAMPLE_DORKS: Record<string, string[]> = {
  exposed_files:  ["filetype:pdf", "filetype:sql", "filetype:env", "filetype:log", "filetype:bak"],
  login_pages:    ["inurl:admin", "inurl:login", "inurl:dashboard", "intitle:admin panel", "inurl:wp-admin"],
  vulnerabilities:["inurl:phpinfo.php", "intitle:Index of /", "inurl:.git", "inurl:debug", "intitle:phpMyAdmin"],
  email_harvest:  ["@domain email", "filetype:pdf email", "intext:contact email", "inurl:contact", "mailto:"],
  subdomains:     ["site:*.domain", "site:domain -www", "inurl:domain", "related:domain", "link:domain"],
  sensitive_info: ["api_key", "DB_PASSWORD", "Authorization: Bearer", "private key", "filetype:env secret"],
};

const COL_CELL: React.CSSProperties = {
  padding:"12px 16px", fontSize:13, color:"#cbd5e1",
  borderBottom:"1px solid rgba(255,255,255,0.03)", verticalAlign:"top",
};

export default function DorkView({ apiKey }: Props) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [selected, setSelected]     = useState("exposed_files");
  const [target, setTarget]         = useState("");
  const [status, setStatus]         = useState<"idle"|"queued"|"started"|"done"|"failed">("idle");
  const [data, setData]             = useState<DorkData|null>(null);
  const [error, setError]           = useState("");
  const [activeDork, setActiveDork] = useState<string|null>(null);
  const pollRef                     = useRef<ReturnType<typeof setInterval>|null>(null);
  const inputRef                    = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch(`${API}/api/dork/categories`, { headers:{"X-API-Key":apiKey} })
      .then(r=>r.json())
      .then(d=>{ if(d.ok) setCategories(d.categories); })
      .catch(()=>{});
  }, [apiKey]);

  const stopPoll = () => { if(pollRef.current) { clearInterval(pollRef.current); pollRef.current=null; } };

  const poll = useCallback((jobId: string) => {
    pollRef.current = setInterval(async () => {
      try {
        const r = await fetch(`${API}/api/dork/result/${jobId}`, { headers:{"X-API-Key":apiKey} });
        const d = await r.json();
        setStatus(d.status);
        if (d.status==="done")   { setData(d.data); stopPoll(); }
        if (d.status==="failed") { setError(d.error??"Failed"); stopPoll(); }
      } catch { stopPoll(); }
    }, 4000);
  }, [apiKey]);

  const run = useCallback(async (cat?: string, dorkHint?: string) => {
    const t = target.trim();
    if (!t) { inputRef.current?.focus(); return; }
    const category = cat ?? selected;
    stopPoll(); setStatus("queued"); setData(null); setError(""); setActiveDork(dorkHint??null);
    try {
      const r = await fetch(`${API}/api/dork/run`, {
        method:"POST", headers:{"X-API-Key":apiKey,"Content-Type":"application/json"},
        body: JSON.stringify({ target:t, category }),
      });
      const d = await r.json();
      if (!d.ok) { setError(d.error??"Failed"); setStatus("failed"); return; }
      poll(d.job_id);
    } catch { setError("Request failed"); setStatus("failed"); }
  }, [apiKey, target, selected, poll]);

  useEffect(() => () => stopPoll(), []);

  const currentCat = categories.find(c=>c.key===selected);
  const samples    = SAMPLE_DORKS[selected] ?? [];
  const running    = status==="queued"||status==="started";
  const hasResults = data && data.dorks.some(d=>d.count>0);

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:0, minHeight:"100%" }}>
      {/* ── Top category tabs ── */}
      <div style={{ display:"flex", gap:4, padding:"0 0 20px", flexWrap:"wrap" }}>
        {categories.map(cat => {
          const active = selected===cat.key;
          return (
            <button key={cat.key} onClick={()=>{ setSelected(cat.key); setData(null); setStatus("idle"); }}
              style={{
                background: active?"#1e293b":"rgba(255,255,255,0.04)",
                border: active?"1px solid rgba(255,255,255,0.12)":"1px solid transparent",
                color: active?"#f8fafc":"#64748b",
                padding:"8px 16px", borderRadius:99, cursor:"pointer",
                fontSize:13, fontWeight:active?600:400,
                display:"flex", alignItems:"center", gap:6,
                transition:"all 0.15s",
              }}>
              <span>{cat.icon}</span> {cat.label}
              {active && <span style={{ width:6, height:6, borderRadius:"50%", background:"#14b8a6" }}/>}
            </button>
          );
        })}
      </div>

      {/* ── Main search area ── */}
      <div style={{ background:"rgba(255,255,255,0.03)", borderRadius:18,
        border:"1px solid rgba(255,255,255,0.06)", padding:"28px 28px 20px", marginBottom:20 }}>

        {/* Search bar */}
        <div style={{ display:"flex", gap:10, marginBottom:20 }}>
          <div style={{ flex:1, display:"flex", alignItems:"center", gap:12,
            background:"#0f172a", border:"1px solid rgba(255,255,255,0.1)",
            borderRadius:14, padding:"0 18px" }}>
            <span style={{ fontSize:18, color:"#475569" }}>🔍</span>
            <input
              ref={inputRef}
              value={target}
              onChange={e=>setTarget(e.target.value)}
              onKeyDown={e=>e.key==="Enter"&&run()}
              placeholder="Enter domain, keyword, or dork..."
              style={{ flex:1, background:"none", border:"none", outline:"none",
                color:"#f8fafc", fontSize:16, padding:"16px 0" }}
            />
          </div>
          <button onClick={()=>run()} disabled={running}
            style={{ background:"#f97316", border:"none", color:"white",
              padding:"0 28px", borderRadius:14, cursor:running?"not-allowed":"pointer",
              fontSize:15, fontWeight:700, opacity:running?0.7:1, whiteSpace:"nowrap" }}>
            {running ? "Searching…" : "Search"}
          </button>
        </div>

        {/* Status */}
        {status!=="idle" && (
          <div style={{ marginBottom:14 }}>
            <p style={{ margin:0, fontSize:13,
              color:status==="done"?"#22c55e":status==="failed"?"#f87171":"#f59e0b" }}>
              {status==="queued"?"⏳ Queued…"
              :status==="started"?"🔍 Running dorks (30–60s)…"
              :status==="done"?`✓ Found ${data?.total??0} results`
              :`✗ ${error}`}
            </p>
          </div>
        )}

        {/* Category description */}
        {currentCat && (
          <div style={{ background:"rgba(20,184,166,0.06)", border:"1px solid rgba(20,184,166,0.15)",
            borderRadius:10, padding:"12px 16px", marginBottom:16 }}>
            <p style={{ margin:"0 0 4px", fontSize:11, fontWeight:700, color:"#14b8a6", letterSpacing:1 }}>
              {currentCat.icon} {currentCat.label.toUpperCase()}
            </p>
            <p style={{ margin:0, fontSize:13, color:"#94a3b8" }}>{currentCat.description}</p>
          </div>
        )}

        {/* Sample dork chips */}
        <div style={{ display:"flex", flexWrap:"wrap", gap:8, alignItems:"center" }}>
          <span style={{ fontSize:11, color:"#475569", fontWeight:600, letterSpacing:0.5 }}>
            SAMPLE DORKS:
          </span>
          {samples.map((dork,i) => (
            <button key={i} onClick={()=>{ setTarget(prev=>prev); run(selected, dork); }}
              style={{
                background: activeDork===dork?"rgba(20,184,166,0.2)":"rgba(255,255,255,0.05)",
                border: activeDork===dork?"1px solid rgba(20,184,166,0.4)":"1px solid rgba(255,255,255,0.08)",
                color: activeDork===dork?"#99f6e4":"#94a3b8",
                padding:"5px 14px", borderRadius:99, cursor:"pointer",
                fontSize:12, fontFamily:"monospace", transition:"all 0.15s",
              }}>
              {dork}
            </button>
          ))}
        </div>
      </div>

      {/* ── Results ── */}
      {data && (
        <div style={g.card}>
          <div style={{ padding:"14px 20px", borderBottom:"1px solid rgba(255,255,255,0.05)",
            display:"flex", justifyContent:"space-between" }}>
            <span style={{ fontSize:14, fontWeight:700, color:"#f8fafc" }}>
              {data.total} results for <span style={{ color:"#99f6e4" }}>{data.target}</span>
            </span>
            <span style={{ fontSize:12, color:"#475569" }}>
              {data.dorks.length} dorks · {data.dorks.filter(d=>d.count>0).length} with results
            </span>
          </div>

          {!hasResults ? (
            <p style={g.empty}>No results found. Try a different target or category.</p>
          ) : (
            data.dorks.filter(d=>d.count>0).map((dork,di) => (
              <div key={di}>
                <div style={{ padding:"10px 16px", background:"rgba(249,115,22,0.06)",
                  borderBottom:"1px solid rgba(255,255,255,0.04)",
                  display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <code style={{ fontSize:12, color:"#f97316" }}>{dork.dork}</code>
                  <span style={{ fontSize:11, color:"#22c55e", fontWeight:700 }}>{dork.count} hits</span>
                </div>
                {dork.results.map((r,ri) => (
                  <div key={ri} style={{ padding:"14px 20px",
                    borderBottom:"1px solid rgba(255,255,255,0.03)" }}>
                    <a href={r.url} target="_blank" rel="noreferrer"
                      style={{ fontSize:15, color:"#60a5fa", fontWeight:600,
                        textDecoration:"none", display:"block", marginBottom:3 }}>
                      {r.title||r.url}
                    </a>
                    <p style={{ margin:"0 0 4px", fontSize:12, color:"#22c55e" }}>
                      {r.url.length>80?r.url.slice(0,80)+"…":r.url}
                    </p>
                    {r.snippet && (
                      <p style={{ margin:0, fontSize:12, color:"#64748b", lineHeight:1.5 }}>
                        {r.snippet}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      )}

      {status==="idle" && !data && (
        <div style={{ ...g.card, padding:40, textAlign:"center" }}>
          <p style={{ fontSize:32, margin:"0 0 12px" }}>🔍</p>
          <p style={{ color:"#64748b", fontSize:14, margin:"0 0 8px" }}>
            Select a category above, enter a target, and click Search.
          </p>
          <p style={{ color:"#334155", fontSize:12, margin:0 }}>
            Educational use only · Results from DuckDuckGo
          </p>
        </div>
      )}
    </div>
  );
}
