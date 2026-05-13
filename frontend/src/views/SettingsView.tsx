import { useState } from "react";
import {
  changePassword,
  deleteAccount,
  rotateApiKey,
} from "../api/client";
import { g } from "../utils/styles";
import type { CurrentUser } from "../types";

interface Props {
  user: CurrentUser;
  apiKey: string;
  onApiKeyRotated: (newKey: string) => void;
  onAccountDeleted: () => void;
}

type Section = "account" | "password" | "api_key" | "danger" | null;

export default function SettingsView({
  user,
  apiKey,
  onApiKeyRotated,
  onAccountDeleted,
}: Props) {
  const [openSection, setOpenSection] = useState<Section>(null);

  // password form
  const [currentPwd, setCurrentPwd] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const [pwdSubmitting, setPwdSubmitting] = useState(false);
  const [pwdError, setPwdError] = useState("");
  const [pwdSuccess, setPwdSuccess] = useState("");

  // rotate
  const [rotating, setRotating] = useState(false);
  const [rotateError, setRotateError] = useState("");

  // delete
  const [delPwd, setDelPwd] = useState("");
  const [delSubmitting, setDelSubmitting] = useState(false);
  const [delError, setDelError] = useState("");

  // copy api key
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  async function submitPasswordChange() {
    setPwdError("");
    setPwdSuccess("");
    if (!currentPwd || !newPwd) {
      setPwdError("Both fields are required");
      return;
    }
    if (newPwd.length < 8) {
      setPwdError("New password must be at least 8 characters");
      return;
    }
    setPwdSubmitting(true);
    try {
      await changePassword(apiKey, currentPwd, newPwd);
      setPwdSuccess("Password updated successfully");
      setCurrentPwd("");
      setNewPwd("");
    } catch (e: unknown) {
      setPwdError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setPwdSubmitting(false);
    }
  }

  async function submitRotate() {
    if (
      !confirm(
        "Rotate your API key? The old key will stop working immediately. " +
          "Make sure to save the new one.",
      )
    )
      return;
    setRotateError("");
    setRotating(true);
    try {
      const d = await rotateApiKey(apiKey);
      onApiKeyRotated(d.api_key);
    } catch (e: unknown) {
      setRotateError(e instanceof Error ? e.message : "Rotation failed");
    } finally {
      setRotating(false);
    }
  }

  async function submitDelete() {
    setDelError("");
    if (!delPwd) {
      setDelError("Password required to confirm deletion");
      return;
    }
    if (
      !confirm(
        "This will permanently delete your account and all your scans. Continue?",
      )
    )
      return;
    setDelSubmitting(true);
    try {
      await deleteAccount(apiKey, delPwd);
      onAccountDeleted();
    } catch (e: unknown) {
      setDelError(e instanceof Error ? e.message : "Deletion failed");
    } finally {
      setDelSubmitting(false);
    }
  }

  return (
    <div style={g.gap}>
      {/* ── Account info ───────────────────────────────────────────── */}
      <div style={g.card}>
        <div style={g.cardHead}>Account</div>
        <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
          {[
            { label: "Email", val: user.email },
            { label: "Role", val: user.role.toUpperCase() },
            { label: "Total Scans", val: String(user.scan_count) },
          ].map(({ label, val }) => (
            <div
              key={label}
              style={{
                display: "flex",
                justifyContent: "space-between",
                padding: "12px 16px",
                background: "#0f172a",
                borderRadius: 10,
              }}
            >
              <span style={{ color: "#64748b", fontSize: 13 }}>{label}</span>
              <span
                style={{
                  color: "#f1f5f9",
                  fontWeight: 600,
                  fontSize: 13,
                }}
              >
                {val}
              </span>
            </div>
          ))}
          <div style={{ padding: "14px 16px", background: "#0f172a", borderRadius: 10 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 8,
              }}
            >
              <span style={{ color: "#64748b", fontSize: 13 }}>API Key</span>
              <div style={{ display: "flex", gap: 8 }}>
                <button onClick={copy} style={g.btnSm}>
                  {copied ? "✓ Copied!" : "Copy"}
                </button>
                <button
                  onClick={submitRotate}
                  disabled={rotating}
                  style={g.btnSm}
                >
                  {rotating ? "Rotating…" : "↻ Rotate"}
                </button>
              </div>
            </div>
            <code
              style={{ color: "#67e8f9", fontSize: 12, wordBreak: "break-all" }}
            >
              {apiKey}
            </code>
            {rotateError && (
              <div style={{ ...g.errorBox, marginTop: 10 }}>{rotateError}</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Change password ─────────────────────────────────────────── */}
      <div style={g.card}>
        <button
          onClick={() => setOpenSection(openSection === "password" ? null : "password")}
          style={{
            ...g.cardHead,
            width: "100%",
            textAlign: "left",
            cursor: "pointer",
            background: "none",
            border: "none",
            color: "#f8fafc",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>Change Password</span>
          <span style={{ color: "#64748b" }}>
            {openSection === "password" ? "▴" : "▾"}
          </span>
        </button>
        {openSection === "password" && (
          <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
            {pwdError && <div style={g.errorBox}>{pwdError}</div>}
            {pwdSuccess && <div style={g.successBox}>{pwdSuccess}</div>}
            <input
              type="password"
              placeholder="Current password"
              value={currentPwd}
              onChange={(e) => setCurrentPwd(e.target.value)}
              style={g.input}
            />
            <input
              type="password"
              placeholder="New password (min 8 chars)"
              value={newPwd}
              onChange={(e) => setNewPwd(e.target.value)}
              style={g.input}
            />
            <button
              onClick={submitPasswordChange}
              disabled={pwdSubmitting}
              style={g.btnPrimary}
            >
              {pwdSubmitting ? "Updating…" : "Update Password"}
            </button>
          </div>
        )}
      </div>

      {/* ── Danger zone ─────────────────────────────────────────────── */}
      <div
        style={{
          ...g.card,
          border: "1px solid rgba(239,68,68,0.2)",
        }}
      >
        <button
          onClick={() => setOpenSection(openSection === "danger" ? null : "danger")}
          style={{
            ...g.cardHead,
            width: "100%",
            textAlign: "left",
            cursor: "pointer",
            background: "none",
            border: "none",
            color: "#fca5a5",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>Danger Zone</span>
          <span style={{ color: "#64748b" }}>
            {openSection === "danger" ? "▴" : "▾"}
          </span>
        </button>
        {openSection === "danger" && (
          <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
            <p style={{ margin: 0, color: "#94a3b8", fontSize: 13 }}>
              Deleting your account permanently removes your user record, all
              your scans, findings, custom commands, and audit log links.
              <br />
              This action cannot be undone.
            </p>
            {delError && <div style={g.errorBox}>{delError}</div>}
            <input
              type="password"
              placeholder="Confirm with your password"
              value={delPwd}
              onChange={(e) => setDelPwd(e.target.value)}
              style={g.input}
            />
            <button
              onClick={submitDelete}
              disabled={delSubmitting}
              style={g.btnDanger}
            >
              {delSubmitting ? "Deleting…" : "Permanently Delete My Account"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
