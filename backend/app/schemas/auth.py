import re
from typing import Optional
from datetime import datetime, date
from uuid import UUID
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from app.models.user import RoleEnum

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


class UserRegisterRequest(BaseModel):
    """
    Schema for user registration requests.
    """
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Full name of the user",
        examples=["Test Athlete"],
    )
    email: str = Field(
        ...,
        description="User email address (will be stored lowercased)",
        examples=["athlete@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plaintext password to be securely hashed with Argon2",
        examples=["StrongPassword123"],
    )
    role: Optional[RoleEnum] = Field(
        default=RoleEnum.ATHLETE,
        description="Assigned user role (Defaults to Athlete; Administrator self-registration is forbidden)",
        examples=["Athlete"],
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Optional contact telephone number",
        examples=["9876543210"],
    )
    date_of_birth: Optional[date] = Field(
        default=None,
        description="Date of birth (YYYY-MM-DD)",
        examples=["2005-08-15"],
    )

    @field_validator("email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Email address must be a string")
        cleaned = v.strip().lower()
        if not EMAIL_REGEX.match(cleaned):
            raise ValueError(
                "Invalid email address format. Must be a valid email containing a domain with extension (e.g. name@example.com)."
            )
        parts = cleaned.split("@")
        if len(parts) != 2:
            raise ValueError("Invalid email format.")
        domain = parts[1]
        if "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Email domain must contain a valid domain extension (e.g., .com, .edu, .org).")
        return cleaned

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[RoleEnum]) -> RoleEnum:
        if v == RoleEnum.ADMINISTRATOR:
            raise ValueError(
                "Self-registration as Administrator is not permitted. "
                "Administrator accounts must be provisioned internally."
            )
        return v or RoleEnum.ATHLETE

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty or whitespace only")
        return cleaned


class UserUpdateRequest(BaseModel):
    """
    Schema for updating user profile.
    """
    name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=50)
    profile_image: Optional[str] = Field(default=None)
    date_of_birth: Optional[date] = Field(default=None)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Name cannot be empty or whitespace only")
        return cleaned


class UserResponse(BaseModel):
    """
    Safe public response schema for user accounts.
    Never exposes passwords, hashes, or sensitive internal credentials.
    """
    user_id: UUID
    name: str
    email: str
    role: RoleEnum
    phone: Optional[str] = None
    profile_image: Optional[str] = None
    date_of_birth: Optional[date] = None
    computed_age: Optional[int] = None
    is_minor: Optional[bool] = False
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """
    Standard OAuth2 bearer token response.
    Returned by POST /auth/login on successful authentication.
    """
    access_token: str
    token_type: str = "bearer"


class UserLoginRequest(BaseModel):
    """
    Schema for JSON-body login requests (alternative to OAuth2PasswordRequestForm).
    The ``username`` field is treated as the user's email address.
    """
    username: str = Field(
        ...,
        description="User email address (treated as username per OAuth2 convention)",
        examples=["athlete@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Plaintext password",
        examples=["StrongPassword123"],
    )

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v


class GoogleLoginRequest(BaseModel):
    """
    Schema for Google OAuth 2.0 / OpenID Connect login request.
    """
    credential: str = Field(
        ...,
        description="Google ID token returned by Google Identity Services",
        examples=["eyJhbGciOiJSUzI1NiIsImtpZCI6..."],
    )
    password: Optional[str] = Field(
        default=None,
        description="Optional password required when explicitly linking Google to an existing password account",
        examples=["StrongPassword123"],
    )

