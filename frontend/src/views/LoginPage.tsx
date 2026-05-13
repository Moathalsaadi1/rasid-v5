import { useState } from "react";
import { login, register } from "../api/client";
import type { CurrentUser } from "../types";

interface Props {
  onAuthSuccess: (apiKey: string, user: CurrentUser) => void;
}

type Tab = "login" | "register";

export default function LoginPage({ onAuthSuccess }: Props) {
  const [tab, setTab] = useState<Tab>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    const trimmedEmail = email.trim().toLowerCase();
    if (!trimmedEmail || !password) {
      setError("Email and password are required.");
      return;
    }
    if (tab === "register" && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const action = tab === "login" ? login : register;
      const data = await action(trimmedEmail, password);
      onAuthSuccess(data.user.api_key, data.user);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  function switchTab(t: Tab) {
    setTab(t);
    setError("");
  }

  return (
    <div style={s.page}>
      <div style={s.card}>
        <div style={s.brand}>
          <span style={{ fontSize: 36 }}>🛡</span>
          <div>
            <p style={s.brandTitle}>RASID</p>
            <p style={s.brandSub}>Reconnaissance Automation System</p>
          </div>
        </div>

        <div style={s.tabs}>
          {(["login", "register"] as const).map((t) => (
            <button
              key={t}
              onClick={() => switchTab(t)}
              style={{ ...s.tab, ...(tab === t ? s.tabActive : {}) }}
            >
              {t === "login" ? "Sign In" : "Register"}
            </button>
          ))}
        </div>

        {error && <div style={s.error}>{error}</div>}

        <div style={s.form}>
          <div style={s.field}>
            <label style={s.label}>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              style={s.input}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
          <div style={s.field}>
            <label style={s.label}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={tab === "register" ? "min 8 characters" : "••••••••"}
              style={s.input}
              onKeyDown={(e) => e.key === "Enter" && submit()}
            />
          </div>
          <button onClick={submit} disabled={loading} style={s.btn}>
            {loading
              ? "Please wait..."
              : tab === "login"
                ? "Sign In"
                : "Create Account"}
          </button>
        </div>

        <p style={s.hint}>
          {tab === "login" ? "No account? " : "Already registered? "}
          <button
            onClick={() => switchTab(tab === "login" ? "register" : "login")}
            style={s.link}
          >
            {tab === "login" ? "Register here" : "Sign in"}
          </button>
        </p>

        <p style={s.note}>
          First registered account becomes Admin automatically.
        </p>
      </div>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "#0b1220",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 20,
  },
  card: {
    background: "#1e293b",
    borderRadius: 20,
    padding: 40,
    width: "100%",
    maxWidth: 420,
    border: "1px solid rgba(255,255,255,0.07)",
  },
  brand: { display: "flex", alignItems: "center", gap: 14, marginBottom: 28 },
  brandTitle: {
    margin: 0,
    fontWeight: 700,
    fontSize: 22,
    color: "#f8fafc",
    letterSpacing: 1,
  },
  brandSub: { margin: "4px 0 0", fontSize: 12, color: "#64748b" },
  tabs: {
    display: "flex",
    background: "#0f172a",
    borderRadius: 10,
    padding: 4,
    marginBottom: 24,
    gap: 4,
  },
  tab: {
    flex: 1,
    padding: "8px 0",
    background: "transparent",
    border: "none",
    color: "#64748b",
    borderRadius: 8,
    cursor: "pointer",
    fontSize: 14,
    fontWeight: 600,
  },
  tabActive: { background: "#14b8a6", color: "#06261f" },
  error: {
    background: "rgba(239,68,68,0.12)",
    color: "#fca5a5",
    border: "1px solid rgba(239,68,68,0.25)",
    borderRadius: 10,
    padding: "10px 14px",
    marginBottom: 16,
    fontSize: 13,
  },
  form: { display: "flex", flexDirection: "column", gap: 16 },
  field: { display: "flex", flexDirection: "column", gap: 6 },
  label: { fontSize: 13, color: "#94a3b8", fontWeight: 600 },
  input: {
    background: "#0f172a",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: 10,
    padding: "11px 14px",
    color: "#e5e7eb",
    fontSize: 14,
    outline: "none",
  },
  btn: {
    background: "#14b8a6",
    color: "#06261f",
    border: "none",
    borderRadius: 12,
    padding: "13px 0",
    fontWeight: 700,
    fontSize: 15,
    cursor: "pointer",
    marginTop: 4,
  },
  hint: {
    textAlign: "center",
    color: "#64748b",
    fontSize: 13,
    marginTop: 20,
    marginBottom: 0,
  },
  link: {
    background: "none",
    border: "none",
    color: "#14b8a6",
    cursor: "pointer",
    fontSize: 13,
    fontWeight: 600,
  },
  note: {
    textAlign: "center",
    color: "#334155",
    fontSize: 11,
    marginTop: 12,
    marginBottom: 0,
  },
};
