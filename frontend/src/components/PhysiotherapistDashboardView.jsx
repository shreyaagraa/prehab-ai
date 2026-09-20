import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  Users,
  ClipboardCheck,
  AlertTriangle,
  ArrowUpRight,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Search,
  Eye,
  FileVideo,
  Sparkles,
  Stethoscope,
  HeartPulse,
  RotateCcw,
  Check,
  Info,
} from "lucide-react";

import RiskBadge from "./RiskBadge";
import AthleteDetailModal from "./AthleteDetailModal";

function formatDate(dateStr) {
  if (!dateStr) return "Never assessed";
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function PhysiotherapistDashboardView({
  user,
  teamAthletes,
  teamAssessments,
  onRefresh,
}) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedAthlete, setSelectedAthlete] = useState(null);

  // ── REHABILITATION & RISK COMPUTATIONS (REAL APP DATA ONLY) ─────────────
  const totalAthletes = teamAthletes.length;

  const activeRehabCount = teamAthletes.filter(
    (a) => a.injury_status === "Injured" || a.injury_status === "Recovering"
  ).length;

  const needingReassessmentCount = teamAthletes.filter(
    (a) => a.needs_reassessment
  ).length;

  const highRiskCount = teamAthletes.filter(
    (a) =>
      (a.latest_risk_level || "").toUpperCase() === "HIGH" ||
      (a.latest_risk_score || 0) >= 70
  ).length;

  const assessedAthletesCount = teamAthletes.filter(
    (a) => a.latest_risk_score !== null && a.latest_risk_score !== undefined
  ).length;

  // Filtered Athletes List
  const filteredAthletes = teamAthletes.filter((a) => {
    const matchesSearch =
      (a.name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (a.sport || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (a.position || "").toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (statusFilter === "rehab") {
      return a.injury_status === "Injured" || a.injury_status === "Recovering";
    }
    if (statusFilter === "reassessment") {
      return a.needs_reassessment;
    }
    if (statusFilter === "high_risk") {
      return (
        (a.latest_risk_level || "").toUpperCase() === "HIGH" ||
        (a.latest_risk_score || 0) >= 70
      );
    }
    if (statusFilter === "healthy") {
      return a.injury_status === "Healthy";
    }

    return true;
  });

  // Risk Distribution Breakdown
  const teamAssessed = teamAthletes.filter((a) => a.latest_risk_score !== null);
  const tLow = teamAssessed.filter((a) => a.latest_risk_score < 40).length;
  const tMod = teamAssessed.filter((a) => a.latest_risk_score >= 40 && a.latest_risk_score < 70).length;
  const tHigh = teamAssessed.filter((a) => a.latest_risk_score >= 70).length;
  const tTotal = teamAssessed.length;
  const tLowPct = tTotal > 0 ? Math.round((tLow / tTotal) * 100) : 0;
  const tModPct = tTotal > 0 ? Math.round((tMod / tTotal) * 100) : 0;
  const tHighPct = tTotal > 0 ? Math.round((tHigh / tTotal) * 100) : 0;

  // Priority Patients Needing Attention
  const priorityList = teamAthletes.filter(
    (a) =>
      a.injury_status === "Injured" ||
      a.injury_status === "Recovering" ||
      (a.latest_risk_level || "").toUpperCase() === "HIGH" ||
      (a.latest_risk_score || 0) >= 70 ||
      a.needs_reassessment
  );

  return (
    <>
      {/* ── Hero Banner ─────────────────────────────────────────────────── */}
      <div className="dash-hero">
        <div className="dash-hero-content">
          <div className="dash-hero-badge">
            <Stethoscope size={14} />
            <span>PHYSIOTHERAPIST REHABILITATION WORKSPACE</span>
          </div>

          <h1>Welcome back, {user?.name || "Physiotherapist"}</h1>

          <p>
            Clinical rehabilitation tracking, injury recovery progress monitoring, and movement biomechanics risk screening.
          </p>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginTop: 12,
              background: "rgba(255,255,255,0.08)",
              padding: "6px 14px",
              borderRadius: 8,
              fontSize: "0.82rem",
              color: "#e2e8f0",
              maxWidth: "fit-content",
            }}
          >
            <Info size={15} style={{ color: "#38bdf8", flexShrink: 0 }} />
            <span>
              <strong>Clinical Note:</strong> AI movement risk scores are biomechanical screening indicators, not medical diagnoses.
            </span>
          </div>
        </div>

        <div className="dash-hero-actions">
          <Link
            to="/assessments"
            className="primary-button hero-cta"
            style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
          >
            <ClipboardCheck size={18} />
            All Clinical Assessments
          </Link>
        </div>
      </div>

      {/* ── Module 1: Clinical Overview & KPIs ──────────────────────────── */}
      <div className="stats-grid">
        <div className="stat-card-modern">
          <div className="stat-header">
            <span className="stat-title">Active Rehab Patients</span>
            <div className="stat-icon-wrapper red">
              <HeartPulse size={20} />
            </div>
          </div>
          <div className="stat-value">{activeRehabCount}</div>
          <div className="stat-subtext">Athletes currently injured or recovering</div>
        </div>

        <div className="stat-card-modern">
          <div className="stat-header">
            <span className="stat-title">Reassessments Due</span>
            <div className="stat-icon-wrapper indigo">
              <Clock size={20} />
            </div>
          </div>
          <div className="stat-value">{needingReassessmentCount}</div>
          <div className="stat-subtext">Athletes requiring follow-up testing</div>
        </div>

        <div className={`stat-card-modern ${highRiskCount > 0 ? "danger-card" : ""}`}>
          <div className="stat-header">
            <span className="stat-title">High Movement Risk</span>
            <div className={`stat-icon-wrapper ${highRiskCount > 0 ? "red" : "gray"}`}>
              <AlertTriangle size={20} />
            </div>
          </div>
          <div className="stat-value">{highRiskCount}</div>
          <div className="stat-subtext">Screened with elevated biomechanical risk</div>
        </div>

        <div className="stat-card-modern">
          <div className="stat-header">
            <span className="stat-title">Assessed Roster</span>
            <div className="stat-icon-wrapper teal">
              <CheckCircle2 size={20} />
            </div>
          </div>
          <div className="stat-value">
            {assessedAthletesCount} / {totalAthletes}
          </div>
          <div className="stat-subtext">Athletes with completed baseline testing</div>
        </div>
      </div>

      {/* ── Priority Patient Alerts Banner ──────────────────────────────── */}
      {priorityList.length > 0 && (
        <section
          className="panel card-panel"
          style={{ borderLeft: "4px solid #ef4444", marginBottom: 24 }}
        >
          <div className="panel-header">
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <ShieldAlert size={22} style={{ color: "#ef4444" }} />
              <div>
                <h2 style={{ fontSize: "1.1rem" }}>
                  Clinical Priority Alerts — Athletes Requiring Attention ({priorityList.length})
                </h2>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
                  Athletes with active injuries, high movement risk scores, or overdue reassessments
                </p>
              </div>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
              gap: 12,
              marginTop: 12,
            }}
          >
            {priorityList.slice(0, 4).map((ath) => (
              <div
                key={ath.athlete_id}
                style={{
                  background: "rgba(239, 68, 68, 0.05)",
                  border: "1px solid rgba(239, 68, 68, 0.2)",
                  borderRadius: 10,
                  padding: 12,
                  cursor: "pointer",
                }}
                onClick={() => setSelectedAthlete(ath)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <strong style={{ fontSize: "0.95rem" }}>{ath.name}</strong>
                  <RiskBadge level={ath.latest_risk_level || "HIGH"} />
                </div>
                <div style={{ fontSize: "0.82rem", color: "var(--color-text-muted)", marginTop: 4 }}>
                  {ath.sport} • {ath.position || "Player"}
                </div>
                <div
                  style={{
                    display: "flex",
                    justify: "space-between",
                    alignItems: "center",
                    marginTop: 8,
                    fontSize: "0.82rem",
                  }}
                >
                  <span>
                    Status:{" "}
                    <strong
                      style={{
                        color:
                          ath.injury_status === "Injured"
                            ? "#ef4444"
                            : ath.injury_status === "Recovering"
                            ? "#f59e0b"
                            : "#64748b",
                      }}
                    >
                      {ath.injury_status || "Needs Evaluation"}
                    </strong>
                  </span>
                  {ath.latest_risk_score != null && (
                    <span style={{ fontWeight: 600 }}>Score: {Math.round(ath.latest_risk_score)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── Main Workspace Grid ─────────────────────────────────────────── */}
      <div className="dashboard-grid">
        {/* Left Column: Module 2 - Rehabilitation Tracking & Roster Management */}
        <section className="panel card-panel">
          <div className="panel-header" style={{ flexDirection: "column", alignItems: "flex-start", gap: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
              <div>
                <h2>Rehabilitation & Roster Tracking</h2>
                <p>Track athlete recovery status, rehabilitation notes, and physical baselines</p>
              </div>
            </div>

            {/* Filter Pills */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {[
                { id: "all", label: `All Athletes (${teamAthletes.length})` },
                { id: "rehab", label: `In Rehab / Recovering (${activeRehabCount})` },
                { id: "reassessment", label: `Reassessment Due (${needingReassessmentCount})` },
                { id: "high_risk", label: `High Risk (${highRiskCount})` },
                { id: "healthy", label: "Healthy / Cleared" },
              ].map((chip) => {
                const isActive = statusFilter === chip.id;
                return (
                  <button
                    key={chip.id}
                    type="button"
                    onClick={() => setStatusFilter(chip.id)}
                    style={{
                      padding: "6px 14px",
                      borderRadius: 20,
                      fontSize: "0.82rem",
                      border: isActive ? "1px solid #6366f1" : "1px solid #cbd5e1",
                      background: isActive ? "#6366f1" : "#f8fafc",
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

            {/* Search Input */}
            <div className="search-box" style={{ width: "100%", marginTop: 4 }}>
              <Search size={16} />
              <input
                type="text"
                placeholder="Search rehab patients by name, sport, or position..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          {/* Athletes Grid */}
          {filteredAthletes.length === 0 ? (
            <div className="empty-state-card" style={{ padding: "30px 0" }}>
              <Users size={32} style={{ opacity: 0.5 }} />
              <p>No athletes match the current rehabilitation filter.</p>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14, marginTop: 12 }}>
              {filteredAthletes.map((ath) => (
                <div
                  key={ath.athlete_id}
                  className="stat-card-modern"
                  style={{
                    padding: 14,
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "space-between",
                  }}
                  onClick={() => setSelectedAthlete(ath)}
                >
                  <div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div className="avatar" style={{ width: 34, height: 34, fontSize: "0.9rem" }}>
                          {(ath.name || "A").charAt(0)}
                        </div>
                        <div>
                          <strong style={{ fontSize: "0.95rem", display: "block" }}>{ath.name}</strong>
                          <span style={{ fontSize: "0.78rem", color: "var(--color-text-muted)" }}>
                            {ath.sport || "Sport"} • {ath.position || "Player"}
                          </span>
                        </div>
                      </div>
                      <RiskBadge level={ath.latest_risk_level || "UNASSESSED"} />
                    </div>

                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr",
                        gap: 8,
                        marginTop: 14,
                        background: "rgba(255,255,255,0.02)",
                        padding: 8,
                        borderRadius: 6,
                        fontSize: "0.8rem",
                      }}
                    >
                      <div>
                        <span style={{ color: "var(--color-text-muted)", display: "block" }}>Risk Score</span>
                        <strong>{ath.latest_risk_score !== null ? Math.round(ath.latest_risk_score) : "N/A"}</strong>
                      </div>
                      <div>
                        <span style={{ color: "var(--color-text-muted)", display: "block" }}>LESS Score</span>
                        <strong>{ath.latest_less_score !== null ? `${ath.latest_less_score}/${ath.latest_less_max || 12}` : "N/A"}</strong>
                      </div>
                    </div>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      justify: "space-between",
                      alignItems: "center",
                      marginTop: 12,
                      fontSize: "0.78rem",
                      borderTop: "1px solid rgba(255,255,255,0.05)",
                      paddingTop: 8,
                    }}
                  >
                    <span style={{ color: "var(--color-text-muted)" }}>
                      Last test: {formatDate(ath.last_assessment_date)}
                    </span>
                    <span
                      style={{
                        color:
                          ath.injury_status === "Injured"
                            ? "#ef4444"
                            : ath.injury_status === "Recovering"
                            ? "#f59e0b"
                            : "#10b981",
                        fontWeight: 600,
                      }}
                    >
                      {ath.injury_status || "Healthy"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Right Column: Modules 3, 4 & 5 */}
        <div className="side-panels-column">
          {/* Module 3: Injury Risk Monitoring */}
          <section className="panel card-panel">
            <div className="panel-header">
              <h2>Injury Risk Distribution</h2>
            </div>
            {tTotal === 0 ? (
              <p style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>
                No completed movement assessments available.
              </p>
            ) : (
              <div className="risk-overview-stack">
                <RiskBar label="Low Risk (<40)" count={tLow} percentage={tLowPct} colorClass="bg-emerald" />
                <RiskBar label="Moderate Risk (40-69)" count={tMod} percentage={tModPct} colorClass="bg-amber" />
                <RiskBar label="High Risk (≥70)" count={tHigh} percentage={tHighPct} colorClass="bg-rose" />
              </div>
            )}
          </section>

          {/* Module 4: Movement Correction Analytics */}
          <section className="panel card-panel">
            <div className="panel-header">
              <div>
                <h2>Movement Correction Findings</h2>
                <p>Common biomechanical errors & PreHab recommendations</p>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: 12, borderRadius: 8, fontSize: "0.85rem" }}>
                <strong style={{ color: "#4f46e5", display: "block", marginBottom: 4 }}>Knee Valgus / Medial Collapse</strong>
                <p style={{ margin: 0, color: "#475569" }}>
                  Observed in landing/squat movement assessments. Recommend gluteus medius strengthening and dynamic knee-tracking exercises.
                </p>
              </div>

              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: 12, borderRadius: 8, fontSize: "0.85rem" }}>
                <strong style={{ color: "#4f46e5", display: "block", marginBottom: 4 }}>Asymmetric Ground Impact</strong>
                <p style={{ margin: 0, color: "#475569" }}>
                  Limb loading asymmetry detected during landing phase. Recommend unilateral single-leg stability and drop-landing protocols.
                </p>
              </div>
            </div>
          </section>

          {/* Module 5: Recovery & Assessment Reports */}
          <section className="panel card-panel">
            <div className="panel-header">
              <div>
                <h2>Recent Recovery Reports</h2>
                <p>Latest movement evaluations across roster</p>
              </div>
              <Link to="/assessments" className="view-all-link">
                <span>All</span>
                <ArrowUpRight size={16} />
              </Link>
            </div>

            {teamAssessments.length === 0 ? (
              <div className="empty-substate">
                <p>No video assessments uploaded yet across team.</p>
              </div>
            ) : (
              <div className="assessment-card-list">
                {teamAssessments.slice(0, 4).map((item) => (
                  <div
                    key={item.video_id}
                    className="assessment-card-row"
                    onClick={() => navigate(`/analysis/${item.video_id}`)}
                  >
                    <div className="card-row-left">
                      <div className="video-thumb-icon">
                        <FileVideo size={18} />
                      </div>
                      <div className="card-row-info">
                        <strong className="video-name">{item.athlete_name || "Athlete"}</strong>
                        <span className="video-date">
                          {formatDate(item.uploaded_at)} • {item.sport || "Sport"}
                        </span>
                      </div>
                    </div>

                    <div className="card-row-right">
                      {item.has_pose_landmarks && (
                        <span className="ai-pose-tag-pill" title="AI Pose Analysis Available">
                          AI POSE ✓
                        </span>
                      )}
                      {item.overall_risk_score !== null && (
                        <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>
                          {Math.round(item.overall_risk_score)}
                        </span>
                      )}
                      <RiskBadge level={item.risk_level || "PENDING"} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Athlete Detail Modal */}
      <AthleteDetailModal
        isOpen={!!selectedAthlete}
        onClose={() => setSelectedAthlete(null)}
        athlete={selectedAthlete}
        onUpdate={() => onRefresh && onRefresh()}
      />
    </>
  );
}

function RiskBar({ label, count, percentage, colorClass }) {
  return (
    <div className="risk-bar-group">
      <div className="risk-bar-meta">
        <span className="risk-bar-title">{label}</span>
        <span className="risk-bar-stats">
          <strong>{percentage}%</strong> ({count})
        </span>
      </div>
      <div className="risk-bar-track">
        <div
          className={`risk-bar-progress ${colorClass}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  );
}

export default PhysiotherapistDashboardView;
