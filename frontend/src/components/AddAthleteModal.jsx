import { useState, useEffect } from "react";
import { X, UserPlus, Link as LinkIcon } from "lucide-react";
import { registerAthleteWithUser, getAthletes, assignAthlete } from "../api/athletes";
import { useAuth } from "../context/AuthContext";

function AddAthleteModal({ isOpen, onClose, onAthleteAdded }) {
  const { user: currentUser } = useAuth();
  const [tab, setTab] = useState("create"); // "create" | "assign"

  // Create form state
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("Athlete123!");
  const [sport, setSport] = useState("Football");
  const [position, setPosition] = useState("Forward");
  const [age, setAge] = useState("");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [injuryStatus, setInjuryStatus] = useState("Healthy");
  const [notes, setNotes] = useState("");

  // Assign mode state
  const [allAthletes, setAllAthletes] = useState([]);
  const [selectedAthleteId, setSelectedAthleteId] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Lock body scrolling cleanly while modal is open, restoring original state on close
  useEffect(() => {
    if (!isOpen) return;

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && tab === "assign") {
      loadUnassignedAthletes();
    }
  }, [isOpen, tab]);

  async function loadUnassignedAthletes() {
    try {
      const data = await getAthletes();
      const list = Array.isArray(data) ? data : data.items || [];
      setAllAthletes(list);
      if (list.length > 0) setSelectedAthleteId(list[0].athlete_id);
    } catch (err) {
      console.error(err);
    }
  }

  if (!isOpen) return null;

  async function handleSubmitCreate(e) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const newAthlete = await registerAthleteWithUser({
        name,
        email,
        password,
        sport,
        position,
        age: age ? parseInt(age, 10) : null,
        height: height ? parseFloat(height) : null,
        weight: weight ? parseFloat(weight) : null,
        injury_status: injuryStatus,
        coach_notes: notes,
      });

      if (onAthleteAdded) onAthleteAdded(newAthlete);
      onClose();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to create athlete account."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmitAssign(e) {
    e.preventDefault();
    if (!selectedAthleteId) return;
    setLoading(true);
    setError("");

    try {
      const updated = await assignAthlete(selectedAthleteId, {
        coach_id: currentUser?.user_id,
        injury_status: injuryStatus,
      });

      if (onAthleteAdded) onAthleteAdded(updated);
      onClose();
    } catch (err) {
      setError(
        err.response?.data?.detail || "Failed to assign athlete."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="add-athlete-modal-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="add-athlete-modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div className="stat-icon-wrapper purple">
              <UserPlus size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: "1.1rem" }}>Add Athlete to Roster</h3>
              <p style={{ margin: "2px 0 0", fontSize: "0.82rem", color: "var(--color-text-muted, #94a3b8)" }}>
                Register a new athlete profile or assign an existing athlete
              </p>
            </div>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        {/* Tabs */}
        <div className="add-athlete-modal-tabs">
          <button
            type="button"
            className={`tab-btn ${tab === "create" ? "active" : ""}`}
            onClick={() => setTab("create")}
          >
            <UserPlus size={16} />
            New Athlete Profile
          </button>

          <button
            type="button"
            className={`tab-btn ${tab === "assign" ? "active" : ""}`}
            onClick={() => setTab("assign")}
          >
            <LinkIcon size={16} />
            Assign Existing
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="add-athlete-modal-body">
          {error && <div className="error-box" style={{ marginBottom: 12 }}>{error}</div>}

          {tab === "create" ? (
            <form id="create-athlete-form" onSubmit={handleSubmitCreate} className="modal-form">
              <div className="form-grid-2col">
                <div className="form-group">
                  <label>Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Alex Morgan"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Email Address *</label>
                  <input
                    type="email"
                    required
                    placeholder="alex@team.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-grid-2col">
                <div className="form-group">
                  <label>Sport</label>
                  <select value={sport} onChange={(e) => setSport(e.target.value)}>
                    <option value="Football">Football / Soccer</option>
                    <option value="Basketball">Basketball</option>
                    <option value="Cricket">Cricket</option>
                    <option value="Running">Running / Track</option>
                    <option value="Tennis">Tennis</option>
                    <option value="Volleyball">Volleyball</option>
                    <option value="Other">Other Sport</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Position / Event</label>
                  <input
                    type="text"
                    placeholder="e.g. Midfielder"
                    value={position}
                    onChange={(e) => setPosition(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-grid-3col">
                <div className="form-group">
                  <label>Age</label>
                  <input
                    type="number"
                    placeholder="22"
                    value={age}
                    onChange={(e) => setAge(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Height (cm)</label>
                  <input
                    type="number"
                    placeholder="178"
                    value={height}
                    onChange={(e) => setHeight(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Weight (kg)</label>
                  <input
                    type="number"
                    placeholder="72"
                    value={weight}
                    onChange={(e) => setWeight(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label>Injury Status</label>
                <select value={injuryStatus} onChange={(e) => setInjuryStatus(e.target.value)}>
                  <option value="Healthy">Healthy (Fully Cleared)</option>
                  <option value="Injured">Injured (Out of Play)</option>
                  <option value="Recovering">Recovering / Limited</option>
                  <option value="Needs Evaluation">Needs Evaluation</option>
                </select>
              </div>

              <div className="form-group">
                <label>Initial Password for Athlete</label>
                <input
                  type="text"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Coach Notes</label>
                <textarea
                  rows={2}
                  placeholder="Initial observations or movement baseline notes..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                />
              </div>
            </form>
          ) : (
            <form id="assign-athlete-form" onSubmit={handleSubmitAssign} className="modal-form">
              <div className="form-group">
                <label>Select Athlete from System</label>
                <select
                  value={selectedAthleteId}
                  onChange={(e) => setSelectedAthleteId(e.target.value)}
                  style={{ width: "100%", padding: 10 }}
                >
                  {allAthletes.length === 0 ? (
                    <option value="">No athletes found</option>
                  ) : (
                    allAthletes.map((ath) => (
                      <option key={ath.athlete_id} value={ath.athlete_id}>
                        {ath.name || "Athlete"} ({ath.sport || "Unspecified"} • {ath.email || "No email"})
                        {ath.coach_id === currentUser?.user_id ? " [Already assigned]" : ""}
                      </option>
                    ))
                  )}
                </select>
              </div>

              <div className="form-group" style={{ marginTop: 14 }}>
                <label>Set Injury Status</label>
                <select value={injuryStatus} onChange={(e) => setInjuryStatus(e.target.value)}>
                  <option value="Healthy">Healthy (Fully Cleared)</option>
                  <option value="Injured">Injured (Out of Play)</option>
                  <option value="Recovering">Recovering / Limited</option>
                  <option value="Needs Evaluation">Needs Evaluation</option>
                </select>
              </div>
            </form>
          )}
        </div>

        {/* Footer */}
        <div className="add-athlete-modal-footer">
          <button type="button" className="secondary-button" onClick={onClose}>
            Cancel
          </button>
          <button
            type="submit"
            form={tab === "create" ? "create-athlete-form" : "assign-athlete-form"}
            className="primary-button"
            disabled={loading || (tab === "assign" && !selectedAthleteId)}
          >
            {tab === "create"
              ? loading ? "Creating..." : "Create Athlete Account"
              : loading ? "Assigning..." : "Assign to My Roster"
            }
          </button>
        </div>
      </div>
    </div>
  );
}

export default AddAthleteModal;
