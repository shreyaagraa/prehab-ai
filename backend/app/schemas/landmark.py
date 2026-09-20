"""
app/schemas/landmark.py
-----------------------
Pydantic schemas for the Pose Landmarks overlay endpoint.
"""
from typing import List, Optional
from uuid import UUID

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict


class SingleLandmarkSchema(BaseModel):
    """Coordinates for a single MediaPipe pose joint."""
    landmark_index: int       # 0–32 (MediaPipe topology)
    landmark_name: str        # e.g. "LEFT_KNEE", "NOSE"
    x: float                  # Normalized [0.0, 1.0] by image width
    y: float                  # Normalized [0.0, 1.0] by image height
    z: float                  # Relative depth
    visibility: float         # [0.0, 1.0] detection confidence

    model_config = ConfigDict(from_attributes=True)


class FramePoseLandmarksSchema(BaseModel):
    """All 33 landmarks detected for a single video frame."""
    frame_number: int
    timestamp_ms: float
    landmarks: List[SingleLandmarkSchema]

    model_config = ConfigDict(from_attributes=True)


class AnalysisPoseLandmarksResponse(BaseModel):
    """
    Response schema for GET /videos/{video_id}/landmarks.
    Scoped to an exact analysis_id.
    """
    analysis_id: UUID
    video_id: UUID
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    total_frames: int
    frames_with_pose: int
    has_pose_data: bool
    frames: List[FramePoseLandmarksSchema]

    model_config = ConfigDict(from_attributes=True)
