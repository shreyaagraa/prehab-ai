import uuid
from datetime import timedelta
from typing import Annotated

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from fastapi.security import OAuth2PasswordRequestForm
# pyrefly: ignore [missing-import]
from sqlalchemy import func
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.config import settings
from app.database import get_db
from app.models.user import User, RoleEnum
from app.schemas.auth import UserRegisterRequest, UserResponse, TokenResponse, GoogleLoginRequest, UserUpdateRequest
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.dependencies import get_current_user, require_role, require_roles


router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Registers an athlete, coach, physiotherapist, or sports scientist account. Passwords are securely hashed with Argon2.",
)
def register_user(
    user_in: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> User:
    """
    Registers a new user account:
    - Normalizes and verifies unique email address.
    - Rejects unauthorized Administrator self-registration.
    - Hashes password using Argon2id algorithm.
    - Persists new user and returns a sanitized user profile.
    """
    # 1. Check for duplicate email (case-insensitive to handle any legacy mixed-case rows)
    normalized_email = user_in.email.strip().lower()
    existing_user = db.query(User).filter(func.lower(User.email) == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    # 2. Defense-in-depth: Ensure Administrator role cannot be self-registered
    if user_in.role == RoleEnum.ADMINISTRATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self-registration as Administrator is not permitted.",
        )

    # 3. Hash password using Argon2id
    hashed_password = get_password_hash(user_in.password)

    # 4. Instantiate User model
    new_user = User(
        user_id=uuid.uuid4(),
        name=user_in.name,
        email=normalized_email,  # always store the normalized (strip().lower()) form
        password=hashed_password,
        role=user_in.role,
        phone=user_in.phone,
        date_of_birth=user_in.date_of_birth,
        is_active=True,
        is_verified=False,
    )

    # 5. Commit to database with error handling and rollback
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # If registering as Athlete, automatically provision their Athlete profile row
        if new_user.role == RoleEnum.ATHLETE:
            from app.models.athlete import Athlete
            existing_athlete = db.query(Athlete).filter(Athlete.user_id == new_user.user_id).first()
            if not existing_athlete:
                auto_athlete = Athlete(
                    user_id=new_user.user_id,
                    age=new_user.computed_age,
                    injury_status="Healthy",
                )
                db.add(auto_athlete)
                db.commit()

    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating your account. Please try again later.",
        ) from exc

    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and obtain an access token",
    description=(
        "Authenticates a user with email and password using an OAuth2-compatible "
        "form body. Returns a signed JWT bearer token on success."
    ),
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticates the user and returns a signed JWT access token.

    - ``username`` is treated as the user's email address (normalized to lowercase).
    - Returns a generic 401 for both wrong email and wrong password to prevent
      user enumeration.
    - Rejects inactive accounts with 403 Forbidden.
    - Never logs the plaintext password.
    """
    # 1. Normalize the submitted email (same rule as registration)
    email = form_data.username.strip().lower()

    # 2. Retrieve user by email — case-insensitive to handle any legacy mixed-case rows;
    #    constant-time path is preserved regardless of whether the user exists.
    user = db.query(User).filter(func.lower(User.email) == email).first()

    # 3. Verify password — always call verify_password even when user is None
    #    to prevent timing-based user enumeration.
    _DUMMY_HASH = (
        "$argon2id$v=19$m=65536,t=3,p=4"
        "$dGhpcyBpcyBhIGZha2Ugc2FsdA"
        "$dGhpcyBpcyBhIGZha2UgaGFzaA"
    )
    stored_hash = user.password if user else _DUMMY_HASH
    password_ok = verify_password(form_data.password, stored_hash)

    # 4. Unified failure branch — same error for bad email OR bad password
    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 5. Account status check
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact support.",
        )

    # 6. Build and sign the JWT
    access_token = create_access_token(
        subject=str(user.user_id),
        role=user.role.value,
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(access_token=access_token, token_type="bearer")


@router.post(
    "/google",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate or register with Google OAuth 2.0 / OpenID Connect ID token",
    description=(
        "Verifies Google ID token server-side using Google's official verification SDK. "
        "Authenticates existing Google users, handles secure account linking for existing password users, "
        "or registers a new Athlete user account."
    ),
)
def google_auth(
    body: GoogleLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Google OAuth Authentication Handler:
    1. Cryptographically verifies Google ID token (signature, aud, iss, exp, email_verified).
    2. Extracts sub, email, name, profile image.
    3. Looks up user by google_sub first.
    4. If not found by google_sub, checks by email:
       - Requires password authentication if user has existing password account (ACCOUNT_LINKING_REQUIRED).
       - Explicitly links google_sub upon password confirmation.
    5. If user does not exist, registers new Athlete user marked email_verified.
    6. Returns application JWT token.
    """
    # 1. Verify Google ID token
    try:
        req = google_requests.Request()
        aud = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None
        id_info = id_token.verify_oauth2_token(body.credential, req, audience=aud)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google ID token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to verify Google ID token with Google servers.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # 2. Validate Issuer & Claims
    issuer = id_info.get("iss")
    if issuer not in ["accounts.google.com", "https://accounts.google.com"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer.",
        )

    # Validate email_verified claim
    email_verified = id_info.get("email_verified")
    if email_verified is not True and str(email_verified).lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified.",
        )

    google_sub = id_info.get("sub")
    raw_email = id_info.get("email")
    if not google_sub or not raw_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token missing required identity claims.",
        )

    email = raw_email.strip().lower()
    name = id_info.get("name") or email.split("@")[0]
    picture = id_info.get("picture")

    # 3. Lookup user by google_sub
    user = db.query(User).filter(User.google_sub == google_sub).first()

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account has been deactivated. Please contact support.",
            )
        # Refresh profile picture if available and user doesn't have one
        if picture and not user.profile_image:
            user.profile_image = picture
            db.commit()
    else:
        # 4. Check if email belongs to an existing password account
        existing_email_user = db.query(User).filter(func.lower(User.email) == email).first()

        if existing_email_user:
            if not existing_email_user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="This account has been deactivated. Please contact support.",
                )

            # Account Linking Policy Enforcement:
            # Require authentication with the existing password account before linking.
            if not body.password:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="ACCOUNT_LINKING_REQUIRED: An account with this email already exists. Please enter your password to link your Google account.",
                )

            # Validate the provided account password
            _DUMMY_HASH = (
                "$argon2id$v=19$m=65536,t=3,p=4"
                "$dGhpcyBpcyBhIGZha2Ugc2FsdA"
                "$dGhpcyBpcyBhIGZha2UgaGFzaA"
            )
            stored_hash = existing_email_user.password if existing_email_user.password else _DUMMY_HASH
            password_ok = verify_password(body.password, stored_hash)

            if not password_ok:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect password for account linking.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            # Link Google identity
            existing_email_user.google_sub = google_sub
            existing_email_user.is_verified = True
            if picture and not existing_email_user.profile_image:
                existing_email_user.profile_image = picture
            
            try:
                db.commit()
                db.refresh(existing_email_user)
            except Exception as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to link Google account.",
                ) from exc

            user = existing_email_user
        else:
            # 5. Create new Google user
            new_user = User(
                user_id=uuid.uuid4(),
                name=name,
                email=email,
                password=None,
                google_sub=google_sub,
                role=RoleEnum.ATHLETE,
                profile_image=picture,
                is_active=True,
                is_verified=True,
            )

            try:
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
            except Exception as exc:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="An error occurred while creating your Google account.",
                ) from exc

            user = new_user

    # 6. Issue application JWT access token
    access_token = create_access_token(
        subject=str(user.user_id),
        role=user.role.value,
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )

    return TokenResponse(access_token=access_token, token_type="bearer")



@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user",
    description=(
        "Returns the profile of the currently authenticated user, sourced directly "
        "from the database. The role and all other fields reflect the current "
        "database state — the JWT payload is used only for identity verification, "
        "never as an authoritative data source. Sensitive fields (password hash, "
        "oauth_id) are never returned."
    ),
)
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Returns the database-authoritative profile of the authenticated user.

    - Requires a valid ``Authorization: Bearer <token>`` header.
    - The ``role`` field is fetched from PostgreSQL, not blindly from the JWT.
    - Returns ``HTTP 401`` if the token is missing, invalid, expired, or the
      user no longer exists / is inactive.
    - Never exposes ``password``, ``oauth_id``, or other sensitive credentials.
    """
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile information",
    description="Allows authenticated user (Coach, Athlete, Staff) to edit their name, phone, profile image, or date of birth.",
)
def update_me(
    user_in: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> User:
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    # If date_of_birth changed and user is athlete, sync age on Athlete model
    if "date_of_birth" in update_data and current_user.date_of_birth is not None:
        from app.models.athlete import Athlete
        athlete = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).first()
        if athlete:
            athlete.age = current_user.computed_age

    try:
        db.commit()
        db.refresh(current_user)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating profile information.",
        ) from exc

    return current_user


# ---------------------------------------------------------------------------
# RBAC probe endpoints – used exclusively by tests/test_rbac.py
# ---------------------------------------------------------------------------
# These endpoints are deliberately minimal.  They exist so the RBAC dependency
# factories can be exercised over a real HTTP stack without polluting actual
# application routes.  Each route is named after the role(s) it protects.

@router.get(
    "/rbac-probe/athlete",
    tags=["RBAC Probes"],
    summary="[TEST] Athlete-only endpoint",
    include_in_schema=False,
)
def rbac_probe_athlete(
    current_user: Annotated[User, Depends(require_role(RoleEnum.ATHLETE))],
) -> dict:
    return {"role": current_user.role.value, "user_id": str(current_user.user_id)}


@router.get(
    "/rbac-probe/coach",
    tags=["RBAC Probes"],
    summary="[TEST] Coach-only endpoint",
    include_in_schema=False,
)
def rbac_probe_coach(
    current_user: Annotated[User, Depends(require_role(RoleEnum.COACH))],
) -> dict:
    return {"role": current_user.role.value, "user_id": str(current_user.user_id)}


@router.get(
    "/rbac-probe/physiotherapist",
    tags=["RBAC Probes"],
    summary="[TEST] Physiotherapist-only endpoint",
    include_in_schema=False,
)
def rbac_probe_physiotherapist(
    current_user: Annotated[User, Depends(require_role(RoleEnum.PHYSIOTHERAPIST))],
) -> dict:
    return {"role": current_user.role.value, "user_id": str(current_user.user_id)}


@router.get(
    "/rbac-probe/sports-scientist",
    tags=["RBAC Probes"],
    summary="[TEST] Sports Scientist-only endpoint",
    include_in_schema=False,
)
def rbac_probe_sports_scientist(
    current_user: Annotated[User, Depends(require_role(RoleEnum.SPORTS_SCIENTIST))],
) -> dict:
    return {"role": current_user.role.value, "user_id": str(current_user.user_id)}


@router.get(
    "/rbac-probe/administrator",
    tags=["RBAC Probes"],
    summary="[TEST] Administrator-only endpoint",
    include_in_schema=False,
)
def rbac_probe_administrator(
    current_user: Annotated[User, Depends(require_role(RoleEnum.ADMINISTRATOR))],
) -> dict:
    return {"role": current_user.role.value, "user_id": str(current_user.user_id)}


@router.get(
    "/rbac-probe/multi-role",
    tags=["RBAC Probes"],
    summary="[TEST] Coach or Physiotherapist endpoint",
    include_in_schema=False,
)
def rbac_probe_multi_role(
    current_user: Annotated[
        User,
        Depends(require_roles(RoleEnum.COACH, RoleEnum.PHYSIOTHERAPIST)),
    ],
) -> dict:
    return {"role": current_user.role.value, "user_id": str(current_user.user_id)}
