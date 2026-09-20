"""
tests/test_rbac.py
------------------
Reusable Role-Based Access Control (RBAC) tests.

Tests:
1. Correct role is allowed (200).
2. Wrong role is rejected (403).
3. Missing token is rejected (401).
4. Invalid token is rejected (401).
5. require_roles() allows Coach.
6. require_roles() allows Physiotherapist.
7. require_roles() rejects Athlete.
8. Database role is authoritative, not the JWT role claim.
9. All five individual role dependencies work correctly.
10. Resource-level ownership & RBAC boundary tests.

All test users are cleaned up after the test module.
"""

import uuid
from datetime import datetime, timedelta, timezone

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from jose import jwt

from app.config import settings
from app.core.security import get_password_hash
from app.database import SessionLocal
from app.main import app
from app.models.user import RoleEnum, User
from app.models.athlete import Athlete
from app.models.video import Video


client = TestClient(app)

_TEST_PASSWORD = "TestPassword@Step4!"
_CLEANUP_EMAILS: list[str] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_user(
    name: str,
    email: str,
    role: RoleEnum,
    is_active: bool = True,
) -> User:
    """Create a test user directly in the database."""
    db = SessionLocal()
    try:
        user = User(
            user_id=uuid.uuid4(),
            name=name,
            email=email,
            password=get_password_hash(_TEST_PASSWORD),
            role=role,
            is_active=is_active,
            is_verified=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        _CLEANUP_EMAILS.append(email)

        return user
    finally:
        db.close()


def _create_test_athlete(user: User, sport: str = "Soccer") -> Athlete:
    """Create a test athlete profile linked to user."""
    db = SessionLocal()
    try:
        athlete = Athlete(
            athlete_id=uuid.uuid4(),
            user_id=user.user_id,
            sport=sport,
            position="Forward",
            age=22,
            height=175.0,
            weight=70.0,
        )
        db.add(athlete)
        db.commit()
        db.refresh(athlete)
        return athlete
    finally:
        db.close()


def _make_token(
    subject: str,
    *,
    role: str = RoleEnum.ATHLETE.value,
    secret: str = settings.SECRET_KEY,
    expires_delta: timedelta = timedelta(minutes=30),
) -> str:
    """Create a signed JWT for RBAC testing."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + expires_delta,
    }

    return jwt.encode(
        payload,
        secret,
        algorithm=settings.ALGORITHM,
    )


def _auth_header(token: str) -> dict[str, str]:
    """Build an Authorization header."""
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Teardown
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="module")
def cleanup_test_users():
    """Delete all users created by this test module after all tests finish."""
    yield

    db = SessionLocal()
    try:
        if _CLEANUP_EMAILS:
            user_ids = [
                u.user_id for u in db.query(User).filter(User.email.in_(_CLEANUP_EMAILS)).all()
            ]
            if user_ids:
                db.query(Athlete).filter(Athlete.user_id.in_(user_ids)).delete(synchronize_session=False)
                db.query(User).filter(User.user_id.in_(user_ids)).delete(synchronize_session=False)
                db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Single-role RBAC tests
# ---------------------------------------------------------------------------

class TestSingleRoleRBAC:
    """Tests for require_role()."""

    @pytest.mark.parametrize(
        ("role", "endpoint"),
        [
            (RoleEnum.ATHLETE, "/auth/rbac-probe/athlete"),
            (RoleEnum.COACH, "/auth/rbac-probe/coach"),
            (RoleEnum.PHYSIOTHERAPIST, "/auth/rbac-probe/physiotherapist"),
            (RoleEnum.SPORTS_SCIENTIST, "/auth/rbac-probe/sports-scientist"),
            (RoleEnum.ADMINISTRATOR, "/auth/rbac-probe/administrator"),
        ],
    )
    def test_correct_role_is_allowed(self, role, endpoint):
        """A user with the required role receives HTTP 200."""
        user = _create_test_user(
            name=f"{role.value} RBAC User",
            email=f"rbac.correct.{role.name.lower()}@test.invalid",
            role=role,
        )

        token = _make_token(
            str(user.user_id),
            role=role.value,
        )

        response = client.get(
            endpoint,
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["role"] == role.value
        assert data["user_id"] == str(user.user_id)

    @pytest.mark.parametrize(
        ("user_role", "endpoint"),
        [
            (RoleEnum.ATHLETE, "/auth/rbac-probe/coach"),
            (RoleEnum.COACH, "/auth/rbac-probe/athlete"),
            (RoleEnum.PHYSIOTHERAPIST, "/auth/rbac-probe/administrator"),
            (RoleEnum.SPORTS_SCIENTIST, "/auth/rbac-probe/physiotherapist"),
            (RoleEnum.ADMINISTRATOR, "/auth/rbac-probe/athlete"),
        ],
    )
    def test_wrong_role_returns_403(self, user_role, endpoint):
        """An authenticated user with the wrong role receives HTTP 403."""
        user = _create_test_user(
            name=f"Wrong Role {user_role.value}",
            email=f"rbac.wrong.{user_role.name.lower()}@test.invalid",
            role=user_role,
        )

        token = _make_token(
            str(user.user_id),
            role=user_role.value,
        )

        response = client.get(
            endpoint,
            headers=_auth_header(token),
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Multi-role RBAC tests
# ---------------------------------------------------------------------------

class TestMultiRoleRBAC:
    """Tests for require_roles()."""

    def test_coach_allowed_on_multi_role_endpoint(self):
        """Coach is allowed by require_roles(Coach, Physiotherapist)."""
        user = _create_test_user(
            name="Multi Role Coach",
            email="rbac.multirole.coach@test.invalid",
            role=RoleEnum.COACH,
        )

        token = _make_token(
            str(user.user_id),
            role=RoleEnum.COACH.value,
        )

        response = client.get(
            "/auth/rbac-probe/multi-role",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        assert response.json()["role"] == RoleEnum.COACH.value

    def test_physiotherapist_allowed_on_multi_role_endpoint(self):
        """Physiotherapist is allowed by require_roles(Coach, Physiotherapist)."""
        user = _create_test_user(
            name="Multi Role Physiotherapist",
            email="rbac.multirole.physio@test.invalid",
            role=RoleEnum.PHYSIOTHERAPIST,
        )

        token = _make_token(
            str(user.user_id),
            role=RoleEnum.PHYSIOTHERAPIST.value,
        )

        response = client.get(
            "/auth/rbac-probe/multi-role",
            headers=_auth_header(token),
        )

        assert response.status_code == 200
        assert response.json()["role"] == RoleEnum.PHYSIOTHERAPIST.value

    def test_athlete_rejected_from_multi_role_endpoint(self):
        """Athlete is rejected because it is not an allowed role."""
        user = _create_test_user(
            name="Multi Role Athlete",
            email="rbac.multirole.athlete@test.invalid",
            role=RoleEnum.ATHLETE,
        )

        token = _make_token(
            str(user.user_id),
            role=RoleEnum.ATHLETE.value,
        )

        response = client.get(
            "/auth/rbac-probe/multi-role",
            headers=_auth_header(token),
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Authentication vs authorization semantics
# ---------------------------------------------------------------------------

class TestRBACAuthenticationBoundary:
    """Verify 401 authentication vs 403 authorization behavior."""

    def test_missing_token_returns_401(self):
        """No JWT means authentication failed → 401."""
        response = client.get("/auth/rbac-probe/coach")

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"].startswith("Bearer")

    def test_invalid_token_returns_401(self):
        """Invalid JWT means authentication failed → 401."""
        response = client.get(
            "/auth/rbac-probe/coach",
            headers={"Authorization": "Bearer invalid.token.value"},
        )

        assert response.status_code == 401

    def test_inactive_user_returns_401(self):
        """Inactive users cannot reach RBAC authorization → 401."""
        user = _create_test_user(
            name="Inactive RBAC User",
            email="rbac.inactive@test.invalid",
            role=RoleEnum.COACH,
            is_active=False,
        )

        token = _make_token(
            str(user.user_id),
            role=RoleEnum.COACH.value,
        )

        response = client.get(
            "/auth/rbac-probe/coach",
            headers=_auth_header(token),
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Database-authoritative role test
# ---------------------------------------------------------------------------

class TestDatabaseAuthoritativeRole:
    """Verify RBAC never trusts the JWT role claim."""

    def test_rbac_uses_database_role_not_jwt_role(self):
        """
        A token claiming an elevated role must not grant access when the
        database says the user has a different role.
        """
        user = _create_test_user(
            name="Database Role Authority User",
            email="rbac.db.authority@test.invalid",
            role=RoleEnum.ATHLETE,
        )

        # Deliberately forge a JWT claiming Administrator.
        token = _make_token(
            str(user.user_id),
            role=RoleEnum.ADMINISTRATOR.value,
        )

        response = client.get(
            "/auth/rbac-probe/administrator",
            headers=_auth_header(token),
        )

        # Authentication succeeds, but database role is Athlete.
        # Therefore authorization must reject the request.
        assert response.status_code == 403
        assert "Administrator" in response.json()["detail"]
        assert "Athlete" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test token for a nonexistent user
# ---------------------------------------------------------------------------

class TestRBACUserValidation:
    """Verify RBAC depends on a real authenticated database user."""

    def test_nonexistent_user_returns_401(self):
        """A valid JWT for a nonexistent user must fail authentication."""
        nonexistent_user_id = str(uuid.uuid4())

        token = _make_token(
            nonexistent_user_id,
            role=RoleEnum.COACH.value,
        )

        response = client.get(
            "/auth/rbac-probe/coach",
            headers=_auth_header(token),
        )

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Resource-level & endpoint RBAC boundary tests
# ---------------------------------------------------------------------------

class TestResourceLevelRBAC:
    """Tests for resource ownership & endpoint-specific authorization rules."""

    def test_athlete_cannot_access_other_athlete_profile(self):
        """Athlete A cannot access Athlete B's profile via GET /athletes/{id} -> 403."""
        user_a = _create_test_user("Athlete A", "athlete.a@test.invalid", RoleEnum.ATHLETE)
        user_b = _create_test_user("Athlete B", "athlete.b@test.invalid", RoleEnum.ATHLETE)

        _create_test_athlete(user_a)
        athlete_b = _create_test_athlete(user_b)

        token_a = _make_token(str(user_a.user_id), role=RoleEnum.ATHLETE.value)

        response = client.get(
            f"/api/v1/athletes/{athlete_b.athlete_id}",
            headers=_auth_header(token_a),
        )

        assert response.status_code == 403
        assert "only access your own" in response.json()["detail"]

    def test_athlete_can_access_own_athlete_profile(self):
        """Athlete A can access own profile via GET /athletes/{id} -> 200."""
        user_a = _create_test_user("Athlete Own Profile", "athlete.own@test.invalid", RoleEnum.ATHLETE)
        athlete_a = _create_test_athlete(user_a)

        token_a = _make_token(str(user_a.user_id), role=RoleEnum.ATHLETE.value)

        response = client.get(
            f"/api/v1/athletes/{athlete_a.athlete_id}",
            headers=_auth_header(token_a),
        )

        assert response.status_code == 200
        assert response.json()["athlete_id"] == str(athlete_a.athlete_id)

    def test_staff_role_can_access_any_athlete_profile(self):
        """Coach can access Athlete A's profile via GET /athletes/{id} -> 200."""
        user_a = _create_test_user("Athlete for Coach", "athlete.coach.target@test.invalid", RoleEnum.ATHLETE)
        athlete_a = _create_test_athlete(user_a)

        coach_user = _create_test_user("Staff Coach", "coach.staff@test.invalid", RoleEnum.COACH)
        coach_token = _make_token(str(coach_user.user_id), role=RoleEnum.COACH.value)

        response = client.get(
            f"/api/v1/athletes/{athlete_a.athlete_id}",
            headers=_auth_header(coach_token),
        )

        assert response.status_code == 200
        assert response.json()["athlete_id"] == str(athlete_a.athlete_id)

    def test_non_athlete_cannot_upload_video(self):
        """Coach role attempting POST /videos receives HTTP 403."""
        coach_user = _create_test_user("Coach Video Upload", "coach.upload@test.invalid", RoleEnum.COACH)
        coach_token = _make_token(str(coach_user.user_id), role=RoleEnum.COACH.value)

        files = {"file": ("test.mp4", b"dummy video bytes", "video/mp4")}
        response = client.post(
            "/api/v1/videos",
            headers=_auth_header(coach_token),
            files=files,
        )

        assert response.status_code == 403
        assert "Only Athlete users" in response.json()["detail"]

    def test_non_admin_cannot_delete_athlete_profile(self):
        """Coach attempting DELETE /athletes/{id} receives HTTP 403."""
        user_a = _create_test_user("Athlete to Delete Test", "athlete.nodelete@test.invalid", RoleEnum.ATHLETE)
        athlete_a = _create_test_athlete(user_a)

        coach_user = _create_test_user("Coach No Admin", "coach.noadmin@test.invalid", RoleEnum.COACH)
        coach_token = _make_token(str(coach_user.user_id), role=RoleEnum.COACH.value)

        response = client.delete(
            f"/api/v1/athletes/{athlete_a.athlete_id}",
            headers=_auth_header(coach_token),
        )

        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]

    def test_admin_can_delete_athlete_profile(self):
        """Administrator attempting DELETE /athletes/{id} receives HTTP 204."""
        user_a = _create_test_user("Athlete to Delete Admin", "athlete.delete.admin@test.invalid", RoleEnum.ATHLETE)
        athlete_a = _create_test_athlete(user_a)

        admin_user = _create_test_user("Admin Delete User", "admin.delete@test.invalid", RoleEnum.ADMINISTRATOR)
        admin_token = _make_token(str(admin_user.user_id), role=RoleEnum.ADMINISTRATOR.value)

        response = client.delete(
            f"/api/v1/athletes/{athlete_a.athlete_id}",
            headers=_auth_header(admin_token),
        )

        assert response.status_code == 204

    def test_athlete_list_returns_only_own_profile(self):
        """Athlete calling GET /athletes receives list containing only their own record."""
        user_a = _create_test_user("Athlete List Self", "athlete.list.self@test.invalid", RoleEnum.ATHLETE)
        athlete_a = _create_test_athlete(user_a)

        token_a = _make_token(str(user_a.user_id), role=RoleEnum.ATHLETE.value)

        response = client.get(
            "/api/v1/athletes",
            headers=_auth_header(token_a),
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["athlete_id"] == str(athlete_a.athlete_id)

    def test_coach_can_access_assigned_athlete_video_analysis(self):
        """Coach can access video analysis of an athlete assigned to their roster."""
        coach_user = _create_test_user("Coach Assigned", "coach.assigned@test.invalid", RoleEnum.COACH)
        athlete_user = _create_test_user("Athlete Roster", "athlete.roster@test.invalid", RoleEnum.ATHLETE)

        db = SessionLocal()
        try:
            athlete = Athlete(
                athlete_id=uuid.uuid4(),
                user_id=athlete_user.user_id,
                coach_id=coach_user.user_id,
                sport="Soccer",
            )
            db.add(athlete)
            db.commit()

            video = Video(
                video_id=uuid.uuid4(),
                athlete_id=athlete.athlete_id,
                original_filename="test.mp4",
                video_url="/uploads/test.mp4",
                processing_status="COMPLETED",
            )
            db.add(video)
            db.commit()

            coach_token = _make_token(str(coach_user.user_id), role=RoleEnum.COACH.value)
            response = client.get(
                f"/api/v1/videos/{video.video_id}/analysis",
                headers=_auth_header(coach_token),
            )
            # Authorization passes (returns 404 since no AnalysisResult row exists, NOT 403)
            assert response.status_code == 404
            assert "No analysis found" in response.json()["detail"]
        finally:
            db.close()

    def test_coach_cannot_access_unassigned_athlete_video_analysis(self):
        """Coach cannot access video analysis of an athlete not in their roster -> 403."""
        coach_user = _create_test_user("Coach Unassigned", "coach.unassigned@test.invalid", RoleEnum.COACH)
        other_coach = _create_test_user("Coach Other", "coach.other@test.invalid", RoleEnum.COACH)
        athlete_user = _create_test_user("Athlete Other Roster", "athlete.otherroster@test.invalid", RoleEnum.ATHLETE)

        db = SessionLocal()
        try:
            athlete = Athlete(
                athlete_id=uuid.uuid4(),
                user_id=athlete_user.user_id,
                coach_id=other_coach.user_id,
                sport="Soccer",
            )
            db.add(athlete)
            db.commit()

            video = Video(
                video_id=uuid.uuid4(),
                athlete_id=athlete.athlete_id,
                original_filename="test2.mp4",
                video_url="/uploads/test2.mp4",
                processing_status="COMPLETED",
            )
            db.add(video)
            db.commit()

            coach_token = _make_token(str(coach_user.user_id), role=RoleEnum.COACH.value)
            response = client.get(
                f"/api/v1/videos/{video.video_id}/analysis",
                headers=_auth_header(coach_token),
            )
            assert response.status_code == 403
            assert "permission" in response.json()["detail"].lower()
        finally:
            db.close()