import { useState, useEffect } from "react";
import { ShieldCheck, ShieldAlert, Lock, Info, X, Check, Loader2, UserCheck } from "lucide-react";
import { getConsentStatus, grantConsent } from "../api/consent";

function ConsentGateModal({ isOpen, onClose, onConsentGranted, user }) {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [statusData, setStatusData] = useState(null);

  const [consentRisk, setConsentRisk] = useState(true);
  const [consentProgress, setConsentProgress] = useState(true);
  const [consentResearch, setConsentResearch] = useState(false);

  const [guardianName, setGuardianName] = useState("");
  const [guardianEmail, setGuardianEmail] = useState("");
  const [guardianRelationship, setGuardianRelationship] = useState("Parent / Legal Guardian");

  useEffect(() => {
    if (isOpen) {
      loadConsentStatus();
    }
  }, [isOpen]);

  async function loadConsentStatus() {
    setLoading(true);
    setError("");
    try {
      const res = await getConsentStatus();
      setStatusData(res);
      
      // Initialize checkboxes based on current DB state
      const riskItem = res.consents.find((c) => c.purpose === "injury_risk_analysis");
      const progItem = res.consents.find((c) => c.purpose === "progress_tracking");
      const resItem = res.consents.find((c) => c.purpose === "research_anonymised");

      setConsentRisk(riskItem ? riskItem.status === "GRANTED" : true);
      setConsentProgress(progItem ? progItem.status === "GRANTED" : true);
      setConsentResearch(resItem ? resItem.status === "GRANTED" : false);

      if (riskItem?.guardian_name) setGuardianName(riskItem.guardian_name);
      if (riskItem?.guardian_email) setGuardianEmail(riskItem.guardian_email);
      if (riskItem?.guardian_relationship) setGuardianRelationship(riskItem.guardian_relationship);

    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load consent status.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!consentRisk || !consentProgress) {
      setError("Both Injury-Risk Analysis and Progress Tracking consents are required to upload videos.");
      return;
    }

    if (statusData?.is_minor && !guardianName.trim()) {
      setError("Parent / Legal Guardian full name is required for athletes under 18.");
      return;
    }

    setError("");
    setSubmitting(true);

    try {
      const payload = [];

      if (consentRisk) {
        payload.push({
          purpose: "injury_risk_analysis",
          notice_version: "v1.0",
          provided_by: statusData?.is_minor ? "parent_guardian" : "self",
          guardian_name: statusData?.is_minor ? guardianName : null,
          guardian_email: statusData?.is_minor ? guardianEmail : null,
          guardian_relationship: statusData?.is_minor ? guardianRelationship : null,
        });
      }

      if (consentProgress) {
        payload.push({
          purpose: "progress_tracking",
          notice_version: "v1.0",
          provided_by: statusData?.is_minor ? "parent_guardian" : "self",
          guardian_name: statusData?.is_minor ? guardianName : null,
          guardian_email: statusData?.is_minor ? guardianEmail : null,
          guardian_relationship: statusData?.is_minor ? guardianRelationship : null,
        });
      }

      if (consentResearch) {
        payload.push({
          purpose: "research_anonymised",
          notice_version: "v1.0",
          provided_by: statusData?.is_minor ? "parent_guardian" : "self",
          guardian_name: statusData?.is_minor ? guardianName : null,
          guardian_email: statusData?.is_minor ? guardianEmail : null,
          guardian_relationship: statusData?.is_minor ? guardianRelationship : null,
        });
      }

      await grantConsent(payload);
      onConsentGranted();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to record consent decision. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="consent-modal-overlay">
      <div className="consent-modal-container">
        {/* Header */}
        <div className="consent-modal-header">
          <div className="consent-header-icon cyan">
            <ShieldCheck size={24} />
          </div>
          <div className="consent-header-title">
            <h3>PreHab AI Video Collection Consent Gate</h3>
            <p>Purpose-specific privacy permissions before video upload</p>
          </div>
          <button type="button" className="consent-close-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        {/* Loading / Error States */}
        {loading ? (
          <div className="consent-loading-box">
            <Loader2 size={32} className="spinner-icon" />
            <p>Checking privacy consent status...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="consent-modal-body">
            {error && (
              <div className="consent-error-alert" role="alert">
                <ShieldAlert size={18} />
                <span>{error}</span>
              </div>
            )}

            {/* Minor Notification Banner */}
            {statusData?.is_minor && (
              <div className="consent-minor-alert">
                <UserCheck size={20} className="minor-alert-icon" />
                <div>
                  <strong>Parental / Guardian Consent Required</strong>
                  <p>
                    Athlete is under 18 years of age (born {statusData?.date_of_birth || "N/A"}). Parental or legal guardian authorization is required before processing movement data.
                  </p>
                </div>
              </div>
            )}

            {/* Explanation Section */}
            <div className="consent-info-banner">
              <Info size={18} className="info-icon" />
              <div>
                <strong>Why we collect your video data:</strong>
                <p>
                  Your uploaded movement video is processed by AI computer vision to compute joint flexion angles, bilateral asymmetry, and Landing Error Scoring System (LESS) risk metrics.
                </p>
              </div>
            </div>

            {/* Purpose-Specific Checkboxes */}
            <div className="consent-purposes-list">
              {/* Purpose A: Injury Risk */}
              <div className={`consent-purpose-card ${consentRisk ? "active" : ""}`}>
                <label className="purpose-checkbox-label">
                  <input
                    type="checkbox"
                    checked={consentRisk}
                    onChange={(e) => setConsentRisk(e.target.checked)}
                  />
                  <div className="purpose-text font-semibold">
                    <span className="purpose-title">A. Injury-Risk & Movement Analysis</span>
                    <span className="purpose-badge required">Required</span>
                    <p className="purpose-desc">
                      Authorize PreHab AI to process your video movement data for biomechanical joint tracking and injury risk analysis.
                    </p>
                  </div>
                </label>
              </div>

              {/* Purpose B: Progress Tracking */}
              <div className={`consent-purpose-card ${consentProgress ? "active" : ""}`}>
                <label className="purpose-checkbox-label">
                  <input
                    type="checkbox"
                    checked={consentProgress}
                    onChange={(e) => setConsentProgress(e.target.checked)}
                  />
                  <div className="purpose-text font-semibold">
                    <span className="purpose-title">B. Progress & Longitudinal Tracking</span>
                    <span className="purpose-badge required">Required</span>
                    <p className="purpose-desc">
                      Authorize retention of movement assessment data to track risk progression and recovery over time.
                    </p>
                  </div>
                </label>
              </div>

              {/* Purpose C: Research (Optional) */}
              <div className={`consent-purpose-card ${consentResearch ? "active" : ""}`}>
                <label className="purpose-checkbox-label">
                  <input
                    type="checkbox"
                    checked={consentResearch}
                    onChange={(e) => setConsentResearch(e.target.checked)}
                  />
                  <div className="purpose-text font-semibold">
                    <span className="purpose-title">C. Anonymised Research & AI Improvement</span>
                    <span className="purpose-badge optional">Optional</span>
                    <p className="purpose-desc">
                      Allow anonymised, de-identified movement features to be used for scientific research and improving AI scoring accuracy.
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Parent / Guardian Input (Only for Minors < 18) */}
            {statusData?.is_minor && (
              <div className="consent-guardian-form">
                <h4 className="guardian-form-title">
                  <Lock size={16} /> Parent / Legal Guardian Details
                </h4>

                <div className="form-group">
                  <label htmlFor="guardian-name-input">Guardian Full Name *</label>
                  <input
                    id="guardian-name-input"
                    type="text"
                    value={guardianName}
                    onChange={(e) => setGuardianName(e.target.value)}
                    placeholder="Enter parent or guardian's full name"
                    required
                  />
                </div>

                <div className="form-row" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                  <div className="form-group">
                    <label htmlFor="guardian-email-input">Guardian Contact Email / Phone</label>
                    <input
                      id="guardian-email-input"
                      type="text"
                      value={guardianEmail}
                      onChange={(e) => setGuardianEmail(e.target.value)}
                      placeholder="parent@example.com"
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="guardian-rel-input">Relationship</label>
                    <select
                      id="guardian-rel-input"
                      value={guardianRelationship}
                      onChange={(e) => setGuardianRelationship(e.target.value)}
                    >
                      <option value="Parent / Legal Guardian">Parent / Legal Guardian</option>
                      <option value="Mother">Mother</option>
                      <option value="Father">Father</option>
                      <option value="Legal Guardian">Legal Guardian</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Footer Buttons */}
            <div className="consent-modal-footer">
              <button
                type="button"
                className="consent-cancel-btn"
                onClick={onClose}
                disabled={submitting}
              >
                Cancel / Go Back
              </button>
              <button
                type="submit"
                className="consent-submit-btn"
                disabled={submitting || !consentRisk || !consentProgress}
              >
                {submitting ? (
                  <>
                    <Loader2 size={16} className="spinner-icon" />
                    <span>Recording Consent...</span>
                  </>
                ) : (
                  <>
                    <Check size={16} />
                    <span>Agree & Continue to Upload</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default ConsentGateModal;
