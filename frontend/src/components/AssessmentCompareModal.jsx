import { useEffect, useState } from "react";
import { X, TrendingUp, TrendingDown, Minus, ShieldAlert, Info } from "lucide-react";
import RiskBadge from "./RiskBadge";
import { getAnalysisStatus } from "../api/videos";

function AssessmentCompareModal({ isOpen, onClose, assessmentA, assessmentB }) {
  const [detailsA, setDetailsA] = useState(null);
  const [detailsB, setDetailsB] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    if (!isOpen || !assessmentA) {
      setDetailsA(null);
      setDetailsB(null);
      return;
    }

    let isMounted = true;
    async function loadFullDetails() {
      setLoadingDetails(true);
      try {
        const promises = [
          assessmentA?.video_id ? getAnalysisStatus(assessmentA.video_id).catch(() => null) : Promise.resolve(null),
          assessmentB?.video_id ? getAnalysisStatus(assessmentB.video_id).catch(() => null) : Promise.resolve(null),
        ];
        const [resA, resB] = await Promise.all(promises);
        if (isMounted) {
          setDetailsA(resA);
          setDetailsB(resB);
        }
      } finally {
        if (isMounted) setLoadingDetails(false);
      }
    }

    loadFullDetails();
    return () => {
      isMounted = false;
    };
  }, [isOpen, assessmentA, assessmentB]);

  if (!isOpen || !assessmentA) return null;

  const athleteName = assessmentA.athlete_name || "Athlete";
  const hasPrevious = Boolean(assessmentB);
  const b = assessmentB || {};

  const scoreA = assessmentA.overall_risk_score !== null && assessmentA.overall_risk_score !== undefined
    ? Math.round(assessmentA.overall_risk_score)
    : (detailsA?.overall_risk_score != null ? Math.round(detailsA.overall_risk_score) : null);

  const scoreB = hasPrevious && (b.overall_risk_score !== null && b.overall_risk_score !== undefined)
    ? Math.round(b.overall_risk_score)
    : (hasPrevious && detailsB?.overall_risk_score != null ? Math.round(detailsB.overall_risk_score) : null);

  const scoreDelta = scoreA !== null && scoreB !== null ? scoreA - scoreB : null;

  function formatDate(dStr) {
    if (!dStr) return "N/A";
    return new Date(dStr).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  // Factor values
  const sBioA = detailsA?.s_bio ?? assessmentA.s_bio;
  const sBioB = detailsB?.s_bio ?? b.s_bio;

  const sAsymA = detailsA?.s_asym ?? detailsA?.symmetry_score ?? assessmentA.s_asym;
  const sAsymB = detailsB?.s_asym ?? detailsB?.symmetry_score ?? b.s_asym;

  const sFatigueA = detailsA?.s_fatigue ?? detailsA?.fatigue_score ?? assessmentA.s_fatigue;
  const sFatigueB = detailsB?.s_fatigue ?? detailsB?.fatigue_score ?? b.s_fatigue;

  const lessA = assessmentA.less_score;
  const lessB = b.less_score;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="compare-modal-panel" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="compare-modal-header">
          <div>
            <span className="eyebrow" style={{ color: "#818cf8", fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.05em" }}>
              MOVEMENT ANALYSIS COMPARISON
            </span>
            <h3>{athleteName} Movement Progression</h3>
            <p>Side-by-side evaluation of risk movement biomechanics across assessments</p>
          </div>
          <button type="button" className="compare-close-btn" onClick={onClose} title="Close Comparison">
            <X size={20} />
          </button>
        </div>

        {/* Header Cards Grid */}
        <div className="compare-banner-grid">
          {/* Current Assessment */}
          <div className="compare-card">
            <span className="compare-card-title" style={{ color: "#818cf8" }}>Current Assessment</span>
            <div className="compare-card-score" style={{ color: scoreA >= 70 ? "#ef4444" : scoreA >= 40 ? "#f59e0b" : "#10b981" }}>
              {scoreA !== null ? `${scoreA}/100` : "N/A"}
            </div>
            <div style={{ display: "flex", justifyContent: "center", gap: 6, margin: "4px 0" }}>
              <RiskBadge level={assessmentA.risk_level || "PENDING"} />
            </div>
            <span style={{ fontSize: "0.78rem", color: "#94a3b8" }}>
              {formatDate(assessmentA.uploaded_at || assessmentA.completed_at)}
            </span>
            <span style={{ fontSize: "0.75rem", color: "#64748b", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>
              {assessmentA.original_filename || "Current Video"}
            </span>
          </div>

          {/* Change Delta or Single Assessment Notice */}
          <div className="compare-delta-box">
            <span style={{ fontSize: "0.72rem", color: "#94a3b8", fontWeight: 700, letterSpacing: "0.05em", marginBottom: 6 }}>
              RISK DELTA
            </span>
            {hasPrevious && scoreDelta !== null ? (
              <div className={`compare-delta-badge ${scoreDelta > 0 ? "compare-delta-worsened" : scoreDelta < 0 ? "compare-delta-improved" : "compare-delta-unchanged"}`}>
                {scoreDelta > 0 ? <TrendingUp size={18} /> : scoreDelta < 0 ? <TrendingDown size={18} /> : <Minus size={18} />}
                <span>
                  {scoreDelta > 0 ? `+${scoreDelta} pts (Worsened)` : scoreDelta < 0 ? `${scoreDelta} pts (Improved)` : "0 pts (Unchanged)"}
                </span>
              </div>
            ) : (
              <span style={{ fontSize: "0.82rem", color: "#94a3b8", background: "rgba(255,255,255,0.05)", padding: "6px 12px", borderRadius: 16 }}>
                Single Assessment
              </span>
            )}
          </div>

          {/* Previous Assessment */}
          {hasPrevious ? (
            <div className="compare-card">
              <span className="compare-card-title" style={{ color: "#94a3b8" }}>Previous Assessment</span>
              <div className="compare-card-score" style={{ color: scoreB >= 70 ? "#ef4444" : scoreB >= 40 ? "#f59e0b" : "#10b981" }}>
                {scoreB !== null ? `${scoreB}/100` : "N/A"}
              </div>
              <div style={{ display: "flex", justifyContent: "center", gap: 6, margin: "4px 0" }}>
                {b.risk_level ? <RiskBadge level={b.risk_level} /> : <span style={{ fontSize: "0.8rem", color: "#94a3b8" }}>Completed</span>}
              </div>
              <span style={{ fontSize: "0.78rem", color: "#94a3b8" }}>
                {formatDate(b.uploaded_at || b.completed_at)}
              </span>
              <span style={{ fontSize: "0.75rem", color: "#64748b", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }}>
                {b.original_filename || "Previous Video"}
              </span>
            </div>
          ) : (
            <div className="compare-card" style={{ opacity: 0.65 }}>
              <span className="compare-card-title" style={{ color: "#94a3b8" }}>Previous Assessment</span>
              <div className="compare-card-score" style={{ fontSize: "1.5rem", color: "#64748b", margin: "12px 0" }}>
                No Baseline
              </div>
              <span style={{ fontSize: "0.78rem", color: "#94a3b8" }}>
                First test on record
              </span>
            </div>
          )}
        </div>

        {/* Significant Risk Increase Alert Banner */}
        {hasPrevious && scoreDelta !== null && scoreDelta >= 15 && (
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            background: "rgba(239, 68, 68, 0.15)",
            border: "1px solid #ef4444",
            color: "#fca5a5",
            padding: "12px 16px",
            borderRadius: 10,
            fontSize: "0.88rem"
          }}>
            <ShieldAlert size={20} style={{ color: "#ef4444", flexShrink: 0 }} />
            <span>
              <strong>Significant Risk Spike Detected:</strong> Overall movement injury risk increased by {scoreDelta} points compared to the previous test on {formatDate(b.uploaded_at || b.completed_at)}. Review movement technique recommendations.
            </span>
          </div>
        )}

        {/* No Previous Assessment Baseline Card */}
        {!hasPrevious && (
          <div className="compare-no-baseline-card">
            <Info size={32} style={{ color: "#818cf8" }} />
            <h4>No Previous Assessment Available</h4>
            <p>
              This is <strong>{athleteName}</strong>'s first or only completed assessment in the system.
              Once additional movement evaluations are completed for this athlete, automated side-by-side progression tracking and risk deltas will be displayed here.
            </p>
          </div>
        )}

        {/* Detailed Metrics Table */}
        {hasPrevious && (
          <div className="compare-metrics-table-wrapper">
            <table className="compare-metrics-table">
              <thead>
                <tr>
                  <th>Biomechanical Metric</th>
                  <th style={{ color: "#818cf8" }}>Current Test</th>
                  <th>Previous Test</th>
                  <th>Comparison / Change</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Overall Injury Risk Score</strong></td>
                  <td><strong>{scoreA !== null ? `${scoreA} / 100` : "N/A"}</strong></td>
                  <td>{scoreB !== null ? `${scoreB} / 100` : "N/A"}</td>
                  <td>
                    {scoreDelta !== null ? (
                      <span style={{ color: scoreDelta > 0 ? "#f87171" : scoreDelta < 0 ? "#34d399" : "#94a3b8", fontWeight: 600 }}>
                        {scoreDelta > 0 ? `+${scoreDelta} pts (Higher Risk)` : scoreDelta < 0 ? `${scoreDelta} pts (Improved)` : "0 pts (Equal)"}
                      </span>
                    ) : "N/A"}
                  </td>
                </tr>

                <tr>
                  <td><strong>LESS Score (Technique Errors)</strong></td>
                  <td>
                    {lessA !== null && lessA !== undefined ? `${lessA} / ${assessmentA.less_max_computable_score || 12}` : "N/A"}
                  </td>
                  <td>
                    {lessB !== null && lessB !== undefined ? `${lessB} / ${b.less_max_computable_score || 12}` : "N/A"}
                  </td>
                  <td>
                    {lessA != null && lessB != null ? (
                      <span style={{ color: lessA - lessB > 0 ? "#f87171" : lessA - lessB < 0 ? "#34d399" : "#94a3b8", fontWeight: 600 }}>
                        {lessA - lessB > 0 ? `+${lessA - lessB} errors (Worsened)` : lessA - lessB < 0 ? `${lessA - lessB} errors (Improved)` : "0 errors (Equal)"}
                      </span>
                    ) : "N/A"}
                  </td>
                </tr>

                <tr>
                  <td><strong>Biomechanical Risk (S_bio)</strong></td>
                  <td>{sBioA != null ? `${Math.round(sBioA * 100) / 100}` : "N/A"}</td>
                  <td>{sBioB != null ? `${Math.round(sBioB * 100) / 100}` : "N/A"}</td>
                  <td>
                    {sBioA != null && sBioB != null ? (
                      <span style={{ color: sBioA - sBioB > 0 ? "#f87171" : sBioA - sBioB < 0 ? "#34d399" : "#94a3b8", fontWeight: 600 }}>
                        {Math.round((sBioA - sBioB) * 100) / 100 > 0
                          ? `+${(Math.round((sBioA - sBioB) * 100) / 100).toFixed(1)} (Higher)`
                          : `${(Math.round((sBioA - sBioB) * 100) / 100).toFixed(1)} (Lower)`}
                      </span>
                    ) : "N/A"}
                  </td>
                </tr>

                <tr>
                  <td><strong>Asymmetry Factor (S_asym)</strong></td>
                  <td>{sAsymA != null ? `${Math.round(sAsymA * 100) / 100}` : "N/A"}</td>
                  <td>{sAsymB != null ? `${Math.round(sAsymB * 100) / 100}` : "N/A"}</td>
                  <td>
                    {sAsymA != null && sAsymB != null ? (
                      <span style={{ color: sAsymA - sAsymB > 0 ? "#f87171" : sAsymA - sAsymB < 0 ? "#34d399" : "#94a3b8", fontWeight: 600 }}>
                        {Math.round((sAsymA - sAsymB) * 100) / 100 > 0
                          ? `+${(Math.round((sAsymA - sAsymB) * 100) / 100).toFixed(1)}`
                          : `${(Math.round((sAsymA - sAsymB) * 100) / 100).toFixed(1)}`}
                      </span>
                    ) : "N/A"}
                  </td>
                </tr>

                <tr>
                  <td><strong>Fatigue Factor (S_fatigue)</strong></td>
                  <td>{sFatigueA != null ? `${Math.round(sFatigueA * 100) / 100}` : "N/A"}</td>
                  <td>{sFatigueB != null ? `${Math.round(sFatigueB * 100) / 100}` : "N/A"}</td>
                  <td>
                    {sFatigueA != null && sFatigueB != null ? (
                      <span style={{ color: sFatigueA - sFatigueB > 0 ? "#f87171" : sFatigueA - sFatigueB < 0 ? "#34d399" : "#94a3b8", fontWeight: 600 }}>
                        {Math.round((sFatigueA - sFatigueB) * 100) / 100 > 0
                          ? `+${(Math.round((sFatigueA - sFatigueB) * 100) / 100).toFixed(1)}`
                          : `${(Math.round((sFatigueA - sFatigueB) * 100) / 100).toFixed(1)}`}
                      </span>
                    ) : "N/A"}
                  </td>
                </tr>

                <tr>
                  <td><strong>Video Source</strong></td>
                  <td style={{ textOverflow: "ellipsis", overflow: "hidden", maxWidth: 140 }}>
                    {assessmentA.original_filename || "Current Video"}
                  </td>
                  <td style={{ textOverflow: "ellipsis", overflow: "hidden", maxWidth: 140 }}>
                    {b.original_filename || "Previous Video"}
                  </td>
                  <td>—</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: 8 }}>
          <button type="button" className="secondary-button" onClick={onClose} style={{ padding: "8px 20px", fontSize: "0.88rem" }}>
            Close Comparison
          </button>
        </div>
      </div>
    </div>
  );
}

export default AssessmentCompareModal;

