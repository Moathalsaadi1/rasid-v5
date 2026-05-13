import { g } from "../utils/styles";
import type { CurrentUser } from "../types";

interface Props {
  title: string;
  user: CurrentUser;
  onLogout: () => void;
  onRefresh?: () => void;
  unreadCount: number;
  onOpenNotifications: () => void;
}

export default function Topbar({
  title,
  user,
  onLogout,
  onRefresh,
  unreadCount,
  onOpenNotifications,
}: Props) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        marginBottom: 24,
      }}
    >
      <div>
        <h1
          style={{
            margin: 0,
            fontSize: 26,
            fontWeight: 700,
            color: "#f8fafc",
          }}
        >
          {title}
        </h1>
        <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: 13 }}>
          {user.email} ·{" "}
          <span
            style={{
              color: "#14b8a6",
              textTransform: "uppercase",
              fontSize: 11,
              fontWeight: 700,
            }}
          >
            {user.role}
          </span>
        </p>
      </div>
      <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
        <button
          onClick={onOpenNotifications}
          style={{
            ...g.btnSm,
            position: "relative",
            padding: "6px 12px",
            fontSize: 16,
          }}
          aria-label="Notifications"
        >
          🔔
          {unreadCount > 0 && (
            <span
              style={{
                position: "absolute",
                top: -4,
                right: -4,
                background: "#ef4444",
                color: "#fff",
                fontSize: 9,
                fontWeight: 700,
                borderRadius: 999,
                padding: "1px 5px",
                minWidth: 14,
                textAlign: "center",
                lineHeight: "12px",
              }}
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </button>
        {onRefresh && (
          <button onClick={onRefresh} style={g.btnSm}>
            ↻ Refresh
          </button>
        )}
        <button
          onClick={onLogout}
          style={{ ...g.btnSm, color: "#f87171" }}
        >
          Logout
        </button>
      </div>
    </div>
  );
}
