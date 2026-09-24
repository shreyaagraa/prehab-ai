import { useState, useEffect } from "react";
import { Edit3, ShieldAlert, Check, X, Loader2 } from "lucide-react";
import { updateAthlete } from "../api/athletes";

function EditAthleteModal({ isOpen, onClose, athlete, onAthleteUpdated }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [form, setForm] = useState({
    sport: "",
    position: "",
    dominant_leg: "",
    height: "",
    weight: "",
    training_sessions_per_week: "",
    average_session_duration: "",
    average_session_rpe: "",
    current_fatigue_level: "",
    has_injury_history: "NO",
    injury_status: "Healthy",
    coach_notes: "",
  });

  useEffect(() => {
    if (athlete) {
      setForm({
        sport: athlete.sport || "",
        position: athlete.position || "",
        dominant_leg: athlete.dominant_leg || "",
        height: athlete.height || "",
        weight: athlete.weight || "",
        training_sessions_per_week: athlete.training_sessions_per_week || "",
        average_session_duration: athlete.average_session_duration || "",
        average_session_rpe: athlete.average_session_rpe || "",
        current_fatigue_level: athlete.current_fatigue_level || "",
        has_injury_history: athlete.has_injury_history || "NO",
        injury_status: athlete.injury_status || "Healthy",
        coach_notes: athlete.coach_notes || "",
      });
      setError("");
      setSuccessMsg("");
    }
  }, [athlete]);

  if (!isOpen || !athlete) return null;

  function updateField(e) {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setLoading(true);

    try {
      const payload = {
        sport: form.sport ? form.sport.trim() : null,
        position: form.position ? form.position.trim() : null,
        dominant_leg: form.dominant_leg ? form.dominant_leg.trim() : null,
        height: form.height ? parseFloat(form.height) : null,
        weight: form.weight ? parseFloat(form.weight) : null,
        training_sessions_per_week: form.training_sessions_per_week ? parseInt(form.training_sessions_per_week, 10) : null,
        average_session_duration: form.average_session_duration ? parseInt(form.average_session_duration, 10) : null,
        average_session_rpe: form.average_session_rpe ? parseFloat(form.average_session_rpe) : null,
        current_fatigue_level: form.current_fatigue_level ? parseInt(form.current_fatigue_level, 10) : null,
        has_injury_history: form.has_injury_history || null,
        injury_status: form.injury_status || "Healthy",
        coach_notes: form.coach_notes ? form.coach_notes.trim() : null,
      };

      const updated = await updateAthlete(athlete.athlete_id, payload);
      setSuccessMsg("Athlete profile updated successfully!");
      if (onAthleteUpdated) {
        onAthleteUpdated(updated);
      }
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to update athlete profile. Please verify your permissions."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="consent-modal-overlay">
      <div className="consent-modal-container" style={{ maxWidth: "600px" }}>
        <div className="consent-modal-header">
          <div className="consent-header-icon blue">
            <Edit3 size={24} />
          </div>
          <div className="consent-header-title">
            <h3>Edit Athlete Profile</h3>
            <p>{athlete.name || "Athlete Profile"} • Roster Management</p>
          </div>
          <button type="button" className="consent-close-btn" onClick={onClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="consent-modal-body">
          {error && (
            <div className="consent-error-alert" role="alert">
              <ShieldAlert size={18} />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="consent-success-alert" style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.75rem", backgroundColor: "rgba(16, 185, 129, 0.15)", border: "1px solid #10b981", borderRadius: "0.5rem", color: "#34d399", marginBottom: "1rem" }}>
              <Check size={18} />
              <span>{successMsg}</span>
            </div>
          )}

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            <div className="form-group">
              <label htmlFor="edit-ath-sport">Sport</label>
              <input
                id="edit-ath-sport"
                type="text"
                name="sport"
                value={form.sport}
                onChange={updateField}
                placeholder="e.g. Football, Basketball"
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-position">Position</label>
              <input
                id="edit-ath-position"
                type="text"
                name="position"
                value={form.position}
                onChange={updateField}
                placeholder="e.g. Midfielder, Guard"
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-height">Height (cm)</label>
              <input
                id="edit-ath-height"
                type="number"
                name="height"
                value={form.height}
                onChange={updateField}
                placeholder="180"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-weight">Weight (kg)</label>
              <input
                id="edit-ath-weight"
                type="number"
                name="weight"
                value={form.weight}
                onChange={updateField}
                placeholder="75"
                step="0.1"
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-dominant-leg">Dominant Leg</label>
              <select
                id="edit-ath-dominant-leg"
                name="dominant_leg"
                value={form.dominant_leg}
                onChange={updateField}
              >
                <option value="">Select Dominant Leg</option>
                <option value="Right">Right</option>
                <option value="Left">Left</option>
                <option value="Ambidextrous">Ambidextrous</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-injury-status">Injury Status</label>
              <select
                id="edit-ath-injury-status"
                name="injury_status"
                value={form.injury_status}
                onChange={updateField}
              >
                <option value="Healthy">Healthy</option>
                <option value="At Risk">At Risk</option>
                <option value="Injured">Injured</option>
                <option value="Rehabilitating">Rehabilitating</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-sessions">Sessions / Week</label>
              <input
                id="edit-ath-sessions"
                type="number"
                name="training_sessions_per_week"
                value={form.training_sessions_per_week}
                onChange={updateField}
                placeholder="5"
                min="0"
                max="30"
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-duration">Duration (min)</label>
              <input
                id="edit-ath-duration"
                type="number"
                name="average_session_duration"
                value={form.average_session_duration}
                onChange={updateField}
                placeholder="90"
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-rpe">Average Session RPE (1-10)</label>
              <input
                id="edit-ath-rpe"
                type="number"
                name="average_session_rpe"
                value={form.average_session_rpe}
                onChange={updateField}
                placeholder="7.5"
                step="0.1"
                min="1"
                max="10"
              />
            </div>

            <div className="form-group">
              <label htmlFor="edit-ath-fatigue">Fatigue Level (1-10)</label>
              <input
                id="edit-ath-fatigue"
                type="number"
                name="current_fatigue_level"
                value={form.current_fatigue_level}
                onChange={updateField}
                placeholder="4"
                min="1"
                max="10"
              />
            </div>
          </div>

          <div className="form-group" style={{ marginTop: "1rem" }}>
            <label htmlFor="edit-ath-notes">Coach Notes & Clinical Observations</label>
            <textarea
              id="edit-ath-notes"
              name="coach_notes"
              value={form.coach_notes}
              onChange={updateField}
              rows={3}
              placeholder="Enter notes on athlete movement, biomechanical focus, or rehab progress..."
              style={{ width: "100%", padding: "0.625rem", backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "0.375rem", color: "#f8fafc" }}
            />
          </div>

          <div className="consent-modal-footer">
            <button type="button" className="consent-cancel-btn" onClick={onClose} disabled={loading}>
              Cancel
            </button>
            <button type="submit" className="consent-submit-btn" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={16} className="spinner-icon" />
                  <span>Saving Changes...</span>
                </>
              ) : (
                <>
                  <Check size={16} />
                  <span>Save Profile</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default EditAthleteModal;
