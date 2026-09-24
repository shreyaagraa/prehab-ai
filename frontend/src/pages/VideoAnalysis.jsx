import { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import {
    Upload,
    Video,
    Activity,
    User,
    AlertTriangle,
    CheckCircle2,
    FileVideo,
    Play,
    Clock,
    Loader2,
    XCircle,
    History,
    Sparkles,
    FileUp,
    Trash2,
    ArrowDown,
    ShieldAlert,
    Info,
} from "lucide-react";

import AnalysisReportView from "../components/AnalysisReportView";
import RiskBadge from "../components/RiskBadge";
import {
    uploadVideoFile,
    triggerAnalysis,
    getAnalysisStatus,
    getAnalysisFeatures,
    getLessResult,
    getRecommendations,
    getMediaBaseUrl,
} from "../api/videos";
import { getMyAthleteProfile } from "../api/athletes";

import ConsentGateModal from "../components/ConsentGateModal";
import { getConsentStatus } from "../api/consent";

const REQUIRED_FIELDS = ["sport", "position", "age", "height", "weight"];

function isProfileComplete(profile) {
    if (!profile) return false;
    return REQUIRED_FIELDS.every(
        (f) =>
            profile[f] !== null &&
            profile[f] !== undefined &&
            profile[f] !== ""
    );
}

function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024)
        return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

const STATUS_PENDING = "PENDING";
const STATUS_PROCESSING = "PROCESSING";
const STATUS_COMPLETED = "COMPLETED";
const STATUS_FAILED = "FAILED";

const POLL_INTERVAL_MS = 2000;

function VideoAnalysis() {
    const mediaBase = getMediaBaseUrl();

    // Profile state
    const [profile, setProfile] = useState(null);
    const [profileLoading, setProfileLoading] = useState(true);
    const [profileError, setProfileError] = useState("");

    // Consent modal state
    const [showConsentModal, setShowConsentModal] = useState(false);
    const [pendingUploadFile, setPendingUploadFile] = useState(null);

    // Upload state
    const [file, setFile] = useState(null);
    const [previewUrl, setPreviewUrl] = useState(null);
    const [isDragging, setIsDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [uploadPct, setUploadPct] = useState(0);
    const [uploadedVideo, setUploadedVideo] = useState(null);
    const [uploadError, setUploadError] = useState("");

    // Analysis state
    const [analysisId, setAnalysisId] = useState(null);
    const [analysisStatus, setAnalysisStatus] = useState(null);
    const [analysisFeatures, setAnalysisFeatures] = useState(null);
    const [analysisLess, setAnalysisLess] = useState(null);
    const [analysisRecommendations, setAnalysisRecommendations] = useState(null);
    const [analyzing, setAnalyzing] = useState(false);
    const [analyzeError, setAnalyzeError] = useState("");

    const pollRef = useRef(null);
    const reportRef = useRef(null);

    // Fetch profile on mount
    useEffect(() => {
        async function fetchProfile() {
            setProfileLoading(true);
            setProfileError("");
            try {
                const data = await getMyAthleteProfile();
                setProfile(data);
            } catch (err) {
                if (err.response?.status === 404 || err.response?.status === 403) {
                    setProfile(null);
                } else {
                    setProfileError(
                        err.response?.data?.detail || "Could not load athlete profile."
                    );
                }
            } finally {
                setProfileLoading(false);
            }
        }

        fetchProfile();
    }, []);

    // Cleanup object URL & polling timer
    useEffect(() => {
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
            if (previewUrl) URL.revokeObjectURL(previewUrl);
        };
    }, [previewUrl]);

    // Handle file selection
    function handleSelectedFile(selectedFile) {
        if (!selectedFile) return;

        // Check type
        if (!selectedFile.type.startsWith("video/")) {
            setUploadError("Please select a valid video file (.mp4, .mov, .avi).");
            return;
        }

        if (previewUrl) URL.revokeObjectURL(previewUrl);

        setFile(selectedFile);
        setPreviewUrl(URL.createObjectURL(selectedFile));
        setUploadError("");
        setUploadedVideo(null);
        setUploadPct(0);
        setAnalysisId(null);
        setAnalysisStatus(null);
        setAnalysisFeatures(null);
        setAnalysisLess(null);
        setAnalyzeError("");
        if (pollRef.current) clearInterval(pollRef.current);
    }

    function handleFileInputChange(event) {
        const selectedFile = event.target.files?.[0];
        handleSelectedFile(selectedFile);
    }

    // Drag and drop handlers
    function handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(true);
    }

    function handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }

    function handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);

        const droppedFile = e.dataTransfer.files?.[0];
        if (droppedFile) {
            handleSelectedFile(droppedFile);
        }
    }

    function handleClearFile() {
        if (previewUrl) URL.revokeObjectURL(previewUrl);
        setFile(null);
        setPreviewUrl(null);
        setUploadedVideo(null);
        setUploadError("");
        setUploadPct(0);
        setAnalysisId(null);
        setAnalysisStatus(null);
        setAnalysisFeatures(null);
        setAnalysisLess(null);
        setAnalysisRecommendations(null);
        setAnalyzeError("");
        if (pollRef.current) clearInterval(pollRef.current);
    }

    // Analyze handler
    const handleAnalyze = useCallback(async (targetVideoId = null) => {
        const videoId = typeof targetVideoId === "string" ? targetVideoId : uploadedVideo?.video_id;
        if (!videoId) return;
        if (analyzing) return;

        setAnalyzing(true);
        setAnalyzeError("");
        setAnalysisId(null);
        setAnalysisStatus(null);
        setAnalysisFeatures(null);
        setAnalysisLess(null);
        setAnalysisRecommendations(null);
        if (pollRef.current) clearInterval(pollRef.current);

        try {
            const triggerResp = await triggerAnalysis(videoId);
            setAnalysisId(triggerResp.analysis_id);

            pollRef.current = setInterval(async () => {
                try {
                    const statusObj = await getAnalysisStatus(videoId);
                    setAnalysisStatus(statusObj);

                    const st = statusObj.status;

                    if (st === STATUS_COMPLETED) {
                        clearInterval(pollRef.current);
                        pollRef.current = null;
                        setAnalyzing(false);

                        // Fetch features & LESS results
                        try {
                            const featObj = await getAnalysisFeatures(videoId);
                            setAnalysisFeatures(featObj);
                        } catch {
                            // Non-fatal
                        }
                        try {
                            const lessObj = await getLessResult(videoId);
                            setAnalysisLess(lessObj);
                        } catch {
                            // Non-fatal
                        }
                        if (!statusObj.recommendations) {
                            try {
                                const recObj = await getRecommendations(videoId);
                                setAnalysisRecommendations(recObj);
                            } catch {
                                // Non-fatal
                            }
                        }
                    } else if (st === STATUS_FAILED) {
                        clearInterval(pollRef.current);
                        pollRef.current = null;
                        setAnalyzing(false);
                        setAnalyzeError(
                            statusObj.error_message || "Video analysis failed. Please try again."
                        );
                    }
                } catch (pollErr) {
                    clearInterval(pollRef.current);
                    pollRef.current = null;
                    setAnalyzing(false);
                    setAnalyzeError("Lost connection while checking analysis status.");
                }
            }, POLL_INTERVAL_MS);

        } catch (err) {
            setAnalyzing(false);
            setAnalyzeError(
                err.response?.data?.detail || "Could not start video analysis."
            );
        }
    }, [uploadedVideo, analyzing]);

    async function executeActualUpload(targetFile) {
        const fileToUpload = targetFile || file;
        if (!fileToUpload) return;

        setUploading(true);
        setUploadError("");
        setUploadPct(0);
        setUploadedVideo(null);
        setAnalysisId(null);
        setAnalysisStatus(null);
        setAnalysisFeatures(null);
        setAnalysisLess(null);
        setAnalysisRecommendations(null);
        setAnalyzeError("");

        try {
            const videoMeta = await uploadVideoFile(fileToUpload, (pct) => {
                const numericPct = typeof pct === "number" ? pct : 0;
                setUploadPct(numericPct);
            });
            setUploadedVideo(videoMeta);
            setUploading(false);

            if (videoMeta?.video_id) {
                await handleAnalyze(videoMeta.video_id);
            }
        } catch (err) {
            setUploading(false);
            setUploadError(
                err.response?.data?.detail || "Video upload failed. Please try again."
            );
        }
    }

    // Upload & Analyze workflow with Consent Gate check
    async function handleUpload(event) {
        event.preventDefault();
        if (!file) return;

        setUploadError("");

        // Check consent status before uploading
        try {
            const consentRes = await getConsentStatus();
            if (!consentRes.can_upload) {
                setPendingUploadFile(file);
                setShowConsentModal(true);
                return;
            }
        } catch (err) {
            console.warn("Could not check consent status prior to upload:", err);
        }

        await executeActualUpload(file);
    }

    function handleConsentGranted() {
        setShowConsentModal(false);
        if (pendingUploadFile || file) {
            executeActualUpload(pendingUploadFile || file);
            setPendingUploadFile(null);
        }
    }

    const currentStatus = analysisStatus?.status || (analyzing ? STATUS_PROCESSING : null);

    // Compute active step in workflow tracker (1: Upload, 2: Uploading, 3: Processing, 4: Completed)
    let currentStep = 1;
    if (uploading) currentStep = 2;
    else if (analyzing || currentStatus === STATUS_PROCESSING || currentStatus === STATUS_PENDING) currentStep = 3;
    else if (currentStatus === STATUS_COMPLETED) currentStep = 4;

    const videoSrc = uploadedVideo?.video_url
        ? `${mediaBase}${uploadedVideo.video_url}`
        : analysisStatus?.video_url
            ? `${mediaBase}${analysisStatus.video_url}`
            : previewUrl;

    const isProfileReady = isProfileComplete(profile);

    return (
        <div className="app-layout">
            <main className="dashboard">
                {/* ── Page Header ─────────────────────────────────────────────── */}
                <div className="page-header">
                    <div>
                        <span className="eyebrow">MOVEMENT ANALYSIS</span>
                        <h1>Video Analysis & Risk Evaluation</h1>
                        <p>Upload jump-landing or athletic movement videos for AI biomechanical risk analysis.</p>
                    </div>
                </div>

                {/* Profile Incomplete Warning Banner */}
                {!profileLoading && !isProfileReady && (
                    <div className="profile-alert-banner warning">
                        <ShieldAlert size={18} />
                        <div>
                            <strong>Profile Incomplete:</strong> Complete your athlete profile (sport, position, age, height, weight) for accurate 5-factor risk scoring.
                            {" "}
                            <Link to="/profile" className="alert-link">Update Profile &rarr;</Link>
                        </div>
                    </div>
                )}

                {/* ── Visual Workflow Pipeline Tracker ───────────────────────────── */}
                <div className="workflow-steps-card">
                    <div className={`step-item ${currentStep >= 1 ? "active" : ""}`}>
                        <div className="step-badge">1</div>
                        <span>Upload Video</span>
                    </div>

                    <div className="step-line" />

                    <div className={`step-item ${currentStep >= 2 ? "active" : ""}`}>
                        <div className="step-badge">2</div>
                        <span>Uploading File</span>
                    </div>

                    <div className="step-line" />

                    <div className={`step-item ${currentStep >= 3 ? "active" : ""}`}>
                        <div className="step-badge">3</div>
                        <span>AI Movement Processing</span>
                    </div>

                    <div className="step-line" />

                    <div className={`step-item ${currentStep >= 4 ? "completed" : ""}`}>
                        <div className="step-badge">{currentStep === 4 ? <CheckCircle2 size={14} /> : "4"}</div>
                        <span>Analysis Complete</span>
                    </div>
                </div>

                {/* ── Upload & Processing Panel ─────────────────────────────────── */}
                <section className="panel card-panel">
                    <form onSubmit={handleUpload}>
                        {!file ? (
                            /* Drag & Drop Dropzone */
                            <div
                                className={`upload-dropzone ${isDragging ? "dragging" : ""}`}
                                onDragOver={handleDragOver}
                                onDragLeave={handleDragLeave}
                                onDrop={handleDrop}
                            >
                                <input
                                    type="file"
                                    id="video-file-input"
                                    accept="video/mp4,video/quicktime,video/x-msvideo"
                                    onChange={handleFileInputChange}
                                    style={{ display: "none" }}
                                />

                                <div className="dropzone-icon-circle">
                                    <FileUp size={32} />
                                </div>

                                <h3>Drag and drop your movement video here</h3>
                                <p className="dropzone-hint">
                                    Supports MP4, MOV, or AVI files up to 100MB
                                </p>

                                <label htmlFor="video-file-input" className="primary-button dropzone-browse-btn">
                                    <Upload size={16} />
                                    Browse Files
                                </label>
                            </div>
                        ) : (
                            /* Selected File Preview Card */
                            <div className="file-preview-card">
                                <div className="preview-video-container">
                                    {previewUrl ? (
                                        <video src={previewUrl} className="file-preview-video" controls />
                                    ) : (
                                        <FileVideo size={48} />
                                    )}
                                </div>

                                <div className="file-preview-details">
                                    <div className="file-preview-header">
                                        <div>
                                            <span className="file-format-badge">MP4 / VIDEO</span>
                                            <h4 className="file-name-title">{file.name}</h4>
                                            <span className="file-size-tag">{formatBytes(file.size)}</span>
                                        </div>

                                        {!uploading && !analyzing && currentStatus !== STATUS_COMPLETED && (
                                            <button
                                                type="button"
                                                onClick={handleClearFile}
                                                className="icon-button-danger"
                                                title="Remove File"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        )}
                                    </div>

                                    {/* Upload Progress */}
                                    {uploading && (
                                        <div className="upload-progress-wrapper">
                                            <div className="progress-info">
                                                <span>Uploading video to PreHab AI AI...</span>
                                                <strong>{typeof uploadPct === "number" ? uploadPct : 0}%</strong>
                                            </div>
                                            <div className="progress-bar-track">
                                                <div
                                                    className="progress-bar-fill"
                                                    style={{ width: `${typeof uploadPct === "number" ? uploadPct : 0}%` }}
                                                />
                                            </div>
                                        </div>
                                    )}

                                    {/* Processing & Polling Indicator */}
                                    {analyzing && (
                                        <div className="processing-indicator-box">
                                            <Loader2 size={20} className="spinner-icon text-purple" />
                                            <div>
                                                <strong>Analyzing Movement & Extracting Pose Landmarks...</strong>
                                                <p>MediaPipe pose estimator is detecting joint angles and computing LESS approximation scores.</p>
                                            </div>
                                        </div>
                                    )}

                                    {/* Upload Error */}
                                    {uploadError && <div className="error-box">{uploadError}</div>}
                                    {analyzeError && <div className="error-box">{analyzeError}</div>}

                                    {/* Upload & Analyze Action Button */}
                                    {!uploading && !analyzing && currentStatus !== STATUS_COMPLETED && (
                                        <div className="action-button-row">
                                            <button
                                                type="submit"
                                                className="primary-button hero-cta"
                                                id="start-analysis-btn"
                                            >
                                                <Sparkles size={18} />
                                                Start AI Movement Analysis
                                            </button>

                                            <button
                                                type="button"
                                                onClick={handleClearFile}
                                                className="secondary-button"
                                            >
                                                Choose Different Video
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}
                    </form>
                </section>

                {/* ── Upload Instructions Panel ──────────────────────────────────── */}
                <aside className="upload-instructions-panel">
                    <div className="upload-instructions-header">
                        <Info size={15} className="upload-instructions-icon" />
                        <span>For best analysis results</span>
                    </div>
                    <ul className="upload-instructions-list">
                        <li>Record the athlete in good lighting with the <strong>full body clearly visible</strong> from head to toe.</li>
                        <li>Keep the camera <strong>stable</strong> throughout the movement — avoid shaking or panning.</li>
                        <li>Position the athlete <strong>centered in frame</strong> and visible throughout the entire movement.</li>
                        <li>Capture the <strong>complete movement</strong> from preparation through landing or finish.</li>
                        <li>Use an appropriate <strong>side-view or front-view</strong> angle suited to the movement being assessed (e.g., side view for jump-landing).</li>
                        <li>Ensure no other people or objects are <strong>blocking the athlete</strong>.</li>
                        <li>Use <strong>sufficient video resolution</strong> for clear joint landmark detection.</li>
                    </ul>
                    <div className="upload-instructions-meta">
                        <span className="upload-meta-chip">
                            <FileVideo size={12} />
                            MP4 · MOV · AVI · WebM · MKV
                        </span>
                        <span className="upload-meta-divider" aria-hidden="true">·</span>
                        <span className="upload-meta-chip">
                            <ArrowDown size={12} />
                            Max 500 MB
                        </span>
                    </div>
                </aside>

                {/* ── Post-Analysis Completion Summary Banner ───────────────────── */}
                {currentStatus === STATUS_COMPLETED && (
                    <section className="panel card-panel completion-hero-card">
                        <div className="completion-hero-header">
                            <div className="check-badge">
                                <CheckCircle2 size={24} />
                            </div>
                            <div>
                                <h2>Movement Analysis Complete!</h2>
                                <p>All biomechanical joint landmarks, LESS scores, and 5-factor risk levels calculated.</p>
                            </div>
                        </div>

                        <div className="completion-summary-grid">
                            <div className="completion-metric-box">
                                <span className="metric-label">Overall Risk Score</span>
                                <div className="metric-value-row">
                                    <span className="metric-value-big">
                                        {analysisStatus?.overall_risk_score != null && !isNaN(analysisStatus.overall_risk_score)
                                            ? Math.round(analysisStatus.overall_risk_score)
                                            : "—"}
                                    </span>
                                    <RiskBadge level={analysisStatus?.risk_level || "LOW"} />
                                </div>
                            </div>

                            <div className="completion-metric-box">
                                <span className="metric-label">LESS Score</span>
                                <span className="metric-value-big">
                                    {(analysisLess?.score ?? analysisLess?.less_score) != null
                                        ? `${analysisLess.score ?? analysisLess.less_score}/${analysisLess.max_computable_score || 12}`
                                        : "—"}
                                </span>
                            </div>

                            <div className="completion-actions-row">
                                <button
                                    type="button"
                                    onClick={() => {
                                        reportRef.current?.scrollIntoView({ behavior: "smooth" });
                                    }}
                                    className="primary-button"
                                    id="view-report-scroll-btn"
                                >
                                    <ArrowDown size={16} />
                                    View Full Report Below
                                </button>

                                <Link to="/analysis/history" className="secondary-button">
                                    <History size={16} />
                                    View History
                                </Link>

                                <button
                                    type="button"
                                    onClick={handleClearFile}
                                    className="secondary-button"
                                >
                                    Analyze Another Video
                                </button>
                            </div>
                        </div>
                    </section>
                )}

                {/* ── Detailed Analysis Report View ─────────────────────────────── */}
                {(currentStatus === STATUS_COMPLETED || analysisStatus?.status === STATUS_COMPLETED) && (
                    <div ref={reportRef}>
                        <AnalysisReportView
                            analysisStatus={analysisStatus}
                            analysisFeatures={analysisFeatures}
                            analysisLess={analysisLess}
                            recommendations={analysisRecommendations || analysisStatus?.recommendations}
                            uploadedVideo={uploadedVideo}
                            videoSrc={videoSrc}
                        />
                    </div>
                )}
                {/* ── Consent Gate Modal ─────────────────────────────────────── */}
                <ConsentGateModal
                    isOpen={showConsentModal}
                    onClose={() => setShowConsentModal(false)}
                    onConsentGranted={handleConsentGranted}
                />
            </main>
        </div>
    );
}

export default VideoAnalysis;