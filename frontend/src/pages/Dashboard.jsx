import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  Users,
  ClipboardCheck,
  AlertTriangle,
  ArrowUpRight,
  UserCircle,
  Video,
  TrendingUp,
  FileVideo,
  ChevronRight,
  Sparkles,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Plus,
  Filter,
  Search,
  UserPlus,
  Eye,
  ArrowLeftRight,
} from "lucide-react";

import RiskBadge from "../components/RiskBadge";
import AddAthleteModal from "../components/AddAthleteModal";
import AthleteDetailModal from "../components/AthleteDetailModal";
import AssessmentCompareModal from "../components/AssessmentCompareModal";
import PhysiotherapistDashboardView from "../components/PhysiotherapistDashboardView";
import SportsScientistDashboardView from "../components/SportsScientistDashboardView";

import { useAuth } from "../context/AuthContext";
import { getMyHistory, getAllAssessments } from "../api/videos";
import { getMyAthleteProfile, getAthletes } from "../api/athletes";

function formatDate(dateStr) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const isAthlete = user?.role === "Athlete";
  const isPhysio = user?.role === "Physiotherapist";
  const isSportsScientist = user?.role === "Sports Scientist";

  // Athlete mode state
  const [history, setHistory] = useState([]);
  const [profile, setProfile] = useState(null);

  // Coach mode state
  const [teamAthletes, setTeamAthletes] = useState([]);
  const [teamAssessments, setTeamAssessments] = useState([]);
  const [activeGroupFilter, setActiveGroupFilter] = useState("all"); // "all" | "my" | "high_risk" | "reassessment" | "injured" | "Football" | "Basketball" | "Cricket"
  const [searchQuery, setSearchQuery] = useState("");

  // Refined Dropdown Filter States
  const [scopeFilter, setScopeFilter] = useState("all"); // "all" | "my"
  const [sportFilter, setSportFilter] = useState("all");
  const [positionFilter, setPositionFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all"); // "all" | "high" | "moderate" | "low"
  const [statusFilter, setStatusFilter] = useState("all"); // "all" | "reassessment" | "injured" | "healthy"

  // Modals state
  const [isAddAthleteOpen, setIsAddAthleteOpen] = useState(false);
  const [selectedAthlete, setSelectedAthlete] = useState(null);
  const [compareAssessmentA, setCompareAssessmentA] = useState(null);
  const [compareAssessmentB, setCompareAssessmentB] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadData = async () => {
    setLoading(true);
    setError("");

    try {
      if (isAthlete) {
        const [historyData, profileData] = await Promise.allSettled([
          getMyHistory(),
          getMyAthleteProfile(),
        ]);

        if (historyData.status === "fulfilled") setHistory(historyData.value || []);
        if (profileData.status === "fulfilled") setProfile(profileData.value || null);
      } else {
        // Coach / Staff view
        const [athletesRes, assessmentsRes] = await Promise.allSettled([
          getAthletes(),
          getAllAssessments(),
        ]);

        if (athletesRes.status === "fulfilled") {
          const list = Array.isArray(athletesRes.value) ? athletesRes.value : athletesRes.value?.items || [];
          setTeamAthletes(list);
        }
        if (assessmentsRes.status === "fulfilled") {
          setTeamAssessments(assessmentsRes.value || []);
        }
      }
    } catch (err) {
      setError("Failed to load dashboard data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [isAthlete]);

  // ── ATHLETE MODE COMPUTATIONS ─────────────────────────────────────────────
  const completedItems = history.filter(
    (h) => h.analysis_status === "COMPLETED" || h.processing_status === "COMPLETED"
  );
  const totalAssessments = history.length;
  const latestAssessment = completedItems[0] || history[0] || null;
  const latestRiskScore =
    latestAssessment?.overall_risk_score !== null &&
    latestAssessment?.overall_risk_score !== undefined
      ? Math.round(latestAssessment.overall_risk_score)
      : null;
  const latestRiskLevel = latestAssessment?.risk_level || null;
  const averageRiskScore =
    completedItems.length > 0
      ? Math.round(
          completedItems.reduce(
            (acc, item) => acc + (item.overall_risk_score || 0),
            0
          ) / completedItems.length
        )
      : null;
  const highRiskCount = completedItems.filter(
    (item) =>
      (item.risk_level || "").toUpperCase() === "HIGH" ||
      (item.risk_level || "").toUpperCase() === "CRITICAL" ||
      (item.overall_risk_score || 0) >= 70
  ).length;
  const lowRiskCount = completedItems.filter(
    (item) =>
      (item.risk_level || "").toUpperCase() === "LOW" ||
      (item.overall_risk_score !== null && item.overall_risk_score < 40)
  ).length;
  const moderateRiskCount = completedItems.filter(
    (item) =>
      (item.risk_level || "").toUpperCase() === "MODERATE" ||
      (item.overall_risk_score !== null &&
        item.overall_risk_score >= 40 &&
        item.overall_risk_score < 70)
  ).length;
  const totalCompleted = completedItems.length;
  const lowPct = totalCompleted > 0 ? Math.round((lowRiskCount / totalCompleted) * 100) : 0;
  const modPct = totalCompleted > 0 ? Math.round((moderateRiskCount / totalCompleted) * 100) : 0;
  const highPct = totalCompleted > 0 ? Math.round((highRiskCount / totalCompleted) * 100) : 0;

  const isProfileComplete =
    profile &&
    ["sport", "position", "age", "height", "weight"].every(
      (f) => profile[f] !== null && profile[f] !== undefined && profile[f] !== ""
    );

  // ── COACH MODE COMPUTATIONS ───────────────────────────────────────────────
  const totalRoster = teamAthletes.length;
  const now = new Date();
  const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  const assessedThisWeek = teamAthletes.filter((a) => {
    if (!a.last_assessment_date) return false;
    return new Date(a.last_assessment_date) >= sevenDaysAgo;
  }).length;

  const teamHighRiskCount = teamAthletes.filter(
    (a) =>
      (a.latest_risk_level || "").toUpperCase() === "HIGH" ||
      (a.latest_risk_score || 0) >= 70
  ).length;

  const needingReassessmentCount = teamAthletes.filter((a) => a.needs_reassessment).length;

  // Needs Attention Athletes (High Risk OR Risk Spike > 15 OR Injured)
  const needsAttentionList = teamAthletes.filter(
    (a) =>
      (a.latest_risk_level || "").toUpperCase() === "HIGH" ||
      (a.latest_risk_score || 0) >= 70 ||
      (a.risk_change || 0) >= 15 ||
      a.injury_status === "Injured" ||
      a.injury_status === "Recovering"
  );

  // Team Risk Distribution Breakdown
  const teamAssessed = teamAthletes.filter((a) => a.latest_risk_score !== null);
  const tLow = teamAssessed.filter((a) => a.latest_risk_score < 40).length;
  const tMod = teamAssessed.filter((a) => a.latest_risk_score >= 40 && a.latest_risk_score < 70).length;
  const tHigh = teamAssessed.filter((a) => a.latest_risk_score >= 70).length;
  const tTotal = teamAssessed.length;
  const tLowPct = tTotal > 0 ? Math.round((tLow / tTotal) * 100) : 0;
  const tModPct = tTotal > 0 ? Math.round((tMod / tTotal) * 100) : 0;
  const tHighPct = tTotal > 0 ? Math.round((tHigh / tTotal) * 100) : 0;

  // Smart Group Filtering - Dynamic Options
  const availablePositions = Array.from(
    new Set(teamAthletes.map((a) => a.position).filter(Boolean))
  ).sort();

  const availableSports = Array.from(
    new Set([
      "Football",
      "Basketball",
      "Cricket",
      "Running",
      "Tennis",
      "Volleyball",
      ...teamAthletes.map((a) => a.sport).filter(Boolean),
    ])
  ).sort();

  const resetAllFilters = () => {
    setActiveGroupFilter("all");
    setScopeFilter("all");
    setSportFilter("all");
    setPositionFilter("all");
    setRiskFilter("all");
    setStatusFilter("all");
  };

  const filteredAthletes = teamAthletes.filter((a) => {
    const matchesSearch =
      (a.name || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (a.sport || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (a.position || "").toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    // Scope filter (or activeGroupFilter legacy setting)
    if (scopeFilter === "my" || activeGroupFilter === "my") {
      if (a.coach_id !== user?.user_id) return false;
    }

    // Sport filter
    if (sportFilter !== "all") {
      if ((a.sport || "").toLowerCase() !== sportFilter.toLowerCase()) return false;
    }

    // Position filter
    if (positionFilter !== "all") {
      if ((a.position || "").toLowerCase() !== positionFilter.toLowerCase()) return false;
    }

    // Risk level filter (or activeGroupFilter high_risk)
    if (riskFilter === "high" || activeGroupFilter === "high_risk") {
      const isHigh = (a.latest_risk_level || "").toUpperCase() === "HIGH" || (a.latest_risk_score || 0) >= 70;
      if (!isHigh) return false;
    } else if (riskFilter === "moderate") {
      const score = a.latest_risk_score;
      const isMod = (a.latest_risk_level || "").toUpperCase() === "MODERATE" || (score !== null && score >= 40 && score < 70);
      if (!isMod) return false;
    } else if (riskFilter === "low") {
      const score = a.latest_risk_score;
      const isLow = (a.latest_risk_level || "").toUpperCase() === "LOW" || (score !== null && score < 40);
      if (!isLow) return false;
    }

    // Assessment / Injury Status filter
    if (statusFilter === "reassessment" || activeGroupFilter === "reassessment") {
      if (!a.needs_reassessment) return false;
    }
    if (statusFilter === "injured" || activeGroupFilter === "injured") {
      if (!(a.injury_status === "Injured" || a.injury_status === "Recovering")) return false;
    } else if (statusFilter === "healthy") {
      if (a.injury_status !== "Healthy") return false;
    }

    return true;
  });

  return (
    <div className="app-layout">
      <main className="dashboard">
        {isPhysio ? (
          <PhysiotherapistDashboardView
            user={user}
            teamAthletes={teamAthletes}
            teamAssessments={teamAssessments}
            onRefresh={loadData}
          />
        ) : isSportsScientist ? (
          <SportsScientistDashboardView
            user={user}
            teamAthletes={teamAthletes}
            teamAssessments={teamAssessments}
            onRefresh={loadData}
          />
        ) : (
          <>
            {/* ── Welcome Hero Banner ─────────────────────────────────────── */}
            <div className="dash-hero">
              <div className="dash-hero-content">
                <div className="dash-hero-badge">
                  <Sparkles size={14} />
                  <span>
                    {isAthlete ? "PREHAB AI MOVEMENT PLATFORM" : "COACH & CLINICAL INJURY MONITORING WORKSPACE"}
                  </span>
                </div>

                <h1>
                  Welcome back, {user?.name || (isAthlete ? "Athlete" : "Coach")}
                </h1>

                <p>
                  {isAthlete
                    ? profile?.sport
                      ? `${profile.sport} Athlete • ${profile.position || "Player"} — AI movement analysis and injury prevention dashboard.`
                      : "AI movement analysis and injury-risk assessment dashboard."
                    : "Monitor team roster movement biomechanics, track injury risk trends, and manage athlete evaluations."}
                </p>

                {!isProfileComplete && isAthlete && (
                  <div className="profile-alert-banner">
                    <ShieldAlert size={16} />
                    <span>Complete your athlete profile for accurate biomechanical risk scoring.</span>
                    <Link to="/profile" className="profile-alert-link">
                      Update Profile &rarr;
                    </Link>
                  </div>
                )}
              </div>

              <div className="dash-hero-actions">
                {isAthlete ? (
                  <Link to="/analysis" className="primary-button hero-cta" id="hero-upload-btn">
                    <Plus size={18} />
                    Analyze New Video
                  </Link>
                ) : (
                  <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                    <button
                      type="button"
                      className="primary-button hero-cta"
                      onClick={() => setIsAddAthleteOpen(true)}
                      style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
                    >
                      <UserPlus size={18} style={{ flexShrink: 0 }} />
                      <span>Add Athlete</span>
                    </button>
                    <Link
                      to="/assessments"
                      className="primary-button hero-cta"
                      style={{ display: "inline-flex", alignItems: "center", gap: 8 }}
                    >
                      <ClipboardCheck size={18} style={{ flexShrink: 0 }} />
                      <span>All Assessments</span>
                    </Link>
                  </div>
                )}
              </div>
            </div>

            {/* ── ATHLETE DASHBOARD VIEW ──────────────────────────────────── */}
            {isAthlete ? (
              <>
            {/* Statistics Grid */}
            <div className="stats-grid">
              <div className="stat-card-modern">
                <div className="stat-header">
                  <span className="stat-title">Total Assessments</span>
                  <div className="stat-icon-wrapper purple">
                    <FileVideo size={20} />
                  </div>
                </div>
                <div className="stat-value">{totalAssessments}</div>
                <div className="stat-subtext">
                  {totalAssessments === 0
                    ? "No videos uploaded yet"
                    : `${totalCompleted} completed analysis`}
                </div>
              </div>

              <div className="stat-card-modern">
                <div className="stat-header">
                  <span className="stat-title">Current Risk Score</span>
                  <div className="stat-icon-wrapper indigo">
                    <Activity size={20} />
                  </div>
                </div>
                <div className="stat-value-row">
                  <span className="stat-value">
                    {latestRiskScore !== null ? `${latestRiskScore}` : "N/A"}
                  </span>
                  {latestRiskLevel && <RiskBadge level={latestRiskLevel} />}
                </div>
                <div className="stat-subtext">
                  {latestAssessment
                    ? `Latest: ${formatDate(latestAssessment.uploaded_at)}`
                    : "Upload video to get risk score"}
                </div>
              </div>

              <div className="stat-card-modern">
                <div className="stat-header">
                  <span className="stat-title">Average Risk Score</span>
                  <div className="stat-icon-wrapper teal">
                    <TrendingUp size={20} />
                  </div>
                </div>
                <div className="stat-value">
                  {averageRiskScore !== null ? `${averageRiskScore}` : "N/A"}
                </div>
                <div className="stat-subtext">
                  {totalCompleted > 0
                    ? `Average across ${totalCompleted} analyses`
                    : "No completed scores yet"}
                </div>
              </div>

              <div className={`stat-card-modern ${highRiskCount > 0 ? "danger-card" : ""}`}>
                <div className="stat-header">
                  <span className="stat-title">High Risk Alerts</span>
                  <div className={`stat-icon-wrapper ${highRiskCount > 0 ? "red" : "gray"}`}>
                    <AlertTriangle size={20} />
                  </div>
                </div>
                <div className="stat-value">{highRiskCount}</div>
                <div className="stat-subtext">
                  {highRiskCount > 0
                    ? "Requires bio-technique attention"
                    : "All movement tests within threshold"}
                </div>
              </div>
            </div>

            {/* Main Layout Grid */}
            <div className="dashboard-grid">
              <section className="panel card-panel">
                <div className="panel-header">
                  <div>
                    <h2>Recent Assessments</h2>
                    <p>Latest AI movement risk evaluations from real uploads</p>
                  </div>
                  <Link to="/analysis/history" className="view-all-link">
                    <span>View History</span>
                    <ArrowUpRight size={16} />
                  </Link>
                </div>

                {loading ? (
                  <div className="loading-container" style={{ padding: "40px 0" }}>
                    <div className="spinner" />
                    <span>Loading analysis history...</span>
                  </div>
                ) : history.length === 0 ? (
                  <div className="empty-state-card">
                    <div className="empty-icon-wrapper">
                      <Video size={28} />
                    </div>
                    <h3>No movement assessments yet</h3>
                    <p>
                      Upload a video of your jump-landing or movement test to generate
                      your first AI injury risk report.
                    </p>
                    <Link to="/analysis" className="primary-button" style={{ marginTop: 12 }}>
                      <Plus size={16} />
                      Upload First Video
                    </Link>
                  </div>
                ) : (
                  <div className="assessment-card-list">
                    {history.slice(0, 4).map((item) => {
                      const score =
                        item.overall_risk_score !== null && item.overall_risk_score !== undefined
                          ? Math.round(item.overall_risk_score)
                          : null;

                      return (
                        <div
                          key={item.video_id}
                          className="assessment-card-row"
                          onClick={() => navigate(`/analysis/${item.video_id}`)}
                        >
                          <div className="card-row-left">
                            <div className="video-thumb-icon">
                              <FileVideo size={20} />
                            </div>
                            <div className="card-row-info">
                              <strong className="video-name">
                                {item.original_filename || "Movement Video"}
                              </strong>
                              <span className="video-date">
                                <Clock size={12} />
                                {formatDate(item.uploaded_at)}
                              </span>
                            </div>
                          </div>

                          <div className="card-row-right">
                            {item.has_pose_landmarks && (
                              <span className="ai-pose-tag-pill" title="AI Pose Analysis Available">
                                AI POSE ✓
                              </span>
                            )}

                            {score !== null ? (
                              <div className="score-pillar">
                                <span className="score-num">{score}</span>
                                <span className="score-label">Score</span>
                              </div>
                            ) : (
                              <span className="pending-tag">{item.processing_status || "PENDING"}</span>
                            )}

                            {item.less_score !== null && item.less_score !== undefined && (
                              <span className="less-pill">
                                LESS {item.less_score}/{item.less_max_computable_score || 12}
                              </span>
                            )}

                            <RiskBadge level={item.risk_level || "PENDING"} />
                            <ChevronRight size={18} className="row-arrow" />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

              </section>

              <div className="side-panels-column">
                <section className="panel card-panel">
                  <div className="panel-header">
                    <h2>Risk Distribution</h2>
                  </div>
                  {totalCompleted === 0 ? (
                    <p style={{ color: "var(--color-text-muted)", fontSize: "0.88rem" }}>
                      Complete at least 1 video assessment to view your risk distribution.
                    </p>
                  ) : (
                    <div className="risk-overview-stack">
                      <RiskDistributionBar label="Low Risk (<40)" count={lowRiskCount} percentage={lowPct} colorClass="bg-emerald" />
                      <RiskDistributionBar label="Moderate Risk (40-69)" count={moderateRiskCount} percentage={modPct} colorClass="bg-amber" />
                      <RiskDistributionBar label="High Risk (≥70)" count={highRiskCount} percentage={highPct} colorClass="bg-rose" />
                    </div>
                  )}
                </section>
              </div>
            </div>
          </>
        ) : (
          /* ── COACH WORKSPACE VIEW ─────────────────────────────────────── */
          <>
            {/* 1. Coach Overview Cards */}
            <div className="stats-grid">
              <div className="stat-card-modern">
                <div className="stat-header">
                  <span className="stat-title">Total Roster</span>
                  <div className="stat-icon-wrapper purple">
                    <Users size={20} />
                  </div>
                </div>
                <div className="stat-value">{totalRoster}</div>
                <div className="stat-subtext">Active athletes under management</div>
              </div>

              <div className="stat-card-modern">
                <div className="stat-header">
                  <span className="stat-title">Assessed This Week</span>
                  <div className="stat-icon-wrapper teal">
                    <CheckCircle2 size={20} />
                  </div>
                </div>
                <div className="stat-value">{assessedThisWeek}</div>
                <div className="stat-subtext">Athletes evaluated in last 7 days</div>
              </div>

              <div className={`stat-card-modern ${teamHighRiskCount > 0 ? "danger-card" : ""}`}>
                <div className="stat-header">
                  <span className="stat-title">High-Risk Athletes</span>
                  <div className={`stat-icon-wrapper ${teamHighRiskCount > 0 ? "red" : "gray"}`}>
                    <AlertTriangle size={20} />
                  </div>
                </div>
                <div className="stat-value">{teamHighRiskCount}</div>
                <div className="stat-subtext">Require bio-technique attention</div>
              </div>

              <div className="stat-card-modern">
                <div className="stat-header">
                  <span className="stat-title">Needs Reassessment</span>
                  <div className="stat-icon-wrapper indigo">
                    <Clock size={20} />
                  </div>
                </div>
                <div className="stat-value">{needingReassessmentCount}</div>
                <div className="stat-subtext">Overdue or never assessed</div>
              </div>
            </div>

            {/* 2. Needs Attention Priority Banner / Section */}
            {needsAttentionList.length > 0 && (
              <section className="panel card-panel" style={{ borderLeft: "4px solid var(--color-danger, #ef4444)", marginBottom: 24 }}>
                <div className="panel-header">
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <ShieldAlert size={22} style={{ color: "var(--color-danger, #ef4444)" }} />
                    <div>
                      <h2 style={{ fontSize: "1.1rem" }}>Needs Attention — High Priority Athletes ({needsAttentionList.length})</h2>
                      <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
                        Athletes flagged with high movement risk, significant score spikes, or injury status
                      </p>
                    </div>
                  </div>
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12, marginTop: 12 }}>
                  {needsAttentionList.slice(0, 3).map((ath) => (
                    <div
                      key={ath.athlete_id}
                      style={{
                        background: "rgba(239, 68, 68, 0.06)",
                        border: "1px solid rgba(239, 68, 68, 0.2)",
                        borderRadius: 8,
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
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8, fontSize: "0.82rem" }}>
                        <span>Status: <strong style={{ color: "#fca5a5" }}>{ath.injury_status || "Needs Review"}</strong></span>
                        {ath.latest_risk_score != null && (
                          <span style={{ fontWeight: 600 }}>Score: {Math.round(ath.latest_risk_score)}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* 3. Main Coach Workspace Layout */}
            <div className="dashboard-grid">
              {/* Left Column: Smart Athlete Groups & Roster Cards */}
              <section className="panel card-panel">
                <div className="panel-header" style={{ flexDirection: "column", alignItems: "flex-start", gap: 12 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", width: "100%", alignItems: "center" }}>
                    <div>
                      <h2>Smart Athlete Groups</h2>
                      <p>Filter athletes by sport, position, risk, or assessment status</p>
                    </div>
                    <button
                      type="button"
                      className="primary-button"
                      style={{ fontSize: "0.85rem", padding: "6px 12px" }}
                      onClick={() => setIsAddAthleteOpen(true)}
                    >
                      <UserPlus size={16} /> Add Athlete
                    </button>
                  </div>

                  {/* Refined Compact Filter Dropdowns */}
                  <div className="coach-filter-bar">
                    {/* Roster Scope */}
                    <select
                      value={scopeFilter}
                      onChange={(e) => {
                        setScopeFilter(e.target.value);
                        if (activeGroupFilter !== "all") setActiveGroupFilter("all");
                      }}
                      className={`coach-filter-select ${scopeFilter !== "all" || activeGroupFilter === "my" ? "active" : ""}`}
                      aria-label="Filter by roster scope"
                    >
                      <option value="all">All Athletes</option>
                      <option value="my">My Roster</option>
                    </select>

                    {/* Sport */}
                    <select
                      value={sportFilter}
                      onChange={(e) => {
                        setSportFilter(e.target.value);
                        if (activeGroupFilter !== "all") setActiveGroupFilter("all");
                      }}
                      className={`coach-filter-select ${sportFilter !== "all" ? "active" : ""}`}
                      aria-label="Filter by sport"
                    >
                      <option value="all">All Sports</option>
                      {availableSports.map((sp) => (
                        <option key={sp} value={sp}>
                          {sp}
                        </option>
                      ))}
                    </select>

                    {/* Position */}
                    <select
                      value={positionFilter}
                      onChange={(e) => {
                        setPositionFilter(e.target.value);
                        if (activeGroupFilter !== "all") setActiveGroupFilter("all");
                      }}
                      className={`coach-filter-select ${positionFilter !== "all" ? "active" : ""}`}
                      aria-label="Filter by position"
                    >
                      <option value="all">All Positions</option>
                      {availablePositions.map((pos) => (
                        <option key={pos} value={pos}>
                          {pos}
                        </option>
                      ))}
                    </select>

                    {/* Risk Level */}
                    <select
                      value={riskFilter}
                      onChange={(e) => {
                        setRiskFilter(e.target.value);
                        if (activeGroupFilter !== "all") setActiveGroupFilter("all");
                      }}
                      className={`coach-filter-select ${riskFilter !== "all" || activeGroupFilter === "high_risk" ? "active" : ""}`}
                      aria-label="Filter by risk level"
                    >
                      <option value="all">All Risk Levels</option>
                      <option value="high">High Risk</option>
                      <option value="moderate">Moderate Risk</option>
                      <option value="low">Low Risk</option>
                    </select>

                    {/* Assessment Status */}
                    <select
                      value={statusFilter}
                      onChange={(e) => {
                        setStatusFilter(e.target.value);
                        if (activeGroupFilter !== "all") setActiveGroupFilter("all");
                      }}
                      className={`coach-filter-select ${statusFilter !== "all" || activeGroupFilter === "reassessment" || activeGroupFilter === "injured" ? "active" : ""}`}
                      aria-label="Filter by assessment status"
                    >
                      <option value="all">All Statuses</option>
                      <option value="reassessment">Needs Reassessment</option>
                      <option value="injured">Injured / Recovering</option>
                      <option value="healthy">Healthy (Cleared)</option>
                    </select>

                    {(scopeFilter !== "all" || sportFilter !== "all" || positionFilter !== "all" || riskFilter !== "all" || statusFilter !== "all" || activeGroupFilter !== "all") && (
                      <button
                        type="button"
                        className="coach-filter-reset-btn"
                        onClick={resetAllFilters}
                      >
                        Reset Filters
                      </button>
                    )}
                  </div>

                  {/* Search Bar */}
                  <div className="search-box" style={{ width: "100%", marginTop: 4 }}>
                    <Search size={16} />
                    <input
                      type="text"
                      placeholder="Search athletes by name, sport, or position..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                    />
                  </div>
                </div>

                {/* Athlete Cards Grid */}
                {filteredAthletes.length === 0 ? (
                  <div className="empty-state-card" style={{ padding: "30px 0" }}>
                    <Users size={32} style={{ opacity: 0.5 }} />
                    <p>No athletes found matching current group filter.</p>
                  </div>
                ) : (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 14, marginTop: 12 }}>
                    {filteredAthletes.map((ath) => (
                      <div
                        key={ath.athlete_id}
                        className="stat-card-modern"
                        style={{ padding: 14, cursor: "pointer", display: "flex", flexDirection: "column", justifyContent: "space-between" }}
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

                          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginTop: 14, background: "rgba(255,255,255,0.02)", padding: 8, borderRadius: 6, fontSize: "0.8rem" }}>
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

                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 12, fontSize: "0.78rem", borderTop: "1px solid rgba(255,255,255,0.05)", paddingTop: 8 }}>
                          <span style={{ color: "var(--color-text-muted)" }}>
                            Last test: {formatDate(ath.last_assessment_date)}
                          </span>
                          <span style={{ color: ath.injury_status === "Injured" ? "#ef4444" : "#10b981", fontWeight: 600 }}>
                            {ath.injury_status || "Healthy"}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* Right Column: Risk Monitoring & Recent Team Assessments */}
              <div className="side-panels-column">
                {/* Team Risk Distribution Chart */}
                <section className="panel card-panel">
                  <div className="panel-header">
                    <h2>Team Risk Monitoring</h2>
                  </div>
                  {tTotal === 0 ? (
                    <p style={{ color: "var(--color-text-muted)", fontSize: "0.85rem" }}>
                      No assessed athletes yet.
                    </p>
                  ) : (
                    <div className="risk-overview-stack">
                      <RiskDistributionBar label="Low Risk (<40)" count={tLow} percentage={tLowPct} colorClass="bg-emerald" />
                      <RiskDistributionBar label="Moderate Risk (40-69)" count={tMod} percentage={tModPct} colorClass="bg-amber" />
                      <RiskDistributionBar label="High Risk (≥70)" count={tHigh} percentage={tHighPct} colorClass="bg-rose" />
                    </div>
                  )}
                </section>

                {/* Recent Team Assessments Table */}
                <section className="panel card-panel">
                  <div className="panel-header">
                    <div>
                      <h2>Recent Team Assessments</h2>
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
                              <span className="video-date">{formatDate(item.uploaded_at)} • {item.sport || "Sport"}</span>
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

                {/* Quick Actions Panel */}
                <section className="panel card-panel">
                  <div className="panel-header">
                    <h2>Quick Actions</h2>
                  </div>
                  <div className="quick-actions-list">
                    <button
                      type="button"
                      className="quick-action-btn primary"
                      onClick={() => setIsAddAthleteOpen(true)}
                    >
                      <UserPlus size={18} />
                      <span>Add New Athlete to Roster</span>
                      <ChevronRight size={16} />
                    </button>

                    <button
                      type="button"
                      className="quick-action-btn secondary"
                      onClick={() => setActiveGroupFilter("high_risk")}
                    >
                      <AlertTriangle size={18} />
                      <span>View High-Risk Athletes</span>
                      <ChevronRight size={16} />
                    </button>

                    <Link to="/assessments" className="quick-action-btn secondary">
                      <ClipboardCheck size={18} />
                      <span>View All Team Assessments</span>
                      <ChevronRight size={16} />
                    </Link>
                  </div>
                </section>
              </div>
            </div>
          </>
        )}
        </>
      )}
      </main>

      {/* Modals */}
      <AddAthleteModal
        isOpen={isAddAthleteOpen}
        onClose={() => setIsAddAthleteOpen(false)}
        onAthleteAdded={() => loadData()}
      />

      <AthleteDetailModal
        isOpen={!!selectedAthlete}
        onClose={() => setSelectedAthlete(null)}
        athlete={selectedAthlete}
        onUpdate={() => loadData()}
      />

      <AssessmentCompareModal
        isOpen={!!compareAssessmentA}
        onClose={() => setCompareAssessmentA(null)}
        assessmentA={compareAssessmentA}
        assessmentB={compareAssessmentB}
      />
    </div>
  );
}

function RiskDistributionBar({ label, count, percentage, colorClass }) {
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

export default Dashboard;