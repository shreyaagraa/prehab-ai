"""
tests/test_recommendation_engine.py
------------------------------------
Comprehensive unit and integration test suite for Corrective Recommendation Engine v1.

Covers:
1. No detected issues -> baseline/clean recommendations, no unnecessary issue recs
2. Knee valgus -> knee/hip strengthening, alignment drills, adductor mobility
3. Poor landing mechanics -> deceleration & landing drills, eccentric strength
4. Limited ankle mobility -> ankle dorsiflexion mobility & stability drills
5. Joint asymmetry -> unilateral stability & strength suggestions
6. High training load -> volume modification & active deload
7. High fatigue -> fatigue management recovery protocol
8. Multiple combined issues -> unified multi-category recommendations
9. Low risk scoring -> low intensity recommendations
10. High risk scoring -> high priority recovery & volume modifications
11. Missing feature -> no fabricated recommendations
12. Duplicate recommendations deduplication
13. Categories & priorities validity
14. CorrectiveActionPlanResponse schema validation
"""
from __future__ import annotations

import uuid
import pytest

from app.services.recommendation_engine import (
    CorrectiveRecommendationEngine,
    DEFAULT_DISCLAIMER,
)
from app.schemas.recommendation import CorrectiveActionPlanResponse


class TestRecommendationEngine:
    """
    Unit test cases for CorrectiveRecommendationEngine detection rules & generation.
    """

    def test_01_no_detected_issues(self):
        """Clean movement metrics should produce zero issue-specific recommendations."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            features={
                "knee_asymmetry": 2.0,
                "hip_asymmetry": 1.5,
                "ankle_asymmetry": 2.0,
                "ankle_rom_mean": 38.0,
                "trunk_angle_mean": 12.0,
                "trunk_angle_max": 20.0,
            },
            less_items=[
                {"item_number": 1, "item_name": "Knee flexion at IC", "status": "PASS"},
                {"item_number": 2, "item_name": "Hip flexion at IC", "status": "PASS"},
                {"item_number": 3, "item_name": "Trunk flexion at IC", "status": "PASS"},
                {"item_number": 4, "item_name": "Ankle plantar-flexion", "status": "PASS"},
                {"item_number": 5, "item_name": "Medial knee at IC", "status": "PASS"},
                {"item_number": 6, "item_name": "Lateral trunk flexion", "status": "PASS"},
                {"item_number": 12, "item_name": "Knee displacement", "status": "PASS"},
                {"item_number": 13, "item_name": "Hip displacement", "status": "PASS"},
                {"item_number": 14, "item_name": "Trunk displacement", "status": "PASS"},
                {"item_number": 15, "item_name": "Knee valgus MKF", "status": "PASS"},
            ],
            risk_score=22.0,
            risk_level="LOW",
            training_data={"training_load": 800.0, "fatigue_level": 2.0},
        )

        assert len(res["exercise_recommendations"]) == 0
        assert len(res["mobility_recommendations"]) == 0
        assert len(res["strengthening_recommendations"]) == 0
        assert len(res["training_modifications"]) == 0
        assert len(res["recovery_plan"]) == 1
        assert res["recovery_plan"][0]["focus"] == "Routine Recovery Practices"
        assert res["disclaimer"] == DEFAULT_DISCLAIMER

    def test_02_knee_valgus_detection(self):
        """Knee valgus finding should generate hip abductor and knee alignment recommendations."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            less_items=[
                {"item_number": 5, "item_name": "Medial knee at IC", "status": "ERROR"},
                {"item_number": 15, "item_name": "Knee valgus MKF", "status": "ERROR"},
            ],
            features={"knee_asymmetry": 14.0},
            risk_score=62.0,
            risk_level="MODERATE",
        )

        assert "Knee Stability & Alignment" in res["priority_areas"]
        strength_titles = [r["title"] for r in res["strengthening_recommendations"]]
        assert any("Gluteus Medius" in t for t in strength_titles)
        exercise_titles = [r["title"] for r in res["exercise_recommendations"]]
        assert any("Knee Tracking" in t for t in exercise_titles)
        mobility_titles = [r["title"] for r in res["mobility_recommendations"]]
        assert any("Adductor" in t for t in mobility_titles)

        # Priority should be high since both IC and MKF valgus occurred with asymmetry
        assert res["strengthening_recommendations"][0]["priority"] == "high"

    def test_03_poor_landing_mechanics(self):
        """Stiff landing with reduced knee displacement should trigger landing control exercises."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            less_items=[
                {"item_number": 1, "item_name": "Knee flexion at IC", "status": "ERROR"},
                {"item_number": 12, "item_name": "Knee displacement", "status": "ERROR"},
            ],
            less_result={"score": 8, "classification": "ELEVATED_LESS_SCREENING_SCORE"},
            risk_score=68.0,
            risk_level="HIGH",
        )

        assert "Landing Mechanics & Deceleration" in res["priority_areas"]
        exercise_titles = [r["title"] for r in res["exercise_recommendations"]]
        assert any("Controlled Deceleration" in t for t in exercise_titles)
        assert any("Plyometric & Landing Volume" in m["title"] for m in res["training_modifications"])

    def test_04_limited_ankle_mobility(self):
        """Restricted ankle ROM should trigger ankle mobility mobilization."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            features={"ankle_rom_mean": 19.5},
            less_items=[{"item_number": 4, "item_name": "Ankle plantar-flexion", "status": "ERROR"}],
            risk_score=35.0,
            risk_level="LOW",
        )

        assert "Ankle Mobility" in res["priority_areas"]
        mob_titles = [r["title"] for r in res["mobility_recommendations"]]
        assert any("Ankle Dorsiflexion" in t for t in mob_titles)
        # Should have knee-to-wall drill
        ankle_rec = next(r for r in res["mobility_recommendations"] if "Ankle" in r["title"])
        assert any("Knee-to-wall" in ex for ex in ankle_rec["exercises"])

    def test_05_joint_asymmetry(self):
        """High bilateral asymmetry should trigger unilateral stability and strength training."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            features={"knee_asymmetry": 18.2, "hip_asymmetry": 16.0},
            risk_score=55.0,
            risk_level="MODERATE",
        )

        assert "Bilateral Symmetry" in res["priority_areas"]
        exercise_titles = [r["title"] for r in res["exercise_recommendations"]]
        assert any("Unilateral Neuromuscular" in t for t in exercise_titles)
        strength_titles = [r["title"] for r in res["strengthening_recommendations"]]
        assert any("Isolated Single-Limb" in t for t in strength_titles)
        mod_titles = [m["title"] for m in res["training_modifications"]]
        assert any("Unilateral Training" in t for t in mod_titles)

    def test_06_high_training_workload(self):
        """High training load should trigger volume modifications and recovery protocol."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            training_data={"training_load": 2600.0, "s_load": 78.0},
            risk_score=65.0,
            risk_level="MODERATE",
        )

        assert "Workload & Fatigue Recovery" in res["priority_areas"]
        assert any("Acute-to-Chronic Workload" in m["title"] for m in res["training_modifications"])
        assert res["recovery_plan"][0]["focus"] == "Active Recovery & Neuromuscular Rest"

    def test_07_high_fatigue_indicators(self):
        """High fatigue should prioritize recovery and fatigue-responsive modifications."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            training_data={"fatigue_level": 9.0, "s_fatigue": 90.0},
            risk_score=75.0,
            risk_level="HIGH",
        )

        assert "Workload & Fatigue Recovery" in res["priority_areas"]
        rec_plan = res["recovery_plan"][0]
        assert rec_plan["priority"] == "high"
        assert any("sleep" in g.lower() for g in rec_plan["guidelines"])

    def test_08_multiple_combined_issues(self):
        """Combined issues should cleanly aggregate without drop-offs."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            features={
                "knee_asymmetry": 16.0,
                "hip_asymmetry": 14.0,
                "ankle_rom_mean": 21.0,
                "trunk_angle_mean": 28.0,
                "trunk_angle_max": 48.0,
            },
            less_items=[
                {"item_number": 5, "item_name": "Medial knee IC", "status": "ERROR"},
                {"item_number": 6, "item_name": "Lateral trunk flexion", "status": "ERROR"},
                {"item_number": 12, "item_name": "Knee displacement", "status": "ERROR"},
            ],
            risk_score=78.0,
            risk_level="HIGH",
            training_data={"training_load": 2400.0, "fatigue_level": 8.0},
        )

        assert len(res["priority_areas"]) >= 4
        assert len(res["exercise_recommendations"]) >= 2
        assert len(res["mobility_recommendations"]) >= 2
        assert len(res["strengthening_recommendations"]) >= 3
        assert len(res["training_modifications"]) >= 2
        assert res["total_recommendations"] > 8

    def test_09_low_risk_appropriate_intensity(self):
        """Low risk profile should have baseline maintenance and non-alarmist phrasing."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            risk_score=18.0,
            risk_level="LOW",
        )

        assert res["risk_level"] == "LOW"
        assert res["total_recommendations"] == 1  # Standard recovery baseline
        assert res["recovery_plan"][0]["priority"] == "low"

    def test_10_high_risk_appropriate_modifications(self):
        """High/Critical risk triggers high priority recovery focus."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            risk_score=82.0,
            risk_level="CRITICAL",
        )

        assert res["recovery_plan"][0]["priority"] == "high"
        assert "Workload & Fatigue Recovery" in res["priority_areas"]

    def test_11_missing_features_no_fabrication(self):
        """None/missing features should not cause false positive recommendations."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            features=None,
            less_items=None,
            less_result=None,
            risk_score=None,
            risk_level=None,
            training_data=None,
        )

        assert len(res["exercise_recommendations"]) == 0
        assert len(res["mobility_recommendations"]) == 0
        assert len(res["strengthening_recommendations"]) == 0
        assert len(res["training_modifications"]) == 0
        assert len(res["priority_areas"]) == 0
        assert len(res["recovery_plan"]) == 1

    def test_12_deduplication(self):
        """Multiple overlapping rules must not duplicate recommendation items."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            less_items=[
                {"item_number": 5, "item_name": "Medial knee at IC", "status": "ERROR"},
                {"item_number": 15, "item_name": "Knee valgus MKF", "status": "ERROR"},
            ],
            features={"knee_asymmetry": 18.0},
        )

        all_ids = [r["id"] for r in res["strengthening_recommendations"]]
        assert len(all_ids) == len(set(all_ids)), "Duplicate recommendation IDs found!"

    def test_13_schema_validation(self):
        """Generated dictionary must validate against CorrectiveActionPlanResponse schema."""
        res = CorrectiveRecommendationEngine.generate_recommendations(
            analysis_id=uuid.uuid4(),
            video_id=uuid.uuid4(),
            features={"knee_asymmetry": 15.0, "ankle_rom_mean": 22.0},
            less_items=[{"item_number": 5, "item_name": "Medial knee", "status": "ERROR"}],
            risk_score=68.0,
            risk_level="HIGH",
        )

        # Validate with Pydantic
        validated = CorrectiveActionPlanResponse.model_validate(res)
        assert validated.total_recommendations > 0
        assert validated.disclaimer == DEFAULT_DISCLAIMER


from datetime import timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import AnalysisResult, ANALYSIS_STATUS_COMPLETED
from app.models.analysis_feature import AnalysisFeature
from app.models.analysis_less import AnalysisLESS
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)


def _token_for(user: User) -> str:
    return create_access_token(
        subject=str(user.user_id),
        role=user.role.value,
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_delta=timedelta(minutes=30),
    )


class TestRecommendationApiEndpoint:
    """
    Integration tests for GET /videos/{video_id}/recommendations and status attachment.
    """

    @pytest.fixture(autouse=True)
    def setup_db(self):
        db = SessionLocal()
        try:
            # Athlete 1
            self.user1 = User(
                name="Rec Athlete 1",
                email=f"rec_ath1_{uuid.uuid4().hex[:8]}@test.com",
                password=get_password_hash("TestPass123!"),
                role=RoleEnum.ATHLETE,
                is_active=True,
            )
            db.add(self.user1)
            db.flush()

            self.athlete1 = Athlete(
                user_id=self.user1.user_id,
                sport="Football",
                position="Midfielder",
                age=23,
                height=180.0,
                training_sessions_per_week=4,
                average_session_duration=60,
                average_session_rpe=7.0,
                current_fatigue_level=6,
            )
            db.add(self.athlete1)
            db.flush()

            self.video1 = Video(
                athlete_id=self.athlete1.athlete_id,
                original_filename="rec_jump_test.mp4",
                content_type="video/mp4",
                file_size=1024,
                video_url="/uploads/rec_jump_test.mp4",
                processing_status="completed",
            )
            db.add(self.video1)
            db.flush()

            self.analysis1 = AnalysisResult(
                video_id=self.video1.video_id,
                athlete_id=self.athlete1.athlete_id,
                status=ANALYSIS_STATUS_COMPLETED,
                overall_risk_score=64.0,
                risk_level="MODERATE",
            )
            db.add(self.analysis1)
            db.flush()

            self.feature1 = AnalysisFeature(
                analysis_id=self.analysis1.analysis_id,
                feature_version="v2",
                features={
                    "knee_asymmetry": 14.5,
                    "hip_asymmetry": 6.2,
                    "ankle_rom_mean": 22.0,
                },
            )
            db.add(self.feature1)

            self.less1 = AnalysisLESS(
                analysis_id=self.analysis1.analysis_id,
                score=6,
                max_computable_score=12,
                computable_items=12,
                error_items=6,
                not_computable_items=5,
                classification="ELEVATED_LESS_SCREENING_SCORE_APPROXIMATION_ONLY",
                source="Padua et al., 2009",
                validation_source="Padua et al., 2015",
                disclaimer="Test LESS disclaimer",
                items=[
                    {"item_number": 5, "item_name": "Medial knee at IC", "status": "ERROR"},
                    {"item_number": 12, "item_name": "Knee displacement", "status": "ERROR"},
                ],
            )
            db.add(self.less1)

            # Athlete 2
            self.user2 = User(
                name="Rec Athlete 2",
                email=f"rec_ath2_{uuid.uuid4().hex[:8]}@test.com",
                password=get_password_hash("TestPass123!"),
                role=RoleEnum.ATHLETE,
                is_active=True,
            )
            db.add(self.user2)
            db.flush()

            self.athlete2 = Athlete(
                user_id=self.user2.user_id,
                sport="Running",
                position="Sprinter",
            )
            db.add(self.athlete2)
            db.flush()

            # Coach user
            self.coach_user = User(
                name="Rec Coach",
                email=f"rec_coach_{uuid.uuid4().hex[:8]}@test.com",
                password=get_password_hash("TestPass123!"),
                role=RoleEnum.COACH,
                is_active=True,
            )
            db.add(self.coach_user)

            db.commit()

            self.user1_id = self.user1.user_id
            self.user2_id = self.user2.user_id
            self.coach_id = self.coach_user.user_id
            self.video1_id = self.video1.video_id
            self.analysis1_id = self.analysis1.analysis_id
            self.athlete1_id = self.athlete1.athlete_id
            self.athlete2_id = self.athlete2.athlete_id

            self.token_user1 = _token_for(self.user1)
            self.token_user2 = _token_for(self.user2)
            self.token_coach = _token_for(self.coach_user)
        finally:
            db.close()

        yield

        # Cleanup
        db_td = SessionLocal()
        try:
            db_td.query(AnalysisLESS).filter(AnalysisLESS.analysis_id == self.analysis1_id).delete()
            db_td.query(AnalysisFeature).filter(AnalysisFeature.analysis_id == self.analysis1_id).delete()
            db_td.query(AnalysisResult).filter(AnalysisResult.video_id == self.video1_id).delete()
            db_td.query(Video).filter(Video.video_id == self.video1_id).delete()
            db_td.query(Athlete).filter(Athlete.athlete_id.in_([self.athlete1_id, self.athlete2_id])).delete()
            db_td.query(User).filter(User.user_id.in_([self.user1_id, self.user2_id, self.coach_id])).delete()
            db_td.commit()
        except Exception:
            db_td.rollback()
        finally:
            db_td.close()

    def test_14_get_recommendations_owner_success(self):
        """Athlete should successfully retrieve structured recommendations for their own video."""
        response = client.get(
            f"/api/v1/videos/{self.video1_id}/recommendations",
            headers={"Authorization": f"Bearer {self.token_user1}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == str(self.video1_id)
        assert len(data["priority_areas"]) > 0
        assert len(data["exercise_recommendations"]) > 0
        assert len(data["strengthening_recommendations"]) > 0
        assert data["total_recommendations"] > 0
        assert "PreHab AI" in data["disclaimer"]

    def test_15_get_recommendations_coach_success(self):
        """Coach should have permission to view recommendations for team athletes."""
        response = client.get(
            f"/api/v1/videos/{self.video1_id}/recommendations",
            headers={"Authorization": f"Bearer {self.token_coach}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == str(self.video1_id)
        assert data["total_recommendations"] > 0

    def test_16_get_recommendations_forbidden_other_athlete(self):
        """Athlete 2 should receive 403 Forbidden when requesting Athlete 1's recommendations."""
        response = client.get(
            f"/api/v1/videos/{self.video1_id}/recommendations",
            headers={"Authorization": f"Bearer {self.token_user2}"},
        )
        assert response.status_code == 403

    def test_17_get_recommendations_unauthorized(self):
        """Unauthenticated request must return 401 Unauthorized."""
        response = client.get(f"/api/v1/videos/{self.video1_id}/recommendations")
        assert response.status_code == 401

    def test_18_analysis_status_attaches_recommendations(self):
        """GET /api/v1/videos/{video_id}/analysis should include recommendations when COMPLETED."""
        response = client.get(
            f"/api/v1/videos/{self.video1_id}/analysis",
            headers={"Authorization": f"Bearer {self.token_user1}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert data["recommendations"] is not None
        assert data["recommendations"]["total_recommendations"] > 0

