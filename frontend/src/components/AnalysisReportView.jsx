/**
 * AnalysisReportView.jsx
 * ─────────────────────
 * Pure presentational component — renders the full AI risk analysis report.
 * Accepts already-fetched data as props; NEVER triggers new analysis.
 *
 * Used by:
 *   - VideoAnalysis.jsx  (live result after upload + analyze)
 *   - AnalysisReport.jsx (historical read-only view via /analysis/:videoId)
 *
 * ─── DATA INTEGRITY ───────────────────────────────────────────────────────
 * All values rendered here come directly from the API response props.
 * No values are fabricated, hard-coded, or modified.
 * Risk thresholds, LESS logic, and model outputs are untouched.
 * ──────────────────────────────────────────────────────────────────────────
 */

import { useEffect, useRef, useState } from "react";
import {
    Activity,
    AlertTriangle,
    BarChart3,
    CheckCircle,
    CheckCircle2,
    FileVideo,
    ShieldAlert,
    ShieldCheck,
    Sliders,
    TrendingUp,
    Video,
    Zap,
    ChevronRight,
    ChevronDown,
    ChevronUp,
    Dumbbell,
    Flame,
    Target,
    HeartPulse,
    Clock,
    Sparkles,
    RotateCcw,
    AlertCircle,
    Info,
    Calendar,
    Moon,
    Droplets,
    Layers,
    ListChecks,
    Brain,
    Shield,
    Cpu,
    Wand2,
    ArrowRight,
    CircleDot,
} from "lucide-react";

import { getMediaBaseUrl, getAnalysisLandmarks } from "../api/videos";
import CorrectiveActionPlan from "./CorrectiveActionPlan";
import AIPoseVideoPlayer from "./AIPoseVideoPlayer";

// ── Colour helpers ─────────────────────────────────────────────────────────


function riskColor(level) {
    switch ((level || "").toUpperCase()) {
        case "LOW":      return "#16a34a";
        case "MODERATE": return "#d97706";
        case "HIGH":     return "#ea580c";
        case "CRITICAL": return "#dc2626";
        default:         return "#64748b";
    }
}

function riskBgColor(level) {
    switch ((level || "").toUpperCase()) {
        case "LOW":      return "#f0fdf4";
        case "MODERATE": return "#fffbeb";
        case "HIGH":     return "#fff7ed";
        case "CRITICAL": return "#fef2f2";
        default:         return "#f8fafc";
    }
}

function riskBorderColor(level) {
    switch ((level || "").toUpperCase()) {
        case "LOW":      return "#bbf7d0";
        case "MODERATE": return "#fde68a";
        case "HIGH":     return "#fed7aa";
        case "CRITICAL": return "#fecaca";
        default:         return "#e2e8f0";
    }
}

function riskBadgeClass(level) {
    switch ((level || "").toUpperCase()) {
        case "LOW":      return "risk-badge risk-badge--low";
        case "MODERATE": return "risk-badge risk-badge--moderate";
        case "HIGH":     return "risk-badge risk-badge--high";
        case "CRITICAL": return "risk-badge risk-badge--critical";
        default:         return "risk-badge risk-badge--unknown";
    }
}

function priorityBadgeClass(priority) {
    switch ((priority || "").toUpperCase()) {
        case "HIGH":   return "rec-priority-badge rec-priority-badge--high";
        case "MEDIUM": return "rec-priority-badge rec-priority-badge--medium";
        case "LOW":    return "rec-priority-badge rec-priority-badge--low";
        default:       return "rec-priority-badge";
    }
}

function categoryBadgeClass(category) {
    switch ((category || "").toLowerCase()) {
        case "strengthening":        return "rec-cat-badge rec-cat-badge--strength";
        case "mobility":             return "rec-cat-badge rec-cat-badge--mobility";
        case "exercise":             return "rec-cat-badge rec-cat-badge--exercise";
        case "recovery":             return "rec-cat-badge rec-cat-badge--recovery";
        case "training_modification": return "rec-cat-badge rec-cat-badge--mod";
        default:                     return "rec-cat-badge";
    }
}

function categoryIcon(category) {
    switch ((category || "").toLowerCase()) {
        case "strengthening":        return Dumbbell;
        case "mobility":             return RotateCcw;
        case "exercise":             return Activity;
        case "recovery":             return HeartPulse;
        case "training_modification": return Sliders;
        default:                     return Zap;
    }
}

function riskInterpretation(level) {
    switch ((level || "").toUpperCase()) {
        case "LOW":
            return "Biomechanical movement patterns are within normal ranges. No significant deviations detected.";
        case "MODERATE":
            return "Some biomechanical deviations observed. Movement patterns differ moderately from reference cohort. Consider targeted corrective exercises.";
        case "HIGH":
            return "Significant biomechanical deviations detected. Movement patterns show elevated differences from reference cohort. Corrective intervention recommended.";
        case "CRITICAL":
            return "Severe biomechanical deviations detected. Movement patterns are substantially outside normal ranges. Immediate professional assessment advised.";
        default:
            return "Risk level could not be determined from the available data.";
    }
}

function gaugeStrokeColor(score) {
    if (score == null) return "#94a3b8";
    if (score < 30)    return "#16a34a";
    if (score < 55)    return "#d97706";
    if (score < 75)    return "#ea580c";
    return "#dc2626";
}

// ── Formatting helpers ─────────────────────────────────────────────────────

function fmtDeg(val) { return val == null ? "—" : `${val.toFixed(1)}°`; }
function fmtPct(val) { return val == null ? "—" : `${val.toFixed(1)}%`; }
function fmtVal(val, unit) { return val == null ? "—" : `${val} ${unit}`; }
function fmtScore(val) { return val == null ? "—" : Number(val).toFixed(1); }

function formatDate(dt) {
    if (!dt) return "—";
    return new Date(dt).toLocaleString(undefined, {
        year: "numeric", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit",
    });
}

function formatDateShort(dt) {
    if (!dt) return "—";
    return new Date(dt).toLocaleDateString(undefined, {
        year: "numeric", month: "short", day: "numeric",
    });
}

// ── Animated gauge hook ─────────────────────────────────────────────────────

function useAnimatedValue(target, delay = 100) {
    const [value, setValue] = useState(0);
    useEffect(() => {
        const t = setTimeout(() => setValue(target ?? 0), delay);
        return () => clearTimeout(t);
    }, [target, delay]);
    return value;
}

// ── Sub-components ─────────────────────────────────────────────────────────

function RiskLevelIcon({ level }) {
    const l = (level || "").toUpperCase();
    if (l === "LOW")      return <ShieldCheck size={14} />;
    if (l === "MODERATE") return <AlertCircle size={14} />;
    if (l === "HIGH")     return <AlertTriangle size={14} />;
    if (l === "CRITICAL") return <ShieldAlert size={14} />;
    return <Activity size={14} />;
}

/** Premium section panel with accent icon */
function SectionPanel({ icon: Icon, iconBg, iconColor, title, subtitle, accentColor, children }) {
    return (
        <div className="arv2-section">
            <div className="arv2-section-header">
                <div className="arv2-section-header-left">
                    {Icon && (
                        <div
                            className="arv2-section-icon"
                            style={{ background: iconBg || "#f1f5f9", color: iconColor || "#64748b" }}
                        >
                            <Icon size={18} />
                        </div>
                    )}
                    <div>
                        <p className="arv2-section-title">{title}</p>
                        {subtitle && <p className="arv2-section-subtitle">{subtitle}</p>}
                    </div>
                </div>
            </div>
            {accentColor && (
                <div className="arv2-section-accent-bar" style={{ background: accentColor }} />
            )}
            <div className="arv2-section-body">{children}</div>
        </div>
    );
}

/** Bio metric card with optional accent color */
function BioCard({ label, value, sub, accentColor }) {
    return (
        <div className="arv2-bio-card" style={accentColor ? { borderLeftColor: accentColor, borderLeftWidth: 3 } : {}}>
            <div className="arv2-bio-label">{label}</div>
            <div className="arv2-bio-value">{value}</div>
            {sub && <div className="arv2-bio-sub">{sub}</div>}
        </div>
    );
}

/** Animated factor bar */
function FactorBar({ label, weight, score, available, sub }) {
    const animPct = useAnimatedValue(
        available && score != null ? Math.min(100, Math.max(0, Number(score))) : 0,
        200
    );
    const color = available ? gaugeStrokeColor(animPct) : "#cbd5e1";

    return (
        <div className="arv2-factor-row">
            <div className="arv2-factor-top">
                <span className="arv2-factor-name">{label}</span>
                <div className="arv2-factor-meta">
                    {!available ? (
                        <span className="arv2-factor-chip arv2-factor-chip--unavail">EXCLUDED</span>
                    ) : (
                        <span className="arv2-factor-chip arv2-factor-chip--avail">CALCULATED</span>
                    )}
                    <span className="arv2-factor-score" style={{ color: available ? color : "#94a3b8" }}>
                        {available && score != null ? fmtScore(score) : "N/A"}
                    </span>
                    <span className="arv2-factor-weight">×{weight}</span>
                </div>
            </div>
            <div className="arv2-factor-track">
                <div
                    className="arv2-factor-fill"
                    style={{
                        width: `${animPct}%`,
                        background: color,
                    }}
                />
            </div>
            {sub && <span className="arv2-factor-sub">{sub}</span>}
        </div>
    );
}

/** LESS dot matrix visualization */
function LessDotMatrix({ score, max }) {
    const filled = typeof score === "number" ? Math.max(0, Math.min(score, max || 12)) : 0;
    const total  = max || 12;
    return (
        <div className="arv2-less-dots">
            {Array.from({ length: total }).map((_, i) => (
                <span
                    key={i}
                    className={`arv2-less-dot ${i < filled ? "arv2-less-dot--filled" : ""}`}
                />
            ))}
        </div>
    );
}

/** LESS item row (visual list instead of dense table) */
function LessItemRow({ item, index }) {
    const s = (item.status || "").toUpperCase();
    let statusIcon, statusColor, statusBg;
    if (s === "PASS") {
        statusIcon = <CheckCircle2 size={14} />;
        statusColor = "#15803d";
        statusBg = "#f0fdf4";
    } else if (s === "ERROR") {
        statusIcon = <AlertTriangle size={14} />;
        statusColor = "#b91c1c";
        statusBg = "#fef2f2";
    } else {
        statusIcon = <Info size={14} />;
        statusColor = "#64748b";
        statusBg = "#f8fafc";
    }

    const measuredDisplay =
        item.reason
            ? <span style={{ fontStyle: "italic", color: "#94a3b8" }}>{item.reason}</span>
            : item.measured_value != null
                ? `${typeof item.measured_value === "number" ? item.measured_value.toFixed(1) : item.measured_value}${item.unit ? ` ${item.unit}` : ""}`
                : "—";

    return (
        <div className={`arv2-less-item ${index % 2 === 0 ? "arv2-less-item--even" : ""}`}>
            <span className="arv2-less-item-num">{item.item_number}</span>
            <span className="arv2-less-item-name">{item.item_name}</span>
            <span
                className="arv2-less-item-status"
                style={{ color: statusColor, background: statusBg }}
            >
                {statusIcon}
                {item.status || "NC"}
            </span>
            <span className="arv2-less-item-score">
                {item.score !== null && item.score !== undefined ? item.score : "—"}
            </span>
            <span className="arv2-less-item-measured">{measuredDisplay}</span>
            <span className="arv2-less-item-ref">{item.reference || "—"}</span>
        </div>
    );
}

/** Metric chip for the hero metrics strip */
function MetricChip({ label, value, sub, accentColor, icon: Icon }) {
    return (
        <div className="arv2-metric-chip" style={{ borderTopColor: accentColor || "#6366f1" }}>
            {Icon && (
                <div className="arv2-metric-chip-icon" style={{ color: accentColor || "#6366f1" }}>
                    <Icon size={14} />
                </div>
            )}
            <div className="arv2-metric-chip-value" style={{ color: accentColor || "#0f172a" }}>
                {value}
            </div>
            <div className="arv2-metric-chip-label">{label}</div>
            {sub && <div className="arv2-metric-chip-sub">{sub}</div>}
        </div>
    );
}

/** Assessment timeline step indicator */
function AssessmentTimeline() {
    const steps = [
        { label: "Video Uploaded",       icon: FileVideo,    done: true },
        { label: "Pose Detected",         icon: Cpu,          done: true },
        { label: "Biomechanics Analyzed", icon: BarChart3,    done: true },
        { label: "Risk Calculated",       icon: Brain,        done: true },
    ];

    return (
        <div className="arv2-timeline">
            {steps.map((step, i) => {
                const Icon = step.icon;
                return (
                    <div key={step.label} className="arv2-timeline-step">
                        <div className="arv2-timeline-step-inner">
                            <div className={`arv2-timeline-icon ${step.done ? "arv2-timeline-icon--done" : ""}`}>
                                <Icon size={14} />
                            </div>
                            <span className="arv2-timeline-label">{step.label}</span>
                        </div>
                        {i < steps.length - 1 && (
                            <div className="arv2-timeline-connector">
                                <ArrowRight size={12} />
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

// ── Main component ─────────────────────────────────────────────────────────

export default function AnalysisReportView({
    videoUrl,
    mediaBase,
    filename,
    analysisStatus,
    features,
    less,
    recommendations,
    landmarks,
    analysisFeatures,
    analysisLess,
    uploadedVideo,
    videoSrc: customVideoSrc,
}) {
    const resolvedMediaBase       = mediaBase || getMediaBaseUrl();
    const resolvedVideoUrl        = videoUrl || uploadedVideo?.video_url || analysisStatus?.video_url;
    const resolvedFilename        = filename || uploadedVideo?.original_filename || analysisStatus?.original_filename;
    const resolvedFeatures        = features || analysisFeatures;
    const resolvedLess            = less || analysisLess;
    const resolvedRecommendations = recommendations || analysisStatus?.recommendations;

    // Collapsible LESS details state (collapsed by default)
    const [showLessDetails, setShowLessDetails] = useState(false);

    // AI Pose Landmarks State (strictly scoped to the exact analysis_id)
    const [landmarksData, setLandmarksData] = useState(landmarks || null);
    const [loadingLandmarks, setLoadingLandmarks] = useState(false);

    useEffect(() => {
        if (landmarks) {
            setLandmarksData(landmarks);
            return;
        }

        const videoId = analysisStatus?.video_id || uploadedVideo?.video_id;
        const analysisId = analysisStatus?.analysis_id;

        if (!videoId || !analysisId) return;

        let cancelled = false;
        async function fetchLandmarks() {
            setLoadingLandmarks(true);
            try {
                const data = await getAnalysisLandmarks(videoId, analysisId);
                if (!cancelled) {
                    setLandmarksData(data);
                }
            } catch {
                if (!cancelled) {
                    setLandmarksData(null);
                }
            } finally {
                if (!cancelled) {
                    setLoadingLandmarks(false);
                }
            }
        }

        fetchLandmarks();
        return () => { cancelled = true; };
    }, [landmarks, analysisStatus?.video_id, analysisStatus?.analysis_id, uploadedVideo?.video_id]);


    const score       = analysisStatus?.overall_risk_score;
    const level       = analysisStatus?.risk_level;
    const color       = gaugeStrokeColor(score);
    const completedAt = analysisStatus?.completed_at || analysisStatus?.created_at;

    // Animated gauge
    const R          = 60;
    const CIRC       = 2 * Math.PI * R;
    const animScore  = useAnimatedValue(score, 150);
    const pct        = animScore != null ? Math.min(100, Math.max(0, animScore)) / 100 : 0;
    const dashFill   = pct * CIRC;

    // Derive video src
    const videoSrc = customVideoSrc || (resolvedVideoUrl ? `${resolvedMediaBase}${resolvedVideoUrl}` : null);

    const disclaimer =
        analysisStatus?.disclaimer ||
        analysisStatus?.risk_breakdown?.model_framing ||
        "This overall risk score is based on a Biomechanical Deviation Classifier that quantifies movement pattern differences relative to clinical cohorts. It measures current biomechanical deviation and movement quality — NOT future injury probability or prospective clinical diagnosis. This is a screening heuristic and not a medical assessment.";

    const displayName = resolvedFilename || analysisStatus?.title || "Video Analysis";

    return (
        <>
            {/* ─────────────────────────────────────────────────────────────
                A. REPORT HEADER — Light gradient with AI badge
                ───────────────────────────────────────────────────────────── */}
            <div className="arv2-header">
                {/* Decorative background dots */}
                <div className="arv2-header-pattern" aria-hidden="true" />

                <div className="arv2-header-body">
                    {/* Left: metadata */}
                    <div className="arv2-header-left">
                        <div className="arv2-header-eyebrow-row">
                            <span className="arv2-header-eyebrow">AI Risk Analysis Report</span>
                            <span className="arv2-ai-badge">
                                <Sparkles size={10} />
                                AI-POWERED ANALYSIS
                            </span>
                        </div>

                        <h2 className="arv2-header-title">{displayName}</h2>

                        <div className="arv2-header-meta-row">
                            <span className="arv2-header-meta-item">
                                <Calendar size={12} />
                                {formatDate(completedAt)}
                            </span>
                            {resolvedFilename && resolvedFilename !== displayName && (
                                <span className="arv2-header-meta-item">
                                    <FileVideo size={12} />
                                    {resolvedFilename}
                                </span>
                            )}
                            <span
                                className="arv2-header-status-chip"
                                style={{
                                    background: "#dcfce7",
                                    color: "#15803d",
                                    borderColor: "#bbf7d0",
                                }}
                            >
                                <CheckCircle2 size={11} />
                                Analysis Complete
                            </span>
                        </div>
                    </div>

                    {/* Right: risk level badge */}
                    <div className="arv2-header-right">
                        <div
                            className="arv2-header-risk-badge"
                            style={{
                                background: riskBgColor(level),
                                borderColor: riskBorderColor(level),
                                color: riskColor(level),
                            }}
                        >
                            <RiskLevelIcon level={level} />
                            <span className="arv2-header-risk-label">{level || "Unknown"}</span>
                            <span className="arv2-header-risk-sub">Risk Level</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* ─────────────────────────────────────────────────────────────
                TIMELINE — Assessment pipeline steps
                ───────────────────────────────────────────────────────────── */}
            <AssessmentTimeline />

            {/* ─────────────────────────────────────────────────────────────
                B. ASSESSMENT RESULT — Two-Column Layout: Risk Score (LEFT) | Video (RIGHT)
                ───────────────────────────────────────────────────────────── */}
            <div className="arv2-assessment-grid">
                {/* LEFT: Risk Score & Key Metrics */}
                {typeof score === "number" && !isNaN(score) && (
                    <div className="arv2-hero-card">
                        {/* Left: Gauge */}
                        <div className="arv2-hero-gauge-col">
                            <div className="arv2-gauge-ring" aria-label={`Risk score: ${score.toFixed(0)} out of 100`}>
                                <svg width="150" height="150" viewBox="0 0 150 150">
                                    {/* Track */}
                                    <circle cx="75" cy="75" r={R} fill="none" stroke="#f1f5f9" strokeWidth="12" />
                                    {/* Glow ring */}
                                    <circle
                                        cx="75" cy="75" r={R}
                                        fill="none"
                                        stroke={color}
                                        strokeWidth="12"
                                        strokeOpacity="0.15"
                                        strokeDasharray={`${CIRC} ${CIRC}`}
                                    />
                                    {/* Fill */}
                                    <circle
                                        cx="75" cy="75" r={R}
                                        fill="none"
                                        stroke={color}
                                        strokeWidth="12"
                                        strokeDasharray={`${dashFill} ${CIRC}`}
                                        strokeLinecap="round"
                                        style={{ transition: "stroke-dasharray 1.2s cubic-bezier(0.4,0,0.2,1)" }}
                                    />
                                </svg>
                                <div className="arv2-gauge-inner">
                                    <span className="arv2-gauge-number" style={{ color }}>
                                        {score.toFixed(0)}
                                    </span>
                                    <span className="arv2-gauge-denom">/100</span>
                                    <span className="arv2-gauge-sub">RISK SCORE</span>
                                </div>
                            </div>

                            {/* Risk level pill below gauge */}
                            <div
                                className="arv2-gauge-level-pill"
                                style={{
                                    background: riskBgColor(level),
                                    color: riskColor(level),
                                    borderColor: riskBorderColor(level),
                                }}
                            >
                                <RiskLevelIcon level={level} />
                                {level || "Unknown"} Risk
                            </div>
                        </div>

                        {/* Right: interpretation + threshold bar + metric chips */}
                        <div className="arv2-hero-detail-col">
                            <div className="arv2-hero-interpretation">
                                <p className="arv2-hero-interp-text">{riskInterpretation(level)}</p>
                                <span className="arv2-hero-engine-tag">
                                    <Cpu size={11} /> 5-Factor Weighted Risk Engine
                                </span>
                            </div>

                            {/* Threshold bar */}
                            <div className="arv2-threshold-bar-wrap">
                                <div className="arv2-threshold-track">
                                    <div
                                        className="arv2-threshold-fill"
                                        style={{ width: `${pct * 100}%`, background: color }}
                                    />
                                    {/* Threshold markers */}
                                    <span className="arv2-threshold-mark" style={{ left: "30%" }} />
                                    <span className="arv2-threshold-mark" style={{ left: "55%" }} />
                                    <span className="arv2-threshold-mark" style={{ left: "75%" }} />
                                </div>
                                <div className="arv2-threshold-labels">
                                    <span style={{ color: "#16a34a" }}>Low</span>
                                    <span style={{ color: "#d97706" }}>Moderate</span>
                                    <span style={{ color: "#ea580c" }}>High</span>
                                    <span style={{ color: "#dc2626" }}>Critical</span>
                                </div>
                            </div>

                            {/* Key metrics strip */}
                            <div className="arv2-metrics-strip">
                                <MetricChip
                                    label="Overall Risk"
                                    value={score.toFixed(0)}
                                    sub="out of 100"
                                    accentColor={color}
                                    icon={Activity}
                                />
                                {resolvedLess && resolvedLess.score != null && (
                                    <MetricChip
                                        label="LESS Score"
                                        value={`${resolvedLess.score}/${resolvedLess.max_computable_score || 12}`}
                                        sub="lower = better"
                                        accentColor="#0891b2"
                                        icon={ShieldAlert}
                                    />
                                )}
                                {resolvedFeatures?.features?.total_frames != null && (
                                    <MetricChip
                                        label="Frames"
                                        value={resolvedFeatures.features.total_frames}
                                        sub="analyzed"
                                        accentColor="#7c3aed"
                                        icon={Layers}
                                    />
                                )}
                                {(() => {
                                    const totalActionItems =
                                        resolvedRecommendations?.total_recommendations ??
                                        ((Array.isArray(resolvedRecommendations?.exercise_recommendations) ? resolvedRecommendations.exercise_recommendations.length : 0) +
                                        (Array.isArray(resolvedRecommendations?.mobility_recommendations) ? resolvedRecommendations.mobility_recommendations.length : 0) +
                                        (Array.isArray(resolvedRecommendations?.strengthening_recommendations) ? resolvedRecommendations.strengthening_recommendations.length : 0) +
                                        (Array.isArray(resolvedRecommendations?.recommendations) ? resolvedRecommendations.recommendations.length : 0) +
                                        (Array.isArray(resolvedRecommendations?.recovery_plan) ? resolvedRecommendations.recovery_plan.length : 0) +
                                        (Array.isArray(resolvedRecommendations?.training_modifications) ? resolvedRecommendations.training_modifications.length : 0) +
                                        (Array.isArray(resolvedRecommendations) ? resolvedRecommendations.length : 0));

                                    return totalActionItems > 0 ? (
                                        <MetricChip
                                            label="Action Items"
                                            value={totalActionItems}
                                            sub="corrective drills"
                                            accentColor="#2563eb"
                                            icon={Target}
                                        />
                                    ) : null;
                                })()}
                            </div>
                        </div>
                    </div>
                )}

                {/* RIGHT: Assessment Video Player with Synchronized AI Pose Skeleton Overlay */}
                <div className="arv2-video-section">
                    <AIPoseVideoPlayer
                        videoUrl={resolvedVideoUrl}
                        mediaBase={resolvedMediaBase}
                        filename={resolvedFilename}
                        landmarksData={landmarksData}
                        loadingLandmarks={loadingLandmarks}
                        title="AI Pose Visualization"
                        subtitle="Visual representation of detected body landmarks during the assessment"
                    />
                </div>
            </div>


            {/* ─────────────────────────────────────────────────────────────
                C. 5-FACTOR RISK BREAKDOWN
                ───────────────────────────────────────────────────────────── */}
            {(analysisStatus?.s_bio != null || analysisStatus?.risk_breakdown) && (
                <SectionPanel
                    icon={Zap}
                    iconBg="#faf5ff"
                    iconColor="#7c3aed"
                    title="5-Factor Weighted Risk Breakdown"
                    subtitle="Biomechanical Deviation Model · Kinematic RF v2 Classifier"
                    accentColor="#7c3aed"
                >
                    <div className="arv2-factor-list">
                        <FactorBar
                            label="Biomechanical Deviations"
                            weight="35%"
                            score={analysisStatus.s_bio ?? analysisStatus.risk_breakdown?.s_bio}
                            available={analysisStatus.s_bio_available ?? analysisStatus.risk_breakdown?.s_bio_available ?? true}
                            sub={(analysisStatus.s_bio_available ?? analysisStatus.risk_breakdown?.s_bio_available ?? true) ? "Kinematic RF v2 classifier score based on video joint angles & motion" : "Biomechanical ML score unavailable — insufficient valid kinematic features"}
                        />
                        <FactorBar
                            label="Historical Injury Factors"
                            weight="20%"
                            score={analysisStatus.s_hist ?? analysisStatus.risk_breakdown?.s_hist}
                            available={analysisStatus.s_hist_available ?? analysisStatus.risk_breakdown?.s_hist_available ?? (analysisStatus.s_hist != null)}
                            sub={(analysisStatus.s_hist_available ?? analysisStatus.risk_breakdown?.s_hist_available) ? "Derived from athlete injury history records" : "Injury history unavailable — dynamically excluded"}
                        />
                        <FactorBar
                            label="Movement Asymmetry"
                            weight="20%"
                            score={analysisStatus.s_asym ?? analysisStatus.risk_breakdown?.s_asym}
                            available={analysisStatus.s_asym_available ?? analysisStatus.risk_breakdown?.s_asym_available ?? true}
                            sub="Left / Right knee, hip & ankle symmetry delta"
                        />
                        <FactorBar
                            label="Training Load"
                            weight="15%"
                            score={analysisStatus.s_load ?? analysisStatus.risk_breakdown?.s_load}
                            available={analysisStatus.s_load_available ?? analysisStatus.risk_breakdown?.s_load_available ?? false}
                            sub={(analysisStatus.s_load_available ?? analysisStatus.risk_breakdown?.s_load_available) ? "Derived workload index (sessions × duration × RPE)" : "Training load unavailable — dynamically excluded"}
                        />
                        <FactorBar
                            label="Fatigue Level"
                            weight="10%"
                            score={analysisStatus.s_fatigue ?? analysisStatus.risk_breakdown?.s_fatigue}
                            available={analysisStatus.s_fatigue_available ?? analysisStatus.risk_breakdown?.s_fatigue_available ?? false}
                            sub={(analysisStatus.s_fatigue_available ?? analysisStatus.risk_breakdown?.s_fatigue_available) ? "Derived from self-reported fatigue indicator scale (1–10)" : "Fatigue data unavailable — dynamically excluded"}
                        />
                    </div>
                </SectionPanel>
            )}

            {/* ─────────────────────────────────────────────────────────────
                D. BIOMECHANICAL ANALYSIS
                ───────────────────────────────────────────────────────────── */}
            {resolvedFeatures?.features && (
                <SectionPanel
                    icon={Sliders}
                    iconBg="#eff6ff"
                    iconColor="#3b82f6"
                    title="Biomechanical Analysis"
                    subtitle={`MediaPipe BlazePose · 33 landmarks · Schema ${resolvedFeatures.feature_version}`}
                    accentColor="#3b82f6"
                >
                    {/* Joint Angles group */}
                    <p className="arv2-bio-group-label">Joint Angles (Mean / ROM)</p>
                    <div className="arv2-bio-grid">
                        <BioCard label="Knee Angle (L)" value={fmtDeg(resolvedFeatures.features.knee_angle_left_mean)}  sub={`ROM ${fmtDeg(resolvedFeatures.features.knee_angle_left_rom)}`}  accentColor="#0891b2" />
                        <BioCard label="Knee Angle (R)" value={fmtDeg(resolvedFeatures.features.knee_angle_right_mean)} sub={`ROM ${fmtDeg(resolvedFeatures.features.knee_angle_right_rom)}`} accentColor="#0891b2" />
                        <BioCard label="Hip Angle (L)"  value={fmtDeg(resolvedFeatures.features.hip_angle_left_mean)}   sub={`ROM ${fmtDeg(resolvedFeatures.features.hip_angle_left_rom)}`}  accentColor="#7c3aed" />
                        <BioCard label="Hip Angle (R)"  value={fmtDeg(resolvedFeatures.features.hip_angle_right_mean)}  sub={`ROM ${fmtDeg(resolvedFeatures.features.hip_angle_right_rom)}`} accentColor="#7c3aed" />
                        <BioCard label="Ankle Angle (L)" value={fmtDeg(resolvedFeatures.features.ankle_angle_left_mean)} sub={`ROM ${fmtDeg(resolvedFeatures.features.ankle_angle_left_rom)}`} accentColor="#059669" />
                        <BioCard label="Ankle Angle (R)" value={fmtDeg(resolvedFeatures.features.ankle_angle_right_mean)} sub={`ROM ${fmtDeg(resolvedFeatures.features.ankle_angle_right_rom)}`} accentColor="#059669" />
                        <BioCard label="Trunk Lean"     value={fmtDeg(resolvedFeatures.features.trunk_angle_mean)}      sub={`Max ${fmtDeg(resolvedFeatures.features.trunk_angle_max)}`}      accentColor="#d97706" />
                    </div>

                    {/* Symmetry & Kinematics group */}
                    <p className="arv2-bio-group-label" style={{ marginTop: 24 }}>L/R Symmetry & Kinematics</p>
                    <div className="arv2-bio-grid">
                        <BioCard label="Knee Symmetry"    value={fmtPct(resolvedFeatures.features.knee_symmetry_score)}  sub="L vs R ROM" accentColor="#0891b2" />
                        <BioCard label="Hip Symmetry"     value={fmtPct(resolvedFeatures.features.hip_symmetry_score)}   sub="L vs R ROM" accentColor="#7c3aed" />
                        <BioCard label="Ankle Symmetry"   value={fmtPct(resolvedFeatures.features.ankle_symmetry_score)} sub="L vs R ROM" accentColor="#059669" />
                        <BioCard label="3D Displacement"  value={fmtVal(resolvedFeatures.features.total_joint_displacement, "n.u.")} sub="Mid-hip travel" accentColor="#2563eb" />
                        <BioCard label="Max Velocity"     value={fmtVal(resolvedFeatures.features.max_joint_velocity, "u/s")}  sub="Peak mid-hip speed" accentColor="#ea580c" />
                        <BioCard label="Mean Velocity"    value={fmtVal(resolvedFeatures.features.mean_joint_velocity, "u/s")} sub="Avg mid-hip speed"  accentColor="#d97706" />
                    </div>
                </SectionPanel>
            )}

            {/* ─────────────────────────────────────────────────────────────
                E. LESS ASSESSMENT — Dot-matrix + visual item list
                ───────────────────────────────────────────────────────────── */}
            {resolvedLess && (
                <SectionPanel
                    icon={ShieldAlert}
                    iconBg="#f0fdf4"
                    iconColor="#16a34a"
                    title="Rule-Based Movement Quality Assessment (LESS)"
                    subtitle={`Padua et al. 2009 Jump-Landing Protocol · Approximation Heuristic · v${resolvedLess.source_version}`}
                    accentColor="#16a34a"
                >
                    {/* LESS Score Overview */}
                    <div className="arv2-less-overview">
                        {/* Big score display */}
                        <div className="arv2-less-score-block">
                            <div className="arv2-less-score-number">
                                <span className="arv2-less-score-val">{resolvedLess.score}</span>
                                <span className="arv2-less-score-max">/{resolvedLess.max_computable_score || 12}</span>
                            </div>
                            <div className="arv2-less-score-label">LESS Score</div>
                            <div className="arv2-less-score-hint">lower score = better movement quality</div>
                            <LessDotMatrix score={resolvedLess.score} max={resolvedLess.max_computable_score || 12} />
                        </div>

                        {/* Stats column */}
                        <div className="arv2-less-stats-col">
                            <div className="arv2-less-stat-card">
                                <span className="arv2-less-stat-label">Classification</span>
                                <span
                                    className="arv2-less-stat-value"
                                    style={{
                                        color: (resolvedLess.classification || "").toUpperCase().includes("ELEVATED") ? "#b91c1c" : "#15803d",
                                        fontSize: 15,
                                        fontWeight: 700,
                                    }}
                                >
                                    {(resolvedLess.classification || "").toUpperCase().includes("ELEVATED") ? "Elevated Risk" : "Lower Risk"}
                                </span>
                                <span className="arv2-less-stat-sub">Approximation heuristic</span>
                            </div>
                            <div className="arv2-less-stat-card">
                                <span className="arv2-less-stat-label">Item Coverage</span>
                                <span className="arv2-less-stat-value">{resolvedLess.computable_items} / 17</span>
                                <span className="arv2-less-stat-sub">
                                    {resolvedLess.error_items} errors · {resolvedLess.not_computable_items} skipped
                                </span>
                            </div>
                        </div>
                    </div>

                    {/* LESS disclaimer */}
                    <div className="arv2-less-disclaimer">
                        <Info size={14} />
                        <p>{resolvedLess.disclaimer}</p>
                    </div>

                    {/* LESS detailed items toggle button */}
                    {resolvedLess.items?.length > 0 && (
                        <div className="arv2-less-toggle-wrap">
                            <button
                                type="button"
                                className={`arv2-less-toggle-btn ${showLessDetails ? "arv2-less-toggle-btn--active" : ""}`}
                                onClick={() => setShowLessDetails((prev) => !prev)}
                                aria-expanded={showLessDetails}
                                aria-controls="less-detailed-assessment-table"
                                id="less-details-toggle-btn"
                            >
                                <span className="arv2-less-toggle-btn-left">
                                    {showLessDetails ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                                    <span className="arv2-less-toggle-label">
                                        {showLessDetails
                                            ? "Hide Detailed LESS Assessment"
                                            : "View Detailed LESS Assessment"}
                                    </span>
                                </span>
                                <span className="arv2-less-toggle-badge">
                                    {resolvedLess.items.length} criteria items
                                </span>
                            </button>
                        </div>
                    )}

                    {/* LESS detailed item list (collapsible accordion) */}
                    {showLessDetails && resolvedLess.items?.length > 0 && (
                        <div
                            className="arv2-less-items-wrapper"
                            id="less-detailed-assessment-table"
                            role="region"
                            aria-labelledby="less-details-toggle-btn"
                        >
                            <div className="arv2-less-items">
                                {/* Header row */}
                                <div className="arv2-less-items-header">
                                    <span>#</span>
                                    <span>Item</span>
                                    <span>Status</span>
                                    <span>Score</span>
                                    <span>Measured</span>
                                    <span>Reference</span>
                                </div>
                                {resolvedLess.items.map((item, idx) => (
                                    <LessItemRow key={item.item_number} item={item} index={idx} />
                                ))}
                            </div>
                        </div>
                    )}
                </SectionPanel>
            )}

            {/* ─────────────────────────────────────────────────────────────
                F. CORRECTIVE ACTION PLAN
                ───────────────────────────────────────────────────────────── */}
            {resolvedRecommendations && (
                <SectionPanel
                    icon={Sparkles}
                    iconBg="#eff6ff"
                    iconColor="#2563eb"
                    title="Corrective Action Plan"
                    subtitle="Deterministic, rule-based corrective recommendations generated from biomechanical findings"
                    accentColor="#2563eb"
                >
                    <CorrectiveActionPlan recommendations={resolvedRecommendations} />
                </SectionPanel>
            )}

            {/* ─────────────────────────────────────────────────────────────
                G. DISCLAIMER — Subtle professional info box
                ───────────────────────────────────────────────────────────── */}
            <div className="arv2-disclaimer">
                <div className="arv2-disclaimer-icon">
                    <Shield size={16} />
                </div>
                <div className="arv2-disclaimer-body">
                    <p className="arv2-disclaimer-title">Non-Medical Screening Disclaimer</p>
                    <p className="arv2-disclaimer-text">{disclaimer}</p>
                    <p className="arv2-disclaimer-text" style={{ marginTop: 6 }}>
                        This AI analysis is intended for informational and sports-performance support purposes only and is <strong>not a medical diagnosis</strong>. Consult a qualified healthcare or sports medicine professional for clinical guidance.
                    </p>
                </div>
            </div>
        </>
    );
}
