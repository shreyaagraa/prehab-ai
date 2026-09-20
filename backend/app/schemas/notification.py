from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notification_id: UUID
    user_id: UUID
    notification_type: Optional[str] = None
    severity: str = "INFO"
    title: Optional[str] = None
    message: Optional[str] = None
    is_read: bool = False
    created_at: datetime
    read_at: Optional[datetime] = None
    related_analysis_id: Optional[UUID] = None
    related_video_id: Optional[UUID] = None
    action_url: Optional[str] = None


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    unread_count: int


class NotificationBulkReadResponse(BaseModel):
    message: str
    updated_count: int
