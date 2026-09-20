from typing import Annotated
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.athlete import Athlete
from app.models.injury_history import InjuryHistory
from app.models.user import RoleEnum, User
from app.schemas.injury_history import (
    InjuryHistoryCreate,
    InjuryHistoryUpdate,
    InjuryHistoryResponse,
)
from app.core.dependencies import get_current_user


router = APIRouter(
    prefix="/injury-history",
    tags=["Injury History"],
)

# Roles authorized to view athlete injury records.
INJURY_VIEW_ROLES = (
    RoleEnum.ADMINISTRATOR,
    RoleEnum.COACH,
    RoleEnum.PHYSIOTHERAPIST,
    RoleEnum.SPORTS_SCIENTIST,
)


@router.get(
    "/me",
    response_model=list[InjuryHistoryResponse],
    summary="Get current athlete's injury history",
)
def get_my_injury_history(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[InjuryHistoryResponse]:
    if current_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Athlete users can access this endpoint.",
        )

    athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    records = (
        db.query(InjuryHistory)
        .filter(InjuryHistory.athlete_id == athlete.athlete_id)
        .order_by(InjuryHistory.injury_date.desc().nulls_last())
        .all()
    )

    return records


@router.post(
    "/me",
    response_model=InjuryHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an injury record for current athlete",
)
def add_my_injury_record(
    injury_in: InjuryHistoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> InjuryHistory:
    if current_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Athlete users can access this endpoint.",
        )

    athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    record = InjuryHistory(
        athlete_id=athlete.athlete_id,
        **injury_in.model_dump(),
    )
    db.add(record)

    # Ensure has_injury_history is set to 'YES' to prevent contradiction with records
    athlete.has_injury_history = "YES"

    try:
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save injury history record.",
        )

    return record


@router.delete(
    "/me/{injury_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an injury record for current athlete",
)
def delete_my_injury_record(
    injury_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> None:
    if current_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Athlete users can access this endpoint.",
        )

    athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    record = (
        db.query(InjuryHistory)
        .filter(
            InjuryHistory.injury_id == injury_id,
            InjuryHistory.athlete_id == athlete.athlete_id,
        )
        .first()
    )

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Injury record not found.",
        )

    db.delete(record)

    # Check remaining records to keep has_injury_history consistent
    remaining = (
        db.query(InjuryHistory)
        .filter(
            InjuryHistory.athlete_id == athlete.athlete_id,
            InjuryHistory.injury_id != injury_id,
        )
        .count()
    )

    if remaining == 0 and athlete.has_injury_history == "YES":
        athlete.has_injury_history = "NO"

    db.commit()


@router.get(
    "/athlete/{athlete_id}",
    response_model=list[InjuryHistoryResponse],
    summary="Get injury history for a specified athlete",
)
def get_athlete_injury_history(
    athlete_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[InjuryHistoryResponse]:
    athlete = db.query(Athlete).filter(Athlete.athlete_id == athlete_id).first()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    if current_user.role == RoleEnum.ATHLETE:
        if athlete.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own injury history.",
            )
    elif current_user.role not in INJURY_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view athlete injury history.",
        )

    records = (
        db.query(InjuryHistory)
        .filter(InjuryHistory.athlete_id == athlete_id)
        .order_by(InjuryHistory.injury_date.desc().nulls_last())
        .all()
    )

    return records
