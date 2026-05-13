import { useCallback, useEffect, useState } from "react";
import {
  adminAuditLogs,
  adminListUsers,
  adminStats,
  adminUpdateUser,
} from "../api/client";
import Badge from "../components/Badge";
import Pagination from "../components/Pagination";
import { fmtDate, fmtRelative } from "../utils/format";
import { g } from "../utils/styles";
import type { AdminStats, AdminUser, AuditLogItem, UserRole } from "../types";

interface Props {
  apiKey: string;
}

type Tab = "users" | "audit";

const AUDIT_PAGE_SIZE = 30;

export default function AdminView({ apiKey }: Props) {
  const [tab, setTab] = useState<Tab>("users");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [usersLoading, setUsersLoading] = useState(false);
  const [error, setError] = useState("");

  // audit log state
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [logsTotal, setLogsTotal] = useState(0);
  const [logsPage, setLogsPage] = useState(1);
  const [logsLoading, setLogsLoading] = useState(false);
  const [actionFilter, setActionFilter] = useState("");

  const loadUsers = useCallback(async () => {
    setUsersLoading(true);
    setError("");
    try {
      const [u, s] = await Promise.all([
        adminListUsers(apiKey),
        adminStats(apiKey),
      ]);
      setUsers(u.users);
      setStats(s.stats);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Load failed");
    } finally {
      setUsersLoading(false);
    }
  }, [apiKey]);

  const loadLogs = useCallback(async () => {
    setLogsLoading(true);
    try {
      const d = await adminAuditLogs(apiKey, {
        page: logsPage,
        per_page: AUDIT_PAGE_SIZE,
        action: actionFilter || undefined,
      });
      setLogs(d.logs);
      setLogsTotal(d.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load audit logs");
    } finally {
      setLogsLoading(false);
    }
  }, [apiKey, logsPage, actionFilter]);

  useEffect(() => {
    if (tab === "users") loadUsers();
  }, [tab, loadUsers]);

  useEffect(() => {
    if (tab === "audit") loadLogs();
  }, [tab, loadLogs]);

  async function toggleActive(u: AdminUser) {
    try {
      await adminUpdateUser(apiKey, u.id, { is_active: !u.is_active });
      loadUsers();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  async function changeRole(u: AdminUser, role: string) {
    try {
      await adminUpdateUser(apiKey, u.id, { role: role as UserRole });
      loadUsers();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Update failed");
    }
  }

  const logsTotalPages = Math.ceil(logsTotal / AUDIT_PAGE_SIZE);

  return (
    <div style={g.gap}>
      {/* ── Stats ──────────────────────────────────────────────────── */}
      {stats && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5,1fr)", gap: 14 }}>
          {Object.entries(stats).map(([k, v]) => (
            <div key={k} style={g.card}>
              <p style={{ margin: "16px 16px 4px", fontSize: 12, color: "#64748b" }}>
                {k.replace(/_/g, " ").toUpperCase()}
              </p>
              <p
                style={{
                  margin: "0 16px 16px",
                  fontSize: 24,
                  fontWeight: 700,
                  color: "#14b8a6",
                }}
              >
                {String(v)}
              </p>
            </div>
          ))}
        </div>
      )}

      {error && <div style={g.errorBox}>{error}</div>}

      {/* ── Tabs ───────────────────────────────────────────────────── */}
      <div style={{ display: "flex", gap: 8 }}>
        {(["users", "audit"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              ...g.btnSm,
              padding: "8px 16px",
              ...(tab === t
                ? { background: "#14b8a6", color: "#06261f", fontWeight: 700 }
                : {}),
            }}
          >
            {t === "users" ? "Users" : "Audit Log"}
          </button>
        ))}
      </div>

      {/* ── Users tab ──────────────────────────────────────────────── */}
      {tab === "users" && (
        <div style={g.card}>
          <div
            style={{
              ...g.cardHead,
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            <span>User Management ({users.length})</span>
            <button onClick={loadUsers} style={g.btnSm}>
              ↻ Refresh
            </button>
          </div>
          <div style={{ padding: 20, overflowX: "auto" }}>
            {usersLoading ? (
              <p style={g.empty}>Loading…</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    {["ID", "Email", "Role", "Scans", "Status", "Joined", "Actions"].map(
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
                  {users.map((u) => (
                    <tr key={u.id}>
                      <td style={g.td}>{u.id}</td>
                      <td style={g.td}>
                        <span style={{ color: "#67e8f9" }}>{u.email}</span>
                      </td>
                      <td style={g.td}>
                        <select
                          value={u.role}
                          onChange={(e) => changeRole(u, e.target.value)}
                          style={{
                            background: "#1e293b",
                            border: "1px solid #334155",
                            borderRadius: 6,
                            color: "#e2e8f0",
                            padding: "4px 8px",
                            fontSize: 12,
                          }}
                        >
                          <option value="admin">admin</option>
                          <option value="user">user</option>
                          <option value="guest">guest</option>
                        </select>
                      </td>
                      <td style={g.td}>{u.scan_count}</td>
                      <td style={g.td}>
                        <Badge
                          label={u.is_active ? "Active" : "Suspended"}
                          color={u.is_active ? "#4ade80" : "#f87171"}
                        />
                      </td>
                      <td style={g.td}>{fmtDate(u.created_at)}</td>
                      <td style={g.td}>
                        <button
                          onClick={() => toggleActive(u)}
                          style={{
                            ...g.btnSm,
                            color: u.is_active ? "#f87171" : "#4ade80",
                          }}
                        >
                          {u.is_active ? "Suspend" : "Activate"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* ── Audit log tab ──────────────────────────────────────────── */}
      {tab === "audit" && (
        <div style={g.card}>
          <div
            style={{
              ...g.cardHead,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 10,
            }}
          >
            <span>Audit Log ({logsTotal})</span>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input
                value={actionFilter}
                onChange={(e) => {
                  setActionFilter(e.target.value);
                  setLogsPage(1);
                }}
                placeholder="Filter by action (e.g. scan.create)"
                style={{ ...g.input, width: 230, padding: "6px 12px" }}
              />
              <button onClick={loadLogs} style={g.btnSm}>
                ↻
              </button>
            </div>
          </div>
          <div style={{ padding: "0 20px 20px", overflowX: "auto" }}>
            {logsLoading ? (
              <p style={g.empty}>Loading…</p>
            ) : logs.length === 0 ? (
              <p style={g.empty}>No audit entries match the filter.</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    {["When", "User", "Action", "Resource", "IP"].map((h) => (
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
                  {logs.map((l) => (
                    <tr key={l.id}>
                      <td style={g.td} title={fmtDate(l.created_at)}>
                        {fmtRelative(l.created_at)}
                      </td>
                      <td style={g.td}>{l.user_id ?? "—"}</td>
                      <td style={g.td}>
                        <code style={{ color: "#67e8f9", fontSize: 12 }}>
                          {l.action}
                        </code>
                      </td>
                      <td style={g.td}>
                        {l.resource_type && l.resource_id
                          ? `${l.resource_type}/${l.resource_id}`
                          : l.resource_type || "—"}
                      </td>
                      <td style={g.td}>
                        <span style={{ color: "#64748b", fontSize: 12 }}>
                          {l.ip_address || "—"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <Pagination
            page={logsPage}
            totalPages={logsTotalPages}
            onPage={(p) => setLogsPage(p)}
          />
        </div>
      )}
    </div>
  );
}
