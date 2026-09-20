"""
app/services/analysis_pipeline.py
------------------------------------
Orchestrates the full video analysis pipeline:

  video file → OpenCV (validate + extract frames)
             → MediaPipe Pose (per-frame landmark extraction)
             → PostgreSQL (bulk-insert pose_landmarks, update analysis_results)

This module is called from the FastAPI BackgroundTasks handler so it runs
after the HTTP response has been sent to the client.

Status flow:
    PENDING → PROCESSING → COMPLETED
                        ↘ FAILED (on any exception)

Error handling:
- All exceptions are caught at the top level.
- The error message is saved to analysis_results.error_message.
- The DB session is rolled back before setting FAILED status.
- The background worker never raises — a crash here would silently kill the
  thread without updating the status row.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.analysis_result import (
    AnalysisResult,
    ANALYSIS_STATUS_PROCESSING,
    ANALYSIS_STATUS_COMPLETED,
    ANALYSIS_STATUS_FAILED,
)
from app.models.pose_landmark import PoseLandmark
from app.services.video_processor import VideoProcessingService, VideoProcessingError
from app.services.pose_estimator import MediaPipePoseEstimator, BasePoseEstimator

logger = logging.getLogger(__name__)

from app.core.storage import UPLOAD_DIR, resolve_video_path
from app.services import less_scorer


def run_analysis_pipeline(
    analysis_id: uuid.UUID,
    video_url: str,
    db: Session,
    frame_sample_rate: int = 5,
    max_processed_frames: int = 300,
    pose_estimator: BasePoseEstimator | None = None,
) -> less_scorer.LESSResult | None:
    """
    Full analysis pipeline executed as a background task.

    Parameters
    ----------
    analysis_id : UUID
        Primary key of the AnalysisResult row to update.
    video_url : str
        The ``video_url`` field from the Video row (e.g. "/uploads/abc_video.mp4").
        The actual file path is resolved relative to ``UPLOAD_DIR``.
    db : Session
        SQLAlchemy session.  The caller owns this session and must close it
        after this function returns.
    frame_sample_rate : int
        Passed to VideoProcessingService.
    max_processed_frames : int
        Passed to VideoProcessingService.
    pose_estimator : BasePoseEstimator | None
        Injectable pose estimator (for testing).  Defaults to
        ``MediaPipePoseEstimator``.
    """
    # ── 1. Fetch the analysis record ──────────────────────────────────────────
    analysis: AnalysisResult | None = db.get(AnalysisResult, analysis_id)
    if analysis is None:
        logger.error("run_analysis_pipeline: analysis_id %s not found", analysis_id)
        return

    try:
        # ── 2. Set status → PROCESSING ────────────────────────────────────────
        analysis.status = ANALYSIS_STATUS_PROCESSING
        db.commit()
        logger.info("Analysis %s: status → PROCESSING", analysis_id)

        # ── 3. Resolve video file path ────────────────────────────────────────
        video_path = resolve_video_path(video_url)

        # ── 4. Extract frames with OpenCV ─────────────────────────────────────
        video_svc = VideoProcessingService(
            frame_sample_rate=frame_sample_rate,
            max_processed_frames=max_processed_frames,
        )
        extraction = video_svc.process(video_path)

        # Persist video metadata immediately
        meta = extraction.metadata
        analysis.fps              = meta.fps
        analysis.frame_count      = meta.frame_count
        analysis.duration_seconds = meta.duration_seconds
        analysis.width            = meta.width
        analysis.height           = meta.height
        db.commit()

        # ── 5. Run pose estimation ────────────────────────────────────────────
        estimator = pose_estimator or MediaPipePoseEstimator()

        landmark_rows: list[PoseLandmark] = []
        frames_with_pose = 0

        with estimator:
            for ef in extraction.frames:
                result = estimator.process_frame(
                    frame_number=ef.frame_number,
                    timestamp_ms=ef.timestamp_ms,
                    image_bgr=ef.image,
                )
                if result is None:
                    continue  # no person detected in this frame — skip

                frames_with_pose += 1
                for lm in result.landmarks:
                    landmark_rows.append(
                        PoseLandmark(
                            landmark_id=uuid.uuid4(),
                            analysis_id=analysis_id,
                            frame_number=ef.frame_number,
                            timestamp_ms=ef.timestamp_ms,
                            landmark_index=lm.landmark_index,
                            landmark_name=lm.landmark_name,
                            x=lm.x,
                            y=lm.y,
                            z=lm.z,
                            visibility=lm.visibility,
                        )
                    )

        # ── 6. Bulk-insert pose landmarks ─────────────────────────────────────
        if landmark_rows:
            db.bulk_save_objects(landmark_rows)
            db.commit()

        # ── 7. Extract biomechanical features ─────────────────────────────────
        if landmark_rows:
            from app.services.feature_extractor import FeatureExtractor  # noqa: PLC0415
            FeatureExtractor.extract_and_save(analysis_id, db)
            logger.info("Analysis %s: Biomechanical features extracted and saved", analysis_id)

        # ── 8. Calculate & Persist LESS Approximation Score ─────────────────────
        less_result = None
        if landmark_rows:
            try:
                less_result = less_scorer.LESSApproximationScorer.score_landmarks(landmark_rows)
                
                # Persist LESS result to database
                from app.models.analysis_less import AnalysisLESS  # noqa: PLC0415
                items_serialized = [
                    {
                        "item_number": item.item_number,
                        "item_name": item.item_name,
                        "status": item.status,
                        "score": item.score,
                        "measured_value": item.measured_value,
                        "criterion_threshold": item.criterion_threshold,
                        "unit": item.unit,
                        "reference": item.reference,
                        "reason": item.reason,
                    }
                    for item in less_result.items
                ]
                
                less_record = AnalysisLESS(
                    analysis_id=analysis_id,
                    score=less_result.score,
                    max_computable_score=less_result.max_computable_score,
                    computable_items=less_result.computable_items,
                    error_items=less_result.error_items,
                    not_computable_items=less_result.not_computable_items,
                    classification=less_result.classification,
                    source=less_result.source,
                    validation_source=less_result.validation_source,
                    source_version=less_result.source_version,
                    disclaimer=less_result.disclaimer,
                    items=items_serialized,
                )
                db.add(less_record)
                db.commit()

                logger.info(
                    "Analysis %s: LESS Scorer completed & persisted — "
                    "landmarks_used=%d, computable_items=%d, not_computable_items=%d, "
                    "score=%d, max_computable_score=%d, classification='%s'",
                    analysis_id,
                    len(landmark_rows),
                    less_result.computable_items,
                    less_result.not_computable_items,
                    less_result.score,
                    less_result.max_computable_score,
                    less_result.classification,
                )
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                logger.exception(
                    "Analysis %s: LESSApproximationScorer failed (non-fatal) — %s",
                    analysis_id,
                    exc,
                )

        # ── 8.5. Calculate & Persist Overall Risk Score ─────────────────────────
        try:
            from app.services.risk_scoring_service import RiskScoringService  # noqa: PLC0415
            risk_service = RiskScoringService()
            risk_service.compute_and_persist(analysis_id=analysis_id, db=db)
            logger.info("Analysis %s: RiskScoringService completed & persisted", analysis_id)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.exception(
                "Analysis %s: RiskScoringService failed (non-fatal) — %s",
                analysis_id,
                exc,
            )

        # ── 9. Mark COMPLETED ──────────────────────────────────────────────────
        analysis.frames_processed = frames_with_pose
        analysis.status           = ANALYSIS_STATUS_COMPLETED
        analysis.completed_at     = datetime.utcnow()
        db.commit()

        logger.info(
            "Analysis %s: COMPLETED — %d frames with pose, %d landmarks stored",
            analysis_id,
            frames_with_pose,
            len(landmark_rows),
        )

        # ── 10. Generate Notifications (Non-blocking) ──────────────────────────
        try:
            from app.services.notification_service import NotificationService  # noqa: PLC0415
            NotificationService.notify_assessment_completed(db=db, analysis_id=analysis_id)
            logger.info("Analysis %s: Notifications dispatched successfully", analysis_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Analysis %s: Failed to dispatch completion notifications (non-fatal) — %s", analysis_id, exc)

        return less_result

    except VideoProcessingError as exc:
        _mark_failed(db, analysis, str(exc))
        logger.warning("Analysis %s: VideoProcessingError — %s", analysis_id, exc)

    except Exception as exc:  # noqa: BLE001
        _mark_failed(db, analysis, f"Unexpected error: {exc}")
        logger.exception("Analysis %s: unexpected error", analysis_id)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _mark_failed(db: Session, analysis: AnalysisResult, message: str) -> None:
    """
    Roll back any pending transaction and persistently record the failure.

    This function swallows its own exceptions to ensure the background
    worker never propagates an error silently.
    """
    try:
        db.rollback()
        analysis.status        = ANALYSIS_STATUS_FAILED
        analysis.error_message = message
        analysis.completed_at  = datetime.utcnow()
        db.commit()
    except Exception:  # noqa: BLE001
        logger.exception(
            "Analysis %s: CRITICAL — could not persist FAILED status",
            analysis.analysis_id,
        )
        return

    # Trigger failure notification safely
    try:
        from app.services.notification_service import NotificationService  # noqa: PLC0415
        NotificationService.notify_assessment_failed(db=db, analysis_id=analysis.analysis_id, error_message=message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analysis %s: Failed to dispatch failure notification (non-fatal) — %s", analysis.analysis_id, exc)
