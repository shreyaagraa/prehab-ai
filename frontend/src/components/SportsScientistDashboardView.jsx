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
  TrendingUp,
  BarChart3,
  FlaskConical,
  Download,
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

function SportsScientistDashboardView({
  user,
  teamAthletes,
  teamAssessments,
  onRefresh,
}) {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedAthlete, setSelectedAthlete] = useState(null);

  // ── SPORTS SCIENCE COMPUTATIONS (REAL DATA ONLY) ──────────────────────────
  const totalRoster = teamAthletes.length;
  const totalAssessments = teamAssessments.length;

  const assessedAthletes = teamAthletes.filter(
    (a) => a.latest_risk_score !== null && a.latest_risk_score !== undefined
  );

  const meanRiskScore =
    assessedAthletes.length > 0
      ? Math.round(
          assessedAthletes.reduce((acc, a) => acc + a.latest_risk_score, 0) /
            assessedAthletes.length
        )
      : null;

  const lessAssessed = teamAthletes.filter(
    (a) => a.latest_less_score !== null && a.latest_less_score !== undefined
  );

  const meanLessScore =
    lessAssessed.length > 0
      ? (
          lessAssessed.reduce((acc, a) => acc + a.latest_less_score, 0) /
          lessAssessed.length
        ).toFixed(1)
      : null;

  const poseSupportedCount = teamAssessments.filter(
    (a) => a.has_pose_landmarks
  ).length;

  // Risk Distribution
  const tLow = assessedAthletes.filter((a) => a.latest_risk_score < 40).length;
  const tMod = assessedAthletes.filter(
    (a) => a.latest_risk_score >= 40 && a.latest_risk_score < 70
  ).length;
  const tHigh = assessedAthletes.filter((a) => a.latest_risk_score >= 70).length;
  const tTotal = assessedAthletes.length;

  const tLowPct = tTotal > 0 ? Math.round((tLow / tTotal) * 100) : 0;
  const tModPct = tTotal > 0 ? Math.round((tMod / tTotal) * 100) : 0;
  const tHighPct = tTotal > 0 ? Math.round((tHigh / tTotal) * 100) : 0;

  // Export Research Summary Handler
  function handleExportResearchSummary() {
    if (teamAssessments.length === 0) {
      alert("No assessment records available for export.");
      return;
    }

    const headers = ["Video ID", "Athlete Name", "Sport", "Uploaded Date", "Risk Score", "Risk Level", "LESS Score"];
    const rows = teamAssessments.map((a) => [
      a.video_id,
      `"${a.athlete_name || "Athlete"}"`,
      `"${a.sport || "Sport"}"`,
      a.uploaded_at || "",
      a.overall_risk_score != null ? Math.round(a.overall_risk_score) : "",
      a.risk_level || "",
      a.less_score != null ? a.less_score : "",
    ]);

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `PreHab_SportsScience_Research_Summary_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  return (
    <>
      {/* ── Hero Banner ─────────────────────────────────────────────────── */}
      <div className="dash-hero">
        <div className="dash-hero-content">
          <div className="dash-hero-badge">
            <FlaskConical size={14} />
            <span>SPORTS SCIENCE & BIOMECHANICAL ANALYTICS WORKSPACE</span>
          </div>

          <h1>Welcome back, {user?.name || "Sports Scientist"}</h1>

          <p>
            Biomechanical evaluation, LESS error distribution, risk factor decomposition, and team research reporting.
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
              <strong>Scientific Disclaimer:</strong> Injury risk insights are computer-vision biomechanical screening outputs, not predictive clinical diagnoses.
            </span>
          </div>
        </div>

        <div className="dash-hero-actions">
          <button
            type="button"
            className="primary-button hero-cta"
            onClick={handleExportResearchSummary}
            style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
          >
            <Download size={18} />
            Export Research CSV
          </button>
        </div>
      </div>

      {/* ── Module 1: Research Overview & Science KPIs ──────────────────── */}
      <div className="stats-grid">
        <div className="stat-card-modern">
          <div className="stat-header">
            <span className="stat-title">Team Roster</span>
            <div className="stat-icon-wrapper purple">
              <Users size={20} />
            </div>
          </div>
          <div className="stat-value">{totalRoster}</div>
          <div className="stat-subtext">Active athletes in biomechanical cohort</div>
        </div>

        <div className="stat-card-modern">
          <div className="stat-header">
            <span className="stat-title">Total Evaluations</span>
            <div className="stat-icon-wrapper indigo">
              <BarChart3 size={20} />
            </div>
          </div>
          <div className="stat-value">{totalAssessments}</div>
          <div className="stat-subtext">Video movement assessments completed</div>
        </div>

        <div className="stat-card-modern">
          <div className="stat-header">
            <span className="stat-title">Mean Risk Score</span>
            <div className="stat-icon-wrapper teal">
              <Activity size={20} />
            </div>
          </div>
          <div className="stat-value">{meanRiskScore !== null ? `${meanRiskScore}` : "N/A"}</div>
          <div className="stat-subtext">Average risk score across assessed cohort</div>
        </div>

        <div className="stat-card-modern">
          <div className="stat-header">
            <span className="stat-title">Mean LESS Errors</span>
            <div className="stat-icon-wrapper gray">
              <Sparkles size={20} />
            </div>
          </div>
          <div className="stat-value">{meanLessScore !== null ? `${meanLessScore}` : "N/A"}</div>
          <div className="stat-subtext">Average landing error technique rating</div>
        </div>
      </div>

      {/* ── Main Workspace Grid ─────────────────────────────────────────── */}
      <div className="dashboard-grid">
        {/* Left Column: Modules 2 & 3 */}
        <section className="panel card-panel">
          <div className="panel-header" style={{ flexDirection: "column", alignItems: "flex-start", gap: 12 }}>
            <div>
              <h2>Biomechanical Roster Analytics</h2>
              <p>Individual athlete movement evaluation parameters and screening metrics</p>
            </div>

            <div className="search-box" style={{ width: "100%", marginTop: 4 }}>
              <Search size={16} />
              <input
                type="text"
                placeholder="Filter cohort by athlete name, sport, or position..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14, marginTop: 12 }}>
            {teamAthletes
              .filter((a) =>
                (a.name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
                (a.sport || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
                (a.position || "").toLowerCase().includes(searchQuery.toLowerCase())
              )
              .map((ath) => (
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
                    <span style={{ fontWeight: 600, color: "#6366f1" }}>View Analytics &rarr;</span>
                  </div>
                </div>
              ))}
          </div>
        </section>

        {/* Right Column: Modules 3, 4 & 5 */}
        <div className="side-panels-column">
          {/* Module 3: Team Performance & Risk Distribution Trends */}
          <section className="panel card-panel">
            <div className="panel-header">
              <h2>Team Risk Trends</h2>
            </div>
            {tTotal === 0 ? (
              <p style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>
                No evaluated assessments available.
              </p>
            ) : (
              <div className="risk-overview-stack">
                <RiskBar label="Low Risk (<40)" count={tLow} percentage={tLowPct} colorClass="bg-emerald" />
                <RiskBar label="Moderate Risk (40-69)" count={tMod} percentage={tModPct} colorClass="bg-amber" />
                <RiskBar label="High Risk (≥70)" count={tHigh} percentage={tHighPct} colorClass="bg-rose" />
              </div>
            )}
          </section>

          {/* Module 4: Injury Risk Factor Insights */}
          <section className="panel card-panel">
            <div className="panel-header">
              <div>
                <h2>Risk Factor Insights</h2>
                <p>Explainable AI feature components</p>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: 12, borderRadius: 8, fontSize: "0.85rem" }}>
                <strong style={{ color: "#4f46e5", display: "block", marginBottom: 2 }}>Biomechanical Factor (S_bio)</strong>
                <p style={{ margin: 0, color: "#475569" }}>
                  Quantifies joint angle flexions during movement landings derived from pose estimation landmarks.
                </p>
              </div>

              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: 12, borderRadius: 8, fontSize: "0.85rem" }}>
                <strong style={{ color: "#4f46e5", display: "block", marginBottom: 2 }}>Asymmetry Factor (S_asym)</strong>
                <p style={{ margin: 0, color: "#475569" }}>
                  Measures bilateral left/right side movement loading variance between limbs.
                </p>
              </div>

              <div style={{ background: "#f8fafc", border: "1px solid #e2e8f0", padding: 12, borderRadius: 8, fontSize: "0.85rem" }}>
                <strong style={{ color: "#4f46e5", display: "block", marginBottom: 2 }}>Fatigue Factor (S_fatigue)</strong>
                <p style={{ margin: 0, color: "#475569" }}>
                  Self-reported physical fatigue contribution factor incorporated into composite risk scoring.
                </p>
              </div>
            </div>
          </section>

          {/* Module 5: Research & Analysis Report List */}
          <section className="panel card-panel">
            <div className="panel-header">
              <div>
                <h2>Assessment Research Dataset</h2>
                <p>Completed movement analysis records</p>
              </div>
              <Link to="/assessments" className="view-all-link">
                <span>All</span>
                <ArrowUpRight size={16} />
              </Link>
            </div>

            {teamAssessments.length === 0 ? (
              <div className="empty-substate">
                <p>No assessment records present in database.</p>
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

export default SportsScientistDashboardView;
