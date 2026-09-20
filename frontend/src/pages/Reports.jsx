import React, { useState, useEffect } from "react";
import {
    FileText,
    FileSpreadsheet,
    Download,
    Eye,
    Filter,
    Calendar,
    User,
    Activity,
    Shield,
    TrendingUp,
    HeartPulse,
    Search,
    RefreshCw,
    AlertCircle,
    CheckCircle2,
    Clock,
} from "lucide-react";
import RiskBadge from "../components/RiskBadge";
import Loading from "../components/Loading";
import ReportViewer from "../components/ReportViewer";
import { useAuth } from "../context/AuthContext";
import {
    getReportOptions,
    getReportData,
    getReportsList,
    downloadReportPdf,
    downloadReportExcel,
} from "../api/reports";

function Reports() {
    const { user } = useAuth();
    const role = user?.role;

    // Loading & state
    const [loadingOptions, setLoadingOptions] = useState(true);
    const [options, setOptions] = useState({
        athletes: [],
        assessments: [],
        report_types: [],
    });
    const [reportsList, setReportsList] = useState([]);
    const [loadingList, setLoadingList] = useState(false);

    // Form selection
    const [selectedReportType, setSelectedReportType] = useState("INJURY_RISK");
    const [selectedAthleteId, setSelectedAthleteId] = useState("");
    const [selectedVideoId, setSelectedVideoId] = useState("");
    const [searchQuery, setSearchQuery] = useState("");
    const [dateFilter, setDateFilter] = useState("all");

    // Action states
    const [generating, setGenerating] = useState(false);
    const [exportingPdf, setExportingPdf] = useState(false);
    const [exportingExcel, setExportingExcel] = useState(false);
    const [actionRowId, setActionRowId] = useState(null);
    const [actionType, setActionType] = useState(null);

    // Preview modal
    const [activeReportPayload, setActiveReportPayload] = useState(null);
    const [errorMsg, setErrorMsg] = useState(null);

    // Page title based on role
    const getPageTitle = () => {
        switch (role) {
            case "Athlete":
                return "My Reports & Exports";
            case "Coach":
                return "Athlete Reports & Exports";
            case "Physiotherapist":
                return "Rehabilitation & Movement Reports";
            case "Sports Scientist":
                return "Biomechanical & Performance Reports";
            default:
                return "Reports & Exports Center";
        }
    };

    // Load initial options & list
    useEffect(() => {
        async function fetchInitial() {
            try {
                setLoadingOptions(true);
                setErrorMsg(null);
                const [opts, list] = await Promise.all([
                    getReportOptions(),
                    getReportsList(),
                ]);
                setOptions(opts);
                setReportsList(list);

                // Auto-select default athlete if available
                if (opts.athletes && opts.athletes.length > 0) {
                    setSelectedAthleteId(opts.athletes[0].athlete_id);
                }
            } catch (err) {
                console.error("Failed to load report options:", err);
                setErrorMsg("Failed to load reports configuration. Please refresh.");
            } finally {
                setLoadingOptions(false);
            }
        }
        fetchInitial();
    }, []);

    // Filter assessments for selected athlete
    const athleteAssessments = options.assessments.filter(
        (ass) => ass.athlete_id === selectedAthleteId
    );

    // Auto-select latest assessment when athlete changes
    useEffect(() => {
        if (athleteAssessments.length > 0) {
            setSelectedVideoId(athleteAssessments[0].video_id);
        } else {
            setSelectedVideoId("");
        }
    }, [selectedAthleteId, options.assessments]);

    // Generate/View Report
    async function handleGenerateReport() {
        if (!selectedAthleteId) {
            setErrorMsg("Please select an athlete first.");
            return;
        }

        try {
            setGenerating(true);
            setErrorMsg(null);
            const payload = await getReportData(
                selectedReportType,
                selectedAthleteId,
                selectedVideoId || null
            );
            setActiveReportPayload(payload);
        } catch (err) {
            console.error("Error generating report:", err);
            const detail = err.response?.data?.detail || "Failed to generate report.";
            setErrorMsg(detail);
        } finally {
            setGenerating(false);
        }
    }

    // Direct PDF Export from selector
    async function handleExportPdf() {
        if (!selectedAthleteId) {
            setErrorMsg("Please select an athlete first.");
            return;
        }

        try {
            setExportingPdf(true);
            setErrorMsg(null);
            await downloadReportPdf(
                selectedReportType,
                selectedAthleteId,
                selectedVideoId || null
            );
        } catch (err) {
            console.error("Error exporting PDF:", err);
            setErrorMsg("Failed to export PDF file.");
        } finally {
            setExportingPdf(false);
        }
    }

    // Direct Excel Export from selector
    async function handleExportExcel() {
        if (!selectedAthleteId) {
            setErrorMsg("Please select an athlete first.");
            return;
        }

        try {
            setExportingExcel(true);
            setErrorMsg(null);
            await downloadReportExcel(
                selectedReportType,
                selectedAthleteId,
                selectedVideoId || null
            );
        } catch (err) {
            console.error("Error exporting Excel:", err);
            setErrorMsg("Failed to export Excel file.");
        } finally {
            setExportingExcel(false);
        }
    }

    // Row Actions in table
    async function handleRowView(item) {
        try {
            setActionRowId(item.video_id || item.athlete_id);
            setActionType("view");
            setErrorMsg(null);
            const payload = await getReportData(
                item.report_type,
                item.athlete_id,
                item.video_id || null
            );
            setActiveReportPayload(payload);
        } catch (err) {
            console.error("Failed to view row report:", err);
            setErrorMsg("Failed to view report data.");
        } finally {
            setActionRowId(null);
            setActionType(null);
        }
    }

    async function handleRowPdf(item) {
        try {
            setActionRowId(item.video_id || item.athlete_id);
            setActionType("pdf");
            setErrorMsg(null);
            await downloadReportPdf(
                item.report_type,
                item.athlete_id,
                item.video_id || null
            );
        } catch (err) {
            console.error("Failed to download PDF for row:", err);
            setErrorMsg("Failed to download PDF report.");
        } finally {
            setActionRowId(null);
            setActionType(null);
        }
    }

    async function handleRowExcel(item) {
        try {
            setActionRowId(item.video_id || item.athlete_id);
            setActionType("excel");
            setErrorMsg(null);
            await downloadReportExcel(
                item.report_type,
                item.athlete_id,
                item.video_id || null
            );
        } catch (err) {
            console.error("Failed to download Excel for row:", err);
            setErrorMsg("Failed to download Excel file.");
        } finally {
            setActionRowId(null);
            setActionType(null);
        }
    }

    // Filtered reports list for table
    const filteredReportsList = reportsList.filter((item) => {
        const matchesSearch =
            !searchQuery ||
            item.athlete_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            (item.sport && item.sport.toLowerCase().includes(searchQuery.toLowerCase())) ||
            item.report_type_label.toLowerCase().includes(searchQuery.toLowerCase());

        if (!matchesSearch) return false;

        if (dateFilter === "30days" && item.date) {
            const itemDate = new Date(item.date);
            const thirtyDaysAgo = new Date();
            thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
            return itemDate >= thirtyDaysAgo;
        }

        return true;
    });

    if (loadingOptions) {
        return (
            <div className="app-layout">
                <main className="dashboard">
                    <Loading message="Loading Reports & Export Center..." />
                </main>
            </div>
        );
    }

    return (
        <div className="app-layout">
            <main className="dashboard reports-page-container">
                {/* Page Title Banner */}
                <div className="reports-page-header">
                    <div>
                        <h1 className="page-title">{getPageTitle()}</h1>
                        <p className="page-subtitle">
                            Generate, preview, and export high-fidelity PDF and Excel assessment reports with PreHab AI.
                        </p>
                    </div>

                    <div className="reports-role-indicator">
                        <Shield size={14} />
                        <span>Role: {role}</span>
                    </div>
                </div>

                {errorMsg && (
                    <div className="report-alert-banner">
                        <AlertCircle size={18} />
                        <span>{errorMsg}</span>
                    </div>
                )}

                {/* ── REPORT GENERATOR CARD ─────────────────────────────────────── */}
                <div className="reports-generator-card">
                    <div className="generator-card-header">
                        <FileText size={20} className="text-primary" />
                        <h3>Report Configuration & Export</h3>
                    </div>

                    {/* Report Type Selector Pills */}
                    <div className="report-type-selector-wrapper">
                        <label className="generator-label">Select Report Type</label>
                        <div className="report-type-pills">
                            {options.report_types.map((t) => (
                                <button
                                    key={t.type}
                                    type="button"
                                    className={`report-type-pill ${selectedReportType === t.type ? "active" : ""}`}
                                    onClick={() => setSelectedReportType(t.type)}
                                >
                                    <span className="pill-title">{t.label}</span>
                                    <span className="pill-desc">{t.description}</span>
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Filter Inputs Grid */}
                    <div className="generator-controls-grid">
                        {/* Athlete Selector */}
                        <div className="control-group">
                            <label className="generator-label">Target Athlete</label>
                            <select
                                className="generator-select"
                                value={selectedAthleteId}
                                onChange={(e) => setSelectedAthleteId(e.target.value)}
                                disabled={options.athletes.length <= 1 && role === "Athlete"}
                            >
                                {options.athletes.length === 0 ? (
                                    <option value="">No athletes available</option>
                                ) : (
                                    options.athletes.map((ath) => (
                                        <option key={ath.athlete_id} value={ath.athlete_id}>
                                            {ath.name} {ath.sport ? `(${ath.sport})` : ""}
                                        </option>
                                    ))
                                )}
                            </select>
                        </div>

                        {/* Assessment Selector */}
                        <div className="control-group">
                            <label className="generator-label">Assessment Video</label>
                            <select
                                className="generator-select"
                                value={selectedVideoId}
                                onChange={(e) => setSelectedVideoId(e.target.value)}
                            >
                                <option value="">Latest Completed Assessment</option>
                                {athleteAssessments.map((ass) => (
                                    <option key={ass.video_id} value={ass.video_id}>
                                        {ass.title || ass.original_filename} — {ass.uploaded_at ? new Date(ass.uploaded_at).toLocaleDateString() : "N/A"} ({ass.analysis_status || "Completed"})
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Generator Action Buttons */}
                    <div className="generator-actions-row">
                        <button
                            type="button"
                            className="btn btn-primary generate-main-btn"
                            onClick={handleGenerateReport}
                            disabled={generating || !selectedAthleteId}
                        >
                            <Eye size={16} />
                            <span>{generating ? "Generating..." : "Generate & View Report"}</span>
                        </button>

                        <button
                            type="button"
                            className="btn btn-secondary export-action-btn"
                            onClick={handleExportPdf}
                            disabled={exportingPdf || !selectedAthleteId}
                        >
                            <Download size={16} />
                            <span>{exportingPdf ? "Exporting PDF..." : "Export PDF"}</span>
                        </button>

                        <button
                            type="button"
                            className="btn btn-secondary export-action-btn"
                            onClick={handleExportExcel}
                            disabled={exportingExcel || !selectedAthleteId}
                        >
                            <FileSpreadsheet size={16} />
                            <span>{exportingExcel ? "Exporting Excel..." : "Export Excel (.xlsx)"}</span>
                        </button>
                    </div>
                </div>

                {/* ── REPORTS & ASSESSMENTS TABLE ─────────────────────────────────── */}
                <div className="reports-table-card">
                    <div className="table-card-header">
                        <div>
                            <h3 className="table-card-title">Available Assessment Reports</h3>
                            <p className="table-card-subtitle">
                                Browse recent video assessments and generate one-click exports.
                            </p>
                        </div>

                        <div className="table-filter-controls">
                            <div className="search-input-wrapper">
                                <Search size={15} className="search-icon" />
                                <input
                                    type="text"
                                    placeholder="Search athlete, sport, or report..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="table-search-input"
                                />
                            </div>

                            <select
                                className="table-filter-select"
                                value={dateFilter}
                                onChange={(e) => setDateFilter(e.target.value)}
                            >
                                <option value="all">All Dates</option>
                                <option value="30days">Last 30 Days</option>
                            </select>
                        </div>
                    </div>

                    {filteredReportsList.length === 0 ? (
                        <div className="reports-empty-state">
                            <FileText size={40} className="empty-icon" />
                            <h4>No Reports Found</h4>
                            <p>
                                {searchQuery
                                    ? "No reports match your search query."
                                    : "No assessments are available to generate reports. Upload a video to get started."}
                            </p>
                        </div>
                    ) : (
                        <div className="report-table-wrapper">
                            <table className="reports-list-table">
                                <thead>
                                    <tr>
                                        <th>Report Type</th>
                                        <th>Athlete</th>
                                        <th>Sport</th>
                                        <th>Date</th>
                                        <th>Status</th>
                                        <th>Risk Screening</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredReportsList.map((item, idx) => {
                                        const isRowActive =
                                            actionRowId === (item.video_id || item.athlete_id);

                                        return (
                                            <tr key={item.video_id || `${item.athlete_id}-${idx}`}>
                                                <td className="font-semibold text-slate-800">
                                                    {item.report_type_label}
                                                </td>
                                                <td className="font-medium text-slate-900">
                                                    {item.athlete_name}
                                                </td>
                                                <td className="text-slate-600">
                                                    {item.sport || "Data unavailable"}
                                                </td>
                                                <td className="text-slate-600">
                                                    {item.date
                                                        ? new Date(item.date).toLocaleDateString()
                                                        : "Data unavailable"}
                                                </td>
                                                <td>
                                                    <span
                                                        className={`status-pill ${
                                                            item.status === "COMPLETED" || item.status === "completed"
                                                                ? "pill-success"
                                                                : (item.status === "FAILED" || item.status === "failed" ? "pill-danger" : "pill-muted")
                                                        }`}
                                                    >
                                                        {item.status}
                                                    </span>
                                                </td>
                                                <td>
                                                    {item.risk_level ? (
                                                        <RiskBadge level={item.risk_level} />
                                                    ) : (
                                                        <span className="text-muted text-xs">Pending</span>
                                                    )}
                                                </td>
                                                <td>
                                                    <div className="table-actions-cell">
                                                        <button
                                                            type="button"
                                                            className="table-action-link text-primary"
                                                            onClick={() => handleRowView(item)}
                                                            disabled={isRowActive && actionType === "view"}
                                                            title="Preview Report"
                                                        >
                                                            <Eye size={15} />
                                                            <span>View</span>
                                                        </button>

                                                        <button
                                                            type="button"
                                                            className="table-action-link text-slate-700"
                                                            onClick={() => handleRowPdf(item)}
                                                            disabled={isRowActive && actionType === "pdf"}
                                                            title="Download PDF"
                                                        >
                                                            <Download size={14} />
                                                            <span>PDF</span>
                                                        </button>

                                                        <button
                                                            type="button"
                                                            className="table-action-link text-emerald-700"
                                                            onClick={() => handleRowExcel(item)}
                                                            disabled={isRowActive && actionType === "excel"}
                                                            title="Download Excel"
                                                        >
                                                            <FileSpreadsheet size={14} />
                                                            <span>Excel</span>
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>

                {/* ── REPORT PREVIEW MODAL ─────────────────────────────────────── */}
                {activeReportPayload && (
                    <ReportViewer
                        payload={activeReportPayload}
                        onClose={() => setActiveReportPayload(null)}
                    />
                )}
            </main>
        </div>
    );
}

export default Reports;
