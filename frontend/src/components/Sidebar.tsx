import { g } from "../utils/styles";
import type { UserRole } from "../types";

export interface SidebarItem {
  key: string;
  label: string;
  icon: string;
  adminOnly?: boolean;
}

const ITEMS: SidebarItem[] = [
  { key: "dashboard", label: "Dashboard", icon: "▣" },
  { key: "scans", label: "Scans", icon: "◉" },
  { key: "findings", label: "Findings", icon: "▲" },
  { key: "assets", label: "Assets", icon: "◆" },
  { key: "tool_commands", label: "Tool Commands", icon: "⚒" },
  { key: "notifications", label: "Notifications", icon: "🔔" },
  { key: "admin", label: "Admin", icon: "⚙", adminOnly: true },
  { key: "settings", label: "Settings", icon: "👤" },
];

interface Props {
  current: string;
  onSelect: (key: string) => void;
  role: UserRole;
  unreadCount: number;
}

export default function Sidebar({ current, onSelect, role, unreadCount }: Props) {
  const items = ITEMS.filter((i) => !i.adminOnly || role === "admin");

  return (
    <aside
      style={{
        width: 220,
        minWidth: 220,
        background: "#071224",
        borderRight: "1px solid rgba(255,255,255,0.06)",
        padding: 20,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 28,
          }}
        >
          <div style={{ ...g.iconBox, borderRadius: 14 }}>
            <span style={{ fontSize: 20 }}>🛡</span>
          </div>
          <div>
            <p
              style={{
                margin: 0,
                fontWeight: 700,
                fontSize: 14,
                letterSpacing: 1,
                color: "#f8fafc",
              }}
            >
              RASID
            </p>
            <p style={{ margin: "2px 0 0", fontSize: 11, color: "#334155" }}>
              Recon Automation
            </p>
          </div>
        </div>

        {items.map(({ key, label, icon }) => {
          const isActive = current === key;
          return (
            <button
              key={key}
              onClick={() => onSelect(key)}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "11px 14px",
                marginBottom: 6,
                borderRadius: 12,
                border: "1px solid transparent",
                background: isActive ? "rgba(20,184,166,0.12)" : "transparent",
                color: isActive ? "#99f6e4" : "#94a3b8",
                cursor: "pointer",
                textAlign: "left",
                fontSize: 14,
                ...(isActive
                  ? { borderColor: "rgba(20,184,166,0.2)" }
                  : {}),
              }}
            >
              <span>{icon}</span>
              <span style={{ flex: 1 }}>{label}</span>
              {key === "notifications" && unreadCount > 0 && (
                <span
                  style={{
                    background: "#ef4444",
                    color: "#fff",
                    fontSize: 10,
                    fontWeight: 700,
                    borderRadius: 999,
                    padding: "2px 7px",
                    minWidth: 18,
                    textAlign: "center",
                  }}
                >
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      <div
        style={{
          background: "#0f172a",
          borderRadius: 12,
          padding: 14,
          border: "1px solid #1e293b",
        }}
      >
        <p style={{ margin: 0, fontSize: 12, color: "#334155" }}>RASID v5.0</p>
        <p style={{ margin: "4px 0 0", fontSize: 11, color: "#1e293b" }}>
          Recon Automation System
        </p>
      </div>
    </aside>
  );
}
