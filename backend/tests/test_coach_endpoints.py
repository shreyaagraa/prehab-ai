"""
tests/test_coach_endpoints.py
-------------------------------
Tests for coach-specific endpoints:
- POST /athletes/register-athlete
- PATCH /athletes/{athlete_id}/assign
- GET /videos/assessments
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.core.security import get_password_hash
from app.database import SessionLocal
from app.main import app
from app.models.user import RoleEnum, User
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import AnalysisResult

client = TestClient(app)

_TEST_PASSWORD = "CoachPassword123!"
_CLEANUP_EMAILS: list[str] = []


def _create_user(name: str, email: str, role: RoleEnum) -> User:
    db = SessionLocal()
    try:
        user = User(
            user_id=uuid.uuid4(),
            name=name,
            email=email,
            password=get_password_hash(_TEST_PASSWORD),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        _CLEANUP_EMAILS.append(email)
        return user
    finally:
        db.close()


def _make_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.user_id),
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True, scope="module")
def cleanup():
    yield
    db = SessionLocal()
    try:
        if _CLEANUP_EMAILS:
            users = db.query(User).filter(User.email.in_(_CLEANUP_EMAILS)).all()
            uids = [u.user_id for u in users]
            if uids:
                db.query(AnalysisResult).filter(AnalysisResult.athlete_id.in_(
                    db.query(Athlete.athlete_id).filter(Athlete.user_id.in_(uids))
                )).delete(synchronize_session=False)
                db.query(Video).filter(Video.athlete_id.in_(
                    db.query(Athlete.athlete_id).filter(Athlete.user_id.in_(uids))
                )).delete(synchronize_session=False)
                db.query(Athlete).filter(Athlete.user_id.in_(uids)).delete(synchronize_session=False)
                db.query(User).filter(User.user_id.in_(uids)).delete(synchronize_session=False)
                db.commit()
    finally:
        db.close()


def test_coach_register_athlete():
    coach = _create_user("Coach Carter", "coach.carter@test.com", RoleEnum.COACH)
    token = _make_token(coach)

    payload = {
        "name": "New Player",
        "email": "new.player@test.com",
        "password": "PlayerPassword123!",
        "sport": "Basketball",
        "position": "Point Guard",
        "age": 20,
        "height": 185.0,
        "weight": 78.0,
        "injury_status": "Healthy",
    }
    _CLEANUP_EMAILS.append("new.player@test.com")

    response = client.post(
        "/api/v1/athletes/register-athlete",
        json=payload,
        headers=_auth_header(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Player"
    assert data["email"] == "new.player@test.com"
    assert data["sport"] == "Basketball"
    assert data["coach_id"] == str(coach.user_id)
    assert data["injury_status"] == "Healthy"


def test_coach_assign_athlete():
    coach = _create_user("Coach Phil", "coach.phil@test.com", RoleEnum.COACH)
    athlete_user = _create_user("Michael Jordan", "mj23@test.com", RoleEnum.ATHLETE)

    # Create athlete profile
    db = SessionLocal()
    ath = Athlete(
        user_id=athlete_user.user_id,
        sport="Basketball",
        position="Shooting Guard",
        injury_status="Healthy",
    )
    db.add(ath)
    db.commit()
    db.refresh(ath)
    ath_id = ath.athlete_id
    db.close()

    token = _make_token(coach)

    # Assign athlete to coach Phil
    assign_payload = {
        "coach_id": str(coach.user_id),
        "injury_status": "Recovering",
        "coach_notes": "Needs knee evaluation.",
    }
    resp = client.patch(
        f"/api/v1/athletes/{ath_id}/assign",
        json=assign_payload,
        headers=_auth_header(token),
    )
    assert resp.status_code == 200
    res_data = resp.json()
    assert res_data["coach_id"] == str(coach.user_id)
    assert res_data["injury_status"] == "Recovering"
    assert res_data["coach_notes"] == "Needs knee evaluation."


def test_get_all_assessments_as_coach_and_athlete():
    coach = _create_user("Coach Gregg", "coach.gregg@test.com", RoleEnum.COACH)
    athlete = _create_user("Tim Duncan", "timmy@test.com", RoleEnum.ATHLETE)

    coach_token = _make_token(coach)
    athlete_token = _make_token(athlete)

    # Coach can access /videos/assessments
    resp_coach = client.get("/api/v1/videos/assessments", headers=_auth_header(coach_token))
    assert resp_coach.status_code == 200
    assert isinstance(resp_coach.json(), list)

    # Athlete is forbidden from /videos/assessments
    resp_ath = client.get("/api/v1/videos/assessments", headers=_auth_header(athlete_token))
    assert resp_ath.status_code == 403
