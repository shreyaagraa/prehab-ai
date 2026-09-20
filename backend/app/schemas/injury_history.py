from typing import Optional
from uuid import UUID
from datetime import date, datetime

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field, field_validator


class InjuryHistoryCreate(BaseModel):
    """
    Schema for creating a new injury history record.
    """
    injury_type: Optional[str] = Field(
        default=None,
        max_length=100,
        examples=["ACL Tear", "Hamstring Strain", "Ankle Sprain"],
    )

    body_part: Optional[str] = Field(
        default=None,
        max_length=100,
        examples=["Knee", "Hamstring", "Ankle"],
    )

    severity: Optional[str] = Field(
        default=None,
        max_length=50,
        examples=["Mild", "Moderate", "Severe"],
    )

    injury_date: Optional[date] = Field(
        default=None,
        description="Approximate or exact date of injury",
    )

    recovery_date: Optional[date] = Field(
        default=None,
        description="Date of full recovery if applicable",
    )

    status: Optional[str] = Field(
        default="Recovered",
        description="Current status: Recovered, Currently affected, Unknown",
    )

    remarks: Optional[str] = Field(
        default=None,
        max_length=500,
    )

    @field_validator("injury_type", "body_part", "severity", "status", "remarks")
    @classmethod
    def strip_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class InjuryHistoryUpdate(BaseModel):
    """
    Schema for updating an existing injury history record.
    """
    injury_type: Optional[str] = Field(default=None, max_length=100)
    body_part: Optional[str] = Field(default=None, max_length=100)
    severity: Optional[str] = Field(default=None, max_length=50)
    injury_date: Optional[date] = None
    recovery_date: Optional[date] = None
    status: Optional[str] = Field(default=None, description="Recovered, Currently affected, Unknown")
    remarks: Optional[str] = Field(default=None, max_length=500)

    @field_validator("injury_type", "body_part", "severity", "status", "remarks")
    @classmethod
    def strip_strings(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned if cleaned else None


class InjuryHistoryResponse(BaseModel):
    """
    Response schema for injury history record.
    """
    injury_id: UUID
    athlete_id: UUID
    injury_type: Optional[str] = None
    body_part: Optional[str] = None
    severity: Optional[str] = None
    injury_date: Optional[date] = None
    recovery_date: Optional[date] = None
    status: Optional[str] = "Recovered"
    remarks: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
