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

// FR-12: lets users customize the args RASID passes to each tool, and save
// the result so subsequent scans of that tool use the customized command.
// Backend whitelists allowed flags per tool — the UI surfaces them.
export default function ToolCommandsView({ apiKey }: Props) {
  const [tools, setTools] = useState<ToolSpec[]>([]);
  const [commands, setCommands] = useState<ToolCommand[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // editor state
  const [selectedTool, setSelectedTool] = useState<string>("");
  const [argsInput, setArgsInput] = useState("");
  const [saving, setSaving] = useState(false);

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

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedSpec = useMemo(
    () => tools.find((t) => t.name === selectedTool) || null,
    [tools, selectedTool],
  );

  const existingCommand = useMemo(
    () => commands.find((c) => c.tool_name === selectedTool) || null,
    [commands, selectedTool],
  );

  // When the selected tool changes, prefill the editor with the saved
  // command (if any) or the tool's defaults.
  useEffect(() => {
    if (!selectedSpec) {
      setArgsInput("");
      return;
    }
    if (existingCommand) {
      setArgsInput(existingCommand.args.join(" "));
    } else {
      setArgsInput(selectedSpec.default_args.join(" "));
    }
  }, [selectedSpec, existingCommand]);

  async function save() {
    if (!selectedSpec) return;
    const parsed = argsInput
      .split(/\s+/)
      .map((s) => s.trim())
      .filter(Boolean);

    if (parsed.length === 0) {
      setError("Args cannot be empty");
      return;
    }

    setSaving(true);
    setError("");
    setSuccess("");
    try {
      await upsertToolCommand(apiKey, selectedTool, parsed);
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
    if (!confirm(`Delete custom command for ${selectedTool}? Default args will be used.`))
      return;
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

  return (
    <div style={g.gap}>
      {/* ── Tool picker (left) + editor (right) ─────────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "260px 1fr",
          gap: 14,
          alignItems: "stretch",
        }}
      >
        {/* Tool list */}
        <div style={g.card}>
          <div style={g.cardHead}>Tools</div>
          <div style={{ padding: 8 }}>
            {loading && tools.length === 0 ? (
              <p style={g.empty}>Loading…</p>
            ) : (
              tools.map((t) => {
                const meta = toolMeta(t.name);
                const hasCustom = commands.some(
                  (c) => c.tool_name === t.name && c.is_active,
                );
                const isSelected = selectedTool === t.name;
                return (
                  <button
                    key={t.name}
                    onClick={() => setSelectedTool(t.name)}
                    style={{
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: "10px 12px",
                      marginBottom: 4,
                      borderRadius: 10,
                      border: "1px solid transparent",
                      background: isSelected
                        ? "rgba(20,184,166,0.12)"
                        : "transparent",
                      color: isSelected ? "#99f6e4" : "#cbd5e1",
                      cursor: "pointer",
                      textAlign: "left",
                      fontSize: 14,
                    }}
                  >
                    <span style={{ fontSize: 16 }}>{meta.emoji}</span>
                    <span style={{ flex: 1, fontWeight: 600 }}>{t.name}</span>
                    {hasCustom && (
                      <span
                        title="Custom command saved"
                        style={{
                          color: "#14b8a6",
                          fontSize: 11,
                          fontWeight: 700,
                        }}
                      >
                        ●
                      </span>
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Editor */}
        <div style={g.card}>
          <div style={g.cardHead}>
            {selectedSpec ? (
              <>
                Edit command — <code>{selectedSpec.name}</code>
              </>
            ) : (
              "Select a tool"
            )}
          </div>
          <div style={{ padding: 20 }}>
            {error && (
              <div style={{ ...g.errorBox, marginBottom: 14 }}>{error}</div>
            )}
            {success && (
              <div style={{ ...g.successBox, marginBottom: 14 }}>{success}</div>
            )}

            {selectedSpec && (
              <>
                <p style={{ color: "#94a3b8", fontSize: 13, marginTop: 0 }}>
                  {selectedSpec.description}
                </p>

                <div style={{ marginBottom: 14 }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: 13,
                      color: "#94a3b8",
                      fontWeight: 600,
                      marginBottom: 6,
                    }}
                  >
                    Command args (space-separated; use{" "}
                    <code style={{ color: "#67e8f9" }}>{"{TARGET}"}</code> as
                    placeholder)
                  </label>
                  <textarea
                    value={argsInput}
                    onChange={(e) => setArgsInput(e.target.value)}
                    rows={3}
                    spellCheck={false}
                    style={{
                      ...g.input,
                      fontFamily:
                        "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                      fontSize: 13,
                      lineHeight: 1.5,
                      resize: "vertical",
                    }}
                  />
                </div>

                <div style={{ marginBottom: 14 }}>
                  <label
                    style={{
                      display: "block",
                      fontSize: 13,
                      color: "#94a3b8",
                      fontWeight: 600,
                      marginBottom: 6,
                    }}
                  >
                    Allowed flags for this tool
                  </label>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {selectedSpec.allowed_flags.map((f) => (
                      <code
                        key={f}
                        onClick={() => setArgsInput((prev) => `${prev} ${f}`.trim())}
                        style={{
                          background: "#0f172a",
                          border: "1px solid #1e293b",
                          color: "#67e8f9",
                          padding: "3px 9px",
                          borderRadius: 6,
                          fontSize: 12,
                          cursor: "pointer",
                        }}
                        title="Click to insert"
                      >
                        {f}
                      </code>
                    ))}
                  </div>
                </div>

                <div
                  style={{
                    background: "#0f172a",
                    border: "1px solid #1e293b",
                    borderRadius: 8,
                    padding: 12,
                    fontSize: 12,
                    color: "#94a3b8",
                    marginBottom: 16,
                  }}
                >
                  <div style={{ marginBottom: 6 }}>
                    <span style={{ color: "#475569" }}>Default:</span>{" "}
                    <code style={{ color: "#cbd5e1" }}>
                      {selectedSpec.default_args.join(" ")}
                    </code>
                  </div>
                  <div>
                    <span style={{ color: "#475569" }}>Timeout:</span>{" "}
                    <span style={{ color: "#cbd5e1" }}>
                      {selectedSpec.timeout_seconds}s
                    </span>
                  </div>
                </div>

                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <button
                    onClick={save}
                    disabled={saving}
                    style={g.btnPrimary}
                  >
                    {saving ? "Saving…" : existingCommand ? "Update" : "Save Custom"}
                  </button>
                  {existingCommand && (
                    <>
                      <button
                        onClick={() => toggleActive(existingCommand.id)}
                        style={g.btnSm}
                      >
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
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 0",
                  borderBottom: "1px solid #1e293b",
                  gap: 10,
                  opacity: c.is_active ? 1 : 0.55,
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div
                    style={{
                      fontWeight: 600,
                      color: "#f1f5f9",
                      fontSize: 14,
                      marginBottom: 2,
                    }}
                  >
                    {toolMeta(c.tool_name).emoji} {c.tool_name}
                    {!c.is_active && (
                      <span
                        style={{ marginLeft: 8, fontSize: 11, color: "#f87171" }}
                      >
                        (disabled)
                      </span>
                    )}
                  </div>
                  <code
                    style={{
                      color: "#67e8f9",
                      fontSize: 12,
                      display: "block",
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {c.args.join(" ")}
                  </code>
                </div>
                <button
                  onClick={() => setSelectedTool(c.tool_name)}
                  style={g.btnSm}
                >
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
