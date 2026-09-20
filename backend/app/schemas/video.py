"""
app/schemas/video.py
--------------------
Pydantic schemas for the Video resource.

The binary payload (file_data) is intentionally excluded from all response
schemas — callers receive only metadata, never the raw bytes over the wire.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict


class VideoUploadResponse(BaseModel):
    """
    Returned to the client after a successful POST /videos upload.

    Never includes file_data — the binary is stored in PostgreSQL but is
    not serialised into the HTTP response.
    """

    video_id: UUID
    athlete_id: UUID

    original_filename: Optional[str] = None
    content_type: Optional[str] = None

    # Size in bytes so the client can show a human-readable confirmation.
    file_size: Optional[int] = None

    processing_status: Optional[str] = None
    activity: Optional[str] = None
    uploaded_at: datetime

    # URL path served by the /uploads StaticFiles mount (e.g. /uploads/uuid_file.mp4)
    # Allows the frontend to display an HTML5 video player without exposing filesystem paths.
    video_url: Optional[str] = None
    title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class VideoUpdate(BaseModel):
    """
    Update payload for PATCH /videos/{video_id}.
    Allows renaming the assessment title without changing the underlying file.
    """
    title: Optional[str] = None


class VideoHistoryItem(BaseModel):
    """
    One row returned by GET /videos/my-history.

    Combines Video metadata with the most recent AnalysisResult summary
    so the history list can display risk scores and LESS scores without
    additional round-trips.
    """
    video_id: UUID
    title: Optional[str] = None
    original_filename: Optional[str] = None
    video_url: Optional[str] = None
    uploaded_at: datetime
    processing_status: Optional[str] = None

    # From the latest AnalysisResult (may be null if never analyzed)
    analysis_id: Optional[UUID] = None
    analysis_status: Optional[str] = None
    overall_risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    completed_at: Optional[datetime] = None

    # From AnalysisLESS (may be null)
    less_score: Optional[int] = None
    less_max_computable_score: Optional[int] = None

    # Pose landmarks presence (true only when usable pose landmark data exists)
    has_pose_landmarks: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

