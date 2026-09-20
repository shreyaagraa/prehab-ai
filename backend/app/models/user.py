import uuid
from datetime import datetime
from enum import Enum

# pyrefly: ignore [missing-import]
from sqlalchemy import Column, String, Text, DateTime, Boolean, Enum as SQLEnum
# pyrefly: ignore [missing-import]
from sqlalchemy.dialects.postgresql import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column
# pyrefly: ignore [missing-import]
from sqlalchemy import String, Text, DateTime, Boolean, Enum as SQLEnum, func

# pyrefly: ignore [missing-import]
from sqlalchemy import Boolean

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