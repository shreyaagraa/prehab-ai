/**
 * AIPoseVideoPlayer.jsx
 * ──────────────────────
 * Polished, high-performance AI Pose Skeleton Overlay Video Player.
 *
 * Base Layer: Original uploaded HTML5 video (untouched, non-destructive).
 * Overlay Layer: Transparent HTML5 Canvas synchronized to video playback.
 * Frame Sync: video.currentTime (ms) -> binary search nearest MediaPipe timestamp.
 *
 * Single Source of Truth: Uses pre-extracted 33 MediaPipe pose landmarks
 * from the database, scoped to the exact analysis_id.
 */

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import {
    Activity,
    Eye,
    EyeOff,
    CheckCircle2,
    Layers,
    FileVideo,
    Sparkles,
    AlertCircle,
    Cpu,
    Maximize2,
} from "lucide-react";

// ── MediaPipe 33-Landmark Pose Topology Connections ──────────────────────────
const POSE_CONNECTIONS = [
    // Head / Facial landmarks
    [0, 1], [1, 2], [2, 3], [3, 7],
    [0, 4], [4, 5], [5, 6], [6, 8],
    [9, 10],

    // Torso / Core
    [11, 12], // Left shoulder - Right shoulder
    [11, 23], // Left shoulder - Left hip
    [12, 24], // Right shoulder - Right hip
    [23, 24], // Left hip - Right hip

    // Left Upper Extremity
    [11, 13], // Left shoulder - Left elbow
    [13, 15], // Left elbow - Left wrist
    [15, 17], [15, 19], [15, 21], [17, 19], // Left hand/fingers

    // Right Upper Extremity
    [12, 14], // Right shoulder - Right elbow
    [14, 16], // Right elbow - Right wrist
    [16, 18], [16, 20], [16, 22], [18, 20], // Right hand/fingers

    // Left Lower Extremity
    [23, 25], // Left hip - Left knee
    [25, 27], // Left knee - Left ankle
    [27, 29], // Left ankle - Left heel
    [29, 31], // Left heel - Left foot index
    [27, 31], // Left ankle - Left foot index

    // Right Lower Extremity
    [24, 26], // Right hip - Right knee
    [26, 28], // Right knee - Right ankle
    [28, 30], // Right ankle - Right heel
    [30, 32], // Right heel - Right foot index
    [28, 32], // Right ankle - Right foot index
];

// Key anatomical landmarks for accent highlights
const ACCENT_JOINTS = new Set([11, 12, 23, 24, 25, 26, 27, 28]); // Shoulders, hips, knees, ankles

// Minimum visibility confidence threshold to render landmark
const MIN_VISIBILITY_THRESHOLD = 0.20;

// Maximum time delta (ms) to consider a landmark frame matched to video.currentTime
const MAX_TIME_DIFF_MS = 350;

function AIPoseVideoPlayer({
    videoUrl,
    mediaBase,
    filename,
    landmarksData,
    loadingLandmarks = false,
    title = "AI Pose Visualization",
    subtitle = "Visual representation of detected body landmarks during the assessment",
}) {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const containerRef = useRef(null);
    const animFrameRef = useRef(null);

    const [skeletonEnabled, setSkeletonEnabled] = useState(true);
    const [videoLoaded, setVideoLoaded] = useState(false);
    const [videoError, setVideoError] = useState(false);
    const [currentFrameNumber, setCurrentFrameNumber] = useState(null);

    // Resolve full video source URL
    const videoSrc = useMemo(() => {
        if (!videoUrl) return null;
        if (videoUrl.startsWith("http://") || videoUrl.startsWith("https://") || videoUrl.startsWith("blob:")) {
            return videoUrl;
        }
        const base = (mediaBase || "").replace(/\/$/, "");
        const path = videoUrl.startsWith("/") ? videoUrl : `/${videoUrl}`;
        return `${base}${path}`;
    }, [videoUrl, mediaBase]);

    // Pre-sort frames by timestamp_ms for binary search
    const sortedFrames = useMemo(() => {
        if (!landmarksData?.frames || !Array.isArray(landmarksData.frames) || landmarksData.frames.length === 0) {
            return [];
        }
        return [...landmarksData.frames].sort((a, b) => a.timestamp_ms - b.timestamp_ms);
    }, [landmarksData]);

    const hasPoseData = Boolean(landmarksData?.has_pose_data && sortedFrames.length > 0);

    /**
     * Binary search to find the nearest landmark frame to the current video playback time (ms).
     */
    const getNearestFrame = useCallback((currentTimeMs) => {
        if (sortedFrames.length === 0) return null;
        if (sortedFrames.length === 1) return sortedFrames[0];

        let low = 0;
        let high = sortedFrames.length - 1;

        while (low <= high) {
            const mid = Math.floor((low + high) / 2);
            const diff = sortedFrames[mid].timestamp_ms - currentTimeMs;

            if (Math.abs(diff) <= 15) {
                return sortedFrames[mid];
            }
            if (sortedFrames[mid].timestamp_ms < currentTimeMs) {
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }

        // Clamp to nearest bound
        const idx1 = Math.max(0, Math.min(sortedFrames.length - 1, low));
        const idx2 = Math.max(0, Math.min(sortedFrames.length - 1, high));

        const dist1 = Math.abs(sortedFrames[idx1].timestamp_ms - currentTimeMs);
        const dist2 = Math.abs(sortedFrames[idx2].timestamp_ms - currentTimeMs);

        const nearest = dist1 < dist2 ? sortedFrames[idx1] : sortedFrames[idx2];
        const minDistance = Math.min(dist1, dist2);

        // Discard if video is seeked beyond landmark coverage window
        if (minDistance > MAX_TIME_DIFF_MS) {
            return null;
        }

        return nearest;
    }, [sortedFrames]);

    /**
     * Renders the MediaPipe human pose skeleton onto the transparent overlay canvas.
     */
    const renderSkeleton = useCallback(() => {
        const canvas = canvasRef.current;
        const video = videoRef.current;
        if (!canvas || !video) return;

        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!skeletonEnabled || !hasPoseData || video.paused && !videoLoaded && video.readyState < 2) {
            return;
        }

        const currentTimeMs = (video.currentTime || 0) * 1000;
        const matchedFrame = getNearestFrame(currentTimeMs);

        if (!matchedFrame || !matchedFrame.landmarks || matchedFrame.landmarks.length === 0) {
            setCurrentFrameNumber(null);
            return;
        }

        setCurrentFrameNumber(matchedFrame.frame_number);

        // Account for letterboxing/pillarboxing inside the video display element
        const videoWidth = video.videoWidth || 1920;
        const videoHeight = video.videoHeight || 1080;
        const canvasWidth = canvas.width;
        const canvasHeight = canvas.height;

        const videoRatio = videoWidth / videoHeight;
        const canvasRatio = canvasWidth / canvasHeight;

        let renderWidth = canvasWidth;
        let renderHeight = canvasHeight;
        let offsetX = 0;
        let offsetY = 0;

        if (canvasRatio > videoRatio) {
            // Pillarbox: black bars on left/right
            renderWidth = canvasHeight * videoRatio;
            offsetX = (canvasWidth - renderWidth) / 2;
        } else {
            // Letterbox: black bars on top/bottom
            renderHeight = canvasWidth / videoRatio;
            offsetY = (canvasHeight - renderHeight) / 2;
        }

        // Map landmarks by index
        const landmarkMap = new Map();
        for (const lm of matchedFrame.landmarks) {
            if (lm.visibility >= MIN_VISIBILITY_THRESHOLD) {
                landmarkMap.set(lm.landmark_index, {
                    x: offsetX + lm.x * renderWidth,
                    y: offsetY + lm.y * renderHeight,
                    z: lm.z,
                    visibility: lm.visibility,
                    index: lm.landmark_index,
                });
            }
        }

        // 1. Draw Skeleton Lines (Bones / Connections)
        ctx.save();
        ctx.lineWidth = Math.max(2, Math.min(4, canvasWidth / 350));
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.shadowColor = "#00f0ff";
        ctx.shadowBlur = 7;
        ctx.strokeStyle = "#00f0ff";

        for (const [i1, i2] of POSE_CONNECTIONS) {
            const p1 = landmarkMap.get(i1);
            const p2 = landmarkMap.get(i2);

            if (p1 && p2) {
                ctx.beginPath();
                ctx.moveTo(p1.x, p1.y);
                ctx.lineTo(p2.x, p2.y);
                ctx.stroke();
            }
        }
        ctx.restore();

        // 2. Draw Joint Markers
        ctx.save();
        const baseRadius = Math.max(3, Math.min(5.5, canvasWidth / 220));

        for (const [idx, pt] of landmarkMap.entries()) {
            const isAccent = ACCENT_JOINTS.has(idx);
            const r = isAccent ? baseRadius * 1.2 : baseRadius;

            // Outer glow ring
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, r + 1.5, 0, Math.PI * 2);
            ctx.fillStyle = isAccent ? "rgba(0, 240, 255, 0.45)" : "rgba(14, 165, 233, 0.35)";
            ctx.fill();

            // Inner circle
            ctx.beginPath();
            ctx.arc(pt.x, pt.y, r, 0, Math.PI * 2);
            ctx.fillStyle = "#ffffff";
            ctx.fill();

            // Stroke boundary
            ctx.lineWidth = 1.5;
            ctx.strokeStyle = isAccent ? "#00f0ff" : "#38bdf8";
            ctx.stroke();
        }
        ctx.restore();
    }, [skeletonEnabled, hasPoseData, videoLoaded, getNearestFrame]);

    // Resize canvas to match the exact rendered size of the video container
    const syncCanvasResolution = useCallback(() => {
        const canvas = canvasRef.current;
        const video = videoRef.current;
        if (!canvas || !video) return;

        const rect = video.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        if (rect.width > 0 && rect.height > 0) {
            const targetWidth = Math.round(rect.width * dpr);
            const targetHeight = Math.round(rect.height * dpr);

            if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
                canvas.width = targetWidth;
                canvas.height = targetHeight;
                canvas.style.width = `${rect.width}px`;
                canvas.style.height = `${rect.height}px`;
            }
        }

        renderSkeleton();
    }, [renderSkeleton]);

    // Setup animation loop for smooth 60fps synchronization during playback
    useEffect(() => {
        let isRunning = true;

        const loop = () => {
            if (!isRunning) return;
            const video = videoRef.current;
            if (video && !video.paused && !video.ended) {
                renderSkeleton();
            }
            animFrameRef.current = requestAnimationFrame(loop);
        };

        animFrameRef.current = requestAnimationFrame(loop);

        return () => {
            isRunning = false;
            if (animFrameRef.current) {
                cancelAnimationFrame(animFrameRef.current);
            }
        };
    }, [renderSkeleton]);

    // Handle video events
    useEffect(() => {
        const video = videoRef.current;
        if (!video) return;

        const handleLoaded = () => {
            setVideoLoaded(true);
            setVideoError(false);
            syncCanvasResolution();
        };

        const handleTimeUpdate = () => {
            renderSkeleton();
        };

        const handleSeeked = () => {
            renderSkeleton();
        };

        const handleResize = () => {
            syncCanvasResolution();
        };

        video.addEventListener("loadedmetadata", handleLoaded);
        video.addEventListener("timeupdate", handleTimeUpdate);
        video.addEventListener("seeked", handleSeeked);
        video.addEventListener("play", handleTimeUpdate);
        video.addEventListener("pause", handleTimeUpdate);
        window.addEventListener("resize", handleResize);

        return () => {
            video.removeEventListener("loadedmetadata", handleLoaded);
            video.removeEventListener("timeupdate", handleTimeUpdate);
            video.removeEventListener("seeked", handleSeeked);
            video.removeEventListener("play", handleTimeUpdate);
            video.removeEventListener("pause", handleTimeUpdate);
            window.removeEventListener("resize", handleResize);
        };
    }, [syncCanvasResolution, renderSkeleton]);

    // Re-render when toggle or landmarks data changes
    useEffect(() => {
        renderSkeleton();
    }, [skeletonEnabled, landmarksData, renderSkeleton]);

    return (
        <div className="ai-pose-player-card" ref={containerRef}>
            {/* Header / Badges */}
            <div className="ai-pose-player-header">
                <div className="ai-pose-header-left">
                    <div className="ai-pose-header-icon">
                        <Activity size={17} />
                    </div>
                    <div>
                        <div className="ai-pose-title-row">
                            <h3 className="ai-pose-title">{title}</h3>
                            <span className="ai-pose-badge-mp">
                                <Cpu size={11} /> MEDIA-PIPE POSE ESTIMATION
                            </span>
                            {hasPoseData && (
                                <span className="ai-pose-badge-ready">
                                    <CheckCircle2 size={11} /> AI POSE ✓
                                </span>
                            )}
                        </div>
                        <p className="ai-pose-subtitle">{subtitle}</p>
                    </div>
                </div>

                {/* Right controls: AI Skeleton Toggle */}
                {hasPoseData && (
                    <div className="ai-pose-header-right">
                        <button
                            type="button"
                            className={`ai-pose-toggle-btn ${skeletonEnabled ? "ai-pose-toggle-btn--active" : ""}`}
                            onClick={() => setSkeletonEnabled((prev) => !prev)}
                            aria-label="Toggle AI Skeleton Overlay"
                            id="ai-skeleton-toggle-button"
                        >
                            <span className="ai-pose-toggle-icon">
                                {skeletonEnabled ? <Eye size={14} /> : <EyeOff size={14} />}
                            </span>
                            <span className="ai-pose-toggle-text">
                                AI SKELETON: <strong>{skeletonEnabled ? "ON" : "OFF"}</strong>
                            </span>
                            <span className={`ai-pose-toggle-pill ${skeletonEnabled ? "ai-pose-toggle-pill--on" : ""}`} />
                        </button>
                    </div>
                )}
            </div>

            {/* Video & Canvas Stage */}
            <div className="ai-pose-stage-container">
                {videoSrc && !videoError ? (
                    <div className="ai-pose-video-wrapper">
                        {/* Base Layer: Original Video */}
                        <video
                            ref={videoRef}
                            className="ai-pose-video-element"
                            controls
                            playsInline
                            preload="metadata"
                            crossOrigin="anonymous"
                            onError={() => setVideoError(true)}
                        >
                            <source src={videoSrc} />
                            Your browser does not support HTML5 video playback.
                        </video>

                        {/* Overlay Layer: Transparent Canvas */}
                        <canvas
                            ref={canvasRef}
                            className={`ai-pose-canvas-overlay ${!skeletonEnabled ? "ai-pose-canvas--hidden" : ""}`}
                            aria-hidden="true"
                        />

                        {/* Loading / Status overlay chips */}
                        {loadingLandmarks && (
                            <div className="ai-pose-status-chip ai-pose-status-chip--loading">
                                <span className="ai-pose-spinner-sm" />
                                <span>Preparing AI Pose Visualization…</span>
                            </div>
                        )}

                        {!loadingLandmarks && !hasPoseData && videoLoaded && (
                            <div className="ai-pose-status-chip ai-pose-status-chip--notice">
                                <AlertCircle size={13} />
                                <span>Pose visualization unavailable for this assessment.</span>
                            </div>
                        )}

                        {skeletonEnabled && hasPoseData && currentFrameNumber !== null && (
                            <div className="ai-pose-frame-tag">
                                <Layers size={11} />
                                <span>Frame #{currentFrameNumber} · 33 Keypoints</span>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="ai-pose-video-placeholder">
                        <FileVideo size={40} strokeWidth={1.5} className="ai-pose-placeholder-icon" />
                        <p className="ai-pose-placeholder-title">
                            {videoError ? "Video Playback Error" : "No Assessment Video Available"}
                        </p>
                        <p className="ai-pose-placeholder-desc">
                            {videoError
                                ? "The video file could not be loaded. It may have been removed or is temporarily unreachable."
                                : "No assessment video recording is linked to this analysis report."}
                        </p>
                    </div>
                )}
            </div>

            {/* Footer Bar info */}
            {filename && (
                <div className="ai-pose-player-footer">
                    <span className="ai-pose-footer-filename">
                        <FileVideo size={13} /> {filename}
                    </span>
                    {hasPoseData && (
                        <span className="ai-pose-footer-info">
                            {sortedFrames.length} synchronized pose frames · Normalized coordinate mesh
                        </span>
                    )}
                </div>
            )}
        </div>
    );
}

export default AIPoseVideoPlayer;
