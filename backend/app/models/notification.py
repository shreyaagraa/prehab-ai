import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id"),
        nullable=False,
        index=True
    )

    title: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    notification_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        index=True
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        default="INFO",
        nullable=False
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        index=True
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    related_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.analysis_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    related_video_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("videos.video_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    action_url: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_dedup", "user_id", "notification_type", "related_analysis_id"),
    )