from typing import Optional
from datetime import datetime
from uuid import UUID
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from app.models.user import RoleEnum


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
    email: EmailStr = Field(
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

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip().lower()
        return v

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

