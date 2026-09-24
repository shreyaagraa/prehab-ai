import { useState, useEffect } from "react";
import { ShieldCheck, ShieldAlert, Lock, UserCheck, RefreshCw, Check, X, Loader2, FileText, ToggleLeft, ToggleRight } from "lucide-react";
import { getConsentStatus, withdrawConsent, grantConsent } from "../api/consent";
import { getReportSharingStatus, updateReportSharing } from "../api/reportSharing";

function PrivacyAndConsentSection({ user }) {
  const [consentData, setConsentData] = useState(null);
  const [loadingConsent, setLoadingConsent] = useState(true);
  const [consentMsg, setConsentMsg] = useState({ type: "", text: "" });

  const [sharingData, setSharingData] = useState(null);
  const [loadingSharing, setLoadingSharing] = useState(true);
  const [sharingMsg, setSharingMsg] = useState({ type: "", text: "" });

  const [withdrawTarget, setWithdrawTarget] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadConsentInfo();
    loadSharingInfo();
  }, []);

  async function loadConsentInfo() {
    setLoadingConsent(true);
    try {
      const data = await getConsentStatus();
      setConsentData(data);
    } catch (err) {
      console.warn("Could not load consent status:", err);
    } finally {
      setLoadingConsent(false);
    }
  }

  async function loadSharingInfo() {
    setLoadingSharing(true);
    try {
      const data = await getReportSharingStatus();
      setSharingData(data);
    } catch (err) {
      console.warn("Could not load report sharing status:", err);
    } finally {
      setLoadingSharing(false);
    }
  }

  async function handleConfirmWithdraw() {
    if (!withdrawTarget) return;
    setActionLoading(true);
    setConsentMsg({ type: "", text: "" });

    try {
      const updated = await withdrawConsent(withdrawTarget.purpose);
      setConsentData(updated);
      setConsentMsg({
        type: "success",
        text: `Consent for '${withdrawTarget.label}' has been withdrawn. Associated data access/upload rules have been activated.`,
      });
      setWithdrawTarget(null);
    } catch (err) {
      setConsentMsg({
        type: "error",
        text: err.response?.data?.detail || "Failed to withdraw consent.",
      });
    } finally {
      setActionLoading(false);
    }
  }

  async function handleToggleSharing(target_role, currentStatus) {
    setSharingMsg({ type: "", text: "" });
    const newStatus = !currentStatus;

    try {
      const updated = await updateReportSharing(target_role, newStatus);
      setSharingData(updated);
      setSharingMsg({
        type: "success",
        text: `Report access for ${target_role} has been ${newStatus ? "authorized" : "revoked"}.`,
      });
    } catch (err) {
      setSharingMsg({
        type: "error",
        text: err.response?.data?.detail || "Failed to update report sharing setting.",
      });
    }
  }

  return (
    <div className="privacy-consent-wrapper" style={{ marginTop: "2rem" }}>
      {/* ── Section Header ───────────────────────────────────────────── */}
      <div className="section-title-row" style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "1rem" }}>
        <ShieldCheck size={22} className="text-emerald" />
        <h2 style={{ fontSize: "1.25rem", fontWeight: "600", color: "#f9fafb", margin: 0 }}>
          Consent & Privacy Management
        </h2>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
        {/* Panel 1: Active Consents */}
        <section className="panel card-panel">
          <div className="panel-header">
            <div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: "600", margin: 0, color: "#f8fafc" }}>
                Active Data Processing Consents
              </h3>
              <p style={{ fontSize: "0.85rem", color: "#94a3b8", margin: "2px 0 0" }}>
                Purpose-specific authorizations for video analysis and tracking
              </p>
            </div>
          </div>

          {consentMsg.text && (
            <div
              style={{
                padding: "0.75rem",
                borderRadius: "0.5rem",
                marginBottom: "1rem",
                fontSize: "0.875rem",
                backgroundColor: consentMsg.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                border: `1px solid ${consentMsg.type === "success" ? "#10b981" : "#ef4444"}`,
                color: consentMsg.type === "success" ? "#34d399" : "#f87171",
              }}
            >
              {consentMsg.text}
            </div>
          )}

          {loadingConsent ? (
            <div style={{ padding: "1.5rem 0", textAlign: "center", color: "#94a3b8" }}>
              <Loader2 size={24} className="spinner-icon" />
              <p>Loading consent log...</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {/* Minor status badge */}
              {consentData?.is_minor && (
                <div style={{ padding: "0.75rem", borderRadius: "0.5rem", backgroundColor: "rgba(245, 158, 11, 0.15)", border: "1px solid #f59e0b", color: "#fbbf24", fontSize: "0.85rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <UserCheck size={18} />
                  <span>Minor Account (&lt;18 yrs) — Guardian: <strong>{consentData?.consents[0]?.guardian_name || "Parent/Guardian"}</strong></span>
                </div>
              )}

              {consentData?.consents.map((item) => (
                <div
                  key={item.purpose}
                  style={{
                    padding: "1rem",
                    borderRadius: "0.5rem",
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    display: "flex",
                    flexDirection: "column",
                    gap: "0.5rem",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <strong style={{ fontSize: "0.95rem", color: "#f8fafc" }}>{item.label}</strong>
                      {item.is_required && (
                        <span style={{ marginLeft: "0.5rem", fontSize: "0.75rem", padding: "0.15rem 0.5rem", borderRadius: "0.25rem", backgroundColor: "rgba(59, 130, 246, 0.2)", color: "#60a5fa", border: "1px solid #3b82f6" }}>
                          Required
                        </span>
                      )}
                    </div>

                    <span
                      style={{
                        padding: "0.2rem 0.6rem",
                        borderRadius: "1rem",
                        fontSize: "0.75rem",
                        fontWeight: "600",
                        backgroundColor: item.status === "GRANTED" ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)",
                        color: item.status === "GRANTED" ? "#34d399" : "#f87171",
                        border: `1px solid ${item.status === "GRANTED" ? "#10b981" : "#ef4444"}`,
                      }}
                    >
                      {item.status === "GRANTED" ? "ACTIVE / GRANTED" : "WITHDRAWN"}
                    </span>
                  </div>

                  <p style={{ fontSize: "0.825rem", color: "#94a3b8", margin: 0 }}>{item.description}</p>

                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "0.5rem", fontSize: "0.75rem", color: "#64748b" }}>
                    <span>Notice: {item.notice_version}</span>
                    {item.status === "GRANTED" && (
                      <button
                        type="button"
                        onClick={() => setWithdrawTarget(item)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#f87171",
                          fontSize: "0.8rem",
                          fontWeight: "500",
                          cursor: "pointer",
                          textDecoration: "underline",
                        }}
                      >
                        Withdraw Consent
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Panel 2: Athlete-Controlled Report Sharing */}
        <section className="panel card-panel">
          <div className="panel-header">
            <div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: "600", margin: 0, color: "#f8fafc" }}>
                Report Sharing & Access Controls
              </h3>
              <p style={{ fontSize: "0.85rem", color: "#94a3b8", margin: "2px 0 0" }}>
                Control which staff roles can access your biomechanical risk reports
              </p>
            </div>
          </div>

          {sharingMsg.text && (
            <div
              style={{
                padding: "0.75rem",
                borderRadius: "0.5rem",
                marginBottom: "1rem",
                fontSize: "0.875rem",
                backgroundColor: sharingMsg.type === "success" ? "rgba(16, 185, 129, 0.15)" : "rgba(239, 68, 68, 0.15)",
                border: `1px solid ${sharingMsg.type === "success" ? "#10b981" : "#ef4444"}`,
                color: sharingMsg.type === "success" ? "#34d399" : "#f87171",
              }}
            >
              {sharingMsg.text}
            </div>
          )}

          {loadingSharing ? (
            <div style={{ padding: "1.5rem 0", textAlign: "center", color: "#94a3b8" }}>
              <Loader2 size={24} className="spinner-icon" />
              <p>Loading sharing permissions...</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
              {sharingData?.shares.map((s) => (
                <div
                  key={s.target_role}
                  style={{
                    padding: "1rem",
                    borderRadius: "0.5rem",
                    backgroundColor: "#1e293b",
                    border: "1px solid #334155",
                    display: "flex",
                    justifySpace: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <strong style={{ fontSize: "0.95rem", color: "#f8fafc", display: "block" }}>{s.target_role_label}</strong>
                    <span style={{ fontSize: "0.8rem", color: s.is_authorized ? "#34d399" : "#f87171" }}>
                      {s.is_authorized ? "Access Authorized ✓" : "Access Revoked ✕"}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleToggleSharing(s.target_role, s.is_authorized)}
                    style={{
                      padding: "0.4rem 0.8rem",
                      borderRadius: "0.375rem",
                      fontSize: "0.8rem",
                      fontWeight: "600",
                      border: s.is_authorized ? "1px solid #ef4444" : "1px solid #10b981",
                      backgroundColor: s.is_authorized ? "rgba(239, 68, 68, 0.15)" : "rgba(16, 185, 129, 0.15)",
                      color: s.is_authorized ? "#f87171" : "#34d399",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.4rem",
                    }}
                  >
                    {s.is_authorized ? "Revoke Access" : "Authorize Access"}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* Confirmation Modal for Consent Withdrawal */}
      {withdrawTarget && (
        <div className="consent-modal-overlay">
          <div className="consent-modal-container" style={{ maxWidth: "450px" }}>
            <div className="consent-modal-header">
              <div className="consent-header-icon" style={{ backgroundColor: "rgba(239, 68, 68, 0.2)", color: "#ef4444" }}>
                <ShieldAlert size={24} />
              </div>
              <div className="consent-header-title">
                <h3>Confirm Consent Withdrawal</h3>
                <p>{withdrawTarget.label}</p>
              </div>
              <button type="button" className="consent-close-btn" onClick={() => setWithdrawTarget(null)}>
                <X size={20} />
              </button>
            </div>

            <div className="consent-modal-body">
              <p style={{ fontSize: "0.9rem", color: "#cbd5e1" }}>
                Are you sure you want to withdraw consent for <strong>{withdrawTarget.label}</strong>?
              </p>
              {withdrawTarget.is_required && (
                <div style={{ padding: "0.75rem", borderRadius: "0.5rem", backgroundColor: "rgba(239, 68, 68, 0.15)", border: "1px solid #ef4444", color: "#f87171", fontSize: "0.85rem" }}>
                  <strong>Warning:</strong> Withdrawing required consent will block future video uploads and prevent new risk assessments.
                </div>
              )}
            </div>

            <div className="consent-modal-footer">
              <button type="button" className="consent-cancel-btn" onClick={() => setWithdrawTarget(null)} disabled={actionLoading}>
                Cancel
              </button>
              <button
                type="button"
                className="consent-submit-btn"
                style={{ backgroundColor: "#dc2626" }}
                onClick={handleConfirmWithdraw}
                disabled={actionLoading}
              >
                {actionLoading ? "Withdrawing..." : "Confirm Withdrawal"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default PrivacyAndConsentSection;
