"""
tests/test_google_auth.py
--------------------------
Comprehensive unit and integration tests for POST /auth/google endpoint:
1. Register new Google user (defaults to Athlete, email_verified=True).
2. Login existing Google user by google_sub.
3. Attempt Google login on existing password account without password -> 409 ACCOUNT_LINKING_REQUIRED.
4. Link Google account on existing password account with valid password -> 200 OK.
5. Attempt linking Google account with invalid password -> 401 Unauthorized.
6. Unverified Google email -> 400 Bad Request.
7. Invalid Google token -> 401 Unauthorized.
"""

import uuid
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.core.security import get_password_hash

client = TestClient(app)

_TEST_GOOGLE_SUB_1 = "google_sub_123456789"
_TEST_GOOGLE_SUB_2 = "google_sub_987654321"
_TEST_PASSWORD = "ExistingUserPass123!"


def _cleanup_user(email: str):
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == email.lower()).delete()
        db.commit()
    finally:
        db.close()


def test_google_auth_new_user():
    test_email = "new.google.user@example.com"
    _cleanup_user(test_email)

    mock_id_info = {
        "sub": _TEST_GOOGLE_SUB_1,
        "email": test_email,
        "email_verified": True,
        "name": "Google New User",
        "picture": "https://lh3.googleusercontent.com/a/photo1",
        "iss": "https://accounts.google.com",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        response = client.post("/auth/google", json={"credential": "mock_google_id_token"})
        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    # Verify user state in DB
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.google_sub == _TEST_GOOGLE_SUB_1).first()
        assert user is not None
        assert user.email == test_email
        assert user.name == "Google New User"
        assert user.role == RoleEnum.ATHLETE
        assert user.is_verified is True
        assert user.password is None
        assert user.profile_image == "https://lh3.googleusercontent.com/a/photo1"
    finally:
        db.close()
        _cleanup_user(test_email)


def test_google_auth_existing_google_user():
    test_email = "existing.google.user@example.com"
    _cleanup_user(test_email)

    # Insert user with google_sub
    db = SessionLocal()
    user_id = uuid.uuid4()
    try:
        user = User(
            user_id=user_id,
            name="Existing Google User",
            email=test_email,
            password=None,
            google_sub=_TEST_GOOGLE_SUB_2,
            role=RoleEnum.COACH,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    mock_id_info = {
        "sub": _TEST_GOOGLE_SUB_2,
        "email": test_email,
        "email_verified": True,
        "name": "Existing Google User",
        "iss": "accounts.google.com",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        response = client.post("/auth/google", json={"credential": "mock_google_id_token"})
        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data

    _cleanup_user(test_email)


def test_google_auth_account_linking_required():
    test_email = "password.account@example.com"
    _cleanup_user(test_email)

    # Insert password user
    db = SessionLocal()
    try:
        user = User(
            user_id=uuid.uuid4(),
            name="Password User",
            email=test_email,
            password=get_password_hash(_TEST_PASSWORD),
            role=RoleEnum.ATHLETE,
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    mock_id_info = {
        "sub": "sub_unlinked_123",
        "email": test_email,
        "email_verified": True,
        "name": "Password User",
        "iss": "https://accounts.google.com",
    }

    # Attempt Google login without password -> Expect 409 Conflict
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        response = client.post("/auth/google", json={"credential": "mock_google_id_token"})
        assert response.status_code == 409
        assert "ACCOUNT_LINKING_REQUIRED" in response.text

    # Attempt Google login with WRONG password -> Expect 401 Unauthorized
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        response = client.post("/auth/google", json={"credential": "mock_google_id_token", "password": "WrongPassword!"})
        assert response.status_code == 401
        assert "Incorrect password" in response.text

    # Attempt Google login with CORRECT password -> Expect 200 OK & linked google_sub
    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        response = client.post("/auth/google", json={"credential": "mock_google_id_token", "password": _TEST_PASSWORD})
        assert response.status_code == 200, response.text
        data = response.json()
        assert "access_token" in data

    # Verify google_sub was linked
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == test_email).first()
        assert user.google_sub == "sub_unlinked_123"
        assert user.is_verified is True
    finally:
        db.close()
        _cleanup_user(test_email)


def test_google_auth_unverified_email():
    mock_id_info = {
        "sub": "sub_unverified_999",
        "email": "unverified@example.com",
        "email_verified": False,
        "iss": "https://accounts.google.com",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_id_info):
        response = client.post("/auth/google", json={"credential": "mock_google_id_token"})
        assert response.status_code == 400
        assert "email is not verified" in response.text


def test_google_auth_invalid_token():
    with patch("google.oauth2.id_token.verify_oauth2_token", side_effect=ValueError("Token expired")):
        response = client.post("/auth/google", json={"credential": "expired_token"})
        assert response.status_code == 401
        assert "Invalid Google ID token" in response.text
