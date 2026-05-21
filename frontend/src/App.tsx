import { useCallback, useEffect, useState } from "react";
import { getDashboard } from "./api/client";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import { useNotifications } from "./hooks/useNotifications";
import { useSession } from "./hooks/useSession";
import { g } from "./utils/styles";
import AdminView from "./views/AdminView";
import AssetsView from "./views/AssetsView";
import DashboardView from "./views/DashboardView";
import FindingsView from "./views/FindingsView";
import LegalAcceptanceModal from "./views/LegalAcceptanceModal";
import LoginPage from "./views/LoginPage";
import NotificationsView from "./views/NotificationsView";
import ScanModal from "./views/ScanModal";
import ScansView from "./views/ScansView";
import SettingsView from "./views/SettingsView";
import ToolCommandsView from "./views/ToolCommandsView";
import type { DashboardData } from "./types";
import AggregateView from "./views/AggregateView";
import DiffView from "./views/DiffView";
import DorkView from "./views/DorkView";

type ViewKey =
  | "dashboard"
  | "scans"
  | "findings"
  | "assets"
  | "aggregate"
  | "diff"
  | "dork"
  | "tool_commands"
  | "notifications"
  | "admin"
  | "settings";

// Top-level shell: auth gate, sidebar/topbar, view router, and the two
// global modals (scan detail + legal acceptance). Every domain concern
// lives in its dedicated component under views/.
export default function App() {
  const session = useSession();
  const { apiKey, user, bootstrapping, setSession, setApiKey, logout, error: sessionError } =
    session;

  const [currentView, setCurrentView] = useState<ViewKey>("dashboard");
  const [globalError, setGlobalError] = useState("");

  // dashboard data (kept here so refresh button can trigger reload)
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [dashLoading, setDashLoading] = useState(false);

  // scan detail modal
  const [openScanId, setOpenScanId] = useState<number | null>(null);

  // legal modal — shown either explicitly via Sidebar settings, or
  // automatically when ScansView reports the gate is closed.
  const [legalOpen, setLegalOpen] = useState(false);

  // notifications (also fed to Sidebar & Topbar for unread badge)
  const notif = useNotifications(apiKey);

  const loadDashboard = useCallback(async () => {
    if (!apiKey) return;
    setDashLoading(true);
    try {
      const d = await getDashboard(apiKey);
      setDashboard(d.dashboard);
    } catch (e: unknown) {
      setGlobalError(e instanceof Error ? e.message : "Failed to load dashboard");
    } finally {
      setDashLoading(false);
    }
  }, [apiKey]);

  // Reload dashboard whenever we land on it.
  useEffect(() => {
    if (apiKey && currentView === "dashboard") loadDashboard();
  }, [apiKey, currentView, loadDashboard]);

  // ── Render ──────────────────────────────────────────────────────────

  if (bootstrapping) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background: "#0b1220",
          color: "#94a3b8",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        Loading…
      </div>
    );
  }

  if (!apiKey || !user) {
    return (
      <LoginPage
        onAuthSuccess={(key, u) => {
          setSession(key, u);
          // Immediately ask the user to accept the legal terms; the modal
          // will detect existing acceptance and close itself if not needed.
          setLegalOpen(true);
        }}
      />
    );
  }

  const titleMap: Record<ViewKey, string> = {
    dashboard: "Dashboard",
    scans: "Scans",
    findings: "Findings",
    assets: "Assets",
    aggregate: "Aggregate Intelligence",
    diff: "Scan Diff",
    dork: "Google Dorking",
    tool_commands: "Tool Commands",
    notifications: "Notifications",
    admin: "Admin",
    settings: "Settings",
  };

  const view = (() => {
    switch (currentView) {
      case "dashboard":
        return <DashboardView data={dashboard} loading={dashLoading} />;
      case "scans":
        return (
          <ScansView
            apiKey={apiKey}
            onOpenScan={(id) => setOpenScanId(id)}
            onLegalRequired={() => setLegalOpen(true)}
          />
        );
      case "findings":
        return <FindingsView apiKey={apiKey} />;
      case "dork":
        return <DorkView apiKey={apiKey} />;
      case "diff":
        return <DiffView apiKey={apiKey} />;
      case "aggregate":
        return <AggregateView apiKey={apiKey} />;
      case "assets":
        return <AssetsView apiKey={apiKey} />;
      case "tool_commands":
        return <ToolCommandsView apiKey={apiKey} />;
      case "notifications":
        return (
          <NotificationsView
            apiKey={apiKey}
            onOpenScan={(id) => setOpenScanId(id)}
          />
        );
      case "admin":
        return user.role === "admin" ? (
          <AdminView apiKey={apiKey} />
        ) : (
          <p style={g.empty}>Access denied.</p>
        );
      case "settings":
        return (
          <SettingsView
            user={user}
            apiKey={apiKey}
            onApiKeyRotated={(newKey) => {
              setApiKey(newKey);
              setGlobalError(
                "Your API key has been rotated. Use the new key for all future requests.",
              );
            }}
            onAccountDeleted={logout}
          />
        );
      default:
        return null;
    }
  })();

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#0b1220",
        color: "#e5e7eb",
        display: "flex",
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <Sidebar
        current={currentView}
        onSelect={(v) => setCurrentView(v as ViewKey)}
        role={user.role}
        unreadCount={notif.unreadCount}
      />

      <main
        style={{
          flex: 1,
          padding: "24px 28px",
          overflowX: "hidden",
          background:
            "radial-gradient(circle at top right, rgba(20,184,166,0.06), transparent 35%)",
        }}
      >
        <div style={{ maxWidth: 1200, margin: "0 auto" }}>
          <Topbar
            title={titleMap[currentView]}
            user={user}
            onLogout={logout}
            onRefresh={currentView === "dashboard" ? loadDashboard : undefined}
            unreadCount={notif.unreadCount}
            onOpenNotifications={() => setCurrentView("notifications")}
          />

          {(globalError || sessionError) && (
            <div
              style={{
                ...g.errorBox,
                marginBottom: 16,
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <span>{globalError || sessionError}</span>
              <button
                onClick={() => setGlobalError("")}
                style={{
                  background: "none",
                  border: "none",
                  color: "#f87171",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>
          )}

          {view}
        </div>
      </main>

      {/* Global modals */}
      <ScanModal
        apiKey={apiKey}
        scanId={openScanId}
        onClose={() => setOpenScanId(null)}
        onChanged={() => {
          // Refresh anything that depends on scan state.
          if (currentView === "dashboard") loadDashboard();
        }}
      />

      <LegalAcceptanceModal
        apiKey={apiKey}
        open={legalOpen}
        onAccepted={() => setLegalOpen(false)}
        onClose={() => setLegalOpen(false)}
      />
    </div>
  );
}
