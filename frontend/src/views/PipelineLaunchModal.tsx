/**
 * PipelineLaunchModal.tsx
 * نافذة إطلاق الـ Pipeline مع تفعيل/تعطيل كل أداة
 *
 * الاستخدام في ScansView.tsx:
 *   import PipelineLaunchModal from "./PipelineLaunchModal";
 *   <PipelineLaunchModal apiKey={apiKey} onClose={() => setShowPipeline(false)} onLaunched={refresh} />
 *
 * يحتاج إضافة دالة في client.ts:
 *   export const createPipelineScan = (apiKey, target, tools) =>
 *     request(apiKey, "/api/scans/pipeline", {
 *       method: "POST",
 *       body: JSON.stringify({ target, enabled_tools: tools }),
 *     });
 */

import { useState } from "react";
import Modal from "../components/Modal";
import { g } from "../utils/styles";

interface Props {
  apiKey: string;
  onClose: () => void;
  onLaunched: (scanId: number) => void;
}

// تعريف الأدوات مع الوصف والأيقونة والترتيب
const PIPELINE_TOOLS = [
  {
    id: "amass",
    label: "Amass",
    stage: 1,
    icon: "🌐",
    desc: "جمع النطاقات الفرعية (Active + Passive)",
    color: "#14b8a6",
  },
  {
    id: "subfinder",
    label: "Subfinder",
    stage: 1,
    icon: "🔍",
    desc: "اكتشاف سريع للنطاقات الفرعية (Passive)",
    color: "#14b8a6",
  },
  {
    id: "masscan",
    label: "Masscan",
    stage: 2,
    icon: "⚡",
    desc: "مسح سريع للمنافذ المفتوحة",
    color: "#f59e0b",
  },
  {
    id: "httpx",
    label: "Httpx",
    stage: 3,
    icon: "🌍",
    desc: "التحقق من خدمات HTTP/HTTPS",
    color: "#6366f1",
  },
  {
    id: "nmap",
    label: "Nmap",
    stage: 4,
    icon: "🛰️",
    desc: "فحص عميق للخدمات والإصدارات",
    color: "#3b82f6",
  },
  {
    id: "nuclei",
    label: "Nuclei",
    stage: 5,
    icon: "☢️",
    desc: "كشف الثغرات بالقوالب الجاهزة",
    color: "#ef4444",
  },
];

const STAGE_LABELS: Record<number, string> = {
  1: "الاستطلاع",
  2: "مسح المنافذ",
  3: "فحص الويب",
  4: "الفحص العميق",
  5: "كشف الثغرات",
};

export default function PipelineLaunchModal({ apiKey, onClose, onLaunched }: Props) {
  const [target, setTarget] = useState("");
  const [enabled, setEnabled] = useState<Record<string, boolean>>(
    Object.fromEntries(PIPELINE_TOOLS.map((t) => [t.id, true]))
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const toggleTool = (id: string) =>
    setEnabled((prev) => ({ ...prev, [id]: !prev[id] }));

  const enabledCount = Object.values(enabled).filter(Boolean).length;

  async function launch() {
    const t = target.trim();
    if (!t) { setError("أدخل الهدف أولاً"); return; }
    if (enabledCount === 0) { setError("يجب تفعيل أداة واحدة على الأقل"); return; }

    setLoading(true);
    setError("");
    try {
      const res = await fetch("http://localhost:8000/api/scans/pipeline", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Api-Key": apiKey,
        },
        body: JSON.stringify({
          target: t,
          enabled_tools: PIPELINE_TOOLS.filter((tool) => enabled[tool.id]).map((tool) => tool.id),
        }),
      });
      const data = await res.json();
      if (!data.ok) throw new Error(data.error || "فشل تشغيل الـ Pipeline");
      onLaunched(data.scan_id);
      onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "خطأ غير متوقع");
    } finally {
      setLoading(false);
    }
  }

  // تجميع الأدوات حسب المرحلة
  const stages = [...new Set(PIPELINE_TOOLS.map((t) => t.stage))];

  return (
    <Modal open onClose={onClose} maxWidth={600}>
      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <p style={{ margin: 0, fontWeight: 700, color: "#f8fafc", fontSize: 17 }}>
          🚀 Pipeline Scan
        </p>
        <p style={{ margin: "4px 0 0", fontSize: 12, color: "#64748b" }}>
          فعّل الأدوات التي تريدها — تعمل بالتسلسل تلقائياً
        </p>
      </div>

      {/* Target input */}
      <div style={{ marginBottom: 20 }}>
        <label style={{ display: "block", fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>
          الهدف (Domain أو IP)
        </label>
        <input
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && launch()}
          placeholder="example.com أو 192.168.1.1"
          disabled={loading}
          style={{
            width: "100%",
            background: "#0f172a",
            border: "1px solid #334155",
            borderRadius: 8,
            padding: "10px 14px",
            color: "#f1f5f9",
            fontSize: 14,
            outline: "none",
            boxSizing: "border-box",
          }}
        />
      </div>

      {/* Tools by stage */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <label style={{ fontSize: 12, color: "#94a3b8" }}>
            الأدوات — {enabledCount} مفعّل
          </label>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => setEnabled(Object.fromEntries(PIPELINE_TOOLS.map((t) => [t.id, true])))}
              style={{ ...g.btnSm, fontSize: 11 }}
            >
              تفعيل الكل
            </button>
            <button
              onClick={() => setEnabled(Object.fromEntries(PIPELINE_TOOLS.map((t) => [t.id, false])))}
              style={{ ...g.btnSm, fontSize: 11, color: "#64748b" }}
            >
              إلغاء الكل
            </button>
          </div>
        </div>

        {stages.map((stage) => {
          const stageTools = PIPELINE_TOOLS.filter((t) => t.stage === stage);
          return (
            <div key={stage} style={{ marginBottom: 12 }}>
              {/* Stage label */}
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 6,
              }}>
                <span style={{
                  fontSize: 10,
                  fontWeight: 700,
                  color: "#475569",
                  background: "#1e293b",
                  padding: "2px 8px",
                  borderRadius: 4,
                  letterSpacing: "0.05em",
                }}>
                  المرحلة {stage} — {STAGE_LABELS[stage]}
                </span>
                <div style={{ flex: 1, height: 1, background: "#1e293b" }} />
              </div>

              {/* Tools in this stage */}
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {stageTools.map((tool) => {
                  const isOn = enabled[tool.id];
                  return (
                    <div
                      key={tool.id}
                      onClick={() => !loading && toggleTool(tool.id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        padding: "10px 14px",
                        borderRadius: 8,
                        border: `1px solid ${isOn ? tool.color + "44" : "#1e293b"}`,
                        background: isOn ? tool.color + "0d" : "#0f172a",
                        cursor: loading ? "not-allowed" : "pointer",
                        transition: "all 0.15s ease",
                        opacity: loading ? 0.6 : 1,
                      }}
                    >
                      {/* Toggle */}
                      <div style={{
                        width: 36,
                        height: 20,
                        borderRadius: 10,
                        background: isOn ? tool.color : "#334155",
                        position: "relative",
                        flexShrink: 0,
                        transition: "background 0.15s",
                      }}>
                        <div style={{
                          position: "absolute",
                          top: 2,
                          left: isOn ? 18 : 2,
                          width: 16,
                          height: 16,
                          borderRadius: "50%",
                          background: "#fff",
                          transition: "left 0.15s",
                        }} />
                      </div>

                      {/* Icon + name */}
                      <span style={{ fontSize: 16 }}>{tool.icon}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{
                          fontSize: 13,
                          fontWeight: 600,
                          color: isOn ? tool.color : "#475569",
                          transition: "color 0.15s",
                        }}>
                          {tool.label}
                        </div>
                        <div style={{ fontSize: 11, color: "#475569", marginTop: 1 }}>
                          {tool.desc}
                        </div>
                      </div>

                      {/* Status badge */}
                      <span style={{
                        fontSize: 10,
                        padding: "2px 8px",
                        borderRadius: 4,
                        background: isOn ? tool.color + "22" : "#1e293b",
                        color: isOn ? tool.color : "#334155",
                        fontWeight: 600,
                        flexShrink: 0,
                        transition: "all 0.15s",
                      }}>
                        {isOn ? "ON" : "OFF"}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Pipeline preview */}
      {enabledCount > 0 && (
        <div style={{
          background: "#0f172a",
          border: "1px solid #1e293b",
          borderRadius: 8,
          padding: "10px 14px",
          marginBottom: 16,
          fontSize: 12,
          color: "#64748b",
          display: "flex",
          flexWrap: "wrap",
          gap: 6,
          alignItems: "center",
        }}>
          <span style={{ color: "#475569", marginRight: 4 }}>التسلسل:</span>
          {PIPELINE_TOOLS.filter((t) => enabled[t.id]).map((t, i, arr) => (
            <span key={t.id} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ color: t.color, fontWeight: 600 }}>{t.label}</span>
              {i < arr.length - 1 && <span style={{ color: "#1e293b" }}>→</span>}
            </span>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ ...g.errorBox, marginBottom: 14 }}>{error}</div>
      )}

      {/* Actions */}
      <div style={{ display: "flex", gap: 10, justifyContent: "flex-end" }}>
        <button onClick={onClose} style={g.btnSm} disabled={loading}>
          إلغاء
        </button>
        <button
          onClick={launch}
          disabled={loading || enabledCount === 0 || !target.trim()}
          style={{
            ...g.btnSm,
            background: loading ? "#1e293b" : "#14b8a6",
            color: "#fff",
            fontWeight: 700,
            opacity: loading || enabledCount === 0 || !target.trim() ? 0.5 : 1,
            padding: "7px 20px",
          }}
        >
          {loading ? "⏳ جاري الإطلاق..." : `🚀 تشغيل Pipeline (${enabledCount} أدوات)`}
        </button>
      </div>
    </Modal>
  );
}
