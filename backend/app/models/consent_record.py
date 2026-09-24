"""
app/models/consent_record.py
-----------------------------
SQLAlchemy model for consent_records table.

Tracks purpose-specific user/athlete consent log, parent/guardian details for minors,
and consent status (GRANTED vs WITHDRAWN) with timestamps.
"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import String, Text, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ConsentPurposeEnum(str, Enum):
    INJURY_RISK_ANALYSIS = "injury_risk_analysis"
    PROGRESS_TRACKING = "progress_tracking"
    RESEARCH_ANONYMISED = "research_anonymised"


class ConsentStatusEnum(str, Enum):
    GRANTED = "GRANTED"
    WITHDRAWN = "WITHDRAWN"


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    consent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    athlete_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.athlete_id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    purpose: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="GRANTED",
        server_default="GRANTED",
        index=True,
    )

    notice_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="v1.0",
        server_default="v1.0",
    )

    provided_by: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="self",
        server_default="self",
    )

    guardian_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    guardian_email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    guardian_relationship: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
