import uuid
from datetime import datetime

# pyrefly: ignore [missing-import]
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, BigInteger, LargeBinary
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Video(Base):
    __tablename__ = "videos"

    video_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.athlete_id"),
        nullable=False
    )

    activity: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    video_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    duration: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    fps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    resolution: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    quality_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )

    processing_status: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # ── Binary storage columns (added via migration) ──────────
    # Stores the raw video bytes in PostgreSQL BYTEA.
    file_data: Mapped[bytes | None] = mapped_column(
        LargeBinary,
        nullable=True
    )

    # Original filename as uploaded by the client.
    original_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    # MIME content type e.g. "video/mp4".
    content_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    # File size in bytes.
    file_size: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True
    )

    # Custom assessment title set by user.
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )