"""
app/models/report_share.py
--------------------------
SQLAlchemy model for report_shares table.

Stores athlete-controlled report access authorizations per recipient role / user ID.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ReportShare(Base):
    __tablename__ = "report_shares"

    __table_args__ = (
        UniqueConstraint("athlete_id", "target_role", name="uq_report_shares_athlete_role"),
    )

    share_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.athlete_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    target_role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    is_authorized: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
