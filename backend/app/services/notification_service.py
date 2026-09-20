"""
app/services/notification_service.py
------------------------------------
Service layer for managing real-time notifications and alerts across the
PreHab AI Sports Injury Risk Detection platform.

Features:
- Event-based notification creation (Assessment Completed, Risk Alerts, Corrective Plan Ready, Assessment Failed)
- Strict deduplication at application and query level
- Role-aware recipient dispatch (Athlete and strictly assigned Coach)
- Non-blocking error containment so notification issues never abort analysis completion
- Medical-disclaimer compliant messaging (no diagnosis claims)
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.analysis_result import AnalysisResult
from app.models.video import Video
from app.models.athlete import Athlete
from app.models.user import User, RoleEnum

logger = logging.getLogger(__name__)

# ── Notification Types ────────────────────────────────────────────────────────
TYPE_ASSESSMENT_COMPLETED    = "ASSESSMENT_COMPLETED"
TYPE_CRITICAL_RISK_ALERT     = "CRITICAL_RISK_ALERT"
TYPE_HIGH_RISK_ALERT         = "HIGH_RISK_ALERT"
TYPE_MODERATE_RISK_ALERT     = "MODERATE_RISK_ALERT"
TYPE_CORRECTIVE_PLAN_READY   = "CORRECTIVE_PLAN_READY"
TYPE_ASSESSMENT_FAILED       = "ASSESSMENT_FAILED"
TYPE_GENERAL                 = "GENERAL"

# ── Severity Levels ───────────────────────────────────────────────────────────
SEVERITY_INFO     = "INFO"
SEVERITY_WARNING  = "WARNING"
SEVERITY_HIGH     = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"


class NotificationService:
    """
    Centralized service for creating, retrieving, and dispatching notifications.
    """

    @staticmethod
    def create_notification(
        db: Session,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        message: str,
        severity: str = SEVERITY_INFO,
        related_analysis_id: Optional[uuid.UUID] = None,
        related_video_id: Optional[uuid.UUID] = None,
        action_url: Optional[str] = None,
    ) -> Notification:
        """
        Creates a notification with strict deduplication for analysis events.
        """
        # Deduplication check: if related_analysis_id is set, ensure no duplicate of the same type exists for this user
        if related_analysis_id is not None:
            existing = (
                db.query(Notification)
                .filter(
                    Notification.user_id == user_id,
                    Notification.notification_type == notification_type,
                    Notification.related_analysis_id == related_analysis_id,
                )
                .first()
            )
            if existing is not None:
                logger.debug(
                    "Duplicate notification suppressed for user %s, type %s, analysis %s",
                    user_id,
                    notification_type,
                    related_analysis_id,
                )
                return existing

        notification = Notification(
            notification_id=uuid.uuid4(),
            user_id=user_id,
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            is_read=False,
            created_at=datetime.utcnow(),
            read_at=None,
            related_analysis_id=related_analysis_id,
            related_video_id=related_video_id,
            action_url=action_url,
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        logger.info(
            "Notification created [id=%s, user=%s, type=%s, severity=%s]",
            notification.notification_id,
            user_id,
            notification_type,
            severity,
        )
        return notification

    @classmethod
    def notify_assessment_completed(
        cls,
        db: Session,
        analysis_id: uuid.UUID,
    ) -> list[Notification]:
        """
        Triggered when video analysis pipeline finishes successfully.
        Generates:
        1. Assessment Completed notification.
        2. High / Critical / Moderate Risk Alert (if applicable).
        3. Corrective Action Plan Ready (if recommendations were generated).
        4. Assigned Coach Alert (if athlete has an assigned coach).

        Non-blocking: any exception here is logged and does not bubble up.
        """
        created_notifications: list[Notification] = []

        try:
            analysis = db.get(AnalysisResult, analysis_id)
            if analysis is None:
                logger.warning("notify_assessment_completed: Analysis %s not found", analysis_id)
                return []

            video = db.get(Video, analysis.video_id)
            if video is None:
                logger.warning("notify_assessment_completed: Video %s not found", analysis.video_id)
                return []

            athlete = db.get(Athlete, video.athlete_id)
            if athlete is None:
                logger.warning("notify_assessment_completed: Athlete %s not found", video.athlete_id)
                return []

            athlete_user = db.get(User, athlete.user_id)
            athlete_name = athlete_user.name if athlete_user else "Athlete"

            activity_label = video.title or video.activity or "movement"
            action_url = f"/analysis/{video.video_id}"

            # ── 1. Assessment Completed Notification for Athlete ──────────────
            completed_notif = cls.create_notification(
                db=db,
                user_id=athlete.user_id,
                notification_type=TYPE_ASSESSMENT_COMPLETED,
                title="Assessment Completed",
                message=f"Your {activity_label} assessment is ready to review.",
                severity=SEVERITY_INFO,
                related_analysis_id=analysis.analysis_id,
                related_video_id=video.video_id,
                action_url=action_url,
            )
            created_notifications.append(completed_notif)

            # ── 2. Risk Alert Notification (CRITICAL / HIGH / MODERATE) ────────
            risk_level = (analysis.risk_level or "").upper()
            if risk_level == "CRITICAL":
                risk_notif = cls.create_notification(
                    db=db,
                    user_id=athlete.user_id,
                    notification_type=TYPE_CRITICAL_RISK_ALERT,
                    title="Critical Risk Alert",
                    message="Critical risk indicators detected in your assessment. Please review the biomechanical findings and consider professional evaluation.",
                    severity=SEVERITY_CRITICAL,
                    related_analysis_id=analysis.analysis_id,
                    related_video_id=video.video_id,
                    action_url=action_url,
                )
                created_notifications.append(risk_notif)
            elif risk_level == "HIGH":
                risk_notif = cls.create_notification(
                    db=db,
                    user_id=athlete.user_id,
                    notification_type=TYPE_HIGH_RISK_ALERT,
                    title="High Risk Detected",
                    message="Elevated injury-risk indicators detected: your recent assessment indicates a high injury-risk level. Review the biomechanical findings and corrective action plan.",
                    severity=SEVERITY_HIGH,
                    related_analysis_id=analysis.analysis_id,
                    related_video_id=video.video_id,
                    action_url=action_url,
                )
                created_notifications.append(risk_notif)
            elif risk_level == "MODERATE":
                risk_notif = cls.create_notification(
                    db=db,
                    user_id=athlete.user_id,
                    notification_type=TYPE_MODERATE_RISK_ALERT,
                    title="Moderate Risk Detected",
                    message="Your assessment indicates some biomechanical risk factors that may benefit from corrective training.",
                    severity=SEVERITY_WARNING,
                    related_analysis_id=analysis.analysis_id,
                    related_video_id=video.video_id,
                    action_url=action_url,
                )
                created_notifications.append(risk_notif)

            # ── 3. Corrective Action Plan Ready (Only if plan has recommendations) ─
            try:
                from app.services.recommendation_engine import CorrectiveRecommendationEngine  # noqa: PLC0415
                rec_data = CorrectiveRecommendationEngine.generate_for_analysis(analysis.analysis_id, db)
                has_recs = bool(
                    rec_data.get("exercise_recommendations")
                    or rec_data.get("priority_areas")
                )
                if has_recs:
                    rec_notif = cls.create_notification(
                        db=db,
                        user_id=athlete.user_id,
                        notification_type=TYPE_CORRECTIVE_PLAN_READY,
                        title="Corrective Action Plan Ready",
                        message="New corrective exercises and training recommendations are available.",
                        severity=SEVERITY_INFO,
                        related_analysis_id=analysis.analysis_id,
                        related_video_id=video.video_id,
                        action_url=action_url,
                    )
                    created_notifications.append(rec_notif)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not check recommendations for notification: %s", exc)

            # ── 4. Role-Aware Notification for Assigned Coach ─────────────────
            # Only notify the coach if the athlete has a coach_id explicitly set
            if athlete.coach_id:
                coach = db.get(User, athlete.coach_id)
                if coach and coach.role in (RoleEnum.COACH, RoleEnum.PHYSIOTHERAPIST, RoleEnum.ADMINISTRATOR):
                    coach_severity = (
                        SEVERITY_CRITICAL if risk_level == "CRITICAL"
                        else SEVERITY_HIGH if risk_level == "HIGH"
                        else SEVERITY_WARNING if risk_level == "MODERATE"
                        else SEVERITY_INFO
                    )
                    coach_notif = cls.create_notification(
                        db=db,
                        user_id=athlete.coach_id,
                        notification_type=TYPE_ASSESSMENT_COMPLETED,
                        title=f"Athlete Assessment: {athlete_name}",
                        message=f"{athlete_name} completed a {activity_label} assessment (Risk Level: {risk_level or 'Normal'}).",
                        severity=coach_severity,
                        related_analysis_id=analysis.analysis_id,
                        related_video_id=video.video_id,
                        action_url=action_url,
                    )
                    created_notifications.append(coach_notif)

        except Exception as exc:  # noqa: BLE001
            logger.exception("notify_assessment_completed failed non-fatally: %s", exc)

        return created_notifications

    @classmethod
    def notify_assessment_failed(
        cls,
        db: Session,
        analysis_id: uuid.UUID,
        error_message: str | None = None,
    ) -> list[Notification]:
        """
        Triggered when video analysis pipeline encounters an unrecoverable failure.
        Ensures safe sanitization (no internal stack traces exposed to athlete).
        """
        created_notifications: list[Notification] = []

        try:
            analysis = db.get(AnalysisResult, analysis_id)
            if analysis is None:
                return []

            video = db.get(Video, analysis.video_id)
            if video is None:
                return []

            athlete = db.get(Athlete, video.athlete_id)
            if athlete is None:
                return []

            # Sanitized user-safe message (never leak raw tracebacks or filesystem paths)
            user_safe_message = "We couldn't complete your assessment. Please try uploading the video again."

            athlete_notif = cls.create_notification(
                db=db,
                user_id=athlete.user_id,
                notification_type=TYPE_ASSESSMENT_FAILED,
                title="Assessment Processing Failed",
                message=user_safe_message,
                severity=SEVERITY_CRITICAL,
                related_analysis_id=analysis.analysis_id,
                related_video_id=video.video_id,
                action_url="/analysis",
            )
            created_notifications.append(athlete_notif)

            # If athlete has an assigned coach, notify coach as well
            if athlete.coach_id:
                athlete_user = db.get(User, athlete.user_id)
                athlete_name = athlete_user.name if athlete_user else "Athlete"
                coach_notif = cls.create_notification(
                    db=db,
                    user_id=athlete.coach_id,
                    notification_type=TYPE_ASSESSMENT_FAILED,
                    title=f"Assessment Failed: {athlete_name}",
                    message=f"Video processing failed for {athlete_name}'s recent upload. A re-upload may be required.",
                    severity=SEVERITY_WARNING,
                    related_analysis_id=analysis.analysis_id,
                    related_video_id=video.video_id,
                    action_url="/assessments",
                )
                created_notifications.append(coach_notif)

        except Exception as exc:  # noqa: BLE001
            logger.exception("notify_assessment_failed failed non-fatally: %s", exc)

        return created_notifications
