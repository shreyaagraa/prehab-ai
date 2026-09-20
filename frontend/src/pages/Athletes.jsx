import { useEffect, useState } from "react";
import { Search, UserRound, UserPlus, Grid, List, Filter, ShieldAlert, CheckCircle2, Eye, Link as LinkIcon } from "lucide-react";

import RiskBadge from "../components/RiskBadge";
import Loading from "../components/Loading";
import AddAthleteModal from "../components/AddAthleteModal";
import AthleteDetailModal from "../components/AthleteDetailModal";

import { getAthletes, assignAthlete } from "../api/athletes";
import { useAuth } from "../context/AuthContext";

function Athletes() {
  const { user } = useAuth();
  const [athletes, setAthletes] = useState([]);
  const [search, setSearch] = useState("");
  const [activeGroupFilter, setActiveGroupFilter] = useState("all"); // "all" | "my" | "high_risk" | "reassessment" | "injured" | "Football" | "Basketball" | "Cricket"
  const [viewMode, setViewMode] = useState("grid"); // "grid" | "table"

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [selectedAthlete, setSelectedAthlete] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadAthletes = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await getAthletes();
      setAthletes(Array.isArray(data) ? data : data.items || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Unable to load athletes.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAthletes();
  }, []);

  const filteredAthletes = athletes.filter((athlete) => {
    const nameMatch = (athlete.name || "").toLowerCase().includes(search.toLowerCase());
    const emailMatch = (athlete.email || "").toLowerCase().includes(search.toLowerCase());
    const sportMatch = (athlete.sport || "").toLowerCase().includes(search.toLowerCase());
    const posMatch = (athlete.position || "").toLowerCase().includes(search.toLowerCase());

    const matchesSearch = nameMatch || emailMatch || sportMatch || posMatch;
    if (!matchesSearch) return false;

    if (activeGroupFilter === "my") return athlete.coach_id === user?.user_id;
    if (activeGroupFilter === "high_risk")
      return (athlete.latest_risk_level || "").toUpperCase() === "HIGH" || (athlete.latest_risk_score || 0) >= 70;
    if (activeGroupFilter === "reassessment") return athlete.needs_reassessment;
    if (activeGroupFilter === "injured") return athlete.injury_status === "Injured" || athlete.injury_status === "Recovering";
    if (["Football", "Basketball", "Cricket", "Running", "Tennis"].includes(activeGroupFilter))
      return (athlete.sport || "").toLowerCase() === activeGroupFilter.toLowerCase();

    return true;
  });

  function formatDate(dStr) {
    if (!dStr) return "Never";
    return new Date(dStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  async function handleToggleAssign(e, athlete) {
    e.stopPropagation();
    try {
      const isAssigned = athlete.coach_id === user?.user_id;
      await assignAthlete(athlete.athlete_id, {
        coach_id: isAssigned ? null : user?.user_id,
      });
      loadAthletes();
    } catch (err) {
      console.error("Assign failed:", err);
    }
  }

  return (
    <div className="app-layout">
      <main className="dashboard">
        <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div>
            <span className="eyebrow">ATHLETE ROSTER & MONITORING</span>
            <h1>Athlete Management</h1>
            <p>
              Comprehensive athlete profiles, biomechanical risk tracking, and smart group roster management.
            </p>
          </div>

          <button
            type="button"
            className="primary-button"
            onClick={() => setIsAddModalOpen(true)}
            style={{ display: "flex", alignItems: "center", gap: 8 }}
          >
            <UserPlus size={18} /> Add Athlete
          </button>
        </div>

        {/* Filters & Control Panel */}
        <section className="panel" style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
            {/* Search */}
            <div className="search-box" style={{ flex: 1, minWidth: 260 }}>
              <Search size={18} />
              <input
                placeholder="Search athletes by name, email, sport, or position..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {/* View Mode Switcher */}
            <div style={{ display: "flex", gap: 6, background: "rgba(255,255,255,0.03)", padding: 4, borderRadius: 8 }}>
              <button
                type="button"
                className={`icon-button ${viewMode === "grid" ? "active" : ""}`}
                onClick={() => setViewMode("grid")}
                title="Grid View"
                style={{ padding: "6px 10px", background: viewMode === "grid" ? "var(--color-primary, #6366f1)" : "transparent", color: "#fff", borderRadius: 6, border: "none", cursor: "pointer" }}
              >
                <Grid size={18} />
              </button>
              <button
                type="button"
                className={`icon-button ${viewMode === "table" ? "active" : ""}`}
                onClick={() => setViewMode("table")}
                title="Table View"
                style={{ padding: "6px 10px", background: viewMode === "table" ? "var(--color-primary, #6366f1)" : "transparent", color: "#fff", borderRadius: 6, border: "none", cursor: "pointer" }}
              >
                <List size={18} />
              </button>
            </div>
          </div>

          {/* Smart Group Chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 14 }}>
            {[
              { id: "all", label: `All Athletes (${athletes.length})` },
              { id: "my", label: `My Roster (${athletes.filter(a => a.coach_id === user?.user_id).length})` },
              { id: "high_risk", label: `High Risk (${athletes.filter(a => (a.latest_risk_level || '').toUpperCase() === 'HIGH' || (a.latest_risk_score || 0) >= 70).length})` },
              { id: "reassessment", label: `Needs Reassessment (${athletes.filter(a => a.needs_reassessment).length})` },
              { id: "injured", label: `Injured / Recovering (${athletes.filter(a => a.injury_status === 'Injured' || a.injury_status === 'Recovering').length})` },
              { id: "Football", label: "Football" },
              { id: "Basketball", label: "Basketball" },
              { id: "Cricket", label: "Cricket" },
            ].map((chip) => {
              const isActive = activeGroupFilter === chip.id;
              return (
                <button
                  key={chip.id}
                  type="button"
                  onClick={() => setActiveGroupFilter(chip.id)}
                  style={{
                    padding: "6px 14px",
                    borderRadius: 20,
                    fontSize: "0.82rem",
                    border: isActive ? "1px solid var(--color-primary, #6366f1)" : "1px solid #cbd5e1",
                    background: isActive ? "var(--color-primary, #6366f1)" : "#f8fafc",
                    color: isActive ? "#ffffff" : "#334155",
                    cursor: "pointer",
                    fontWeight: 500,
                    transition: "all 0.15s ease",
                  }}
                >
                  {chip.label}
                </button>
              );
            })}
          </div>
        </section>

        {/* Content Section */}
        <section className="panel">
          {loading && <Loading />}

          {error && <div className="error-box">{error}</div>}

          {!loading && !error && filteredAthletes.length === 0 && (
            <div className="empty-state-card" style={{ padding: "40px 0" }}>
              <UserRound size={36} style={{ opacity: 0.5 }} />
              <h3>No athletes found</h3>
              <p>No athlete records match your search or selected group filter.</p>
              <button
                type="button"
                className="primary-button"
                style={{ marginTop: 12 }}
                onClick={() => {
                  setSearch("");
                  setActiveGroupFilter("all");
                }}
              >
                Reset Filters
              </button>
            </div>
          )}

          {!loading && !error && filteredAthletes.length > 0 && (
            viewMode === "grid" ? (
              /* GRID VIEW */
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
                {filteredAthletes.map((athlete) => {
                  const isMyAthlete = athlete.coach_id === user?.user_id;

                  return (
                    <div
                      key={athlete.athlete_id || athlete.id}
                      className="stat-card-modern"
                      style={{
                        padding: 16,
                        cursor: "pointer",
                        display: "flex",
                        flexDirection: "column",
                        justify智慧: "space-between",
                        border: isMyAthlete ? "1px solid rgba(99, 102, 241, 0.4)" : undefined,
                      }}
                      onClick={() => setSelectedAthlete(athlete)}
                    >
                      <div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                            <div className="avatar" style={{ width: 40, height: 40, fontSize: "1.1rem" }}>
                              {(athlete.name || "A").charAt(0)}
                            </div>
                            <div>
                              <strong style={{ fontSize: "1rem", display: "block" }}>{athlete.name || "Unnamed Athlete"}</strong>
                              <span style={{ fontSize: "0.82rem", color: "var(--color-text-muted)" }}>
                                {athlete.sport || "Sport"} • {athlete.position || "Player"}
                              </span>
                            </div>
                          </div>
                          <RiskBadge level={athlete.latest_risk_level || "UNASSESSED"} />
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 16, background: "rgba(255,255,255,0.02)", padding: 10, borderRadius: 8, fontSize: "0.85rem" }}>
                          <div>
                            <span style={{ color: "var(--color-text-muted)", display: "block", fontSize: "0.75rem" }}>Risk Score</span>
                            <strong style={{ fontSize: "1.1rem" }}>
                              {athlete.latest_risk_score !== null && athlete.latest_risk_score !== undefined
                                ? Math.round(athlete.latest_risk_score)
                                : "N/A"}
                            </strong>
                          </div>
                          <div>
                            <span style={{ color: "var(--color-text-muted)", display: "block", fontSize: "0.75rem" }}>LESS Score</span>
                            <strong style={{ fontSize: "1.1rem" }}>
                              {athlete.latest_less_score !== null && athlete.latest_less_score !== undefined
                                ? `${athlete.latest_less_score}/${athlete.latest_less_max || 12}`
                                : "N/A"}
                            </strong>
                          </div>
                        </div>
                      </div>

                      <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid rgba(255,255,255,0.05)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ fontSize: "0.78rem", color: "var(--color-text-muted)" }}>
                          Last test: <strong>{formatDate(athlete.last_assessment_date)}</strong>
                        </div>
                        <button
                          type="button"
                          className={isMyAthlete ? "secondary-button" : "primary-button"}
                          style={{ fontSize: "0.78rem", padding: "4px 8px" }}
                          onClick={(e) => handleToggleAssign(e, athlete)}
                        >
                          {isMyAthlete ? "Assigned" : "+ Assign"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              /* TABLE VIEW */
              <div className="athlete-table">
                <div className="table-header" style={{ display: "grid", gridTemplateColumns: "2fr 1.5fr 1fr 1fr 1fr 1fr auto", gap: 12 }}>
                  <span>Athlete</span>
                  <span>Sport & Position</span>
                  <span>Risk Score</span>
                  <span>LESS Score</span>
                  <span>Last Test</span>
                  <span>Status</span>
                  <span>Actions</span>
                </div>

                {filteredAthletes.map((athlete) => {
                  const isMyAthlete = athlete.coach_id === user?.user_id;

                  return (
                    <div
                      className="table-row"
                      key={athlete.athlete_id || athlete.id}
                      style={{ display: "grid", gridTemplateColumns: "2fr 1.5fr 1fr 1fr 1fr 1fr auto", gap: 12, alignItems: "center", cursor: "pointer" }}
                      onClick={() => setSelectedAthlete(athlete)}
                    >
                      <div className="person-cell">
                        <div className="avatar">{(athlete.name || "A").charAt(0)}</div>
                        <div>
                          <strong>{athlete.name || "Unnamed Athlete"}</strong>
                          <span style={{ display: "block", fontSize: "0.75rem", color: "var(--color-text-muted)" }}>{athlete.email || "—"}</span>
                        </div>
                      </div>

                      <span>{athlete.sport || "—"} ({athlete.position || "—"})</span>

                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <strong>{athlete.latest_risk_score !== null ? Math.round(athlete.latest_risk_score) : "—"}</strong>
                        <RiskBadge level={athlete.latest_risk_level || "UNASSESSED"} />
                      </div>

                      <span>{athlete.latest_less_score !== null ? `${athlete.latest_less_score}/${athlete.latest_less_max || 12}` : "—"}</span>

                      <span style={{ fontSize: "0.85rem" }}>{formatDate(athlete.last_assessment_date)}</span>

                      <span style={{ color: athlete.injury_status === "Injured" ? "#ef4444" : "#10b981", fontWeight: 600, fontSize: "0.85rem" }}>
                        {athlete.injury_status || "Healthy"}
                      </span>

                      <div style={{ display: "flex", gap: 6 }}>
                        <button
                          type="button"
                          className="icon-button"
                          title="View Profile"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedAthlete(athlete);
                          }}
                        >
                          <Eye size={16} />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )
          )}
        </section>
      </main>

      {/* Modals */}
      <AddAthleteModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAthleteAdded={() => loadAthletes()}
      />

      <AthleteDetailModal
        isOpen={!!selectedAthlete}
        onClose={() => setSelectedAthlete(null)}
        athlete={selectedAthlete}
        onUpdate={() => loadAthletes()}
      />
    </div>
  );
}

export default Athletes;