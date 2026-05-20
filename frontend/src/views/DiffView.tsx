import { useCallback, useEffect, useState } from "react";
import { g } from "../utils/styles";

interface ScanOption { id:number; tool:string; target:string; created_at:string; items_count?:number; status:string; }
interface ScanInfo { id:number; tool:string; target:string; created_at:string; items_count:number; }
interface DiffSummary { added:number; removed:number; unchanged:number; }
interface DiffResult {
  ok:boolean; scan_a:ScanInfo; scan_b:ScanInfo;
  diff:{ added:string[]; removed:string[]; unchanged:string[]; summary:DiffSummary; };
}
interface Props { apiKey: string; }

const TOOLS = ["nmap","masscan","subfinder","amass","httpx","nuclei","massdns"];
const ROW: React.CSSProperties = { padding:"9px 16px", fontSize:13, borderBottom:"1px solid rgba(255,255,255,0.03)", display:"flex", alignItems:"center", gap:10 };

export default function DiffView({ apiKey }: Props) {
  const [target, setTarget]   = useState("");
  const [tool, setTool]       = useState("nmap");
  const [scans, setScans]     = useState<ScanOption[]>([]);
  const [scanA, setScanA]     = useState<number|null>(null);
  const [scanB, setScanB]     = useState<number|null>(null);
  const [result, setResult]   = useState<DiffResult|null>(null);
  const [loading, setLoading] = useState(false);
  const [loadingScans, setLoadingScans] = useState(false);
  const [error, setError]     = useState("");
  const [showUnchanged, setShowUnchanged] = useState(false);

  // Load scans for target+tool
  const loadScans = useCallback(async () => {
    if (!target.trim()) return;
    setLoadingScans(true); setScans([]); setScanA(null); setScanB(null); setResult(null);
    try {
      const r = await fetch(
        `http://localhost:8000/api/scans?target=${encodeURIComponent(target.trim())}&tool=${tool}&per_page=20&status=SUCCESS`,
        { headers: { "X-API-Key": apiKey } }
      );
      const d = await r.json();
      const list: ScanOption[] = (d.scans ?? []).sort(
        (a: ScanOption, b: ScanOption) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
      setScans(list);
      if (list.length >= 2) { setScanB(list[0].id); setScanA(list[1].id); }
      else if (list.length === 1) { setScanB(list[0].id); }
    } catch { setError("Failed to load scans"); }
    finally { setLoadingScans(false); }
  }, [apiKey, target, tool]);

  const run = useCallback(async () => {
    if (!scanA || !scanB) return;
    setLoading(true); setError(""); setResult(null);
    try {
      const r = await fetch(
        `http://localhost:8000/api/scans/diff?scan_a=${scanA}&scan_b=${scanB}`,
        { headers: { "X-API-Key": apiKey } }
      );
      const d = await r.json();
      if (!d.ok) setError(d.error ?? "Failed");
      else setResult(d);
    } catch { setError("Request failed"); }
    finally { setLoading(false); }
  }, [apiKey, scanA, scanB]);

  const s = result?.diff.summary;

  return (
    <div style={g.gap}>
      {/* Step 1: Target + Tool */}
      <div style={g.card}>
        <div style={{ padding:"18px 20px" }}>
          <p style={{ margin:"0 0 14px", fontWeight:700, color:"#f8fafc", fontSize:15 }}>⚖ Scan Diff</p>
          <div style={{ display:"flex", gap:10, flexWrap:"wrap", alignItems:"flex-end" }}>
            <div>
              <p style={{ margin:"0 0 6px", fontSize:12, color:"#64748b" }}>Target</p>
              <input value={target} onChange={e=>setTarget(e.target.value)}
                onKeyDown={e=>e.key==="Enter"&&loadScans()}
                placeholder="example.com" style={{ ...g.input, width:220 }}/>
            </div>
            <div>
              <p style={{ margin:"0 0 6px", fontSize:12, color:"#64748b" }}>Tool</p>
              <select value={tool} onChange={e=>setTool(e.target.value)}
                style={{ ...g.input, width:130 }}>
                {TOOLS.map(t=><option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <button onClick={loadScans} disabled={loadingScans||!target.trim()}
              style={{ ...g.btn, opacity:loadingScans||!target.trim()?0.5:1, marginBottom:1 }}>
              {loadingScans?"Loading…":"Load Scans"}
            </button>
          </div>
        </div>
      </div>

      {/* Step 2: Pick scans */}
      {scans.length > 0 && (
        <div style={g.card}>
          <div style={{ padding:"14px 20px 10px", borderBottom:"1px solid rgba(255,255,255,0.05)" }}>
            <p style={{ margin:0, fontSize:13, fontWeight:700, color:"#f8fafc" }}>
              {scans.length} successful {tool} scans found for {target}
            </p>
          </div>
          <div style={{ padding:"14px 20px", display:"flex", gap:20, flexWrap:"wrap" }}>
            <div style={{ flex:1, minWidth:200 }}>
              <p style={{ margin:"0 0 8px", fontSize:12, color:"#64748b", fontWeight:700 }}>SCAN A (older baseline)</p>
              <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                {scans.map(sc=>(
                  <label key={sc.id} style={{ display:"flex", alignItems:"center", gap:8,
                    padding:"8px 12px", borderRadius:8, cursor:"pointer",
                    background: scanA===sc.id ? "rgba(20,184,166,0.12)" : "rgba(255,255,255,0.03)",
                    border: scanA===sc.id ? "1px solid rgba(20,184,166,0.3)" : "1px solid transparent" }}>
                    <input type="radio" name="scanA" checked={scanA===sc.id}
                      onChange={()=>setScanA(sc.id)} style={{ accentColor:"#14b8a6" }}/>
                    <div>
                      <span style={{ fontSize:13, color:"#e2e8f0", fontWeight:600 }}>#{sc.id}</span>
                      <span style={{ fontSize:12, color:"#64748b", marginLeft:8 }}>
                        {new Date(sc.created_at).toLocaleString()}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
            </div>
            <div style={{ flex:1, minWidth:200 }}>
              <p style={{ margin:"0 0 8px", fontSize:12, color:"#64748b", fontWeight:700 }}>SCAN B (newer)</p>
              <div style={{ display:"flex", flexDirection:"column", gap:6 }}>
                {scans.map(sc=>(
                  <label key={sc.id} style={{ display:"flex", alignItems:"center", gap:8,
                    padding:"8px 12px", borderRadius:8, cursor:"pointer",
                    background: scanB===sc.id ? "rgba(99,102,241,0.12)" : "rgba(255,255,255,0.03)",
                    border: scanB===sc.id ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent" }}>
                    <input type="radio" name="scanB" checked={scanB===sc.id}
                      onChange={()=>setScanB(sc.id)} style={{ accentColor:"#6366f1" }}/>
                    <div>
                      <span style={{ fontSize:13, color:"#e2e8f0", fontWeight:600 }}>#{sc.id}</span>
                      <span style={{ fontSize:12, color:"#64748b", marginLeft:8 }}>
                        {new Date(sc.created_at).toLocaleString()}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          </div>
          <div style={{ padding:"0 20px 16px" }}>
            <button onClick={run} disabled={loading||!scanA||!scanB||scanA===scanB}
              style={{ ...g.btn, opacity:loading||!scanA||!scanB||scanA===scanB?0.5:1 }}>
              {loading?"Comparing…":"⚖ Compare Scans"}
            </button>
            {scanA===scanB && <span style={{ fontSize:12, color:"#f87171", marginLeft:12 }}>Select different scans</span>}
          </div>
        </div>
      )}

      {scans.length===0 && !loadingScans && target && (
        <div style={{ ...g.card, padding:24, textAlign:"center" }}>
          <p style={{ color:"#475569", fontSize:13, margin:0 }}>
            No successful {tool} scans found for "{target}". Run at least 2 scans first.
          </p>
        </div>
      )}

      {error && <p style={{ color:"#f87171", fontSize:13, padding:"0 4px" }}>{error}</p>}

      {/* Results */}
      {result && (
        <>
          <div style={{ display:"flex", gap:14, flexWrap:"wrap" }}>
            {[
              { label:"Added",     count:s!.added,     color:"#22c55e", icon:"🟢" },
              { label:"Removed",   count:s!.removed,   color:"#ef4444", icon:"🔴" },
              { label:"Unchanged", count:s!.unchanged, color:"#64748b", icon:"⚪" },
            ].map(({label,count,color,icon})=>(
              <div key={label} style={{ ...g.card, flex:1, minWidth:140, padding:"16px 20px",
                display:"flex", alignItems:"center", gap:12 }}>
                <span style={{ fontSize:22 }}>{icon}</span>
                <div>
                  <p style={{ margin:0, fontSize:28, fontWeight:800, color }}>{count}</p>
                  <p style={{ margin:"2px 0 0", fontSize:12, color:"#64748b" }}>{label}</p>
                </div>
              </div>
            ))}
          </div>

          <div style={g.card}>
            {result.diff.added.length>0&&(
              <div>
                <div style={{ padding:"14px 16px 10px", borderBottom:"1px solid rgba(255,255,255,0.05)" }}>
                  <span style={{ fontSize:13, fontWeight:700, color:"#22c55e" }}>🟢 Added ({result.diff.added.length})</span>
                </div>
                {result.diff.added.map((item,i)=>(
                  <div key={i} style={{ ...ROW, borderLeft:"3px solid #22c55e" }}>
                    <span style={{ color:"#22c55e", fontSize:10, fontWeight:700, minWidth:30 }}>NEW</span>
                    <span style={{ fontFamily:"monospace", fontSize:12, color:"#e2e8f0" }}>{item}</span>
                  </div>
                ))}
              </div>
            )}
            {result.diff.removed.length>0&&(
              <div>
                <div style={{ padding:"14px 16px 10px", borderBottom:"1px solid rgba(255,255,255,0.05)",
                  borderTop:result.diff.added.length>0?"1px solid rgba(255,255,255,0.05)":"none" }}>
                  <span style={{ fontSize:13, fontWeight:700, color:"#ef4444" }}>🔴 Removed ({result.diff.removed.length})</span>
                </div>
                {result.diff.removed.map((item,i)=>(
                  <div key={i} style={{ ...ROW, borderLeft:"3px solid #ef4444" }}>
                    <span style={{ color:"#ef4444", fontSize:10, fontWeight:700, minWidth:30 }}>GONE</span>
                    <span style={{ fontFamily:"monospace", fontSize:12, color:"#94a3b8", textDecoration:"line-through" }}>{item}</span>
                  </div>
                ))}
              </div>
            )}
            {result.diff.unchanged.length>0&&(
              <div>
                <div style={{ padding:"14px 16px 10px", borderTop:"1px solid rgba(255,255,255,0.05)",
                  display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <span style={{ fontSize:13, fontWeight:700, color:"#64748b" }}>⚪ Unchanged ({result.diff.unchanged.length})</span>
                  <button onClick={()=>setShowUnchanged(!showUnchanged)} style={{ ...g.btnSm, fontSize:11 }}>
                    {showUnchanged?"Hide":"Show"}
                  </button>
                </div>
                {showUnchanged&&result.diff.unchanged.map((item,i)=>(
                  <div key={i} style={{ ...ROW, borderLeft:"3px solid #1e293b" }}>
                    <span style={{ color:"#334155", fontSize:10, fontWeight:700, minWidth:30 }}>SAME</span>
                    <span style={{ fontFamily:"monospace", fontSize:12, color:"#475569" }}>{item}</span>
                  </div>
                ))}
              </div>
            )}
            {result.diff.added.length===0&&result.diff.removed.length===0&&(
              <p style={{ ...g.empty, color:"#22c55e" }}>✓ No changes between the two scans.</p>
            )}
          </div>
        </>
      )}

      {!result&&!loading&&!error&&scans.length===0&&!target&&(
        <div style={{ ...g.card, padding:40, textAlign:"center" }}>
          <p style={{ fontSize:32, margin:"0 0 12px" }}>⚖</p>
          <p style={{ color:"#475569", fontSize:14, margin:0 }}>
            Enter a target and tool above, then compare two scans to track changes over time.
          </p>
        </div>
      )}
    </div>
  );
}
