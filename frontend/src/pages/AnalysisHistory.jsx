import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
    Activity,
    ChevronRight,
    Clock,
    FileVideo,
    History,
    XCircle,
    CheckCircle2,
    Loader2,
    Plus,
    Calendar,
    Trash2,
    AlertTriangle,
    Pencil,
    Search,
    Filter,
} from "lucide-react";

import RiskBadge from "../components/RiskBadge";
import { getMyHistory, deleteVideoAssessment, updateVideoAssessment } from "../api/videos";

function formatDate(dt) {
    if (!dt) return "—";
    return new Date(dt).toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function StatusBadge({ status }) {
    const s = (status || "").toUpperCase();
    let icon = <Activity size={12} />;
    let bg = "#f1f5f9", color = "#64748b";
    if (s === "COMPLETED") {
        icon = <CheckCircle2 size={12} />;
        bg = "#dcfce7";
        color = "#15803d";
    } else if (s === "FAILED") {
        icon = <XCircle size={12} />;
        bg = "#fee2e2";
        color = "#b91c1c";
    } else if (s === "PROCESSING") {
        icon = <Loader2 size={12} className="spinner-icon" />;
        bg = "#dbeafe";
        color = "#1d4ed8";
    } else if (s === "PENDING") {
        icon = <Clock size={12} />;
        bg = "#fef9c3";
        color = "#a16207";
    }

    return (
        <span className="history-status-badge" style={{ background: bg, color, border: `1px solid ${bg}` }}>
            {icon}
            {status || "—"}
        </span>
    );
}

function AnalysisHistory() {
    const navigate = useNavigate();

    const [history, setHistory]   = useState([]);
    const [loading, setLoading]   = useState(true);
    const [error, setError]       = useState("");

    // Risk Filter & Search states
    const [riskFilter, setRiskFilter]   = useState("all"); // "all" | "low" | "moderate" | "high" | "critical"
    const [searchQuery, setSearchQuery] = useState("");

    // Delete assessment state
    const [deleteModalItem, setDeleteModalItem] = useState(null);
    const [isDeleting, setIsDeleting]           = useState(false);
    const [actionSuccess, setActionSuccess]     = useState("");
    const [actionError, setActionError]         = useState("");

    // Edit/Rename assessment state
    const [editModalItem, setEditModalItem] = useState(null);
    const [editTitle, setEditTitle]         = useState("");
    const [isSavingEdit, setIsSavingEdit]   = useState(false);
    const [editError, setEditError]         = useState("");

    useEffect(() => {
        let cancelled = false;

        async function fetchHistory() {
            setLoading(true);
            setError("");
            try {
                const data = await getMyHistory();
                if (!cancelled) setHistory(data || []);
            } catch (err) {
                if (!cancelled) {
                    setError(
                        err.response?.data?.detail ||
                        "Could not load analysis history. Please try again."
                    );
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        fetchHistory();
        return () => { cancelled = true; };
    }, []);

    // Prevent background scrolling when modal is active
    useEffect(() => {
        if (deleteModalItem || editModalItem) {
            document.body.style.overflow = "hidden";
        } else {
            document.body.style.overflow = "";
        }
        return () => {
            document.body.style.overflow = "";
        };
    }, [deleteModalItem, editModalItem]);

    // Filter history records based on search query and risk level filter
    const filteredHistory = history.filter((item) => {
        // Search query filter
        if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase();
            const title = (item.title || "").toLowerCase();
            const filename = (item.original_filename || "").toLowerCase();
            if (!title.includes(q) && !filename.includes(q)) return false;
        }

        // Risk filter check
        if (riskFilter !== "all") {
            const rawLevel = (item.risk_level || "").toLowerCase();
            const score = item.overall_risk_score;

            let derivedLevel = rawLevel;
            if (!derivedLevel && score !== null && score !== undefined) {
                if (score < 40) derivedLevel = "low";
                else if (score < 70) derivedLevel = "moderate";
                else if (score < 85) derivedLevel = "high";
                else derivedLevel = "critical";
            }

            if (derivedLevel !== riskFilter) {
                return false;
            }
        }

        return true;
    });

    function handleRowClick(videoId) {
        navigate(`/analysis/${videoId}`);
    }

    function openEditModal(item) {
        setEditModalItem(item);
        setEditTitle(item.title || item.original_filename || "");
        setEditError("");
    }

    async function confirmRename(e) {
        if (e) e.preventDefault();
        if (!editModalItem) return;
        const trimmed = editTitle.trim();
        if (!trimmed) {
            setEditError("Assessment name cannot be empty.");
            return;
        }
        setIsSavingEdit(true);
        setEditError("");
        try {
            const updated = await updateVideoAssessment(editModalItem.video_id, { title: trimmed });
            const newTitle = updated.title || trimmed;
            setHistory((prev) =>
                prev.map((h) =>
                    h.video_id === editModalItem.video_id ? { ...h, title: newTitle } : h
                )
            );
            setActionSuccess("Assessment renamed successfully.");
            setEditModalItem(null);
            setTimeout(() => setActionSuccess(""), 4000);
        } catch (err) {
            setEditError(
                err.response?.data?.detail ||
                "Failed to rename assessment. Please try again."
            );
        } finally {
            setIsSavingEdit(false);
        }
    }

    async function confirmDelete() {
        if (!deleteModalItem) return;
        setIsDeleting(true);
        setActionError("");
        try {
            await deleteVideoAssessment(deleteModalItem.video_id);
            setHistory((prev) => prev.filter((h) => h.video_id !== deleteModalItem.video_id));
            setActionSuccess("Assessment deleted successfully.");
            setDeleteModalItem(null);
            setTimeout(() => setActionSuccess(""), 4000);
        } catch (err) {
            setActionError(
                err.response?.data?.detail ||
                "Failed to delete assessment. Please try again."
            );
        } finally {
            setIsDeleting(false);
        }
    }

    return (
        <div className="app-layout">
            <main className="dashboard">
                {/* ── Page Header ─────────────────────────────────────────────── */}
                <div className="page-header">
                    <div>
                        <span className="eyebrow">MY MOVEMENT HISTORY</span>
                        <h1>Analysis History</h1>
                        <p>All previously uploaded and analyzed videos, newest first.</p>
                    </div>

                    <Link to="/analysis" className="primary-button hero-cta" id="new-analysis-btn">
                        <Plus size={18} />
                        Analyze New Video
                    </Link>
                </div>

                {/* Success / Action Error notifications */}
                {actionSuccess && (
                    <div className="success-box" style={{ marginBottom: 20 }}>
                        {actionSuccess}
                    </div>
                )}
                {actionError && (
                    <div className="error-box" style={{ marginBottom: 20 }}>
                        {actionError}
                    </div>
                )}

                {/* ── Main Panel ──────────────────────────────────────────────── */}
                <section className="panel card-panel">
                    {/* Filter & Search Bar */}
                    <div className="history-filter-bar" style={{ marginBottom: 24 }}>
                        <div className="filter-group-search">
                            <div className="search-input-wrapper">
                                <Search size={16} className="search-icon" />
                                <input
                                    type="text"
                                    placeholder="Search assessments..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="history-search-input"
                                    id="history-search-input"
                                />
                                {searchQuery && (
                                    <button
                                        type="button"
                                        className="clear-search-btn"
                                        onClick={() => setSearchQuery("")}
                                        aria-label="Clear search"
                                    >
                                        <XCircle size={14} />
                                    </button>
                                )}
                            </div>
                        </div>

                        <div className="filter-group-risk">
                            <div className="filter-label">
                                <Filter size={14} />
                                <span>Filter by Risk:</span>
                            </div>
                            <div className="risk-pills-row">
                                {[
                                    { id: "all", label: "All Risks" },
                                    { id: "low", label: "Low" },
                                    { id: "moderate", label: "Moderate" },
                                    { id: "high", label: "High" },
                                    { id: "critical", label: "Critical" },
                                ].map((f) => (
                                    <button
                                        key={f.id}
                                        type="button"
                                        className={`risk-filter-pill ${f.id} ${riskFilter === f.id ? "active" : ""}`}
                                        onClick={() => setRiskFilter(f.id)}
                                        id={`filter-pill-${f.id}`}
                                    >
                                        {f.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>

                    <div className="panel-header" style={{ marginBottom: 16 }}>
                        <div style={{ fontSize: 13, color: "#64748b" }}>
                            {!loading && !error && (
                                <span>
                                    {history.length === 0
                                        ? "No analysis history recorded"
                                        : `Showing ${filteredHistory.length} of ${history.length} assessment record${history.length !== 1 ? "s" : ""}`}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Loading State */}
                    {loading && (
                        <div className="loading-container" style={{ padding: "50px 0" }}>
                            <div className="spinner" />
                            <span>Loading movement analysis history…</span>
                        </div>
                    )}

                    {/* Error State */}
                    {!loading && error && (
                        <div className="error-box">{error}</div>
                    )}

                    {/* Empty State */}
                    {!loading && !error && history.length === 0 && (
                        <div className="history-empty">
                            <div className="empty-icon-wrapper">
                                <History size={36} />
                            </div>
                            <h3>No analysis history found</h3>
                            <p>You haven't analyzed any movement videos yet. Upload a video to generate your first AI risk report.</p>
                            <Link to="/analysis" className="primary-button hero-cta" style={{ marginTop: 16 }}>
                                <Plus size={16} />
                                Start First Video Analysis
                            </Link>
                        </div>
                    )}

                    {/* Filtered Empty State */}
                    {!loading && !error && history.length > 0 && filteredHistory.length === 0 && (
                        <div className="history-empty" style={{ padding: "40px 20px" }}>
                            <div className="empty-icon-wrapper">
                                <Filter size={32} />
                            </div>
                            <h3>No matching assessments</h3>
                            <p>No assessment records match the selected risk filter or search query.</p>
                            <button
                                type="button"
                                className="secondary-button"
                                onClick={() => {
                                    setRiskFilter("all");
                                    setSearchQuery("");
                                }}
                                style={{ marginTop: 14 }}
                            >
                                Reset Filters
                            </button>
                        </div>
                    )}

                    {/* History Table */}
                    {!loading && !error && filteredHistory.length > 0 && (
                        <div className="history-table-wrap">
                            <table className="history-table">
                                <thead>
                                    <tr>
                                        <th>Assessment Name</th>
                                        <th>Upload Date</th>
                                        <th>Risk Score</th>
                                        <th>LESS Score</th>
                                        <th>Status</th>
                                        <th style={{ width: 80, textAlign: "right" }}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredHistory.map((item) => {
                                        const displayName = item.title || item.original_filename || `Video ${item.video_id.slice(0, 8)}…`;
                                        const hasCustomTitle = Boolean(item.title && item.original_filename && item.title !== item.original_filename);

                                        return (
                                            <tr
                                                key={item.video_id}
                                                onClick={() => handleRowClick(item.video_id)}
                                                id={`history-row-${item.video_id}`}
                                                role="button"
                                                tabIndex={0}
                                                onKeyDown={(e) => {
                                                    if (e.key === "Enter" || e.key === " ") {
                                                        handleRowClick(item.video_id);
                                                    }
                                                }}
                                            >
                                                {/* Assessment Title & Original Filename */}
                                                <td>
                                                    <div className="history-filename">
                                                        <div className="video-icon-square">
                                                            <FileVideo size={16} />
                                                        </div>
                                                        <div className="history-title-group">
                                                            <div className="assessment-name-wrap">
                                                                <span className="file-title" title={displayName} style={{ fontWeight: 600, color: "#0f172a" }}>
                                                                    {displayName}
                                                                </span>
                                                                {item.has_pose_landmarks && (
                                                                    <span className="ai-pose-tag-pill" title="AI Pose Skeleton Overlay Available">
                                                                        AI POSE ✓
                                                                    </span>
                                                                )}
                                                                <button
                                                                    type="button"
                                                                    className="edit-icon-btn"
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        openEditModal(item);
                                                                    }}
                                                                    title="Rename assessment"
                                                                    aria-label="Rename assessment"
                                                                    id={`edit-btn-${item.video_id}`}
                                                                >
                                                                    <Pencil size={13} />
                                                                </button>
                                                            </div>
                                                            {hasCustomTitle && (
                                                                <span className="original-filename-tag" title={`Original file: ${item.original_filename}`}>
                                                                    {item.original_filename}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </td>


                                                {/* Date */}
                                                <td className="history-date">
                                                    <div className="date-cell">
                                                        <Calendar size={13} />
                                                        <span>{formatDate(item.uploaded_at)}</span>
                                                    </div>
                                                </td>

                                                {/* Risk Score */}
                                                <td>
                                                    {item.overall_risk_score != null ? (
                                                        <div className="history-risk-cell">
                                                            <span className="history-risk-score">
                                                                {Math.round(item.overall_risk_score)}
                                                            </span>
                                                            <RiskBadge level={item.risk_level || "PENDING"} />
                                                        </div>
                                                    ) : (
                                                        <span style={{ color: "#94a3b8", fontSize: 12 }}>—</span>
                                                    )}
                                                </td>

                                                {/* LESS Score */}
                                                <td className="history-less-text">
                                                    {item.less_score != null ? (
                                                        <span className="less-pill">
                                                            LESS {item.less_score}/{item.less_max_computable_score || 12}
                                                        </span>
                                                    ) : (
                                                        <span style={{ color: "#cbd5e1" }}>—</span>
                                                    )}
                                                </td>

                                                {/* Status */}
                                                <td>
                                                    <StatusBadge status={item.analysis_status || item.processing_status} />
                                                </td>

                                                {/* Action Column (Trash icon + Chevron) */}
                                                <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                                                    <div style={{ display: "inline-flex", alignItems: "center", gap: 6 }} onClick={(e) => e.stopPropagation()}>
                                                        <button
                                                            type="button"
                                                            className="icon-action-btn delete-action-btn"
                                                            onClick={() => setDeleteModalItem(item)}
                                                            title="Delete assessment"
                                                            aria-label="Delete assessment"
                                                            id={`delete-btn-${item.video_id}`}
                                                        >
                                                            <Trash2 size={16} />
                                                        </button>
                                                        <ChevronRight size={18} className="history-chevron" />
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>

                {/* Edit / Rename Assessment Modal */}
                {editModalItem && (
                    <div className="modal-overlay" onClick={() => !isSavingEdit && setEditModalItem(null)}>
                        <div className="modal-content" style={{ maxWidth: 440 }} onClick={(e) => e.stopPropagation()}>
                            <form onSubmit={confirmRename}>
                                <div className="modal-header">
                                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                                        <div style={{ width: 40, height: 40, borderRadius: 10, background: "#eff6ff", color: "#2563eb", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                                            <Pencil size={20} />
                                        </div>
                                        <div>
                                            <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: "#0f172a" }}>Rename Assessment</h3>
                                            <span style={{ fontSize: 12, color: "#64748b" }}>Set a custom title for this movement analysis</span>
                                        </div>
                                    </div>
                                </div>

                                <div className="modal-body" style={{ padding: "16px 24px 20px" }}>
                                    {editError && (
                                        <div className="error-box" style={{ marginBottom: 14 }}>
                                            {editError}
                                        </div>
                                    )}

                                    <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
                                        Assessment Name
                                    </label>
                                    <input
                                        type="text"
                                        style={{
                                            width: "100%",
                                            padding: "10px 14px",
                                            borderRadius: 8,
                                            border: "1px solid #cbd5e1",
                                            fontSize: 14,
                                            outline: "none"
                                        }}
                                        value={editTitle}
                                        onChange={(e) => {
                                            setEditTitle(e.target.value);
                                            if (editError) setEditError("");
                                        }}
                                        placeholder="e.g. Tennis — Right Knee Assessment"
                                        autoFocus
                                        id="edit-title-input"
                                    />
                                    {editModalItem.original_filename && (
                                        <p style={{ margin: "10px 0 0", fontSize: 12, color: "#64748b" }}>
                                            Original video file: <strong style={{ color: "#475569" }}>{editModalItem.original_filename}</strong>
                                        </p>
                                    )}
                                </div>

                                <div className="modal-footer" style={{ display: "flex", justifyContent: "flex-end", gap: 10, padding: "14px 24px", borderTop: "1px solid #e2e8f0", background: "#f8fafc", borderRadius: "0 0 16px 16px" }}>
                                    <button
                                        type="button"
                                        className="secondary-button"
                                        disabled={isSavingEdit}
                                        onClick={() => setEditModalItem(null)}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        type="submit"
                                        className="primary-button"
                                        disabled={isSavingEdit}
                                        id="save-edit-btn"
                                    >
                                        {isSavingEdit ? (
                                            <>
                                                <Loader2 size={16} className="spinner-icon" />
                                                Saving…
                                            </>
                                        ) : (
                                            "Save Changes"
                                        )}
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Delete Confirmation Modal */}
                {deleteModalItem && (
                    <div className="modal-overlay" onClick={() => !isDeleting && setDeleteModalItem(null)}>
                        <div className="modal-content" style={{ maxWidth: 440 }} onClick={(e) => e.stopPropagation()}>
                            <div className="modal-header">
                                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                                    <div style={{ width: 40, height: 40, borderRadius: 10, background: "#fee2e2", color: "#dc2626", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                                        <AlertTriangle size={20} />
                                    </div>
                                    <div>
                                        <h3 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: "#0f172a" }}>Delete Assessment</h3>
                                        <span style={{ fontSize: 12, color: "#64748b" }}>This action cannot be undone</span>
                                    </div>
                                </div>
                            </div>

                            <div className="modal-body" style={{ padding: "16px 24px 20px" }}>
                                <p style={{ margin: 0, fontSize: 14, color: "#334155", lineHeight: 1.5 }}>
                                    Are you sure you want to delete this assessment?
                                </p>
                                <div style={{ marginTop: 12, padding: "10px 14px", background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13, color: "#475569", fontWeight: 600, wordBreak: "break-all" }}>
                                    {deleteModalItem.title || deleteModalItem.original_filename}
                                </div>
                            </div>

                            <div className="modal-footer" style={{ display: "flex", justifyContent: "flex-end", gap: 10, padding: "14px 24px", borderTop: "1px solid #e2e8f0", background: "#f8fafc", borderRadius: "0 0 16px 16px" }}>
                                <button
                                    type="button"
                                    className="secondary-button"
                                    disabled={isDeleting}
                                    onClick={() => setDeleteModalItem(null)}
                                >
                                    Cancel
                                </button>
                                <button
                                    type="button"
                                    className="danger-button"
                                    disabled={isDeleting}
                                    onClick={confirmDelete}
                                    id="confirm-delete-btn"
                                >
                                    {isDeleting ? (
                                        <>
                                            <Loader2 size={16} className="spinner-icon" />
                                            Deleting…
                                        </>
                                    ) : (
                                        <>
                                            <Trash2 size={16} />
                                            Delete
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}

export default AnalysisHistory;
