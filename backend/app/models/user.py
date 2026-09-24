import uuid
from datetime import datetime, date
from enum import Enum

# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Text, DateTime, Date, Boolean, Enum as SQLEnum
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column
# pyrefly: ignore [missing-import]
from sqlalchemy import String, Text, DateTime, Date, Boolean, Enum as SQLEnum, func

from app.database import Base


class RoleEnum(str, Enum):
    ATHLETE = "Athlete"
    COACH = "Coach"
    PHYSIOTHERAPIST = "Physiotherapist"
    SPORTS_SCIENTIST = "Sports Scientist"
    ADMINISTRATOR = "Administrator"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    password: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    google_sub: Mapped[str | None] = mapped_column(
        String,
        unique=True,
        nullable=True,
        index=True,
    )

    role: Mapped[RoleEnum] = mapped_column(
        SQLEnum(
            RoleEnum,
            name="user_role_enum",
            native_enum=True,
            values_callable=lambda enum_class: [member.value for member in enum_class],
        ),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    profile_image: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    date_of_birth: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    is_verified: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    @property
    def computed_age(self) -> int | None:
        if self.date_of_birth is None:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    @property
    def is_minor(self) -> bool:
        age_val = self.computed_age
        return age_val is not None and age_val < 18