import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, FileVideo, Calendar, ArrowRight, ArrowLeftRight, Eye, Filter } from "lucide-react";

import RiskBadge from "../components/RiskBadge";
import Loading from "../components/Loading";
import AssessmentCompareModal from "../components/AssessmentCompareModal";

import { getAssessments } from "../api/assessments";
import { useAuth } from "../context/AuthContext";

function Assessments() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [assessments, setAssessments] = useState([]);
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("all"); // "all" | "high" | "moderate" | "low"
  const [selectedForCompare, setSelectedForCompare] = useState([]);

  const [compareModalA, setCompareModalA] = useState(null);
  const [compareModalB, setCompareModalB] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getAssessments();
        setAssessments(Array.isArray(data) ? data : data.items || []);
      } catch (err) {
        setError(err.response?.data?.detail || "Unable to load assessments.");
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  const filteredAssessments = assessments.filter((item) => {
    const filename = item.original_filename || "";
    const athleteName = item.athlete_name || "";
    const sport = item.sport || "";

    const matchesSearch =
      filename.toLowerCase().includes(search.toLowerCase()) ||
      athleteName.toLowerCase().includes(search.toLowerCase()) ||
      sport.toLowerCase().includes(search.toLowerCase());

    if (!matchesSearch) return false;

    const lvl = (item.risk_level || "").toUpperCase();
    if (riskFilter === "high") return lvl === "HIGH" || (item.overall_risk_score || 0) >= 70;
    if (riskFilter === "moderate") return lvl === "MODERATE" || ((item.overall_risk_score || 0) >= 40 && (item.overall_risk_score || 0) < 70);
    if (riskFilter === "low") return lvl === "LOW" || (item.overall_risk_score !== null && item.overall_risk_score < 40);

    return true;
  });

  function formatDate(dStr) {
    if (!dStr) return "—";
    return new Date(dStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function handleOpenCompare(item) {
    if (!item) return;

    // Filter assessments strictly for the SAME athlete
    const athleteAssessments = assessments.filter((a) => {
      const sameId = a.athlete_id && item.athlete_id && a.athlete_id === item.athlete_id;
      const sameName = a.athlete_name && item.athlete_name &&
        a.athlete_name.trim().toLowerCase() === item.athlete_name.trim().toLowerCase();

      const isCompleted = (a.analysis_status === "COMPLETED" || a.processing_status === "COMPLETED") &&
        a.overall_risk_score !== null && a.overall_risk_score !== undefined;

      return (sameId || sameName) && isCompleted;
    });

    // Sort chronologically descending (newest first)
    const sorted = [...athleteAssessments].sort((a, b) => {
      const timeA = new Date(a.uploaded_at || a.completed_at || 0).getTime();
      const timeB = new Date(b.uploaded_at || b.completed_at || 0).getTime();
      return timeB - timeA;
    });

    const idx = sorted.findIndex((a) => a.video_id === item.video_id || (a.id && a.id === item.id));

    let prev = null;
    if (idx >= 0 && idx < sorted.length - 1) {
      prev = sorted[idx + 1];
    } else if (idx === -1 && sorted.length > 0) {
      const itemTime = new Date(item.uploaded_at || item.completed_at || 0).getTime();
      prev = sorted.find((a) => new Date(a.uploaded_at || a.completed_at || 0).getTime() < itemTime) || null;
    }

    setCompareModalA(item);
    setCompareModalB(prev);
  }

  return (
    <div className="app-layout">
      <main className="dashboard">
        <div className="page-header">
          <div>
            <span className="eyebrow">ANALYTICS & MOVEMENT EVALUATIONS</span>
            <h1>Assessment Management</h1>
            <p>
              Review, filter, and compare AI biomechanical movement evaluations across team roster.
            </p>
          </div>
        </div>

        {/* Filter Controls */}
        <section className="panel" style={{ marginBottom: 20 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12, justifyContent: "space-between", alignItems: "center" }}>
            <div className="search-box" style={{ flex: 1, minWidth: 260 }}>
              <Search size={18} />
              <input
                placeholder="Search assessments by athlete, filename, or sport..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>

            {/* Risk Level Filter */}
            <div className="risk-filter-group">
              <span className="risk-filter-label">Risk Filter:</span>
              {[
                { id: "all", label: "All" },
                { id: "high", label: "High Risk" },
                { id: "moderate", label: "Moderate Risk" },
                { id: "low", label: "Low Risk" },
              ].map((btn) => (
                <button
                  key={btn.id}
                  type="button"
                  onClick={() => setRiskFilter(btn.id)}
                  className={`risk-filter-btn ${riskFilter === btn.id ? "active" : ""}`}
                >
                  {btn.label}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Table / List Panel */}
        <section className="panel">
          {loading && <Loading />}

          {error && <div className="error-box">{error}</div>}

          {!loading && !error && filteredAssessments.length === 0 && (
            <div className="empty-state-card" style={{ padding: "40px 0" }}>
              <FileVideo size={36} style={{ opacity: 0.5 }} />
              <h3>No assessments found</h3>
              <p>No video movement evaluations match your current search or risk filter.</p>
            </div>
          )}

          {!loading && !error && filteredAssessments.length > 0 && (
            <div className="assessment-table">
              <div className="table-header" style={{ display: "grid", gridTemplateColumns: "1.1fr 1.6fr 1.8fr 1.1fr 1fr 1fr minmax(185px, auto)", gap: 12 }}>
                <span>Date</span>
                <span>Athlete</span>
                <span>Movement Video</span>
                <span>Risk Score</span>
                <span>LESS Score</span>
                <span>Status</span>
                <span>Actions</span>
              </div>

              {filteredAssessments.map((item) => {
                const score = item.overall_risk_score !== null && item.overall_risk_score !== undefined
                  ? Math.round(item.overall_risk_score)
                  : null;

                return (
                  <div
                    className="table-row"
                    key={item.video_id || item.id}
                    style={{ display: "grid", gridTemplateColumns: "1.1fr 1.6fr 1.8fr 1.1fr 1fr 1fr minmax(185px, auto)", gap: 12, alignItems: "center" }}
                  >
                    <span style={{ fontSize: "0.85rem", color: "var(--color-text-muted)" }}>
                      {formatDate(item.uploaded_at || item.completed_at)}
                    </span>

                    <div>
                      <strong style={{ fontSize: "0.95rem", display: "block" }}>
                        {item.athlete_name || "Athlete"}
                      </strong>
                      <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted)" }}>
                        {item.sport || "Sport"} {item.position ? `• ${item.position}` : ""}
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <FileVideo size={16} style={{ color: "var(--color-primary-light)" }} />
                      <span style={{ fontSize: "0.88rem", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 180 }}>
                        {item.original_filename || "Movement Video"}
                      </span>
                      {item.has_pose_landmarks && (
                        <span className="ai-pose-tag-pill" title="AI Pose Analysis Available">
                          AI POSE ✓
                        </span>
                      )}
                    </div>


                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {score !== null ? <strong>{score}/100</strong> : <span style={{ color: "var(--color-text-muted)" }}>N/A</span>}
                      <RiskBadge level={item.risk_level || "PENDING"} />
                    </div>

                    <span style={{ fontSize: "0.88rem" }}>
                      {item.less_score !== null && item.less_score !== undefined
                        ? `${item.less_score} / ${item.less_max_computable_score || 12}`
                        : "N/A"}
                    </span>

                    <span style={{ fontSize: "0.82rem", fontWeight: 600, color: item.analysis_status === "COMPLETED" || item.processing_status === "COMPLETED" ? "#10b981" : "#f59e0b" }}>
                      {item.analysis_status || item.processing_status || "COMPLETED"}
                    </span>

                    <div className="assessment-actions-group">
                      <button
                        type="button"
                        className="assessment-action-btn"
                        onClick={() => navigate(`/analysis/${item.video_id}`)}
                        title="View Full Report"
                      >
                        <Eye size={14} /> Report
                      </button>

                      <button
                        type="button"
                        className="assessment-action-btn"
                        onClick={() => handleOpenCompare(item)}
                        title="Compare with previous test"
                      >
                        <ArrowLeftRight size={14} /> Compare
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>

      <AssessmentCompareModal
        isOpen={!!compareModalA}
        onClose={() => setCompareModalA(null)}
        assessmentA={compareModalA}
        assessmentB={compareModalB}
      />
    </div>
  );
}

export default Assessments;