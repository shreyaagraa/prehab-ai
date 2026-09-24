"""
app/schemas/consent.py
-----------------------
Pydantic schemas for Consent Management API.
"""
from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.consent_record import ConsentPurposeEnum, ConsentStatusEnum


class ConsentItemGrant(BaseModel):
    purpose: ConsentPurposeEnum
    notice_version: str = "v1.0"
    provided_by: str = "self"  # "self" or "parent_guardian"
    guardian_name: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_relationship: Optional[str] = None


class ConsentGrantRequest(BaseModel):
    consents: List[ConsentItemGrant]


class ConsentWithdrawRequest(BaseModel):
    purpose: ConsentPurposeEnum


class ConsentStatusItem(BaseModel):
    purpose: ConsentPurposeEnum
    label: str
    description: str
    is_required: bool
    status: ConsentStatusEnum  # GRANTED or WITHDRAWN
    notice_version: str
    provided_by: str
    guardian_name: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_relationship: Optional[str] = None
    granted_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None


class ConsentStatusResponse(BaseModel):
    user_id: UUID
    athlete_id: Optional[UUID] = None
    date_of_birth: Optional[date] = None
    computed_age: Optional[int] = None
    is_minor: bool = False
    can_upload: bool = False
    missing_required_consents: List[ConsentPurposeEnum] = []
    consents: List[ConsentStatusItem]
