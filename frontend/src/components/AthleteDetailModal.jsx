import { useState } from "react";
import { X, Activity, Edit3, Check, ShieldAlert, TrendingUp, TrendingDown, Clock, Activity as ActivityIcon } from "lucide-react";
import RiskBadge from "./RiskBadge";
import { assignAthlete } from "../api/athletes";
import { useAuth } from "../context/AuthContext";

function AthleteDetailModal({ isOpen, onClose, athlete, onUpdate, onEditProfile }) {
  const { user: currentUser } = useAuth();
  const [editingNotes, setEditingNotes] = useState(false);
  const [notes, setNotes] = useState(athlete?.coach_notes || "");
  const [injuryStatus, setInjuryStatus] = useState(athlete?.injury_status || "Healthy");
  const [saving, setSaving] = useState(false);

  if (!isOpen || !athlete) return null;

  const isAssignedToMe = athlete.coach_id === currentUser?.user_id;

  async function handleToggleAssign() {
    setSaving(true);
    try {
      const updated = await assignAthlete(athlete.athlete_id, {
        coach_id: isAssignedToMe ? null : currentUser?.user_id,
        injury_status: injuryStatus,
        coach_notes: notes,
      });
      if (onUpdate) onUpdate(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  async function handleSaveStatusAndNotes() {
    setSaving(true);
    try {
      const updated = await assignAthlete(athlete.athlete_id, {
        coach_id: athlete.coach_id,
        injury_status: injuryStatus,
        coach_notes: notes,
      });
      setEditingNotes(false);
      if (onUpdate) onUpdate(updated);
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  }

  function formatDate(dStr) {
    if (!dStr) return "Never assessed";
    return new Date(dStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content card-panel athlete-analytics-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header Banner */}
        <div className="athlete-analytics-header">
          <div>
            <span className="eyebrow" style={{ color: "#6366f1", fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.05em" }}>
              ATHLETE PERFORMANCE ANALYTICS & BIOMECHANICS
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4 }}>
              <div className="avatar" style={{ width: 42, height: 42, fontSize: "1.1rem" }}>
                {(athlete.name || "A").charAt(0)}
              </div>
              <div>
                <h2 style={{ margin: 0, fontSize: "1.25rem", color: "#0f172a" }}>{athlete.name || "Athlete Profile"}</h2>
                <p style={{ margin: "2px 0 0", fontSize: "0.82rem", color: "var(--color-text-muted, #64748b)" }}>
                  {athlete.sport || "Athlete"} • {athlete.position || "Player"} — {athlete.email || "No email"}
                </p>
              </div>
            </div>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close modal">
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="athlete-analytics-body">
          {/* Section 1: Action & Status Control Bar */}
          <div className="analytics-action-bar">
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#475569" }}>Injury Status:</span>
              <select
                value={injuryStatus}
                onChange={(e) => setInjuryStatus(e.target.value)}
                style={{ padding: "6px 12px", borderRadius: 8, background: "#ffffff", color: "#0f172a", border: "1px solid #cbd5e1", fontSize: "0.85rem", fontWeight: 500 }}
              >
                <option value="Healthy">Healthy (Fully Cleared)</option>
                <option value="Injured">Injured (Out of Play)</option>
                <option value="Recovering">Recovering / Limited</option>
                <option value="Needs Evaluation">Needs Evaluation</option>
              </select>
            </div>

            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              {(currentUser?.role === "Coach" || currentUser?.role === "Admin" || currentUser?.role === "Physiotherapist") && (
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => {
                    onClose();
                    if (onEditProfile) onEditProfile(athlete);
                  }}
                  style={{ fontSize: "0.85rem", padding: "7px 14px", display: "flex", alignItems: "center", gap: 6 }}
                >
                  <Edit3 size={15} /> Edit Profile
                </button>
              )}

              <button
                type="button"
                className={isAssignedToMe ? "secondary-button" : "primary-button"}
                onClick={handleToggleAssign}
                disabled={saving}
                style={{ fontSize: "0.85rem", padding: "7px 14px" }}
              >
                {isAssignedToMe ? "Unassign from Me" : "Assign to My Roster"}
              </button>
            </div>
          </div>

          {/* Section 2: Key Risk & Performance Metrics Grid (4-Card Equal Grid) */}
          <div className="analytics-metrics-grid">
            {/* Card 1: Latest Risk */}
            <div className="analytics-metric-card">
              <div className="analytics-card-header">
                <span className="analytics-card-title">Latest Risk Score</span>
                <div className="stat-icon-wrapper indigo" style={{ width: 32, height: 32 }}>
                  <Activity size={16} />
                </div>
              </div>
              <div className="analytics-card-value">
                <span>
                  {athlete.latest_risk_score !== null && athlete.latest_risk_score !== undefined
                    ? Math.round(athlete.latest_risk_score)
                    : "N/A"}
                </span>
                {athlete.latest_risk_level && <RiskBadge level={athlete.latest_risk_level} />}
              </div>
              <span className="analytics-card-subtext">
                Assessed: {formatDate(athlete.last_assessment_date)}
              </span>
            </div>

            {/* Card 2: LESS Score */}
            <div className="analytics-metric-card">
              <div className="analytics-card-header">
                <span className="analytics-card-title">LESS Score</span>
                <div className="stat-icon-wrapper purple" style={{ width: 32, height: 32 }}>
                  <ActivityIcon size={16} />
                </div>
              </div>
              <div className="analytics-card-value">
                <span>
                  {athlete.latest_less_score !== null && athlete.latest_less_score !== undefined
                    ? `${athlete.latest_less_score} / ${athlete.latest_less_max || 12}`
                    : "N/A"}
                </span>
              </div>
              <span className="analytics-card-subtext">
                Landing Error Technique Rating
              </span>
            </div>

            {/* Card 3: Risk Trend */}
            <div className="analytics-metric-card">
              <div className="analytics-card-header">
                <span className="analytics-card-title">Risk Trend</span>
                <div className="stat-icon-wrapper teal" style={{ width: 32, height: 32 }}>
                  {athlete.risk_change > 0 ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
                </div>
              </div>
              <div className="analytics-card-value">
                {athlete.risk_change !== null && athlete.risk_change !== undefined ? (
                  <span style={{ color: athlete.risk_change > 0 ? "#ef4444" : "#10b981", fontSize: "1.2rem" }}>
                    {athlete.risk_change > 0 ? `+${athlete.risk_change}` : `${athlete.risk_change}`} pts
                  </span>
                ) : (
                  <span style={{ fontSize: "1.1rem", color: "#64748b" }}>Baseline</span>
                )}
              </div>
              <span className="analytics-card-subtext">
                vs Previous Test
              </span>
            </div>

            {/* Card 4: Reassessment */}
            <div className="analytics-metric-card">
              <div className="analytics-card-header">
                <span className="analytics-card-title">Reassessment</span>
                <div className="stat-icon-wrapper gray" style={{ width: 32, height: 32 }}>
                  <Clock size={16} />
                </div>
              </div>
              <div className="analytics-card-value">
                {athlete.needs_reassessment ? (
                  <span style={{ color: "#d97706", fontSize: "1.05rem", display: "flex", alignItems: "center", gap: 4 }}>
                    <ShieldAlert size={16} /> Due Now
                  </span>
                ) : (
                  <span style={{ color: "#16a34a", fontSize: "1.05rem", display: "flex", alignItems: "center", gap: 4 }}>
                    <Check size={16} /> Up to Date
                  </span>
                )}
              </div>
              <span className="analytics-card-subtext">
                Monitoring Cadence
              </span>
            </div>
          </div>

          {/* Section 3: Physical Profile & Baseline Metrics */}
          <div className="analytics-section-panel">
            <h4 className="analytics-section-title">
              PHYSICAL PROFILE & BASELINE METRICS
            </h4>
            <div className="analytics-bio-grid">
              <div className="analytics-bio-tile">
                <span className="analytics-bio-label">Age</span>
                <span className="analytics-bio-val">{athlete.age ? `${athlete.age} yrs` : "—"}</span>
              </div>
              <div className="analytics-bio-tile">
                <span className="analytics-bio-label">Height</span>
                <span className="analytics-bio-val">{athlete.height ? `${athlete.height} cm` : "—"}</span>
              </div>
              <div className="analytics-bio-tile">
                <span className="analytics-bio-label">Weight</span>
                <span className="analytics-bio-val">{athlete.weight ? `${athlete.weight} kg` : "—"}</span>
              </div>
              <div className="analytics-bio-tile">
                <span className="analytics-bio-label">Strength Index</span>
                <span className="analytics-bio-val">{athlete.strength ? `${athlete.strength}` : "Standard"}</span>
              </div>
              <div className="analytics-bio-tile">
                <span className="analytics-bio-label">Flexibility Rating</span>
                <span className="analytics-bio-val">{athlete.flexibility ? `${athlete.flexibility}` : "Standard"}</span>
              </div>
              <div className="analytics-bio-tile">
                <span className="analytics-bio-label">Balance Rating</span>
                <span className="analytics-bio-val">{athlete.balance ? `${athlete.balance}` : "Standard"}</span>
              </div>
            </div>
          </div>

          {/* Section 4: Clinical & Coach Observations */}
          <div className="analytics-section-panel">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h4 className="analytics-section-title" style={{ margin: 0 }}>
                CLINICAL & COACH OBSERVATIONS
              </h4>
              {!editingNotes ? (
                <button className="icon-button" onClick={() => setEditingNotes(true)} title="Edit Notes">
                  <Edit3 size={16} />
                </button>
              ) : (
                <button className="primary-button" style={{ fontSize: "0.8rem", padding: "4px 10px" }} onClick={handleSaveStatusAndNotes} disabled={saving}>
                  Save Notes
                </button>
              )}
            </div>

            {editingNotes ? (
              <textarea
                rows={3}
                style={{ width: "100%", padding: 10, borderRadius: 8, background: "#ffffff", color: "#0f172a", border: "1px solid #cbd5e1", fontSize: "0.88rem" }}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            ) : (
              <p style={{ margin: 0, fontSize: "0.88rem", fontStyle: athlete.coach_notes ? "normal" : "italic", color: athlete.coach_notes ? "#334155" : "#94a3b8", lineHeight: 1.5 }}>
                {athlete.coach_notes || notes || "No custom observations recorded for this athlete."}
              </p>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div style={{ display: "flex", justifyContent: "flex-end", padding: "14px 24px", borderTop: "1px solid #e2e8f0", background: "#f8fafc", flexShrink: 0 }}>
          <button className="secondary-button" onClick={onClose} style={{ padding: "8px 20px" }}>
            Close Analytics
          </button>
        </div>
      </div>
    </div>
  );
}

export default AthleteDetailModal;
