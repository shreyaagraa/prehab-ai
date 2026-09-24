"""
app/api/consent.py
-------------------
API router for Consent Management & Compliance.

Enforces purpose-specific consent logging, minor guardian checks,
consent withdrawal, and data isolation.
"""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.athlete import Athlete
from app.models.consent_record import ConsentRecord, ConsentPurposeEnum, ConsentStatusEnum
from app.models.user import User, RoleEnum
from app.schemas.consent import (
    ConsentGrantRequest,
    ConsentWithdrawRequest,
    ConsentStatusResponse,
    ConsentStatusItem,
)
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/consent",
    tags=["Consent & Privacy"],
)

PURPOSE_METADATA = {
    ConsentPurposeEnum.INJURY_RISK_ANALYSIS: {
        "label": "Injury-Risk & Movement Analysis",
        "description": "Permission to process movement and video data for biomechanical and injury-risk assessment.",
        "is_required": True,
    },
    ConsentPurposeEnum.PROGRESS_TRACKING: {
        "label": "Progress & Longitudinal Tracking",
        "description": "Permission to retain movement metrics for tracking performance and injury recovery over time.",
        "is_required": True,
    },
    ConsentPurposeEnum.RESEARCH_ANONYMISED: {
        "label": "Anonymised Research & Model Improvement",
        "description": "Optional permission to use de-identified movement data for scientific research and AI model accuracy.",
        "is_required": False,
    },
}


def check_user_consent_status(user: User, db: Session) -> ConsentStatusResponse:
    athlete = db.query(Athlete).filter(Athlete.user_id == user.user_id).first()
    athlete_id = athlete.athlete_id if athlete else None

    is_minor = user.is_minor

    # Query active/latest consent records for this user
    existing_records = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.user_id == user.user_id)
        .order_by(ConsentRecord.created_at.desc())
        .all()
    )

    # Group by purpose to get latest status per purpose
    latest_by_purpose = {}
    for rec in existing_records:
        if rec.purpose not in latest_by_purpose:
            latest_by_purpose[rec.purpose] = rec

    items = []
    missing_required = []

    for purpose_enum in ConsentPurposeEnum:
        meta = PURPOSE_METADATA[purpose_enum]
        rec = latest_by_purpose.get(purpose_enum.value)

        current_status = ConsentStatusEnum.WITHDRAWN
        granted_at = None
        withdrawn_at = None
        notice_ver = "v1.0"
        provided_by = "self"
        g_name = None
        g_email = None
        g_rel = None

        if rec:
            if rec.status == ConsentStatusEnum.GRANTED.value and rec.withdrawn_at is None:
                current_status = ConsentStatusEnum.GRANTED
            granted_at = rec.granted_at
            withdrawn_at = rec.withdrawn_at
            notice_ver = rec.notice_version
            provided_by = rec.provided_by
            g_name = rec.guardian_name
            g_email = rec.guardian_email
            g_rel = rec.guardian_relationship

        if meta["is_required"] and current_status != ConsentStatusEnum.GRANTED:
            missing_required.append(purpose_enum)

        items.append(
            ConsentStatusItem(
                purpose=purpose_enum,
                label=meta["label"],
                description=meta["description"],
                is_required=meta["is_required"],
                status=current_status,
                notice_version=notice_ver,
                provided_by=provided_by,
                guardian_name=g_name,
                guardian_email=g_email,
                guardian_relationship=g_rel,
                granted_at=granted_at,
                withdrawn_at=withdrawn_at,
            )
        )

    can_upload = len(missing_required) == 0

    return ConsentStatusResponse(
        user_id=user.user_id,
        athlete_id=athlete_id,
        date_of_birth=user.date_of_birth,
        computed_age=user.computed_age,
        is_minor=is_minor,
        can_upload=can_upload,
        missing_required_consents=missing_required,
        consents=items,
    )


@router.get(
    "/status",
    response_model=ConsentStatusResponse,
    summary="Get current consent status and upload eligibility",
)
def get_consent_status(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    return check_user_consent_status(current_user, db)


@router.post(
    "/grant",
    response_model=ConsentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Record/grant consent decisions",
)
def grant_consent(
    payload: ConsentGrantRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()
    athlete_id = athlete.athlete_id if athlete else None

    is_minor = current_user.is_minor

    for item in payload.consents:
        # Check minor requirement
        if is_minor:
            if not item.guardian_name or not item.guardian_name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent or legal guardian full name is required for minor consent.",
                )
            provided_by = "parent_guardian"
        else:
            provided_by = item.provided_by or "self"

        record = ConsentRecord(
            user_id=current_user.user_id,
            athlete_id=athlete_id,
            purpose=item.purpose.value,
            status=ConsentStatusEnum.GRANTED.value,
            notice_version=item.notice_version or "v1.0",
            provided_by=provided_by,
            guardian_name=item.guardian_name.strip() if item.guardian_name else None,
            guardian_email=item.guardian_email.strip() if item.guardian_email else None,
            guardian_relationship=item.guardian_relationship.strip() if item.guardian_relationship else None,
            granted_at=datetime.now(timezone.utc),
            withdrawn_at=None,
        )
        db.add(record)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record consent in database.",
        ) from exc

    return check_user_consent_status(current_user, db)


@router.post(
    "/withdraw",
    response_model=ConsentStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Withdraw a specific consent decision",
)
def withdraw_consent(
    payload: ConsentWithdrawRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ConsentStatusResponse:
    athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()
    athlete_id = athlete.athlete_id if athlete else None

    # Retrieve existing active granted records for this purpose
    active_records = (
        db.query(ConsentRecord)
        .filter(
            ConsentRecord.user_id == current_user.user_id,
            ConsentRecord.purpose == payload.purpose.value,
            ConsentRecord.status == ConsentStatusEnum.GRANTED.value,
            ConsentRecord.withdrawn_at.is_(None),
        )
        .all()
    )

    now = datetime.now(timezone.utc)
    for rec in active_records:
        rec.status = ConsentStatusEnum.WITHDRAWN.value
        rec.withdrawn_at = now

    # Also log a explicit WITHDRAWN record to preserve full immutable history log
    withdraw_log = ConsentRecord(
        user_id=current_user.user_id,
        athlete_id=athlete_id,
        purpose=payload.purpose.value,
        status=ConsentStatusEnum.WITHDRAWN.value,
        notice_version="v1.0",
        provided_by="parent_guardian" if current_user.is_minor else "self",
        granted_at=now,
        withdrawn_at=now,
    )
    db.add(withdraw_log)

    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record consent withdrawal.",
        ) from exc

    return check_user_consent_status(current_user, db)
