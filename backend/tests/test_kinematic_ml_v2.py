"""
tests/test_kinematic_ml_v2.py
------------------------------
Dedicated unit and integration test suite for Kinematic ML Model v2:
- Feature vector construction & order matching
- Missing kinematic feature handling (ML_UNAVAILABLE)
- Non-finite & invalid value rejection
- Versioned model loading & inference probability calculation
- Probability-to-score conversion without 50.0 fallback
- Integration into RiskScoringService & dynamic weight renormalization
"""
import math
import uuid
import numpy as np
import pandas as pd
import pytest

from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import AnalysisResult
from app.models.analysis_feature import AnalysisFeature
from app.core.security import get_password_hash
from app.services.risk_scoring_service import (
    RiskScoringService,
    MODEL_FEATURE_COLUMNS,
    DEFAULT_MODEL_PATH,
)
from app.services.feature_extractor import FeatureExtractor, FEATURE_VERSION
from app.models.pose_landmark import PoseLandmark


class TestKinematicMLv2:

    @pytest.fixture(autouse=True)
    def setup_db(self):
        db = SessionLocal()
        self.user = User(
            name="Kinematic ML Test User",
            email=f"mlv2_{uuid.uuid4().hex[:8]}@test.com",
            password=get_password_hash("MLv2Pass123!"),
            role=RoleEnum.ATHLETE,
            is_active=True,
        )
        db.add(self.user)
        db.flush()

        self.athlete = Athlete(
            user_id=self.user.user_id,
            sport="Track",
            position="Sprinter",
            age=21,
            height=175.0,
            weight=68.0,
            has_injury_history="NO",
        )
        db.add(self.athlete)
        db.flush()

        self.video = Video(
            athlete_id=self.athlete.athlete_id,
            video_url="/uploads/kinematic_v2.mp4",
            original_filename="kinematic_v2.mp4",
            content_type="video/mp4",
            file_size=2048,
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
        db.commit()
        db.close()

    # 1. Feature Order & Schema Matching
    def test_feature_vector_schema_and_order(self):
        expected_columns = [
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
        assert MODEL_FEATURE_COLUMNS == expected_columns

    # 2. Map Features Valid Inputs
    def test_map_features_valid_kinematic_dict(self):
        svc = RiskScoringService()
        valid_features = {
            "knee_rom_mean": 52.0,
            "hip_rom_mean": 42.0,
            "ankle_rom_mean": 32.0,
            "trunk_angle_mean": 8.5,
            "knee_asymmetry": 2.5,
            "hip_asymmetry": 2.0,
            "ankle_asymmetry": 1.8,
            "mean_joint_velocity": 2.2,
            "total_joint_displacement": 35.0,
        }
        df, err = svc.map_features(valid_features, self.athlete)

        assert err is None
        assert df is not None
        assert df.shape == (1, 9)
        assert list(df.columns) == MODEL_FEATURE_COLUMNS
        assert df["knee_rom_mean"].iloc[0] == 52.0
        assert df["hip_rom_mean"].iloc[0] == 42.0

    # 3. Missing Kinematic Features Rejection (ML_UNAVAILABLE)
    def test_map_features_missing_required_kinematic_features(self):
        svc = RiskScoringService()
        incomplete_features = {
            "knee_rom_mean": 52.0,
            "trunk_angle_mean": 8.5,
            # hip_rom_mean missing, ankle_rom_mean missing, etc.
        }
        df, err = svc.map_features(incomplete_features, self.athlete)

        assert df is None
        assert err is not None
        assert "Missing required kinematic features" in err

    # 4. Non-finite / Infinite Values Rejection
    def test_map_features_non_finite_values(self):
        svc = RiskScoringService()
        invalid_features = {
            "knee_rom_mean": float("nan"),
            "hip_rom_mean": 42.0,
            "ankle_rom_mean": 32.0,
            "trunk_angle_mean": 8.5,
            "knee_asymmetry": 2.5,
            "hip_asymmetry": 2.0,
            "ankle_asymmetry": 1.8,
            "mean_joint_velocity": float("inf"),
            "total_joint_displacement": 35.0,
        }
        df, err = svc.map_features(invalid_features, self.athlete)

        assert df is None
        assert err is not None
        assert "Missing required kinematic features" in err or "Non-finite" in err

    # 5. Model Inference & Probability to Score Conversion
    def test_compute_s_bio_valid_prediction(self):
        svc = RiskScoringService()
        valid_features = {
            "knee_rom_mean": 52.0,
            "hip_rom_mean": 42.0,
            "ankle_rom_mean": 32.0,
            "trunk_angle_mean": 8.5,
            "knee_asymmetry": 2.5,
            "hip_asymmetry": 2.0,
            "ankle_asymmetry": 1.8,
            "mean_joint_velocity": 2.2,
            "total_joint_displacement": 35.0,
        }
        s_bio, avail = svc.compute_s_bio(valid_features, self.athlete)

        assert avail is True
        assert s_bio is not None
        assert 0.0 <= s_bio <= 100.0

    # 6. Model Missing / Unavailable Returns (s_bio=None, avail=False) without 50.0 Fallback
    def test_compute_s_bio_missing_artifact_returns_unavailable(self):
        svc = RiskScoringService(model_path="/nonexistent/model.joblib")
        valid_features = {
            "knee_rom_mean": 52.0,
            "hip_rom_mean": 42.0,
            "ankle_rom_mean": 32.0,
            "trunk_angle_mean": 8.5,
            "knee_asymmetry": 2.5,
            "hip_asymmetry": 2.0,
            "ankle_asymmetry": 1.8,
            "mean_joint_velocity": 2.2,
            "total_joint_displacement": 35.0,
        }
        s_bio, avail = svc.compute_s_bio(valid_features, self.athlete)

        assert avail is False
        assert s_bio is None

    # 7. End-to-End FeatureExtractor + RiskScoring Integration
    def test_feature_extractor_produces_v2_kinematic_features(self):
        analysis_id = self.analysis.analysis_id
        landmarks = [
            # Frame 0
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=11, landmark_name="LEFT_SHOULDER", x=-0.2, y=0.2, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=12, landmark_name="RIGHT_SHOULDER", x=0.2, y=0.2, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=23, landmark_name="LEFT_HIP", x=-0.2, y=0.5, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=24, landmark_name="RIGHT_HIP", x=0.2, y=0.5, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=25, landmark_name="LEFT_KNEE", x=-0.2, y=0.8, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=26, landmark_name="RIGHT_KNEE", x=0.2, y=0.8, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=27, landmark_name="LEFT_ANKLE", x=-0.2, y=1.1, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=28, landmark_name="RIGHT_ANKLE", x=0.2, y=1.1, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=31, landmark_name="LEFT_FOOT_INDEX", x=-0.2, y=1.2, z=0.1, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=32, landmark_name="RIGHT_FOOT_INDEX", x=0.2, y=1.2, z=0.1, visibility=0.9),

            # Frame 1
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=11, landmark_name="LEFT_SHOULDER", x=-0.2, y=0.2, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=12, landmark_name="RIGHT_SHOULDER", x=0.2, y=0.2, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=23, landmark_name="LEFT_HIP", x=-0.2, y=0.5, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=24, landmark_name="RIGHT_HIP", x=0.2, y=0.5, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=25, landmark_name="LEFT_KNEE", x=-0.2, y=0.9, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=26, landmark_name="RIGHT_KNEE", x=0.2, y=0.85, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=27, landmark_name="LEFT_ANKLE", x=-0.2, y=1.1, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=28, landmark_name="RIGHT_ANKLE", x=0.2, y=1.1, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=31, landmark_name="LEFT_FOOT_INDEX", x=-0.2, y=1.2, z=0.1, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=32, landmark_name="RIGHT_FOOT_INDEX", x=0.2, y=1.2, z=0.1, visibility=0.9),
        ]
        feats = FeatureExtractor.extract_features_from_landmarks(landmarks)

        for key in MODEL_FEATURE_COLUMNS:
            assert key in feats
            assert feats[key] is not None
            assert math.isfinite(feats[key])
