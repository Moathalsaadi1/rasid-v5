import { useEffect, useState } from "react";
import { acceptLegalTerms, getLegalTerms } from "../api/client";
import { g } from "../utils/styles";
import Modal from "../components/Modal";

interface Props {
  apiKey: string;
  open: boolean;
  onAccepted: () => void;
  onClose: () => void;
}

// Shown the first time a user tries to do anything scan-related when they
// haven't yet accepted the platform terms. Backend enforces the gate on
// POST /api/scans; this UI just helps the user comply.
export default function LegalAcceptanceModal({
  apiKey,
  open,
  onAccepted,
  onClose,
}: Props) {
  const [terms, setTerms] = useState<{
    version: string;
    text: string;
    accepted: boolean;
  } | null>(null);
  const [checked, setChecked] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    getLegalTerms(apiKey)
      .then((d) =>
        setTerms({ version: d.version, text: d.text, accepted: d.accepted }),
      )
      .catch((e: Error) => setError(e.message));
  }, [apiKey, open]);

  async function accept() {
    if (!checked) {
      setError("Please confirm you have read and agreed to the terms.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await acceptLegalTerms(apiKey);
      onAccepted();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to record acceptance");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Terms of Acceptable Use"
      maxWidth={680}
    >
      {error && <div style={{ ...g.errorBox, marginBottom: 14 }}>{error}</div>}

      {!terms ? (
        <p style={g.empty}>Loading terms…</p>
      ) : (
        <>
          <pre
            style={{
              background: "#0f172a",
              border: "1px solid #1e293b",
              borderRadius: 10,
              padding: 16,
              color: "#cbd5e1",
              fontSize: 12,
              lineHeight: 1.6,
              maxHeight: 320,
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              fontFamily:
                "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            }}
          >
            {terms.text}
          </pre>

          <label
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 10,
              padding: "14px 0",
              cursor: "pointer",
              color: "#e2e8f0",
              fontSize: 13,
            }}
          >
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
              style={{ marginTop: 3 }}
            />
            <span>
              I have read and agree to the RASID terms ({terms.version}). I
              confirm that I will only scan targets I own or have explicit
              permission to test.
            </span>
          </label>

          <div
            style={{
              display: "flex",
              gap: 10,
              justifyContent: "flex-end",
              marginTop: 12,
            }}
          >
            <button onClick={onClose} style={g.btnSm}>
              Cancel
            </button>
            <button
              onClick={accept}
              disabled={submitting || !checked}
              style={{
                ...g.btnPrimary,
                opacity: !checked || submitting ? 0.55 : 1,
                cursor: !checked || submitting ? "not-allowed" : "pointer",
              }}
            >
              {submitting ? "Saving…" : "Accept & Continue"}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
