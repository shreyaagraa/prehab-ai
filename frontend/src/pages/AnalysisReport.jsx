/**
 * AnalysisReport.jsx
 * ──────────────────
 * Historical analysis report page.  Loads a previous analysis by video ID
 * from the URL param (:videoId) and renders it with AnalysisReportView.
 *
 * DOES NOT trigger a new analysis — only reads stored results.
 *
 * Route: /analysis/:videoId
 */

import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, History, AlertTriangle, Clock } from "lucide-react";

import AnalysisReportView from "../components/AnalysisReportView";
import {
    getAnalysisStatus,
    getAnalysisFeatures,
    getLessResult,
    getRecommendations,
    getMediaBaseUrl,
} from "../api/videos";

function AnalysisReport() {
    const { videoId } = useParams();
    const mediaBase   = getMediaBaseUrl();

    const [statusData,       setStatusData]       = useState(null);
    const [features,         setFeatures]         = useState(null);
    const [less,             setLess]             = useState(null);
    const [recommendations,  setRecommendations]  = useState(null);
    const [loading,          setLoading]          = useState(true);
    const [error,            setError]            = useState("");

    useEffect(() => {
        if (!videoId) return;

        let cancelled = false;

        async function loadAnalysis() {
            setLoading(true);
            setError("");

            try {
                // Primary: analysis status (required — also returns video_url + original_filename)
                const sd = await getAnalysisStatus(videoId);
                if (cancelled) return;
                setStatusData(sd);
                if (sd?.recommendations) {
                    setRecommendations(sd.recommendations);
                }

                // Secondary: features + LESS + Recommendations (best-effort, only when completed)
                if (sd.status === "COMPLETED") {
                    try {
                        const feat = await getAnalysisFeatures(videoId);
                        if (!cancelled) setFeatures(feat);
                    } catch {
                        // Features unavailable — non-fatal, report still renders
                    }

                    try {
                        const lessData = await getLessResult(videoId);
                        if (!cancelled) setLess(lessData);
                    } catch {
                        // LESS unavailable — non-fatal
                    }

                    if (!sd?.recommendations) {
                        try {
                            const recData = await getRecommendations(videoId);
                            if (!cancelled) setRecommendations(recData);
                        } catch {
                            // Recommendations unavailable — non-fatal
                        }
                    }
                }
            } catch (err) {
                if (!cancelled) {
                    const code = err.response?.status;
                    if (code === 403) {
                        setError("You do not have permission to view this analysis.");
                    } else if (code === 404) {
                        setError("Analysis not found. The video may not have been analyzed yet.");
                    } else {
                        setError(
                            err.response?.data?.detail ||
                            "Failed to load analysis. Please try again."
                        );
                    }
                }
            } finally {
                if (!cancelled) setLoading(false);
            }
        }

        loadAnalysis();
        return () => { cancelled = true; };
    }, [videoId]);

    return (
        <div className="app-layout">
            <main className="dashboard">
                {/* ── Navigation bar ─────────────────────────────────── */}
                <div className="arv2-nav-bar">
                    <Link
                        to="/analysis/history"
                        className="arv2-back-btn"
                        id="back-to-history-link"
                    >
                        <ArrowLeft size={15} />
                        Back to Analysis History
                    </Link>
                </div>

                {/* ── Loading ────────────────────────────────────────── */}
                {loading && (
                    <div className="arv2-loading-state">
                        <div className="arv2-loading-ring" />
                        <span className="arv2-loading-text">Loading AI analysis report…</span>
                    </div>
                )}

                {/* ── Error ──────────────────────────────────────────── */}
                {!loading && error && (
                    <div className="arv2-error-state">
                        <div className="arv2-error-icon">
                            <AlertTriangle size={22} />
                        </div>
                        <div>
                            <p className="arv2-error-title">Unable to Load Report</p>
                            <p className="arv2-error-msg">{error}</p>
                        </div>
                        <Link
                            to="/analysis/history"
                            className="arv2-back-btn"
                            style={{ marginTop: 16 }}
                        >
                            <History size={14} />
                            Return to History
                        </Link>
                    </div>
                )}

                {/* ── Analysis not yet completed ─────────────────────── */}
                {!loading && !error && statusData && statusData.status !== "COMPLETED" && (
                    <div className="arv2-status-pending">
                        <div className="arv2-status-pending-icon">
                            <Clock size={20} />
                        </div>
                        <div>
                            <p className="arv2-status-pending-title">
                                Analysis {statusData.status}
                            </p>
                            <p className="arv2-status-pending-msg">
                                This analysis has status <strong>{statusData.status}</strong> and is not yet complete.
                                {statusData.error_message && (
                                    <span style={{ display: "block", marginTop: 4, fontSize: 12, color: "#92400e" }}>
                                        {statusData.error_message}
                                    </span>
                                )}
                            </p>
                        </div>
                    </div>
                )}

                {/* ── Full report — only when COMPLETED ─────────────── */}
                {!loading && !error && statusData && statusData.status === "COMPLETED" && (
                    <AnalysisReportView
                        videoUrl={statusData.video_url}
                        mediaBase={mediaBase}
                        filename={statusData.original_filename}
                        analysisStatus={statusData}
                        features={features}
                        less={less}
                        recommendations={recommendations}
                    />
                )}
            </main>
        </div>
    );
}

export default AnalysisReport;
