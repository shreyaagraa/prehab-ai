"""
tests/test_risk_scoring_service.py
----------------------------------
Unit and integration tests for RiskScoringService with Dynamic Weight Renormalization.
"""
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

# pyrefly: ignore [missing-import]
pytest = None
# pyrefly: ignore [missing-import]
import pytest

from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import AnalysisResult
from app.models.analysis_feature import AnalysisFeature
from app.models.injury_history import InjuryHistory
from app.core.security import get_password_hash
from app.services.risk_scoring_service import (
    RiskScoringService,
    RiskScoreBreakdown,
    DEFAULT_MODEL_PATH,
    WEIGHT_BIO,
    WEIGHT_HIST,
    WEIGHT_ASYM,
    WEIGHT_LOAD,
    WEIGHT_FATIGUE,
)


class TestRiskScoringService:

    @pytest.fixture(autouse=True)
    def setup_db(self):
        db = SessionLocal()
        self.user = User(
            name="Risk Scoring Test User",
            email=f"risktest_{uuid.uuid4().hex[:8]}@test.com",
            password=get_password_hash("TestPass123!"),
            role=RoleEnum.ATHLETE,
            is_active=True,
        )
        db.add(self.user)
        db.flush()

        self.athlete = Athlete(
            user_id=self.user.user_id,
            sport="Running",
            position="Distance",
            dominant_leg="Right",
            age=25,
            height=180.0,
            weight=75.0,
            training_sessions_per_week=4,
            average_session_duration=60,
            average_session_rpe=7.0,
            weekly_training_load=1680.0,
            current_fatigue_level=5,
            has_injury_history="NO",
        )
        db.add(self.athlete)
        db.flush()

        self.video = Video(
            athlete_id=self.athlete.athlete_id,
            video_url="/uploads/test_run.mp4",
            original_filename="test_run.mp4",
            content_type="video/mp4",
            file_size=1024,
            processing_status="uploaded",
        )
        db.add(self.video)
        db.flush()

        self.analysis = AnalysisResult(
            video_id=self.video.video_id,
            athlete_id=self.athlete.athlete_id,
            status="PROCESSING",
        )
        db.add(self.analysis)
        db.flush()

        self.feature_record = AnalysisFeature(
            analysis_id=self.analysis.analysis_id,
            feature_version="v2",
            features={
                "knee_rom_mean": 50.0,
                "hip_rom_mean": 40.0,
                "ankle_rom_mean": 30.0,
                "trunk_angle_mean": 8.0,
                "knee_asymmetry": 3.0,
                "hip_asymmetry": 2.0,
                "ankle_asymmetry": 1.5,
                "knee_symmetry_score": 90.0,  # 10.0 asymmetry
                "hip_symmetry_score": 85.0,   # 15.0 asymmetry
                "ankle_symmetry_score": 95.0, # 5.0 asymmetry -> Mean asymmetry = 10.0
                "mean_joint_velocity": 2.5,
                "total_joint_displacement": 40.0,
            },
        )
        db.add(self.feature_record)
        db.commit()
        db.close()

    # ── 1. Model Loading ──────────────────────────────────────────────────────
    def test_load_model_missing_file_returns_none(self):
        svc = RiskScoringService(model_path="/path/to/nonexistent/model.joblib")
        assert svc._model is None

    # ── 2. Feature Mapping ────────────────────────────────────────────────────
    def test_map_features_extracts_expected_9_columns(self):
        svc = RiskScoringService()
        df, err = svc.map_features(self.feature_record.features, self.athlete)

        assert err is None
        assert df is not None
        assert df.shape == (1, 9)
        assert list(df.columns) == [
            "knee_rom_mean",
            "hip_rom_mean",
            "ankle_rom_mean",
            "trunk_angle_mean",
            "knee_asymmetry",
            "hip_asymmetry",
            "ankle_asymmetry",
            "mean_joint_velocity",
            "total_joint_displacement",
        ]
        assert df["knee_rom_mean"].iloc[0] == 50.0
        assert df["hip_rom_mean"].iloc[0] == 40.0
        assert df["mean_joint_velocity"].iloc[0] == 2.5

    def test_map_features_handles_none_inputs(self):
        svc = RiskScoringService()
        df, err = svc.map_features(None, None)
        assert df is None
        assert err is not None
        assert "No features dictionary provided" in err

    # ── 3. Factor Calculations & Renormalization ──────────────────────────────
    def test_compute_s_hist_confirmed_no_injuries(self):
        db = SessionLocal()
        try:
            svc = RiskScoringService()
            s_hist, avail = svc.compute_s_hist(self.athlete.athlete_id, db)
            assert s_hist == 0.0
            assert avail is True
        finally:
            db.close()

    def test_compute_s_hist_with_injuries(self):
        db = SessionLocal()
        try:
            for _ in range(3):
                db.add(InjuryHistory(athlete_id=self.athlete.athlete_id, injury_type="Strain"))
            db.commit()

            svc = RiskScoringService()
            s_hist, avail = svc.compute_s_hist(self.athlete.athlete_id, db)
            assert s_hist == 60.0  # 3 * 20
            assert avail is True
        finally:
            db.close()

    def test_compute_s_asym_full_features(self):
        svc = RiskScoringService()
        s_asym, avail = svc.compute_s_asym(self.feature_record.features)
        assert s_asym == 10.0
        assert avail is True

    def test_compute_s_asym_missing_features(self):
        svc = RiskScoringService()
        s_asym, avail = svc.compute_s_asym({})
        assert s_asym is None
        assert avail is False

    def test_compute_s_load_and_fatigue_valid_inputs(self):
        svc = RiskScoringService()
        s_load, load_avail = svc.compute_s_load(self.athlete)
        # 4 sessions * 60 min * 7 RPE = 1680 AU -> 1680 / 3000 * 100 = 56.0
        assert s_load == 56.0
        assert load_avail is True

        s_fatigue, fat_avail = svc.compute_s_fatigue(self.athlete)
        # fatigue_level 5 -> (5 - 1)/9 * 100 = 44.44
        assert s_fatigue == 44.44
        assert fat_avail is True

    def test_compute_s_load_and_fatigue_missing_inputs(self):
        svc = RiskScoringService()
        empty_athlete = Athlete(athlete_id=uuid.uuid4())

        s_load, load_avail = svc.compute_s_load(empty_athlete)
        assert s_load is None
        assert load_avail is False

        s_fatigue, fat_avail = svc.compute_s_fatigue(empty_athlete)
        assert s_fatigue is None
        assert fat_avail is False

    # ── 4. Dynamic Weight Renormalization ──────────────────────────────────────
    def test_dynamic_weight_renormalization_partial_data(self):
        """
        Verify that missing factors are excluded and weights of available factors sum to 100%.
        """
        # Only Bio (35%), Hist (20%), Asym (20%) available -> Sum = 75%
        # Normalized weights: Bio = 35/75 = 0.4667, Hist = 20/75 = 0.2667, Asym = 20/75 = 0.2667
        # Scores: Bio = 40.0, Hist = 0.0, Asym = 10.0
        # Expected = 40 * (35/75) + 0 * (20/75) + 10 * (20/75) = 18.67 + 2.67 = 21.33
        overall = RiskScoringService.calculate_overall_score(
            s_bio=40.0, s_hist=0.0, s_asym=10.0, s_load=None, s_fatigue=None,
            s_bio_avail=True, s_hist_avail=True, s_asym_avail=True, s_load_avail=False, s_fatigue_avail=False
        )
        assert overall == 21.33

    def test_calculate_risk_level_boundaries(self):
        svc = RiskScoringService()
        assert svc.calculate_risk_level(0.0) == "LOW"
        assert svc.calculate_risk_level(39.99) == "LOW"
        assert svc.calculate_risk_level(40.0) == "MODERATE"
        assert svc.calculate_risk_level(69.99) == "MODERATE"
        assert svc.calculate_risk_level(70.0) == "HIGH"
        assert svc.calculate_risk_level(84.99) == "HIGH"
        assert svc.calculate_risk_level(85.0) == "CRITICAL"
        assert svc.calculate_risk_level(100.0) == "CRITICAL"

    # ── 5. Persistence & End-to-End Integration ────────────────────────────────
    def test_compute_and_persist(self):
        db = SessionLocal()
        try:
            svc = RiskScoringService()
            breakdown = svc.compute_and_persist(self.analysis.analysis_id, db)

            assert isinstance(breakdown, RiskScoreBreakdown)
            assert breakdown.s_asym == 10.0
            assert breakdown.s_hist == 0.0
            assert breakdown.s_load == 56.0
            assert breakdown.s_fatigue == 44.44

            ar = db.get(AnalysisResult, self.analysis.analysis_id)
            assert ar is not None
            assert ar.overall_risk_score == breakdown.overall_score
            assert ar.risk_level == breakdown.risk_level
            assert ar.symmetry_score == 10.0
            assert ar.fatigue_score == 44.44
        finally:
            db.close()
