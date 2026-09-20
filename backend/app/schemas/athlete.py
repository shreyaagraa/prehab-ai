from typing import Optional
from uuid import UUID
from datetime import datetime

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field, field_validator, EmailStr


class AthleteCreate(BaseModel):
    """
    Schema for creating an athlete profile.
    """

    user_id: Optional[UUID] = None

    sport: Optional[str] = Field(
        default=None,
        max_length=100,
        examples=["Football"],
    )

    position: Optional[str] = Field(
        default=None,
        max_length=100,
        examples=["Midfielder"],
    )

    dominant_leg: Optional[str] = Field(
        default=None,
        max_length=50,
        examples=["Right"],
    )

    age: Optional[int] = Field(
        default=None,
        ge=0,
        le=120,
    )

    height: Optional[float] = Field(
        default=None,
        gt=0,
        le=300,
        description="Height in centimeters",
    )

    weight: Optional[float] = Field(
        default=None,
        gt=0,
        le=500,
        description="Weight in kilograms",
    )

    training_sessions_per_week: Optional[int] = Field(
        default=None,
        ge=0,
        le=50,
    )

    average_session_duration: Optional[int] = Field(
        default=None,
        ge=0,
        le=1440,
        description="Average session duration in minutes",
    )

    average_session_rpe: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=10.0,
        description="Session RPE on a 1-10 scale",
    )

    weekly_training_load: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    training_load: Optional[float] = Field(
        default=None,
        ge=0.0,
    )

    current_fatigue_level: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Current fatigue level on a 1-10 scale",
    )

    has_injury_history: Optional[str] = Field(
        default=None,
        description="'NO', 'YES', or 'UNKNOWN'",
    )

    flexibility: Optional[float] = Field(default=None, ge=0)
    strength: Optional[float] = Field(default=None, ge=0)
    balance: Optional[float] = Field(default=None, ge=0)
    endurance: Optional[float] = Field(default=None, ge=0)

    coach_notes: Optional[str] = None
    coach_id: Optional[UUID] = None
    injury_status: Optional[str] = "Healthy"

    @field_validator("sport", "position", "dominant_leg", "has_injury_history", "coach_notes", "injury_status")
    @classmethod
    def strip_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class AthleteWithUserCreate(BaseModel):
    """
    Schema for creating a user account and athlete profile in a single coach action.
    """
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field("Athlete123!", min_length=6)
    sport: Optional[str] = "Football"
    position: Optional[str] = "Forward"
    dominant_leg: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    training_sessions_per_week: Optional[int] = None
    average_session_duration: Optional[int] = None
    average_session_rpe: Optional[float] = None
    current_fatigue_level: Optional[int] = None
    has_injury_history: Optional[str] = None
    coach_notes: Optional[str] = None
    injury_status: Optional[str] = "Healthy"


class AthleteAssign(BaseModel):
    """
    Schema for assigning an athlete to a coach or updating status.
    """
    coach_id: Optional[UUID] = None
    injury_status: Optional[str] = None
    coach_notes: Optional[str] = None


class AthleteSelfCreate(BaseModel):
    """
    Schema for an Athlete creating their own profile.
    """
    sport: Optional[str] = Field(default=None, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)
    dominant_leg: Optional[str] = Field(default=None, max_length=50)

    age: Optional[int] = Field(default=None, ge=0, le=120)
    height: Optional[float] = Field(default=None, gt=0, le=300)
    weight: Optional[float] = Field(default=None, gt=0, le=500)

    training_sessions_per_week: Optional[int] = Field(default=None, ge=0, le=50)
    average_session_duration: Optional[int] = Field(default=None, ge=0, le=1440)
    average_session_rpe: Optional[float] = Field(default=None, ge=1.0, le=10.0)
    current_fatigue_level: Optional[int] = Field(default=None, ge=1, le=10)
    has_injury_history: Optional[str] = Field(default=None)

    @field_validator("sport", "position", "dominant_leg", "has_injury_history")
    @classmethod
    def strip_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class AthleteUpdate(BaseModel):
    """
    Schema for partially updating an athlete profile.
    """
    sport: Optional[str] = Field(default=None, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)
    dominant_leg: Optional[str] = Field(default=None, max_length=50)

    age: Optional[int] = Field(default=None, ge=0, le=120)
    height: Optional[float] = Field(default=None, gt=0, le=300)
    weight: Optional[float] = Field(default=None, gt=0, le=500)

    training_sessions_per_week: Optional[int] = Field(default=None, ge=0, le=50)
    average_session_duration: Optional[int] = Field(default=None, ge=0, le=1440)
    average_session_rpe: Optional[float] = Field(default=None, ge=1.0, le=10.0)
    weekly_training_load: Optional[float] = Field(default=None, ge=0.0)
    training_load: Optional[float] = Field(default=None, ge=0.0)

    current_fatigue_level: Optional[int] = Field(default=None, ge=1, le=10)
    has_injury_history: Optional[str] = Field(default=None)

    flexibility: Optional[float] = Field(default=None, ge=0)
    strength: Optional[float] = Field(default=None, ge=0)
    balance: Optional[float] = Field(default=None, ge=0)
    endurance: Optional[float] = Field(default=None, ge=0)

    coach_notes: Optional[str] = None
    coach_id: Optional[UUID] = None
    injury_status: Optional[str] = None

    @field_validator("sport", "position", "dominant_leg", "has_injury_history", "coach_notes", "injury_status")
    @classmethod
    def strip_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class AthleteResponse(BaseModel):
    """
    Response schema for an athlete profile.
    """
    athlete_id: UUID
    user_id: UUID

    name: Optional[str] = None
    email: Optional[str] = None

    sport: Optional[str] = None
    position: Optional[str] = None
    dominant_leg: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None

    training_sessions_per_week: Optional[int] = None
    average_session_duration: Optional[int] = None
    average_session_rpe: Optional[float] = None
    weekly_training_load: Optional[float] = None
    training_load: Optional[float] = None

    current_fatigue_level: Optional[int] = None
    has_injury_history: Optional[str] = None

    flexibility: Optional[float] = None
    strength: Optional[float] = None
    balance: Optional[float] = None
    endurance: Optional[float] = None
    coach_notes: Optional[str] = None

    coach_id: Optional[UUID] = None
    injury_status: Optional[str] = "Healthy"

    # Enriched stats for Coach Workspace
    latest_risk_score: Optional[float] = None
    latest_risk_level: Optional[str] = None
    latest_less_score: Optional[float] = None
    latest_less_max: Optional[float] = None
    last_assessment_date: Optional[datetime] = None
    latest_video_id: Optional[UUID] = None
    previous_risk_score: Optional[float] = None
    risk_change: Optional[float] = None
    needs_reassessment: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)