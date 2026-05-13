import { useState } from "react";
import { useNotifications } from "../hooks/useNotifications";
import Badge from "../components/Badge";
import { fmtRelative, SEV_COLOR } from "../utils/format";
import { g } from "../utils/styles";

interface Props {
  apiKey: string;
  onOpenScan: (id: number) => void;
}

export default function NotificationsView({ apiKey, onOpenScan }: Props) {
  const { items, unreadCount, loading, markRead, markAllRead, reload } =
    useNotifications(apiKey);
  const [filter, setFilter] = useState<"all" | "unread">("all");

  const visible = filter === "unread" ? items.filter((n) => !n.is_read) : items;

  return (
    <div style={g.gap}>
      <div style={g.card}>
        <div
          style={{
            ...g.cardHead,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 10,
            flexWrap: "wrap",
          }}
        >
          <span>
            Notifications
            {unreadCount > 0 && (
              <span
                style={{
                  marginLeft: 10,
                  background: "#ef4444",
                  color: "#fff",
                  fontSize: 11,
                  fontWeight: 700,
                  borderRadius: 999,
                  padding: "2px 9px",
                }}
              >
                {unreadCount} unread
              </span>
            )}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            {(["all", "unread"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                style={{
                  ...g.btnSm,
                  ...(filter === f
                    ? { background: "#14b8a6", color: "#06261f" }
                    : {}),
                }}
              >
                {f === "all" ? "All" : "Unread"}
              </button>
            ))}
            {unreadCount > 0 && (
              <button onClick={markAllRead} style={g.btnSm}>
                ✓ Mark all read
              </button>
            )}
            <button onClick={reload} style={g.btnSm}>
              ↻
            </button>
          </div>
        </div>

        <div style={{ padding: "0 20px 20px" }}>
          {loading && items.length === 0 ? (
            <p style={g.empty}>Loading…</p>
          ) : visible.length === 0 ? (
            <p style={g.empty}>
              {filter === "unread" ? "No unread notifications." : "No notifications yet."}
            </p>
          ) : (
            visible.map((n) => {
              const c = SEV_COLOR[n.severity] || "#6b7280";
              return (
                <div
                  key={n.id}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 12,
                    padding: "14px 0",
                    borderBottom: "1px solid #1e293b",
                    opacity: n.is_read ? 0.6 : 1,
                  }}
                >
                  {/* Unread indicator */}
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      background: n.is_read ? "transparent" : "#14b8a6",
                      marginTop: 7,
                      flexShrink: 0,
                    }}
                  />

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        flexWrap: "wrap",
                        marginBottom: 4,
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 600,
                          color: "#f1f5f9",
                          fontSize: 14,
                        }}
                      >
                        {n.title}
                      </span>
                      <Badge label={n.severity.toUpperCase()} color={c} />
                    </div>
                    {n.message && (
                      <p
                        style={{
                          margin: 0,
                          color: "#94a3b8",
                          fontSize: 13,
                        }}
                      >
                        {n.message}
                      </p>
                    )}
                    <p
                      style={{
                        margin: "4px 0 0",
                        fontSize: 11,
                        color: "#475569",
                      }}
                    >
                      {fmtRelative(n.created_at)}
                    </p>
                  </div>

                  <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                    {n.scan_id != null && (
                      <button
                        onClick={() => onOpenScan(n.scan_id!)}
                        style={g.btnSm}
                      >
                        Open scan →
                      </button>
                    )}
                    {!n.is_read && (
                      <button onClick={() => markRead(n.id)} style={g.btnSm}>
                        ✓
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
