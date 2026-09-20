"""
app/schemas/analysis.py
------------------------
Pydantic request/response schemas for the video analysis endpoints.

POST /videos/{video_id}/analyze  → AnalysisTriggerResponse
GET  /videos/{video_id}/analysis → AnalysisStatusResponse
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict


class AnalysisTriggerResponse(BaseModel):
    """
    Returned immediately after triggering analysis via POST /analyze.

    The background task has been queued; the client should poll
    GET /analysis to track progress.
    """
    analysis_id: UUID
    video_id: UUID
    status: str           # "PENDING" at creation time
    message: str          # Human-readable confirmation

    model_config = ConfigDict(from_attributes=True)


class RiskScoreBreakdownSchema(BaseModel):
    """
    Structured factor breakdown for the 5-factor risk scoring model.
    """
    s_bio: float
    s_hist: float
    s_asym: float
    s_load: float
    s_fatigue: float
    s_load_available: bool
    s_fatigue_available: bool
    overall_score: float
    risk_level: str
    model_framing: str

    model_config = ConfigDict(from_attributes=True)


class AnalysisStatusResponse(BaseModel):
    """
    Returned by GET /videos/{video_id}/analysis.

    Includes video metadata once processing completes, pose landmark summary,
    persisted risk scores, and 5-factor risk breakdown.
    """
    analysis_id: UUID
    video_id: UUID
    athlete_id: UUID
    status: str                           # PENDING | PROCESSING | COMPLETED | FAILED

    # Set when status is FAILED
    error_message: Optional[str] = None

    # Video metadata — populated after OpenCV processing
    fps: Optional[float] = None
    frame_count: Optional[int] = None
    duration_seconds: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    frames_processed: Optional[int] = None
    has_pose_data: Optional[bool] = None

    # Biomechanical Risk Scores & Factors (populated after COMPLETED)
    overall_risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    symmetry_score: Optional[float] = None
    fatigue_score: Optional[float] = None

    # Individual 5-Factor Risk Components
    s_bio: Optional[float] = None
    s_hist: Optional[float] = None
    s_asym: Optional[float] = None
    s_load: Optional[float] = None
    s_fatigue: Optional[float] = None

    # Factor Availability Flags
    s_load_available: Optional[bool] = None
    s_fatigue_available: Optional[bool] = None

    # Framing Disclaimer & Full Breakdown
    disclaimer: Optional[str] = None
    risk_breakdown: Optional[RiskScoreBreakdownSchema] = None

    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None

    # Video metadata passed through for the report UI
    # (populated from the Video record, not the AnalysisResult)
    video_url: Optional[str] = None
    original_filename: Optional[str] = None

    # Corrective Action Plan recommendations
    recommendations: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

