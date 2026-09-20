"""
app/api/notifications.py
-------------------------
Authenticated API endpoints for user notification center and alerts.

Endpoints:
- GET /notifications              — List paginated notifications for current user
- GET /notifications/unread-count — Get fast unread count for navbar badge
- PATCH /notifications/{id}/read  — Mark single notification as read (with ownership verification)
- PATCH /notifications/read-all   — Mark all notifications as read for current user
- DELETE /notifications/{id}      — Dismiss / delete a single notification
"""
import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationBulkReadResponse,
)
from app.core.dependencies import get_current_user

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications"],
)


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get notifications for current user",
    description="Returns paginated notifications belonging exclusively to the authenticated user.",
)
def get_user_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
    skip: int = Query(default=0, ge=0, description="Offset for pagination"),
    limit: int = Query(default=30, ge=1, le=100, description="Page size limit"),
    unread_only: bool = Query(default=False, description="Filter for unread notifications only"),
) -> NotificationListResponse:
    """
    Fetch notifications for the logged-in user with newest notifications first.
    """
    base_query = db.query(Notification).filter(Notification.user_id == current_user.user_id)

    total_count = base_query.count()

    unread_count = (
        db.query(func.count(Notification.notification_id))
        .filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
        .scalar()
        or 0
    )

    query = base_query
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    items = (
        query.order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        total=total_count,
        unread_count=unread_count,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    status_code=status.HTTP_200_OK,
    summary="Get unread notification count",
    description="Fast, lightweight count of unread notifications for badge rendering.",
)
def get_unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    """
    Lightweight endpoint polled by the frontend Navbar for badge counts.
    """
    unread_count = (
        db.query(func.count(Notification.notification_id))
        .filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
        .scalar()
        or 0
    )
    return UnreadCountResponse(unread_count=unread_count)


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark single notification as read",
    description="Marks a specific notification as read. Enforces strict user ownership.",
)
def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """
    Mark one notification as read if it belongs to the authenticated user.
    """
    notification = (
        db.query(Notification)
        .filter(
            Notification.notification_id == notification_id,
            Notification.user_id == current_user.user_id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
        db.refresh(notification)

    return NotificationResponse.model_validate(notification)


@router.patch(
    "/read-all",
    response_model=NotificationBulkReadResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark all notifications as read",
    description="Marks all unread notifications for the authenticated user as read.",
)
def mark_all_notifications_as_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> NotificationBulkReadResponse:
    """
    Bulk marks all unread notifications for current user as read.
    """
    now = datetime.utcnow()
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.user_id,
            Notification.is_read.is_(False),
        )
        .update(
            {"is_read": True, "read_at": now},
            synchronize_session=False,
        )
    )
    db.commit()

    return NotificationBulkReadResponse(
        message="All notifications marked as read.",
        updated_count=updated,
    )


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Dismiss/delete a notification",
    description="Dismisses a notification record for the authenticated user.",
)
def delete_notification(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """
    Dismisses a notification without altering any underlying analysis entities.
    """
    notification = (
        db.query(Notification)
        .filter(
            Notification.notification_id == notification_id,
            Notification.user_id == current_user.user_id,
        )
        .first()
    )

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found.",
        )

    db.delete(notification)
    db.commit()

    return {
        "message": "Notification dismissed.",
        "notification_id": str(notification_id),
    }
