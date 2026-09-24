"""
app/schemas/report_share.py
----------------------------
Pydantic schemas for Report Sharing Controls API.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class ReportShareItem(BaseModel):
    share_id: Optional[UUID] = None
    target_role: str
    target_role_label: str
    is_authorized: bool
    updated_at: Optional[datetime] = None


class ReportShareUpdateRequest(BaseModel):
    target_role: str  # "Coach", "Physiotherapist", "SportsScientist"
    is_authorized: bool


class ReportShareStatusResponse(BaseModel):
    athlete_id: UUID
    user_id: UUID
    shares: List[ReportShareItem]
