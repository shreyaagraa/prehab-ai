import uuid
from datetime import date

from sqlalchemy import String, Text, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class InjuryHistory(Base):
    __tablename__ = "injury_history"

    injury_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("athletes.athlete_id"),
        nullable=False
    )

    injury_type: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    body_part: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    severity: Mapped[str | None] = mapped_column(
        String,
        nullable=True
    )

    injury_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    recovery_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    remarks: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        default="Recovered"
    )