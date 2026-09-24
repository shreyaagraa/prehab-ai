"""
app/api/report_sharing.py
--------------------------
API router for Athlete-Controlled Report Sharing & Access Permissions.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.athlete import Athlete
from app.models.report_share import ReportShare
from app.models.user import User, RoleEnum
from app.schemas.report_share import (
    ReportShareStatusResponse,
    ReportShareItem,
    ReportShareUpdateRequest,
)
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/reports/sharing",
    tags=["Report Sharing & Access Controls"],
)

SUPPORTED_TARGET_ROLES = [
    ("Coach", "Coach & Roster Staff"),
    ("Physiotherapist", "Clinical Physiotherapists"),
    ("SportsScientist", "Biomechanical & Sports Science Team"),
]


@router.get(
    "",
    response_model=ReportShareStatusResponse,
    summary="Get athlete's report sharing authorizations",
)
def get_report_sharing_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ReportShareStatusResponse:
    if current_user.role != RoleEnum.ATHLETE:
        # If coach/staff, look up whether athlete linked exists or return empty
        athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()
        if not athlete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Athlete users can manage report sharing controls.",
            )
    else:
        athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()

    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    existing_shares = (
        db.query(ReportShare)
        .filter(ReportShare.athlete_id == athlete.athlete_id)
        .all()
    )
    share_map = {s.target_role: s for s in existing_shares}

    items = []
    for role_code, role_label in SUPPORTED_TARGET_ROLES:
        s = share_map.get(role_code)
        items.append(
            ReportShareItem(
                share_id=s.share_id if s else None,
                target_role=role_code,
                target_role_label=role_label,
                is_authorized=s.is_authorized if s else True,  # Default to authorized if not explicitly revoked
                updated_at=s.updated_at if s else None,
            )
        )

    return ReportShareStatusResponse(
        athlete_id=athlete.athlete_id,
        user_id=current_user.user_id,
        shares=items,
    )


@router.post(
    "/update",
    response_model=ReportShareStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Authorize or revoke report sharing for a role",
)
def update_report_sharing(
    payload: ReportShareUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ReportShareStatusResponse:
    if current_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Athlete users (or their guardian) can update report sharing authorizations.",
        )

    athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    valid_role_codes = [r[0] for r in SUPPORTED_TARGET_ROLES]
    if payload.target_role not in valid_role_codes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid target role '{payload.target_role}'. Supported roles: {valid_role_codes}",
        )

    share = (
        db.query(ReportShare)
        .filter(
            ReportShare.athlete_id == athlete.athlete_id,
            ReportShare.target_role == payload.target_role,
        )
        .first()
    )

    if share is None:
        share = ReportShare(
            athlete_id=athlete.athlete_id,
            user_id=current_user.user_id,
            target_role=payload.target_role,
            is_authorized=payload.is_authorized,
        )
        db.add(share)
    else:
        share.is_authorized = payload.is_authorized

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update report sharing setting.",
        ) from exc

    return get_report_sharing_status(current_user, db)
