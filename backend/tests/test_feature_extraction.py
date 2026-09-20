"""
tests/test_feature_extraction.py
----------------------------------
Unit and integration tests for Biomechanical Feature Extraction:
  - 3D joint angle calculations
  - Low visibility and missing landmark safety
  - Range of motion (ROM) and left/right symmetry
  - Database persistence via FeatureExtractor
  - Endpoint authorization & response format for GET /videos/{video_id}/features
"""
import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import AnalysisResult, ANALYSIS_STATUS_COMPLETED
from app.models.pose_landmark import PoseLandmark
from app.models.analysis_feature import AnalysisFeature
from app.core.security import get_password_hash, create_access_token
from app.services.feature_extractor import (
    calculate_3d_angle,
    calculate_trunk_angle,
    calculate_symmetry_score,
    FeatureExtractor,
    FEATURE_VERSION,
)

client = TestClient(app)

_TEST_PASSWORD = "FeatureTest@123!"
_CLEANUP_USER_IDS: list[uuid.UUID] = []


def _create_athlete_user(name: str, email: str) -> tuple[User, Athlete]:
    db = SessionLocal()
    try:
        user = User(
            name=name,
            email=email,
            password=get_password_hash(_TEST_PASSWORD),
            role=RoleEnum.ATHLETE,
            is_active=True,
        )
        db.add(user)
        db.flush()

        athlete = Athlete(
            user_id=user.user_id,
            sport="Basketball",
            position="Guard",
            age=24,
            height=190.0,
            weight=85.0,
        )
        db.add(athlete)
        db.commit()
        db.refresh(user)
        db.refresh(athlete)
        _CLEANUP_USER_IDS.append(user.user_id)
        return user, athlete
    finally:
        db.close()


def _token_for(user_id: uuid.UUID, role: str = RoleEnum.ATHLETE.value) -> str:
    return create_access_token(
        subject=str(user_id),
        role=role,
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_delta=timedelta(minutes=30),
    )


def _auth(user_id: uuid.UUID, role: str = RoleEnum.ATHLETE.value) -> dict:
    return {"Authorization": f"Bearer {_token_for(user_id, role)}"}


def teardown_module(_module):
    db = SessionLocal()
    try:
        for uid in _CLEANUP_USER_IDS:
            user = db.query(User).filter(User.user_id == uid).first()
            if not user:
                continue
            athlete = db.query(Athlete).filter(Athlete.user_id == uid).first()
            if athlete:
                videos = db.query(Video).filter(Video.athlete_id == athlete.athlete_id).all()
                for v in videos:
                    analyses = db.query(AnalysisResult).filter(AnalysisResult.video_id == v.video_id).all()
                    for a in analyses:
                        db.query(AnalysisFeature).filter(AnalysisFeature.analysis_id == a.analysis_id).delete()
                        db.query(PoseLandmark).filter(PoseLandmark.analysis_id == a.analysis_id).delete()
                        db.delete(a)
                    db.delete(v)
                db.flush()
                db.delete(athlete)
                db.flush()
            db.delete(user)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Unit tests — Math & Feature Functions
# ---------------------------------------------------------------------------

class TestJointAngleMath:

    def test_calculate_3d_angle_right_angle(self):
        # 90 degree angle at p2=(0,0,0) with p1=(1,0,0) and p3=(0,1,0)
        p1 = (1.0, 0.0, 0.0)
        p2 = (0.0, 0.0, 0.0)
        p3 = (0.0, 1.0, 0.0)
        angle = calculate_3d_angle(p1, p2, p3)
        assert angle is not None
        assert abs(angle - 90.0) < 1e-4

    def test_calculate_3d_angle_straight_line(self):
        # 180 degree angle at p2=(0,0,0) with p1=(-1,0,0) and p3=(1,0,0)
        p1 = (-1.0, 0.0, 0.0)
        p2 = (0.0, 0.0, 0.0)
        p3 = (1.0, 0.0, 0.0)
        angle = calculate_3d_angle(p1, p2, p3)
        assert angle is not None
        assert abs(angle - 180.0) < 1e-4

    def test_calculate_3d_angle_collinear_degenerate(self):
        # Degenerate points (p1 == p2)
        p1 = (0.0, 0.0, 0.0)
        p2 = (0.0, 0.0, 0.0)
        p3 = (1.0, 0.0, 0.0)
        angle = calculate_3d_angle(p1, p2, p3)
        assert angle is None

    def test_trunk_angle_vertical(self):
        # Vertical trunk in image coordinates (y points down)
        l_sh = (-0.2, 0.0, 0.0)
        r_sh = (0.2, 0.0, 0.0)
        l_hip = (-0.2, 1.0, 0.0)
        r_hip = (0.2, 1.0, 0.0)
        angle = calculate_trunk_angle(l_sh, r_sh, l_hip, r_hip)
        assert angle is not None
        assert abs(angle - 0.0) < 1e-4

    def test_symmetry_score_equal(self):
        score = calculate_symmetry_score(45.0, 45.0)
        assert score == 100.0

    def test_symmetry_score_asymmetric(self):
        score = calculate_symmetry_score(50.0, 100.0)
        # 100 * (1 - 50/100) = 50.0%
        assert score == 50.0

    def test_symmetry_score_none_handling(self):
        assert calculate_symmetry_score(None, 45.0) is None
        assert calculate_symmetry_score(45.0, None) is None


# ---------------------------------------------------------------------------
# Unit tests — FeatureExtractor Landmark Processing & Visibility
# ---------------------------------------------------------------------------

class TestFeatureExtractorLandmarks:

    def test_low_visibility_landmarks_are_excluded(self):
        analysis_id = uuid.uuid4()
        # Create landmarks for 1 frame where knee has low visibility (< 0.5)
        landmarks = [
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=23, landmark_name="LEFT_HIP", x=0.5, y=0.5, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=25, landmark_name="LEFT_KNEE", x=0.5, y=0.7, z=0.0, visibility=0.2), # Low visibility!
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=27, landmark_name="LEFT_ANKLE", x=0.5, y=0.9, z=0.0, visibility=0.9),
        ]
        features = FeatureExtractor.extract_features_from_landmarks(landmarks, min_visibility=0.5)
        assert features["knee_angle_left_mean"] is None

    def test_valid_landmarks_compute_features(self):
        analysis_id = uuid.uuid4()
        # Frame 0: 90 degree left knee angle
        # Frame 1: 180 degree left knee angle
        landmarks = [
            # Frame 0
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=23, landmark_name="LEFT_HIP", x=0.0, y=0.0, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=25, landmark_name="LEFT_KNEE", x=0.0, y=1.0, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=0, timestamp_ms=0.0, landmark_index=27, landmark_name="LEFT_ANKLE", x=1.0, y=1.0, z=0.0, visibility=0.9),
            # Frame 1
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=23, landmark_name="LEFT_HIP", x=0.0, y=0.0, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=25, landmark_name="LEFT_KNEE", x=0.0, y=1.0, z=0.0, visibility=0.9),
            PoseLandmark(analysis_id=analysis_id, frame_number=1, timestamp_ms=100.0, landmark_index=27, landmark_name="LEFT_ANKLE", x=0.0, y=2.0, z=0.0, visibility=0.9),
        ]
        features = FeatureExtractor.extract_features_from_landmarks(landmarks)
        assert features["knee_angle_left_min"] == 90.0
        assert features["knee_angle_left_max"] == 180.0
        assert features["knee_angle_left_rom"] == 90.0
        assert features["knee_angle_left_mean"] == 135.0


# ---------------------------------------------------------------------------
# Integration tests — API Endpoint GET /videos/{video_id}/features
# ---------------------------------------------------------------------------

class TestGetAnalysisFeaturesEndpoint:

    def test_get_features_returns_200_and_feature_version_v1(self):
        user, athlete = _create_athlete_user(
            "Feature Test User",
            f"featuser_{uuid.uuid4().hex[:8]}@test.com",
        )
        db = SessionLocal()
        try:
            video = Video(
                athlete_id=athlete.athlete_id,
                video_url="/uploads/feat_test.mp4",
                original_filename="feat_test.mp4",
                content_type="video/mp4",
                file_size=2048,
                processing_status="uploaded",
            )
            db.add(video)
            db.commit()
            db.refresh(video)

            analysis = AnalysisResult(
                video_id=video.video_id,
                athlete_id=athlete.athlete_id,
                status=ANALYSIS_STATUS_COMPLETED,
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)

            feature_rec = AnalysisFeature(
                feature_id=uuid.uuid4(),
                analysis_id=analysis.analysis_id,
                feature_version=FEATURE_VERSION,
                features={"knee_angle_left_mean": 135.0, "knee_angle_left_rom": 90.0},
            )
            db.add(feature_rec)
            db.commit()
        finally:
            db.close()

        resp = client.get(
            f"/api/v1/videos/{video.video_id}/features",
            headers=_auth(user.user_id),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["feature_version"] == FEATURE_VERSION
        assert data["analysis_id"] == str(analysis.analysis_id)
        assert data["features"]["knee_angle_left_mean"] == 135.0
        assert data["features"]["knee_angle_left_rom"] == 90.0

    def test_get_features_no_auth_returns_401(self):
        resp = client.get(f"/api/v1/videos/{uuid.uuid4()}/features")
        assert resp.status_code == 401

    def test_get_features_wrong_user_returns_403(self):
        user1, athlete1 = _create_athlete_user(
            "Owner User",
            f"feat_owner_{uuid.uuid4().hex[:8]}@test.com",
        )
        user2, _ = _create_athlete_user(
            "Intruder User",
            f"feat_intruder_{uuid.uuid4().hex[:8]}@test.com",
        )
        db = SessionLocal()
        try:
            video = Video(
                athlete_id=athlete1.athlete_id,
                video_url="/uploads/feat_test2.mp4",
                original_filename="feat_test2.mp4",
                content_type="video/mp4",
                file_size=2048,
                processing_status="uploaded",
            )
            db.add(video)
            db.commit()
            db.refresh(video)
        finally:
            db.close()

        resp = client.get(
            f"/api/v1/videos/{video.video_id}/features",
            headers=_auth(user2.user_id),
        )
        assert resp.status_code == 403

    def test_get_features_not_found_returns_404(self):
        user, athlete = _create_athlete_user(
            "404 Feature User",
            f"feat404_{uuid.uuid4().hex[:8]}@test.com",
        )
        db = SessionLocal()
        try:
            video = Video(
                athlete_id=athlete.athlete_id,
                video_url="/uploads/no_feat.mp4",
                original_filename="no_feat.mp4",
                content_type="video/mp4",
                file_size=2048,
                processing_status="uploaded",
            )
            db.add(video)
            db.commit()
            db.refresh(video)
        finally:
            db.close()

        resp = client.get(
            f"/api/v1/videos/{video.video_id}/features",
            headers=_auth(user.user_id),
        )
        assert resp.status_code == 404
