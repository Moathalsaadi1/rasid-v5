import type { ReactNode } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  maxWidth?: number;
}

// Lightweight modal: click-outside-to-close, esc not handled here (most
// modals in RASID are non-disruptive enough that the X button suffices).
export default function Modal({
  open,
  onClose,
  title,
  children,
  maxWidth = 760,
}: Props) {
  if (!open) return null;
  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.75)",
        zIndex: 1000,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 20,
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#1e293b",
          borderRadius: 16,
          width: "100%",
          maxWidth,
          maxHeight: "88vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {title && (
          <div
            style={{
              padding: "16px 20px",
              borderBottom: "1px solid #334155",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <p
              style={{
                margin: 0,
                fontWeight: 700,
                color: "#f8fafc",
                fontSize: 15,
              }}
            >
              {title}
            </p>
            <button
              onClick={onClose}
              style={{
                background: "none",
                border: "none",
                color: "#64748b",
                fontSize: 20,
                cursor: "pointer",
              }}
            >
              ✕
            </button>
          </div>
        )}
        <div style={{ overflowY: "auto", padding: 20, flex: 1 }}>{children}</div>
      </div>
    </div>
  );
}
