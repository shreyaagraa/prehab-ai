"""
app/models/pose_landmark.py
----------------------------
SQLAlchemy model for pose_landmarks table.

Stores per-frame 3D pose landmarks (33 MediaPipe joints) extracted from videos.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Float, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.analysis_result import AnalysisResult


class PoseLandmark(Base):
    __tablename__ = "pose_landmarks"

    __table_args__ = (
        Index("ix_pose_landmarks_analysis_frame", "analysis_id", "frame_number"),
        Index("ix_pose_landmarks_analysis_id", "analysis_id"),
    )

    landmark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.analysis_id", ondelete="CASCADE"),
        nullable=False,
    )

    frame_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    timestamp_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    landmark_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    landmark_name: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )

    x: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    y: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    z: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    visibility: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    analysis: Mapped["AnalysisResult"] = relationship(
        "AnalysisResult",
        back_populates="pose_landmarks",
    )
