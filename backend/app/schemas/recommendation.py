"""
app/schemas/recommendation.py
------------------------------
Pydantic schemas for Corrective Recommendation Engine responses.
"""
from __future__ import annotations

from typing import Any, Literal
from uuid import UUID
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field


class RecommendationItem(BaseModel):
    """
    Individual structured corrective recommendation item.
    """
    id: str = Field(..., description="Unique recommendation rule identifier")
    issue: str = Field(..., description="Identified biomechanical or workload issue key")
    category: Literal["exercise", "mobility", "strengthening", "recovery", "training_modification"] = Field(
        ..., description="Recommendation category"
    )
    title: str = Field(..., description="Short descriptive title")
    description: str = Field(..., description="Detailed description of corrective focus")
    why: str = Field(..., description="Plain-language explanation of why this was recommended")
    evidence: str = Field(..., description="Specific metric, LESS item, or factor that triggered this rule")
    exercises: list[str] = Field(default_factory=list, description="Recommended exercises or specific action drills")
    priority: Literal["low", "medium", "high"] = Field(..., description="Corrective priority level")
    frequency: str = Field(..., description="Recommended frequency (e.g. '3-4 sessions / week')")
    duration: str = Field(..., description="Recommended duration per session (e.g. '10-15 minutes')")
    safety_note: str = Field(..., description="Safety and execution guideline")
    reason: str = Field(..., description="Internal rationale / rule logic statement")

    model_config = ConfigDict(from_attributes=True)


class RecoveryPlanItem(BaseModel):
    """
    Recovery guidance item derived from fatigue, workload, and overall risk.
    """
    title: str
    focus: str
    recommendation: str
    priority: Literal["low", "medium", "high"]
    guidelines: list[str] = Field(default_factory=list)


class TrainingModificationItem(BaseModel):
    """
    Practical training volume or intensity adjustment.
    """
    title: str
    action: str
    rationale: str
    priority: Literal["low", "medium", "high"]
    suggestions: list[str] = Field(default_factory=list)


class CorrectiveActionPlanResponse(BaseModel):
    """
    Complete structured corrective action plan response.
    """
    analysis_id: UUID | None = Field(None, description="Analysis result ID")
    video_id: UUID | None = Field(None, description="Video assessment ID")
    risk_score: float | None = Field(None, description="Overall risk score (0-100)")
    risk_level: str | None = Field(None, description="Risk level (LOW, MODERATE, HIGH, CRITICAL)")
    
    # Priority areas (e.g., ["Knee Stability", "Landing Mechanics", "Ankle Mobility"])
    priority_areas: list[str] = Field(default_factory=list, description="Top detected focus areas")

    # Categorized recommendations
    exercise_recommendations: list[RecommendationItem] = Field(
        default_factory=list, description="Movement and neuromuscular control drills"
    )
    mobility_recommendations: list[RecommendationItem] = Field(
        default_factory=list, description="Range of motion and flexibility mobilizations"
    )
    strengthening_recommendations: list[RecommendationItem] = Field(
        default_factory=list, description="Targeted muscle and joint strengthening exercises"
    )
    recovery_plan: list[RecoveryPlanItem] = Field(
        default_factory=list, description="Recovery protocols based on workload & fatigue"
    )
    training_modifications: list[TrainingModificationItem] = Field(
        default_factory=list, description="Suggested volume and intensity adaptations"
    )

    total_recommendations: int = Field(0, description="Total count of actionable recommendations")
    disclaimer: str = Field(..., description="Non-medical screening and performance guidance disclaimer")

    model_config = ConfigDict(from_attributes=True)
