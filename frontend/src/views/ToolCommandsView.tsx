import { useCallback, useEffect, useMemo, useState } from "react";
import {
  deleteToolCommand,
  listTools,
  listToolCommands,
  toggleToolCommand,
  upsertToolCommand,
} from "../api/client";
import { toolMeta } from "../utils/format";
import { g } from "../utils/styles";
import type { ToolCommand, ToolSpec } from "../types";

interface Props {
  apiKey: string;
}

// ─── Option definitions per tool ────────────────────────────────────────────

interface ToolOption {
  id: string;
  label: string;
  desc: string;
  flags: string[];   // the actual CLI flags this option adds
  required: boolean; // required = always included, locked in UI
}

const TOOL_OPTIONS: Record<string, ToolOption[]> = {
  nmap: [
    { id: "nmap_xml",     label: "Save output as XML",          desc: "Required for report generation",          flags: ["-oX", "-"],         required: true  },
    { id: "nmap_nodns",   label: "Skip reverse DNS resolution",  desc: "Speeds up scanning",                      flags: ["-n"],               required: true  },
    { id: "nmap_top1000", label: "Scan top 1000 ports",          desc: "Faster, covers most common ports",        flags: ["--top-ports", "1000"], required: false },
    { id: "nmap_allports",label: "Scan all ports (1–65535)",     desc: "Comprehensive but slower",                flags: ["-p-"],              required: false },
    { id: "nmap_os",      label: "OS detection",                 desc: "Identify the server operating system",    flags: ["-O"],               required: false },
    { id: "nmap_syn",     label: "Stealth SYN scan",             desc: "Less noisy on the network",               flags: ["-sS"],              required: false },
    { id: "nmap_sV",      label: "Detailed version detection",   desc: "Detect exact version of each service",    flags: ["-sV", "--version-intensity", "9"], required: false },
    { id: "nmap_udp",     label: "UDP scan (top 100 ports)",     desc: "Discover UDP services",                   flags: ["-sU", "--top-ports", "100"], required: false },
  ],
  nuclei: [
    { id: "nc_jsonl",     label: "JSON-lines output",            desc: "Required for report display",             flags: ["-jsonl"],           required: true  },
    { id: "nc_omitraw",   label: "Omit raw request/response",    desc: "Cleaner output",                          flags: ["-omit-raw"],        required: true  },
    { id: "nc_crit",      label: "Critical severity only",       desc: "Highest risk findings",                   flags: ["-severity", "critical"],              required: false },
    { id: "nc_highcrit",  label: "High & Critical severity",     desc: "High + Critical",                         flags: ["-severity", "high,critical"],         required: false },
    { id: "nc_all",       label: "All severity levels",          desc: "Low through Critical",                    flags: ["-severity", "low,medium,high,critical"], required: false },
    { id: "nc_cve",       label: "CVE templates only",           desc: "Documented CVE vulnerabilities",          flags: ["-tags", "cve"],     required: false },
    { id: "nc_kev",       label: "KEV templates (actively exploited)", desc: "Known exploited vulnerabilities",  flags: ["-tags", "kev"],     required: false },
    { id: "nc_fast",      label: "Rate-limit (25 req/s, 5 concurrency)", desc: "Reduces load on the target",   flags: ["-rl", "25", "-c", "5"], required: false },
  ],
  subfinder: [
    { id: "sf_silent",    label: "Silent mode (clean output)",   desc: "Required for pipeline processing",        flags: ["-silent"],          required: true  },
    { id: "sf_all",       label: "Use all sources",              desc: "More thorough, slower",                   flags: ["-all"],             required: false },
    { id: "sf_json",      label: "JSON output",                  desc: "Structured output for later analysis",    flags: ["-oJ"],              required: false },
    { id: "sf_t10",       label: "10 concurrent threads",        desc: "Speeds up enumeration",                   flags: ["-t", "10"],         required: false },
  ],
  httpx: [
    { id: "hx_json",      label: "JSON output",                  desc: "Required for report display",             flags: ["-json"],            required: true  },
    { id: "hx_sc",        label: "Show status codes",            desc: "200, 301, 404 etc.",                      flags: ["-status-code"],     required: true  },
    { id: "hx_redir",     label: "Follow redirects",             desc: "Track redirect chains",                   flags: ["-follow-redirects"], required: false },
    { id: "hx_tech",      label: "Technology detection",         desc: "WordPress, Laravel, etc.",                flags: ["-tech-detect"],     required: false },
    { id: "hx_title",     label: "Show page title",              desc: "HTML title for each endpoint",            flags: ["-title"],           required: false },
    { id: "hx_ws",        label: "Show web server header",       desc: "nginx, Apache, etc.",                     flags: ["-web-server"],      required: false },
  ],
  masscan: [
    { id: "ms_json",      label: "JSON output",                  desc: "Required for report display",             flags: ["-oJ", "-"],         required: true  },
    { id: "ms_common",    label: "Scan common ports",            desc: "80, 443, 22, 21, 3306 …",                flags: ["-p", "21,22,23,25,53,80,110,139,143,443,445,993,995,1433,3306,3389,5432,5900,6379,8080,8443"], required: false },
    { id: "ms_allports",  label: "Scan all ports",               desc: "1 to 65535",                             flags: ["-p", "1-65535"],    required: false },
    { id: "ms_rate1k",    label: "Rate: 1 000 pkts/sec",         desc: "Safe for most networks",                  flags: ["--rate", "1000"],   required: false },
    { id: "ms_rate10k",   label: "Rate: 10 000 pkts/sec",        desc: "Very fast — watch the load",              flags: ["--rate", "10000"],  required: false },
  ],
  massdns: [
    { id: "md_resolvers", label: "Use bundled resolver list",    desc: "Required for massdns to work",            flags: ["-r", "/etc/massdns/resolvers.txt"], required: true  },
    { id: "md_json",      label: "JSON output",                  desc: "Structured results",                      flags: ["-o", "J"],          required: false },
    { id: "md_simple",    label: "Simple text output",           desc: "Human-readable",                          flags: ["-o", "S"],          required: false },
    { id: "md_t200",      label: "200 concurrent threads",       desc: "Fast for large lists",                    flags: ["-t", "200"],        required: false },
    { id: "md_t100",      label: "100 concurrent threads",       desc: "Balanced speed and stability",            flags: ["-t", "100"],        required: false },
  ],
  amass: [
    { id: "am_passive",   label: "Passive enumeration only",     desc: "No direct contact with target",           flags: ["-passive"],         required: true  },
    { id: "am_nocolor",   label: "No color output",              desc: "Required for clean parsing",              flags: ["-nocolor"],         required: true  },
    { id: "am_t5",        label: "Timeout: 5 minutes",           desc: "Max runtime per scan",                    flags: ["-timeout", "5"],    required: false },
    { id: "am_active",    label: "Active enumeration",           desc: "Direct contact — more results",           flags: ["-active"],          required: false },
  ],
};

// Build the args array from selected option IDs for a given tool.
// Required options are always included regardless of selectedIds.
function buildArgs(toolName: string, targetFlag: string, selectedIds: Set<string>): string[] {
  const opts = TOOL_OPTIONS[toolName] ?? [];
  const args: string[] = [];

  // target placeholder first (for tools that use a flag like -u or -d)
  if (targetFlag && targetFlag !== "trailing") {
    const flag = targetFlag.replace("via:", "");
    args.push(flag, "{TARGET}");
  }

  opts.forEach((opt) => {
    if (opt.required || selectedIds.has(opt.id)) {
      args.push(...opt.flags);
    }
  });

  // trailing target (for tools like masscan / massdns)
  if (!targetFlag || targetFlag === "trailing" || targetFlag === "via:{TARGET}") {
    args.push("{TARGET}");
  }

  return args;
}

// Parse existing args back into selected option IDs (best-effort).
function inferSelectedIds(toolName: string, existingArgs: string[]): Set<string> {
  const opts = TOOL_OPTIONS[toolName] ?? [];
  const argStr = existingArgs.join(" ");
  const result = new Set<string>();
  opts.forEach((opt) => {
    if (opt.required) return; // required ones are always shown checked
    const flagStr = opt.flags.join(" ");
    if (argStr.includes(flagStr)) result.add(opt.id);
  });
  return result;
}

// ─── Component ───────────────────────────────────────────────────────────────

export default function ToolCommandsView({ apiKey }: Props) {
  const [tools, setTools]       = useState<ToolSpec[]>([]);
  const [commands, setCommands] = useState<ToolCommand[]>([]);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [success, setSuccess]   = useState("");

  const [selectedTool, setSelectedTool] = useState<string>("");
  const [selectedIds, setSelectedIds]   = useState<Set<string>>(new Set());
  const [saving, setSaving]             = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [toolsRes, cmdRes] = await Promise.all([
        listTools(apiKey),
        listToolCommands(apiKey),
      ]);
      setTools(toolsRes.tools);
      setCommands(cmdRes.commands);
      if (toolsRes.tools.length > 0 && !selectedTool) {
        setSelectedTool(toolsRes.tools[0].name);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setLoading(false);
    }
  }, [apiKey, selectedTool]);

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedSpec = useMemo(
    () => tools.find((t) => t.name === selectedTool) || null,
    [tools, selectedTool],
  );

  const existingCommand = useMemo(
    () => commands.find((c) => c.tool_name === selectedTool) || null,
    [commands, selectedTool],
  );

  // When tool or saved command changes, infer checked state from saved args.
  useEffect(() => {
    if (!selectedSpec) { setSelectedIds(new Set()); return; }
    const base = existingCommand ? existingCommand.args : selectedSpec.default_args;
    setSelectedIds(inferSelectedIds(selectedTool, base));
  }, [selectedSpec, existingCommand, selectedTool]);

  function toggleOption(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  // The command that will be sent to the backend (derived from checkboxes).
  const builtArgs = useMemo(() => {
    if (!selectedSpec) return [];
    return buildArgs(selectedTool, selectedSpec.target_position, selectedIds);
  }, [selectedTool, selectedSpec, selectedIds]);

  async function save() {
    if (!selectedSpec || builtArgs.length === 0) return;
    setSaving(true); setError(""); setSuccess("");
    try {
      await upsertToolCommand(apiKey, selectedTool, builtArgs);
      setSuccess(`Saved custom command for ${selectedTool}`);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function resetToDefaults() {
    if (!selectedSpec || !existingCommand) return;
    if (!confirm(`Delete custom command for ${selectedTool}? Default args will be used.`)) return;
    try {
      await deleteToolCommand(apiKey, existingCommand.id);
      setSuccess(`Reset ${selectedTool} to defaults`);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function toggleActive(id: number) {
    try {
      await toggleToolCommand(apiKey, id);
      await load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Toggle failed");
    }
  }

  const toolOptions = TOOL_OPTIONS[selectedTool] ?? [];
  const requiredOpts  = toolOptions.filter((o) => o.required);
  const optionalOpts  = toolOptions.filter((o) => !o.required);
  const optionalCount = optionalOpts.filter((o) => selectedIds.has(o.id)).length;

  return (
    <div style={g.gap}>
      {/* ── Tool picker (left) + editor (right) ─────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "260px 1fr", gap: 14, alignItems: "stretch" }}>

        {/* Tool list */}
        <div style={g.card}>
          <div style={g.cardHead}>Tools</div>
          <div style={{ padding: 8 }}>
            {loading && tools.length === 0 ? (
              <p style={g.empty}>Loading…</p>
            ) : (
              tools.map((t) => {
                const meta = toolMeta(t.name);
                const hasCustom = commands.some((c) => c.tool_name === t.name && c.is_active);
                const isSelected = selectedTool === t.name;
                return (
                  <button
                    key={t.name}
                    onClick={() => setSelectedTool(t.name)}
                    style={{
                      width: "100%", display: "flex", alignItems: "center", gap: 10,
                      padding: "10px 12px", marginBottom: 4, borderRadius: 10,
                      border: "1px solid transparent",
                      background: isSelected ? "rgba(20,184,166,0.12)" : "transparent",
                      color: isSelected ? "#99f6e4" : "#cbd5e1",
                      cursor: "pointer", textAlign: "left", fontSize: 14,
                    }}
                  >
                    <span style={{ fontSize: 16 }}>{meta.emoji}</span>
                    <span style={{ flex: 1, fontWeight: 600 }}>{t.name}</span>
                    {hasCustom && (
                      <span title="Custom command saved" style={{ color: "#14b8a6", fontSize: 11, fontWeight: 700 }}>●</span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Options editor */}
        <div style={g.card}>
          <div style={g.cardHead}>
            {selectedSpec ? <>Edit command — <code>{selectedSpec.name}</code></> : "Select a tool"}
          </div>
          <div style={{ padding: 20 }}>
            {error   && <div style={{ ...g.errorBox,   marginBottom: 14 }}>{error}</div>}
            {success && <div style={{ ...g.successBox, marginBottom: 14 }}>{success}</div>}

            {selectedSpec && (
              <>
                <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 0, marginBottom: 18 }}>
                  {selectedSpec.description}
                </p>

                {/* ── Required options ── */}
                <div style={{ marginBottom: 18 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                    Required options
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    {requiredOpts.map((opt) => (
                      <div
                        key={opt.id}
                        style={{
                          display: "flex", alignItems: "flex-start", gap: 10,
                          padding: "10px 12px", borderRadius: 8,
                          border: "1px solid #1e293b",
                          background: "rgba(20,184,166,0.06)",
                          opacity: 0.8,
                        }}
                      >
                        <span style={{ marginTop: 1, fontSize: 13, color: "#14b8a6" }}>🔒</span>
                        <div>
                          <div style={{ fontSize: 13, color: "#94a3b8", fontWeight: 500 }}>
                            {opt.label}
                            <span style={{
                              marginLeft: 6, fontSize: 10, padding: "1px 6px",
                              borderRadius: 99, background: "rgba(234,179,8,0.15)",
                              color: "#fbbf24", fontWeight: 600,
                            }}>required</span>
                          </div>
                          <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>{opt.desc}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* ── Optional options ── */}
                <div style={{ marginBottom: 18 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8 }}>
                    Optional options
                    {optionalCount > 0 && (
                      <span style={{
                        marginLeft: 8, fontSize: 10, padding: "1px 8px",
                        borderRadius: 99, background: "rgba(20,184,166,0.15)",
                        color: "#14b8a6", fontWeight: 600,
                      }}>
                        {optionalCount} selected
                      </span>
                    )}
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    {optionalOpts.map((opt) => {
                      const isChecked = selectedIds.has(opt.id);
                      return (
                        <div
                          key={opt.id}
                          onClick={() => toggleOption(opt.id)}
                          style={{
                            display: "flex", alignItems: "flex-start", gap: 10,
                            padding: "10px 12px", borderRadius: 8, cursor: "pointer",
                            border: isChecked ? "1px solid #14b8a6" : "1px solid #1e293b",
                            background: isChecked ? "rgba(20,184,166,0.1)" : "transparent",
                            transition: "all 0.15s",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleOption(opt.id)}
                            onClick={(e) => e.stopPropagation()}
                            style={{ marginTop: 2, accentColor: "#14b8a6", flexShrink: 0 }}
                          />
                          <div>
                            <div style={{ fontSize: 13, color: isChecked ? "#e2e8f0" : "#94a3b8", fontWeight: 500 }}>
                              {opt.label}
                            </div>
                            <div style={{ fontSize: 11, color: "#475569", marginTop: 2 }}>{opt.desc}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* ── Generated command preview ── */}
                <div style={{
                  background: "#0f172a", border: "1px solid #1e293b",
                  borderRadius: 8, padding: 12, fontSize: 12,
                  color: "#94a3b8", marginBottom: 16,
                }}>
                  <div style={{ marginBottom: 6 }}>
                    <span style={{ color: "#475569" }}>Generated command:</span>
                  </div>
                  <code style={{ color: "#67e8f9", wordBreak: "break-all", lineHeight: 1.6 }}>
                    {builtArgs.join(" ")}
                  </code>
                  <div style={{ marginTop: 8 }}>
                    <span style={{ color: "#475569" }}>Timeout:</span>{" "}
                    <span style={{ color: "#cbd5e1" }}>{selectedSpec.timeout_seconds}s</span>
                  </div>
                </div>

                {/* Default reference */}
                <div style={{
                  background: "#0f172a", border: "1px solid #1e293b",
                  borderRadius: 8, padding: 12, fontSize: 12,
                  color: "#94a3b8", marginBottom: 16,
                }}>
                  <span style={{ color: "#475569" }}>Default:</span>{" "}
                  <code style={{ color: "#64748b" }}>{selectedSpec.default_args.join(" ")}</code>
                </div>

                {/* Action buttons */}
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button onClick={save} disabled={saving} style={g.btnPrimary}>
                    {saving ? "Saving…" : existingCommand ? "Update" : "Save Custom"}
                  </button>
                  {existingCommand && (
                    <>
                      <button onClick={() => toggleActive(existingCommand.id)} style={g.btnSm}>
                        {existingCommand.is_active ? "Disable" : "Enable"}
                      </button>
                      <button onClick={resetToDefaults} style={g.btnDanger}>
                        Reset to defaults
                      </button>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Saved commands summary ──────────────────────────────────── */}
      {commands.length > 0 && (
        <div style={g.card}>
          <div style={g.cardHead}>Saved Custom Commands ({commands.length})</div>
          <div style={{ padding: "0 20px 20px" }}>
            {commands.map((c) => (
              <div
                key={c.id}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "12px 0", borderBottom: "1px solid #1e293b",
                  gap: 10, opacity: c.is_active ? 1 : 0.55,
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 600, color: "#f1f5f9", fontSize: 14, marginBottom: 2 }}>
                    {toolMeta(c.tool_name).emoji} {c.tool_name}
                    {!c.is_active && (
                      <span style={{ marginLeft: 8, fontSize: 11, color: "#f87171" }}>(disabled)</span>
                    )}
                  </div>
                  <code style={{
                    color: "#67e8f9", fontSize: 12, display: "block",
                    whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                  }}>
                    {c.args.join(" ")}
                  </code>
                </div>
                <button onClick={() => setSelectedTool(c.tool_name)} style={g.btnSm}>
                  Edit →
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
