import React, { useState } from "react";
import {
    Activity,
    AlertTriangle,
    CheckCircle,
    CheckCircle2,
    ChevronDown,
    ChevronUp,
    ChevronRight,
    Clock,
    Dumbbell,
    HeartPulse,
    Info,
    RotateCcw,
    ShieldAlert,
    ShieldCheck,
    Sliders,
    Sparkles,
    Target,
    Zap,
    Calendar,
    Flame,
    FileText,
} from "lucide-react";

/**
 * Format raw snake_case or identifier into clean Title Case
 */
function formatLabel(str) {
    if (!str) return "";
    return str
        .replace(/[_-]/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Priority badge visual styles
 */
function PriorityBadge({ priority }) {
    const p = (priority || "medium").toLowerCase();
    if (p === "high" || p === "critical") {
        return (
            <span className="rec-badge rec-badge--high">
                <AlertTriangle size={11} />
                HIGH PRIORITY
            </span>
        );
    }
    if (p === "medium" || p === "moderate") {
        return (
            <span className="rec-badge rec-badge--medium">
                <Clock size={11} />
                MEDIUM PRIORITY
            </span>
        );
    }
    return (
        <span className="rec-badge rec-badge--low">
            <CheckCircle size={11} />
            LOW PRIORITY
        </span>
    );
}

/**
 * Category badge styles & icons
 */
function CategoryBadge({ category }) {
    const cat = (category || "exercise").toLowerCase();
    let badgeClass = "rec-cat-badge rec-cat-badge--exercise";
    let label = "EXERCISE";

    if (cat === "mobility") {
        badgeClass = "rec-cat-badge rec-cat-badge--mobility";
        label = "MOBILITY";
    } else if (cat === "strengthening" || cat === "strength") {
        badgeClass = "rec-cat-badge rec-cat-badge--strength";
        label = "STRENGTHENING";
    } else if (cat === "recovery") {
        badgeClass = "rec-cat-badge rec-cat-badge--recovery";
        label = "RECOVERY";
    } else if (cat === "training_modification" || cat === "modification") {
        badgeClass = "rec-cat-badge rec-cat-badge--mod";
        label = "TRAINING MOD";
    }

    return <span className={badgeClass}>{label}</span>;
}

function CategoryIcon({ category, size = 18 }) {
    const cat = (category || "exercise").toLowerCase();
    if (cat === "mobility") return <RotateCcw size={size} />;
    if (cat === "strengthening" || cat === "strength") return <Dumbbell size={size} />;
    if (cat === "recovery") return <HeartPulse size={size} />;
    if (cat === "training_modification" || cat === "modification") return <Sliders size={size} />;
    return <Activity size={size} />;
}

/**
 * Individual Recommendation Card with Expand/Collapse support
 */
function RecommendationCard({ rec, isExpanded, onToggle }) {
    const priority = (rec.priority || "medium").toLowerCase();
    const borderClass =
        priority === "high" || priority === "critical"
            ? "rec-card--high"
            : priority === "medium" || priority === "moderate"
            ? "rec-card--medium"
            : "rec-card--low";

    // Exercises array normalization
    const exerciseList = Array.isArray(rec.exercises)
        ? rec.exercises
        : Array.isArray(rec.suggested_exercises)
        ? rec.suggested_exercises
        : rec.exercises
        ? [rec.exercises]
        : [];

    return (
        <div className={`rec-card ${borderClass} ${isExpanded ? "rec-card--expanded" : "rec-card--collapsed"}`}>
            {/* Clickable Card Header */}
            <div
                className="rec-card-header rec-card-header--interactive"
                onClick={onToggle}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        onToggle();
                    }
                }}
                aria-expanded={isExpanded}
            >
                <div className="rec-card-title-group">
                    <div className={`rec-card-icon rec-card-icon--${rec.category || "exercise"}`}>
                        <CategoryIcon category={rec.category} />
                    </div>
                    <div>
                        <h4 className="rec-card-title">{rec.title}</h4>
                        <div className="rec-card-badges">
                            <CategoryBadge category={rec.category} />
                            <PriorityBadge priority={rec.priority} />
                            {rec.issue && (
                                <span className="rec-issue-sub-chip">
                                    Issue: <strong>{formatLabel(rec.issue)}</strong>
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <div className="rec-card-toggle-btn" aria-hidden="true">
                    <span className="rec-toggle-label">{isExpanded ? "Hide Details" : "View Details"}</span>
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </div>
            </div>

            {/* Collapsible Card Body */}
            {isExpanded && (
                <div className="rec-card-body">
                    {/* Traceability / Biomechanical Evidence */}
                    {(rec.evidence || rec.issue || rec.reason) && (
                        <div className="rec-traceability-box">
                            {rec.issue && (
                                <div className="rec-trace-item">
                                    <span className="rec-trace-label">
                                        <AlertTriangle size={13} className="rec-trace-icon" /> Identified Issue:
                                    </span>
                                    <span className="rec-trace-val">{formatLabel(rec.issue)}</span>
                                </div>
                            )}
                            {rec.evidence && (
                                <div className="rec-trace-item">
                                    <span className="rec-trace-label">
                                        <Activity size={13} className="rec-trace-icon" /> Biomechanical Evidence:
                                    </span>
                                    <span className="rec-trace-val rec-trace-evidence">{rec.evidence}</span>
                                </div>
                            )}
                            {rec.reason && rec.reason !== rec.why && (
                                <div className="rec-trace-item">
                                    <span className="rec-trace-label">
                                        <Info size={13} className="rec-trace-icon" /> Rationale:
                                    </span>
                                    <span className="rec-trace-val">{rec.reason}</span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Why this was recommended */}
                    {(rec.why || rec.description) && (
                        <div className="rec-section-block">
                            <span className="rec-section-subtitle">
                                <Info size={13} /> Why this was recommended
                            </span>
                            <p className="rec-description">{rec.why || rec.description}</p>
                        </div>
                    )}

                    {/* Recommended Exercises List */}
                    {exerciseList.length > 0 && (
                        <div className="rec-exercises-section">
                            <span className="rec-section-subtitle">
                                <Dumbbell size={13} /> Recommended Exercises & Drills
                            </span>
                            <ul className="rec-exercise-items">
                                {exerciseList.map((exercise, idx) => (
                                    <li key={idx} className="rec-exercise-item">
                                        <div className="rec-bullet-wrap">
                                            <ChevronRight size={13} className="rec-bullet-icon" />
                                        </div>
                                        <span className="rec-exercise-text">{exercise}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Prescription: Frequency & Duration */}
                    {(rec.frequency || rec.duration) && (
                        <div className="rec-card-meta-grid">
                            {rec.frequency && (
                                <div className="rec-meta-cell">
                                    <span className="rec-meta-cell-label">
                                        <Calendar size={12} /> Recommended Frequency
                                    </span>
                                    <span className="rec-meta-cell-val">{rec.frequency}</span>
                                </div>
                            )}
                            {rec.duration && (
                                <div className="rec-meta-cell">
                                    <span className="rec-meta-cell-label">
                                        <Clock size={12} /> Session Duration
                                    </span>
                                    <span className="rec-meta-cell-val">{rec.duration}</span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Safety and Execution Note */}
                    {(rec.safety_note || rec.safety_notes) && (
                        <div className="rec-safety-note">
                            <ShieldAlert size={15} className="rec-safety-icon" />
                            <div className="rec-safety-content">
                                <span className="rec-safety-title">Safety & Execution Note:</span>
                                <span className="rec-safety-text">{rec.safety_note || rec.safety_notes}</span>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

/**
 * Recovery Protocol Item Card
 */
function RecoveryItemCard({ item }) {
    const guidelines = Array.isArray(item.guidelines) ? item.guidelines : [];
    return (
        <div className="rec-aux-item-card">
            <div className="rec-aux-item-header">
                <div className="rec-aux-item-title-row">
                    <HeartPulse size={16} className="rec-aux-icon--recovery" />
                    <div>
                        <h5 className="rec-aux-item-title">{item.title}</h5>
                        {item.focus && <span className="rec-aux-item-sub">Focus: {item.focus}</span>}
                    </div>
                </div>
                {item.priority && <PriorityBadge priority={item.priority} />}
            </div>

            {item.recommendation && (
                <p className="rec-aux-item-desc">{item.recommendation}</p>
            )}

            {guidelines.length > 0 && (
                <ul className="rec-aux-guidelines">
                    {guidelines.map((g, i) => (
                        <li key={i} className="rec-aux-guideline-item">
                            <CheckCircle2 size={13} className="rec-guideline-icon" />
                            <span>{g}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

/**
 * Training Modification Item Card
 */
function TrainingModItemCard({ item }) {
    const suggestions = Array.isArray(item.suggestions) ? item.suggestions : [];
    return (
        <div className="rec-aux-item-card">
            <div className="rec-aux-item-header">
                <div className="rec-aux-item-title-row">
                    <Sliders size={16} className="rec-aux-icon--mod" />
                    <div>
                        <h5 className="rec-aux-item-title">{item.title}</h5>
                        {item.action && <span className="rec-aux-item-sub">Action: {item.action}</span>}
                    </div>
                </div>
                {item.priority && <PriorityBadge priority={item.priority} />}
            </div>

            {item.rationale && (
                <p className="rec-aux-item-desc">
                    <strong>Rationale:</strong> {item.rationale}
                </p>
            )}

            {suggestions.length > 0 && (
                <ul className="rec-aux-guidelines">
                    {suggestions.map((s, i) => (
                        <li key={i} className="rec-aux-guideline-item">
                            <ChevronRight size={13} className="rec-guideline-icon" />
                            <span>{s}</span>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
}

/**
 * Main CorrectiveActionPlan Component
 */
export default function CorrectiveActionPlan({ recommendations, loading = false }) {
    // Normalization logic: handle all potential shapes of recommendation data
    const raw = recommendations || {};

    // 1. Priority Areas
    const priorityAreas = Array.isArray(raw.priority_areas)
        ? raw.priority_areas
        : Array.isArray(raw.primary_focus_areas)
        ? raw.primary_focus_areas
        : [];

    // 2. Structured Recommendation Items
    const exerciseRecs = Array.isArray(raw.exercise_recommendations) ? raw.exercise_recommendations : [];
    const mobilityRecs = Array.isArray(raw.mobility_recommendations) ? raw.mobility_recommendations : [];
    const strengthRecs = Array.isArray(raw.strengthening_recommendations) ? raw.strengthening_recommendations : [];
    const directRecs = Array.isArray(raw.recommendations)
        ? raw.recommendations
        : Array.isArray(raw)
        ? raw
        : [];

    // Combine all recommendation items while preserving / defaulting category
    const allRecs = [
        ...exerciseRecs.map((r) => ({ ...r, category: r.category || "exercise" })),
        ...mobilityRecs.map((r) => ({ ...r, category: r.category || "mobility" })),
        ...strengthRecs.map((r) => ({ ...r, category: r.category || "strengthening" })),
        ...directRecs.filter(
            (r) =>
                typeof r === "object" &&
                !exerciseRecs.some((e) => e.id === r.id || e.title === r.title) &&
                !mobilityRecs.some((m) => m.id === r.id || m.title === r.title) &&
                !strengthRecs.some((s) => s.id === r.id || s.title === r.title)
        ),
    ];

    // 3. Aux Recovery & Training Modifications
    const recoveryPlan = Array.isArray(raw.recovery_plan) ? raw.recovery_plan : [];
    const trainingMods = Array.isArray(raw.training_modifications) ? raw.training_modifications : [];

    // 4. Count priorities
    const highCount =
        allRecs.filter((r) => (r.priority || "").toLowerCase() === "high" || (r.priority || "").toLowerCase() === "critical").length +
        recoveryPlan.filter((r) => (r.priority || "").toLowerCase() === "high").length +
        trainingMods.filter((r) => (r.priority || "").toLowerCase() === "high").length;

    const medCount =
        allRecs.filter((r) => (r.priority || "").toLowerCase() === "medium" || (r.priority || "").toLowerCase() === "moderate").length +
        recoveryPlan.filter((r) => (r.priority || "").toLowerCase() === "medium").length +
        trainingMods.filter((r) => (r.priority || "").toLowerCase() === "medium").length;

    const lowCount =
        allRecs.filter((r) => (r.priority || "").toLowerCase() === "low").length +
        recoveryPlan.filter((r) => (r.priority || "").toLowerCase() === "low").length +
        trainingMods.filter((r) => (r.priority || "").toLowerCase() === "low").length;

    // Filter category state
    const [selectedCategory, setSelectedCategory] = useState("all");

    // Expanded card states (all expanded initially if <= 3 items, else first 2 expanded)
    const [expandedIds, setExpandedIds] = useState(() => {
        const set = new Set();
        allRecs.forEach((r, idx) => {
            if (allRecs.length <= 3 || idx < 2) {
                set.add(r.id || r.title || `rec-${idx}`);
            }
        });
        return set;
    });

    const toggleCard = (id) => {
        setExpandedIds((prev) => {
            const next = new Set(prev);
            if (next.has(id)) {
                next.delete(id);
            } else {
                next.add(id);
            }
            return next;
        });
    };

    const expandAll = () => {
        const next = new Set();
        allRecs.forEach((r, idx) => next.add(r.id || r.title || `rec-${idx}`));
        setExpandedIds(next);
    };

    const collapseAll = () => {
        setExpandedIds(new Set());
    };

    // Filter items based on category tabs
    const filteredRecs = allRecs.filter((r) => {
        if (selectedCategory === "all") return true;
        const cat = (r.category || "").toLowerCase();
        if (selectedCategory === "exercise") return cat === "exercise";
        if (selectedCategory === "mobility") return cat === "mobility";
        if (selectedCategory === "strengthening") return cat === "strengthening" || cat === "strength";
        return true;
    });

    // Loading State
    if (loading) {
        return (
            <div className="corrective-plan-container">
                <div className="rec-loading-state">
                    <div className="rec-loading-spinner" />
                    <div>
                        <h4 className="rec-loading-title">Generating Corrective Action Plan…</h4>
                        <p className="rec-loading-sub">
                            Analyzing biomechanical findings and identifying targeted corrective drills.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    // Empty State Check
    const hasAnyContent =
        allRecs.length > 0 ||
        priorityAreas.length > 0 ||
        recoveryPlan.length > 0 ||
        trainingMods.length > 0;

    if (!hasAnyContent) {
        return (
            <div className="corrective-plan-container">
                <div className="rec-empty-state">
                    <div className="rec-empty-icon">
                        <CheckCircle2 size={32} />
                    </div>
                    <div className="rec-empty-body">
                        <h4 className="rec-empty-title">No Corrective Actions Required</h4>
                        <p className="rec-empty-msg">
                            No corrective recommendations were identified from the available biomechanical findings.
                            All observed landing and movement patterns are within standard reference thresholds.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="corrective-plan-container" id="corrective-action-plan-section">
            {/* 1. Strategy Overview Banner */}
            <div className="rec-overview-banner">
                <div className="rec-overview-content">
                    <div className="rec-summary-row">
                        <div>
                            <div className="rec-banner-eyebrow">
                                <Sparkles size={13} />
                                <span>TARGETED INTERVENTION STRATEGY</span>
                            </div>
                            <h3 className="rec-plan-heading">Corrective Movement Prescription</h3>
                        </div>

                        {/* Priority Breakdown Chips */}
                        <div className="rec-priority-counts">
                            {highCount > 0 && (
                                <span className="rec-count-chip rec-count-chip--high">
                                    <AlertTriangle size={12} /> {highCount} High Priority
                                </span>
                            )}
                            {medCount > 0 && (
                                <span className="rec-count-chip rec-count-chip--medium">
                                    <Clock size={12} /> {medCount} Medium Priority
                                </span>
                            )}
                            {lowCount > 0 && (
                                <span className="rec-count-chip rec-count-chip--low">
                                    <CheckCircle size={12} /> {lowCount} Low Priority
                                </span>
                            )}
                        </div>
                    </div>

                    <p className="rec-summary-text">
                        Targeted corrective exercises and movement drills formulated to address specific biomechanical deviations, LESS landing criteria errors, and joint loading asymmetries.
                    </p>

                    {/* Priority Areas Badges */}
                    {priorityAreas.length > 0 && (
                        <div className="rec-priority-areas-wrap">
                            <span className="rec-focus-label">
                                <Target size={13} /> Priority Focus Areas:
                            </span>
                            <div className="rec-focus-tags">
                                {priorityAreas.map((area, idx) => (
                                    <span key={idx} className="rec-focus-tag">
                                        • {area}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* 2. Recommendation Cards Section */}
            {allRecs.length > 0 && (
                <div className="rec-main-section">
                    {/* Filter Tabs & Accordion Controls */}
                    <div className="rec-controls-bar">
                        <div className="rec-category-tabs">
                            <button
                                type="button"
                                className={`rec-tab-btn ${selectedCategory === "all" ? "rec-tab-btn--active" : ""}`}
                                onClick={() => setSelectedCategory("all")}
                            >
                                All Recommendations ({allRecs.length})
                            </button>
                            {exerciseRecs.length > 0 && (
                                <button
                                    type="button"
                                    className={`rec-tab-btn ${selectedCategory === "exercise" ? "rec-tab-btn--active" : ""}`}
                                    onClick={() => setSelectedCategory("exercise")}
                                >
                                    <Activity size={13} /> Movement Drills ({exerciseRecs.length})
                                </button>
                            )}
                            {mobilityRecs.length > 0 && (
                                <button
                                    type="button"
                                    className={`rec-tab-btn ${selectedCategory === "mobility" ? "rec-tab-btn--active" : ""}`}
                                    onClick={() => setSelectedCategory("mobility")}
                                >
                                    <RotateCcw size={13} /> Mobility ({mobilityRecs.length})
                                </button>
                            )}
                            {strengthRecs.length > 0 && (
                                <button
                                    type="button"
                                    className={`rec-tab-btn ${selectedCategory === "strengthening" ? "rec-tab-btn--active" : ""}`}
                                    onClick={() => setSelectedCategory("strengthening")}
                                >
                                    <Dumbbell size={13} /> Strengthening ({strengthRecs.length})
                                </button>
                            )}
                        </div>

                        {allRecs.length > 1 && (
                            <div className="rec-expand-controls">
                                <button
                                    type="button"
                                    className="rec-expand-text-btn"
                                    onClick={expandAll}
                                >
                                    Expand All
                                </button>
                                <span className="rec-expand-sep">·</span>
                                <button
                                    type="button"
                                    className="rec-expand-text-btn"
                                    onClick={collapseAll}
                                >
                                    Collapse All
                                </button>
                            </div>
                        )}
                    </div>

                    {/* Cards List */}
                    <div className="rec-cards-list">
                        {filteredRecs.map((rec, idx) => {
                            const id = rec.id || rec.title || `rec-${idx}`;
                            const isExpanded = expandedIds.has(id);
                            return (
                                <RecommendationCard
                                    key={id}
                                    rec={rec}
                                    isExpanded={isExpanded}
                                    onToggle={() => toggleCard(id)}
                                />
                            );
                        })}
                    </div>
                </div>
            )}

            {/* 3. Auxiliary Protocols: Recovery & Training Modifications */}
            {(recoveryPlan.length > 0 || trainingMods.length > 0) && (
                <div className="rec-aux-grid">
                    {/* Recovery Plan */}
                    {recoveryPlan.length > 0 && (
                        <div className="rec-aux-card">
                            <div className="rec-aux-header">
                                <div className="rec-aux-header-icon rec-aux-header-icon--recovery">
                                    <HeartPulse size={16} />
                                </div>
                                <div>
                                    <h4 className="rec-aux-title">Recovery & Fatigue Management</h4>
                                    <span className="rec-aux-subtitle">Workload recovery and tissue restoration protocols</span>
                                </div>
                            </div>
                            <div className="rec-aux-body">
                                {recoveryPlan.map((item, idx) => (
                                    <RecoveryItemCard key={idx} item={item} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Training Modifications */}
                    {trainingMods.length > 0 && (
                        <div className="rec-aux-card">
                            <div className="rec-aux-header">
                                <div className="rec-aux-header-icon rec-aux-header-icon--mod">
                                    <Sliders size={16} />
                                </div>
                                <div>
                                    <h4 className="rec-aux-title">Training Volume & Load Adaptations</h4>
                                    <span className="rec-aux-subtitle">Practical volume, intensity, and progression adjustments</span>
                                </div>
                            </div>
                            <div className="rec-aux-body">
                                {trainingMods.map((item, idx) => (
                                    <TrainingModItemCard key={idx} item={item} />
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
