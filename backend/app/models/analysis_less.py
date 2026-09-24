"""
app/models/analysis_less.py
----------------------------
SQLAlchemy model for analysis_less_results table.

Stores Landing Error Scoring System (LESS) assessment results per analysis.
"""
import uuid
from datetime import datetime
from typing import Any, List, Dict

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Index, text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalysisLESS(Base):
    __tablename__ = "analysis_less_results"

    __table_args__ = (
        Index("ix_analysis_less_results_analysis_id", "analysis_id", unique=True),
    )

    less_id: Mapped[uuid.UUID] = mapped_column(
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

    score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    max_computable_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    computable_items: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    error_items: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    not_computable_items: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    classification: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    validation_source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    source_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="v1",
        server_default="v1",
    )

    disclaimer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    items: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        server_default=text("NOW()"),
        nullable=False,
    )
