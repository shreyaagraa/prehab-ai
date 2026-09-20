"""
tests/test_athlete_inputs.py
-----------------------------
Comprehensive tests for athlete profile inputs, workload calculation, fatigue scale,
injury history endpoints, and dynamic weight renormalization.
"""
import uuid
from datetime import timedelta
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.injury_history import InjuryHistory
from app.core.security import get_password_hash, create_access_token
from app.services.risk_scoring_service import RiskScoringService


client = TestClient(app)


class TestAthleteInputsAndInjuryHistory:

    @pytest.fixture(autouse=True)
    def setup_users(self):
        db = SessionLocal()

        self.athlete_user = User(
            name="Test Athlete",
            email=f"athlete_input_{uuid.uuid4().hex[:8]}@test.com",
            password=get_password_hash("Athlete123!"),
            role=RoleEnum.ATHLETE,
            is_active=True,
        )
        db.add(self.athlete_user)
        db.commit()

        self.athlete = Athlete(
            user_id=self.athlete_user.user_id,
            sport="Football",
            position="Midfielder",
            dominant_leg="Right",
            age=22,
            height=178.0,
            weight=72.0,
            training_sessions_per_week=4,
            average_session_duration=60,
            average_session_rpe=7.0,
            weekly_training_load=1680.0,
            current_fatigue_level=5,
            has_injury_history="NO",
        )
        db.add(self.athlete)
        db.commit()

        self.token = create_access_token(
            subject=str(self.athlete_user.user_id),
            role=self.athlete_user.role.value,
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
            expires_delta=timedelta(minutes=30),
        )
        self.headers = {"Authorization": f"Bearer {self.token}"}

        db.close()

    def test_upsert_athlete_profile_calculates_workload(self):
        payload = {
            "sport": "Basketball",
            "position": "Point Guard",
            "dominant_leg": "Left",
            "age": 24,
            "height": 185.0,
            "weight": 80.0,
            "training_sessions_per_week": 5,
            "average_session_duration": 90,
            "average_session_rpe": 8.0,
            "current_fatigue_level": 6,
            "has_injury_history": "NO",
        }

        res = client.put("/api/v1/athletes/me", json=payload, headers=self.headers)
        assert res.status_code == 200
        data = res.json()

        assert data["sport"] == "Basketball"
        assert data["dominant_leg"] == "Left"
        assert data["training_sessions_per_week"] == 5
        assert data["average_session_duration"] == 90
        assert data["average_session_rpe"] == 8.0
        # 5 * 90 * 8 = 3600 AU
        assert data["weekly_training_load"] == 3600.0
        assert data["training_load"] == 3600.0
        assert data["current_fatigue_level"] == 6
        assert data["has_injury_history"] == "NO"

    def test_validation_rejects_invalid_inputs(self):
        # Invalid RPE (> 10)
        res_rpe = client.put(
            "/api/v1/athletes/me",
            json={"average_session_rpe": 12.0},
            headers=self.headers,
        )
        assert res_rpe.status_code == 422

        # Invalid fatigue (> 10)
        res_fat = client.put(
            "/api/v1/athletes/me",
            json={"current_fatigue_level": 15},
            headers=self.headers,
        )
        assert res_fat.status_code == 422

        # Negative sessions
        res_sess = client.put(
            "/api/v1/athletes/me",
            json={"training_sessions_per_week": -2},
            headers=self.headers,
        )
        assert res_sess.status_code == 422

    def test_fatigue_normalization_formula(self):
        svc = RiskScoringService()

        # 1 -> 0
        a1 = Athlete(current_fatigue_level=1)
        s1, avail1 = svc.compute_s_fatigue(a1)
        assert s1 == 0.0
        assert avail1 is True

        # 5 -> 44.44
        a5 = Athlete(current_fatigue_level=5)
        s5, avail5 = svc.compute_s_fatigue(a5)
        assert s5 == 44.44
        assert avail5 is True

        # 10 -> 100
        a10 = Athlete(current_fatigue_level=10)
        s10, avail10 = svc.compute_s_fatigue(a10)
        assert s10 == 100.0
        assert avail10 is True

    def test_injury_history_endpoints_and_status_sync(self):
        # GET empty injury history
        res_get = client.get("/api/v1/injury-history/me", headers=self.headers)
        assert res_get.status_code == 200
        assert res_get.json() == []

        # POST new injury record
        injury_payload = {
            "injury_type": "Hamstring Strain",
            "body_part": "Hamstring",
            "severity": "Moderate",
            "injury_date": "2025-06-15",
            "status": "Recovered",
            "remarks": "Rehab completed",
        }

        res_post = client.post("/api/v1/injury-history/me", json=injury_payload, headers=self.headers)
        assert res_post.status_code == 201
        created = res_post.json()
        assert created["injury_type"] == "Hamstring Strain"
        assert created["body_part"] == "Hamstring"
        assert created["status"] == "Recovered"

        # Verify has_injury_history automatically updated to 'YES'
        res_me = client.get("/api/v1/athletes/me", headers=self.headers)
        assert res_me.status_code == 200
        assert res_me.json()["has_injury_history"] == "YES"

        # DELETE injury record
        injury_id = created["injury_id"]
        res_del = client.delete(f"/api/v1/injury-history/me/{injury_id}", headers=self.headers)
        assert res_del.status_code == 204

        # Verify profile updated to 'NO' after last record deleted
        res_me2 = client.get("/api/v1/athletes/me", headers=self.headers)
        assert res_me2.status_code == 200
        assert res_me2.json()["has_injury_history"] == "NO"
