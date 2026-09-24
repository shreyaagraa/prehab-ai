"""
tests/test_consent_and_profile_features.py
-------------------------------------------
Comprehensive tests for:
1. Signup email validation (reject sdf@fds, accept test@gmail.com).
2. Date of birth (DOB) & minor calculation.
3. Purpose-specific consent grant, status, and withdrawal.
4. Backend upload consent gate enforcement.
5. Coach profile update & Coach athlete roster profile edit authorization.
6. Athlete-controlled report sharing access controls.
"""
import uuid
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.consent_record import ConsentRecord, ConsentPurposeEnum, ConsentStatusEnum
from app.models.report_share import ReportShare
from app.core.security import create_access_token, get_password_hash

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _create_test_user(db_session, email: str, role: RoleEnum, dob: date = None, name: str = "Test User"):
    user = User(
        user_id=uuid.uuid4(),
        name=name,
        email=email.strip().lower(),
        password=get_password_hash("Password123!"),
        role=role,
        date_of_birth=dob,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    athlete = None
    if role == RoleEnum.ATHLETE:
        athlete = Athlete(
            athlete_id=uuid.uuid4(),
            user_id=user.user_id,
            sport="Football",
            position="Forward",
            age=user.computed_age or 22,
            injury_status="Healthy",
        )
        db_session.add(athlete)
        db_session.commit()
        db_session.refresh(athlete)

    return user, athlete


from app.config import settings
from datetime import timedelta


def _get_auth_headers(user: User):
    token = create_access_token(
        subject=str(user.user_id),
        role=user.role.value,
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_delta=timedelta(minutes=60),
    )
    return {"Authorization": f"Bearer {token}"}


class TestInvalidEmailRegistration:
    def test_reject_invalid_email_sdf_at_fds(self, db):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Invalid Email Test",
                "email": "sdf@fds",
                "password": "Password123!",
                "role": "Athlete",
                "date_of_birth": "2000-01-01",
            },
        )
        assert response.status_code in (422, 400)
        detail = str(response.json())
        assert "Invalid email" in detail or "extension" in detail or "format" in detail

    def test_accept_valid_email_test_gmail(self, db):
        unique_email = f"test_{uuid.uuid4().hex[:6]}@gmail.com"
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Valid Email User",
                "email": unique_email,
                "password": "Password123!",
                "role": "Athlete",
                "date_of_birth": "2000-05-15",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == unique_email
        assert data["is_minor"] is False


class TestUserProfileEditing:
    def test_coach_edits_own_profile(self, db):
        coach, _ = _create_test_user(db, f"coach_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.COACH, dob=date(1985, 4, 10), name="Coach Old Name")
        headers = _get_auth_headers(coach)

        response = client.patch(
            "/api/v1/auth/me",
            headers=headers,
            json={
                "name": "Coach Updated Name",
                "phone": "+19876543210",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Coach Updated Name"
        assert data["phone"] == "+19876543210"


class TestCoachEditAthleteRosterSecurity:
    def test_coach_can_edit_assigned_roster_athlete(self, db):
        coach, _ = _create_test_user(db, f"coach_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.COACH, name="Head Coach")
        athlete_user, athlete = _create_test_user(db, f"ath_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.ATHLETE, dob=date(2002, 1, 1), name="Roster Athlete")
        
        athlete.coach_id = coach.user_id
        db.commit()

        headers = _get_auth_headers(coach)
        response = client.patch(
            f"/api/v1/athletes/{athlete.athlete_id}",
            headers=headers,
            json={
                "sport": "Basketball",
                "position": "Point Guard",
                "coach_notes": "Needs extra agility drills.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sport"] == "Basketball"
        assert data["position"] == "Point Guard"
        assert data["coach_notes"] == "Needs extra agility drills."

    def test_coach_cannot_edit_unassigned_athlete(self, db):
        coach, _ = _create_test_user(db, f"coach_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.COACH, name="Coach Alpha")
        other_coach, _ = _create_test_user(db, f"coach_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.COACH, name="Coach Beta")
        athlete_user, athlete = _create_test_user(db, f"ath_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.ATHLETE, dob=date(2002, 1, 1), name="Beta's Athlete")

        athlete.coach_id = other_coach.user_id
        db.commit()

        # Coach Alpha attempts to edit Coach Beta's athlete
        headers = _get_auth_headers(coach)
        response = client.patch(
            f"/api/v1/athletes/{athlete.athlete_id}",
            headers=headers,
            json={
                "sport": "Tennis",
            },
        )
        assert response.status_code == 403
        assert "not assigned to your roster" in response.json()["detail"]


class TestConsentLifecycle:
    def test_adult_consent_flow_and_upload_gate(self, db):
        adult_user, athlete = _create_test_user(db, f"adult_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.ATHLETE, dob=date(1995, 6, 20), name="Adult Athlete")
        headers = _get_auth_headers(adult_user)

        # 1. Check initial consent status
        res_status = client.get("/api/v1/consent/status", headers=headers)
        assert res_status.status_code == 200
        st_data = res_status.json()
        assert st_data["is_minor"] is False
        assert st_data["can_upload"] is False

        # 2. Grant required consents
        grant_res = client.post(
            "/api/v1/consent/grant",
            headers=headers,
            json={
                "consents": [
                    {"purpose": "injury_risk_analysis", "notice_version": "v1.0"},
                    {"purpose": "progress_tracking", "notice_version": "v1.0"},
                    {"purpose": "research_anonymised", "notice_version": "v1.0"},
                ]
            },
        )
        assert grant_res.status_code == 200
        grant_data = grant_res.json()
        assert grant_data["can_upload"] is True

        # 3. Withdraw consent
        withdraw_res = client.post(
            "/api/v1/consent/withdraw",
            headers=headers,
            json={"purpose": "injury_risk_analysis"},
        )
        assert withdraw_res.status_code == 200
        withdraw_data = withdraw_res.json()
        assert withdraw_data["can_upload"] is False

    def test_minor_parent_guardian_consent_required(self, db):
        # Athlete under 18
        today = date.today()
        minor_dob = date(today.year - 16, today.month, today.day)
        minor_user, athlete = _create_test_user(db, f"minor_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.ATHLETE, dob=minor_dob, name="Minor Athlete")
        headers = _get_auth_headers(minor_user)

        res_status = client.get("/api/v1/consent/status", headers=headers)
        assert res_status.json()["is_minor"] is True

        # Attempt grant without guardian name should fail
        fail_grant = client.post(
            "/api/v1/consent/grant",
            headers=headers,
            json={
                "consents": [
                    {"purpose": "injury_risk_analysis", "guardian_name": ""},
                ]
            },
        )
        assert fail_grant.status_code == 400

        # Valid grant with parent/guardian info
        ok_grant = client.post(
            "/api/v1/consent/grant",
            headers=headers,
            json={
                "consents": [
                    {
                        "purpose": "injury_risk_analysis",
                        "guardian_name": "Jane Parent",
                        "guardian_email": "jane@parent.com",
                        "guardian_relationship": "Mother",
                    },
                    {
                        "purpose": "progress_tracking",
                        "guardian_name": "Jane Parent",
                        "guardian_email": "jane@parent.com",
                        "guardian_relationship": "Mother",
                    },
                ]
            },
        )
        assert ok_grant.status_code == 200
        assert ok_grant.json()["can_upload"] is True


class TestAthleteReportSharingControls:
    def test_athlete_revokes_coach_report_sharing(self, db):
        coach, _ = _create_test_user(db, f"coach_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.COACH, name="Roster Coach")
        athlete_user, athlete = _create_test_user(db, f"ath_{uuid.uuid4().hex[:6]}@test.com", RoleEnum.ATHLETE, name="Privacy Athlete")
        athlete.coach_id = coach.user_id
        db.commit()

        ath_headers = _get_auth_headers(athlete_user)
        coach_headers = _get_auth_headers(coach)

        # Initially coach can access athlete reports options/data
        rep_opt_1 = client.get("/api/v1/reports/options", headers=coach_headers)
        assert rep_opt_1.status_code == 200

        # Athlete revokes Coach access
        revoke_res = client.post(
            "/api/v1/reports/sharing/update",
            headers=ath_headers,
            json={"target_role": "Coach", "is_authorized": False},
        )
        assert revoke_res.status_code == 200

        # Coach attempting to access athlete's report payload should now receive HTTP 403
        data_res = client.get(
            f"/api/v1/reports/data?report_type=INJURY_RISK&athlete_id={athlete.athlete_id}",
            headers=coach_headers,
        )
        assert data_res.status_code == 403
        assert "revoked" in data_res.json()["detail"]
