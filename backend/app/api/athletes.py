from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.athlete import Athlete
from app.models.user import RoleEnum, User
from app.models.analysis_result import AnalysisResult
from app.models.analysis_less import AnalysisLESS
from app.core.security import get_password_hash
from app.schemas.athlete import (
    AthleteCreate,
    AthleteSelfCreate,
    AthleteResponse,
    AthleteUpdate,
    AthleteWithUserCreate,
    AthleteAssign,
)
from app.core.dependencies import get_current_user, require_roles


router = APIRouter(
    prefix="/athletes",
    tags=["Athletes"],
)


# Roles that can manage athlete profiles.
ATHLETE_MANAGEMENT_ROLES = (
    RoleEnum.ADMINISTRATOR,
    RoleEnum.COACH,
    RoleEnum.PHYSIOTHERAPIST,
)


# Roles that can view athlete profiles.
ATHLETE_VIEW_ROLES = (
    RoleEnum.ADMINISTRATOR,
    RoleEnum.COACH,
    RoleEnum.PHYSIOTHERAPIST,
    RoleEnum.SPORTS_SCIENTIST,
)


def _enrich_athlete_response(athlete: Athlete, db: Session) -> AthleteResponse:
    """
    Enrich Athlete model with user details and latest assessment scores.
    """
    user = db.query(User).filter(User.user_id == athlete.user_id).first()
    
    analyses = (
        db.query(AnalysisResult)
        .filter(
            AnalysisResult.athlete_id == athlete.athlete_id,
            AnalysisResult.status == "COMPLETED",
        )
        .order_by(AnalysisResult.created_at.desc())
        .all()
    )

    latest_analysis = analyses[0] if len(analyses) > 0 else None
    previous_analysis = analyses[1] if len(analyses) > 1 else None

    latest_risk_score = None
    latest_risk_level = None
    latest_less_score = None
    latest_less_max = None
    last_assessment_date = None
    latest_video_id = None
    previous_risk_score = None
    risk_change = None

    if latest_analysis:
        latest_risk_score = latest_analysis.overall_risk_score
        latest_risk_level = latest_analysis.risk_level
        last_assessment_date = latest_analysis.completed_at or latest_analysis.created_at
        latest_video_id = latest_analysis.video_id

        less = (
            db.query(AnalysisLESS)
            .filter(AnalysisLESS.analysis_id == latest_analysis.analysis_id)
            .first()
        )
        if less:
            latest_less_score = less.score
            latest_less_max = less.max_computable_score

    if previous_analysis:
        previous_risk_score = previous_analysis.overall_risk_score
        if latest_risk_score is not None and previous_risk_score is not None:
            risk_change = round(latest_risk_score - previous_risk_score, 1)

    # Needs reassessment if no assessment or last assessment older than 14 days
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=14)
    needs_reassessment = False
    if not last_assessment_date:
        needs_reassessment = True
    else:
        # handle naive vs tz aware datetime
        dt = last_assessment_date
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt < cutoff:
            needs_reassessment = True

    resp_dict = {
        "athlete_id": athlete.athlete_id,
        "user_id": athlete.user_id,
        "name": user.name if user else "Athlete",
        "email": user.email if user else None,
        "sport": athlete.sport,
        "position": athlete.position,
        "dominant_leg": athlete.dominant_leg,
        "age": athlete.age,
        "height": athlete.height,
        "weight": athlete.weight,
        "training_sessions_per_week": athlete.training_sessions_per_week,
        "average_session_duration": athlete.average_session_duration,
        "average_session_rpe": athlete.average_session_rpe,
        "weekly_training_load": athlete.weekly_training_load,
        "training_load": athlete.training_load,
        "current_fatigue_level": athlete.current_fatigue_level,
        "has_injury_history": athlete.has_injury_history,
        "flexibility": athlete.flexibility,
        "strength": athlete.strength,
        "balance": athlete.balance,
        "endurance": athlete.endurance,
        "coach_notes": athlete.coach_notes,
        "coach_id": athlete.coach_id,
        "injury_status": athlete.injury_status or "Healthy",
        "latest_risk_score": latest_risk_score,
        "latest_risk_level": latest_risk_level,
        "latest_less_score": latest_less_score,
        "latest_less_max": latest_less_max,
        "last_assessment_date": last_assessment_date,
        "latest_video_id": latest_video_id,
        "previous_risk_score": previous_risk_score,
        "risk_change": risk_change,
        "needs_reassessment": needs_reassessment,
    }

    return AthleteResponse(**resp_dict)




# ============================================================
# CREATE ATHLETE PROFILE
# ============================================================

@router.post(
    "",
    response_model=AthleteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an athlete profile",
)
def create_athlete(
    athlete_in: AthleteCreate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> Athlete:

    # Athletes can only create their own profile.
    if current_user.role == RoleEnum.ATHLETE:

        if athlete_in.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Athletes can only create their own profile.",
            )

    # Other users need an authorized management role.
    elif current_user.role not in ATHLETE_MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create athlete profiles.",
        )

    # Verify target user exists.
    target_user = (
        db.query(User)
        .filter(User.user_id == athlete_in.user_id)
        .first()
    )

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found.",
        )

    # Only Athlete accounts can have an athlete profile.
    if target_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Athlete profile can only be linked to an Athlete user.",
        )

    # Check whether a profile already exists.
    existing_profile = (
        db.query(Athlete)
        .filter(Athlete.user_id == athlete_in.user_id)
        .first()
    )

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An athlete profile already exists for this user.",
        )

    athlete = Athlete(
        **athlete_in.model_dump(),
    )

    db.add(athlete)

    try:
        db.commit()
        db.refresh(athlete)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the athlete profile.",
        )

    return athlete


# ============================================================
# CREATE CURRENT ATHLETE'S OWN PROFILE
# ============================================================

@router.post(
    "/me",
    response_model=AthleteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create current athlete's profile",
)
def create_my_athlete_profile(
    athlete_in: AthleteSelfCreate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> Athlete:

    # Only Athlete accounts can use this endpoint.
    if current_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Athlete users can create an athlete profile.",
        )

    # Check whether this athlete already has a profile.
    existing_profile = (
        db.query(Athlete)
        .filter(Athlete.user_id == current_user.user_id)
        .first()
    )

    if existing_profile:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An athlete profile already exists for this user.",
        )

    # user_id comes from the authenticated JWT.
    # athlete_id is automatically generated by the model.
    athlete = Athlete(
        user_id=current_user.user_id,
        **athlete_in.model_dump(),
    )

    db.add(athlete)

    try:
        db.commit()
        db.refresh(athlete)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the athlete profile.",
        )

    return athlete


def _sync_training_load_calculation(athlete: Athlete) -> None:
    if (
        athlete.training_sessions_per_week is not None
        and athlete.average_session_duration is not None
        and athlete.average_session_rpe is not None
    ):
        load_au = float(
            athlete.training_sessions_per_week
            * athlete.average_session_duration
            * athlete.average_session_rpe
        )
        athlete.weekly_training_load = round(load_au, 2)
        athlete.training_load = round(load_au, 2)


def _sync_injury_history_status(athlete: Athlete, db: Session) -> None:
    if athlete.athlete_id is None:
        return
    from app.models.injury_history import InjuryHistory
    count = db.query(InjuryHistory).filter(InjuryHistory.athlete_id == athlete.athlete_id).count()
    if count > 0:
        athlete.has_injury_history = "YES"


# ============================================================
# UPSERT CURRENT ATHLETE PROFILE (Create or Update)
# ============================================================

@router.put(
    "/me",
    response_model=AthleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update current athlete's profile",
)
def upsert_my_athlete_profile(
    athlete_in: AthleteSelfCreate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> Athlete:
    """
    Upsert the authenticated athlete's profile.

    - If no profile exists, create one (HTTP 200).
    - If a profile already exists, apply a partial update (HTTP 200).
    - ``user_id`` is always sourced from the JWT — the client cannot supply it.
    """

    # Only Athlete accounts may use this endpoint.
    if current_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Athlete users can manage their own profile.",
        )

    athlete = (
        db.query(Athlete)
        .filter(Athlete.user_id == current_user.user_id)
        .first()
    )

    if athlete is None:
        # Profile does not exist — create it.
        athlete = Athlete(
            user_id=current_user.user_id,
            **athlete_in.model_dump(exclude_none=True),
        )
        db.add(athlete)
    else:
        # Profile exists — apply supplied fields.
        update_data = athlete_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(athlete, field, value)

    _sync_training_load_calculation(athlete)
    _sync_injury_history_status(athlete, db)

    try:
        db.commit()
        db.refresh(athlete)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the athlete profile.",
        )

    return athlete



# ============================================================
# LIST ATHLETE PROFILES
# ============================================================

@router.get(
    "",
    response_model=list[AthleteResponse],
    summary="List athlete profiles",
)
def list_athletes(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> list[AthleteResponse]:

    # Athlete can only see their own profile.
    if current_user.role == RoleEnum.ATHLETE:

        profile = (
            db.query(Athlete)
            .filter(Athlete.user_id == current_user.user_id)
            .first()
        )

        return [_enrich_athlete_response(profile, db)] if profile else []

    # Other authorized roles can view all athletes.
    if current_user.role not in ATHLETE_VIEW_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view athlete profiles.",
        )

    athletes = (
        db.query(Athlete)
        .order_by(Athlete.athlete_id)
        .all()
    )

    return [_enrich_athlete_response(a, db) for a in athletes]


# ============================================================
# GET CURRENT ATHLETE PROFILE
# ============================================================

@router.get(
    "/me",
    response_model=AthleteResponse,
    summary="Get current athlete profile",
)
def get_my_athlete_profile(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> Athlete:

    if current_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Athlete users can access this endpoint.",
        )

    athlete = (
        db.query(Athlete)
        .filter(Athlete.user_id == current_user.user_id)
        .first()
    )

    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    return athlete


# ============================================================
# UPDATE CURRENT ATHLETE PROFILE
# ============================================================

@router.patch(
    "/me",
    response_model=AthleteResponse,
    summary="Update current athlete's profile",
)
def update_my_athlete_profile(
    athlete_in: AthleteUpdate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> Athlete:

    if current_user.role != RoleEnum.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Athlete users can update their own profile.",
        )

    athlete = (
        db.query(Athlete)
        .filter(Athlete.user_id == current_user.user_id)
        .first()
    )

    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    update_data = athlete_in.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(athlete, field, value)

    _sync_training_load_calculation(athlete)
    _sync_injury_history_status(athlete, db)

    try:
        db.commit()
        db.refresh(athlete)


    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the athlete profile.",
        )

    return athlete


# ============================================================
# GET ATHLETE BY ID
# ============================================================

@router.get(
    "/{athlete_id}",
    response_model=AthleteResponse,
    summary="Get an athlete profile",
)
def get_athlete(
    athlete_id: UUID,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> AthleteResponse:

    athlete = (
        db.query(Athlete)
        .filter(Athlete.athlete_id == athlete_id)
        .first()
    )

    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    # Athlete can only access their own profile.
    if current_user.role == RoleEnum.ATHLETE:

        if athlete.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own athlete profile.",
            )

    elif current_user.role not in ATHLETE_VIEW_ROLES:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view athlete profiles.",
        )

    return _enrich_athlete_response(athlete, db)


# ============================================================
# UPDATE ATHLETE BY ID
# ============================================================

@router.patch(
    "/{athlete_id}",
    response_model=AthleteResponse,
    summary="Update an athlete profile",
)
def update_athlete(
    athlete_id: UUID,
    athlete_in: AthleteUpdate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> Athlete:

    athlete = (
        db.query(Athlete)
        .filter(Athlete.athlete_id == athlete_id)
        .first()
    )

    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    # Athlete can update only their own profile.
    if current_user.role == RoleEnum.ATHLETE:

        if athlete.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own athlete profile.",
            )

    elif current_user.role not in ATHLETE_MANAGEMENT_ROLES:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update athlete profiles.",
        )

    update_data = athlete_in.model_dump(
        exclude_unset=True
    )

    for field, value in update_data.items():
        setattr(athlete, field, value)

    try:
        db.commit()
        db.refresh(athlete)

    except Exception:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the athlete profile.",
        )

    return athlete


# ============================================================
# DELETE ATHLETE PROFILE
# ============================================================

@router.delete(
    "/{athlete_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an athlete profile",
)
def delete_athlete(
    athlete_id: UUID,
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.ADMINISTRATOR)),
    ],
    db: Session = Depends(get_db),
) -> None:

    athlete = (
        db.query(Athlete)
        .filter(Athlete.athlete_id == athlete_id)
        .first()
    )

    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    db.delete(athlete)
    db.commit()


# ============================================================
# REGISTER NEW ATHLETE (USER + PROFILE) BY COACH
# ============================================================

@router.post(
    "/register-athlete",
    response_model=AthleteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new athlete user and profile",
)
def register_athlete(
    athlete_in: AthleteWithUserCreate,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> AthleteResponse:
    if current_user.role not in ATHLETE_MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create athletes.",
        )

    # Check email duplicate
    existing_user = db.query(User).filter(User.email == athlete_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    new_user = User(
        name=athlete_in.name,
        email=athlete_in.email.lower(),
        password=get_password_hash(athlete_in.password),
        role=RoleEnum.ATHLETE,
        is_active=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    new_athlete = Athlete(
        user_id=new_user.user_id,
        sport=athlete_in.sport,
        position=athlete_in.position,
        age=athlete_in.age,
        height=athlete_in.height,
        weight=athlete_in.weight,
        coach_notes=athlete_in.coach_notes,
        coach_id=current_user.user_id if current_user.role == RoleEnum.COACH else None,
        injury_status=athlete_in.injury_status or "Healthy",
    )
    db.add(new_athlete)
    db.commit()
    db.refresh(new_athlete)

    return _enrich_athlete_response(new_athlete, db)


# ============================================================
# ASSIGN / UNASSIGN ATHLETE TO COACH
# ============================================================

@router.patch(
    "/{athlete_id}/assign",
    response_model=AthleteResponse,
    summary="Assign or unassign an athlete to a coach",
)
def assign_athlete(
    athlete_id: UUID,
    assign_in: AthleteAssign,
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
    db: Session = Depends(get_db),
) -> AthleteResponse:
    if current_user.role not in ATHLETE_MANAGEMENT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to assign athletes.",
        )

    athlete = db.query(Athlete).filter(Athlete.athlete_id == athlete_id).first()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete profile not found.",
        )

    if assign_in.coach_id is not None:
        athlete.coach_id = assign_in.coach_id
    if assign_in.injury_status is not None:
        athlete.injury_status = assign_in.injury_status
    if assign_in.coach_notes is not None:
        athlete.coach_notes = assign_in.coach_notes

    db.commit()
    db.refresh(athlete)

    return _enrich_athlete_response(athlete, db)