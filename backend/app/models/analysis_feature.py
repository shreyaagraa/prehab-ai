"""
app/models/analysis_feature.py
-------------------------------
SQLAlchemy model for analysis_features table.

Stores calculated biomechanical and kinematic feature vectors per analysis.
"""
import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import String, DateTime, ForeignKey, Index, text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalysisFeature(Base):
    __tablename__ = "analysis_features"

    __table_args__ = (
        Index("ix_analysis_features_analysis_id", "analysis_id", unique=True),
    )

    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.analysis_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    feature_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="v1",
        server_default="v1",
    )

    features: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=text("NOW()"),
        nullable=False,
    )
