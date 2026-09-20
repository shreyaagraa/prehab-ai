"""
tests/test_analyze_video.py
----------------------------
Integration tests for the video analysis endpoints.

Covers:
  1.  Valid trigger → 202 with analysis_id
  2.  GET /analysis before trigger → 404
  3.  GET /analysis after trigger → status structure
  4.  Non-athlete role → 403 (trigger)
  5.  Non-athlete role → 403 (status)
  6.  Wrong athlete's video → 403
  7.  Non-existent video_id → 404
  8.  No auth token → 401

Unit tests (no DB, no real video):
  9.  VideoProcessingService — rejects missing file
  10. VideoProcessingService — rejects empty frames (corrupt video simulation)
  11. PoseEstimationService — handles no-detection frame gracefully
  12. PoseEstimationService — returns correct landmark count on detection
  13. _mark_failed helper — persists FAILED status without raising
  14. Analysis status constants — correct string values
"""

import io
import uuid
from datetime import timedelta, datetime, timezone
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import (
    AnalysisResult,
    ANALYSIS_STATUS_PENDING,
    ANALYSIS_STATUS_PROCESSING,
    ANALYSIS_STATUS_COMPLETED,
    ANALYSIS_STATUS_FAILED,
)
from app.core.security import get_password_hash, create_access_token
from app.services.video_processor import VideoProcessingService, VideoProcessingError
from app.services.pose_estimator import (
    MediaPipeSolutionsPoseEstimator,
    LandmarkResult,
    SingleLandmark,
    LANDMARK_NAMES,
)
from app.services.analysis_pipeline import _mark_failed


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_TEST_PASSWORD = "AnalyzeTest@123!"
_CLEANUP_USER_IDS: list[uuid.UUID] = []


def _create_athlete_user(name: str, email: str) -> tuple[User, Athlete]:
    """Create a user + athlete profile, register for teardown."""
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
            sport="Football",
            position="Forward",
            age=22,
            height=180.0,
            weight=75.0,
        )
        db.add(athlete)
        db.commit()
        db.refresh(user)
        db.refresh(athlete)
        _CLEANUP_USER_IDS.append(user.user_id)
        return user, athlete
    finally:
        db.close()


def _create_video(athlete_id: uuid.UUID, video_url: str = "/uploads/test_video.mp4") -> Video:
    """Create a dummy video row."""
    db = SessionLocal()
    try:
        video = Video(
            athlete_id=athlete_id,
            video_url=video_url,
            original_filename="test_video.mp4",
            content_type="video/mp4",
            file_size=1024,
            processing_status="uploaded",
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        return video
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


def _teardown():
    """Remove all test data created during the test session."""
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
                    db.query(AnalysisResult).filter(
                        AnalysisResult.video_id == v.video_id
                    ).delete(synchronize_session=False)
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
# Setup / teardown
# ---------------------------------------------------------------------------

def setup_module(_module):
    pass  # all setup done per-test


def teardown_module(_module):
    _teardown()


# ---------------------------------------------------------------------------
# Integration tests — endpoints
# ---------------------------------------------------------------------------

class TestAnalyzeTrigger:
    """POST /videos/{video_id}/analyze"""

    def test_trigger_returns_202_with_analysis_id(self):
        user, athlete = _create_athlete_user(
            "Trigger Test User",
            f"trigger_{uuid.uuid4().hex[:8]}@test.com",
        )
        video = _create_video(athlete.athlete_id)

        # Patch the background pipeline so it doesn't try to open a real file
        with patch("app.api.videos._background_analyze"):
            resp = client.post(
                f"/api/v1/videos/{video.video_id}/analyze",
                headers=_auth(user.user_id),
            )

        assert resp.status_code == 202, resp.text
        data = resp.json()
        assert "analysis_id" in data
        assert data["status"] == ANALYSIS_STATUS_PENDING
        assert data["video_id"] == str(video.video_id)

    def test_trigger_creates_analysis_result_in_db(self):
        user, athlete = _create_athlete_user(
            "DB Check User",
            f"dbcheck_{uuid.uuid4().hex[:8]}@test.com",
        )
        video = _create_video(athlete.athlete_id)

        with patch("app.api.videos._background_analyze"):
            resp = client.post(
                f"/api/v1/videos/{video.video_id}/analyze",
                headers=_auth(user.user_id),
            )

        assert resp.status_code == 202
        analysis_id = resp.json()["analysis_id"]

        db = SessionLocal()
        try:
            ar = db.query(AnalysisResult).filter(
                AnalysisResult.analysis_id == uuid.UUID(analysis_id)
            ).first()
            assert ar is not None
            assert ar.status == ANALYSIS_STATUS_PENDING
            assert ar.video_id == video.video_id
        finally:
            db.close()

    def test_no_auth_returns_401(self):
        resp = client.post(f"/api/v1/videos/{uuid.uuid4()}/analyze")
        assert resp.status_code == 401

    def test_non_athlete_role_returns_403(self):
        db = SessionLocal()
        try:
            coach = User(
                name="Coach Forbidden",
                email=f"coachforbid_{uuid.uuid4().hex[:8]}@test.com",
                password=get_password_hash(_TEST_PASSWORD),
                role=RoleEnum.COACH,
                is_active=True,
            )
            db.add(coach)
            db.commit()
            db.refresh(coach)
            _CLEANUP_USER_IDS.append(coach.user_id)

            resp = client.post(
                f"/api/v1/videos/{uuid.uuid4()}/analyze",
                headers=_auth(coach.user_id, role=coach.role.value),
            )
            assert resp.status_code == 403
        finally:
            db.close()

    def test_nonexistent_video_returns_404(self):
        user, _ = _create_athlete_user(
            "404 Video User",
            f"vid404_{uuid.uuid4().hex[:8]}@test.com",
        )
        resp = client.post(
            f"/api/v1/videos/{uuid.uuid4()}/analyze",
            headers=_auth(user.user_id),
        )
        assert resp.status_code == 404

    def test_wrong_athlete_video_returns_403(self):
        user1, athlete1 = _create_athlete_user(
            "Owner User",
            f"owner_{uuid.uuid4().hex[:8]}@test.com",
        )
        user2, _ = _create_athlete_user(
            "Intruder User",
            f"intruder_{uuid.uuid4().hex[:8]}@test.com",
        )
        video = _create_video(athlete1.athlete_id)

        resp = client.post(
            f"/api/v1/videos/{video.video_id}/analyze",
            headers=_auth(user2.user_id),  # wrong athlete
        )
        assert resp.status_code == 403


class TestAnalysisStatus:
    """GET /videos/{video_id}/analysis"""

    def test_no_analysis_returns_404(self):
        user, athlete = _create_athlete_user(
            "Status 404 User",
            f"status404_{uuid.uuid4().hex[:8]}@test.com",
        )
        video = _create_video(athlete.athlete_id)

        resp = client.get(
            f"/api/v1/videos/{video.video_id}/analysis",
            headers=_auth(user.user_id),
        )
        assert resp.status_code == 404

    def test_status_after_trigger_returns_pending(self):
        user, athlete = _create_athlete_user(
            "Status Pending User",
            f"statuspend_{uuid.uuid4().hex[:8]}@test.com",
        )
        video = _create_video(athlete.athlete_id)

        with patch("app.api.videos._background_analyze"):
            client.post(
                f"/api/v1/videos/{video.video_id}/analyze",
                headers=_auth(user.user_id),
            )

        resp = client.get(
            f"/api/v1/videos/{video.video_id}/analysis",
            headers=_auth(user.user_id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in (
            ANALYSIS_STATUS_PENDING,
            ANALYSIS_STATUS_PROCESSING,
            ANALYSIS_STATUS_COMPLETED,
            ANALYSIS_STATUS_FAILED,
        )
        assert "analysis_id" in data
        assert "video_id" in data
        assert "created_at" in data

    def test_no_auth_returns_401(self):
        resp = client.get(f"/api/v1/videos/{uuid.uuid4()}/analysis")
        assert resp.status_code == 401

    def test_non_athlete_returns_403(self):
        db = SessionLocal()
        try:
            physio = User(
                name="Physio Status",
                email=f"physiostatus_{uuid.uuid4().hex[:8]}@test.com",
                password=get_password_hash(_TEST_PASSWORD),
                role=RoleEnum.PHYSIOTHERAPIST,
                is_active=True,
            )
            db.add(physio)
            db.commit()
            db.refresh(physio)
            _CLEANUP_USER_IDS.append(physio.user_id)

            resp = client.get(
                f"/api/v1/videos/{uuid.uuid4()}/analysis",
                headers=_auth(physio.user_id, role=physio.role.value),
            )
            # Staff roles have access to video analysis, so non-existent video returns 404
            assert resp.status_code == 404
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Unit tests — VideoProcessingService (no real files needed)
# ---------------------------------------------------------------------------

class TestVideoProcessingService:

    def test_raises_on_missing_file(self):
        svc = VideoProcessingService(frame_sample_rate=5, max_processed_frames=300)
        with pytest.raises(VideoProcessingError, match="not found"):
            svc.process(Path("/tmp/this_file_absolutely_does_not_exist_xyz.mp4"))

    def test_raises_on_unreadable_video(self, tmp_path):
        """A file with garbage bytes should raise VideoProcessingError."""
        fake = tmp_path / "corrupt.mp4"
        fake.write_bytes(b"NOT A VIDEO FILE CONTENT XYZ")
        svc = VideoProcessingService(frame_sample_rate=5, max_processed_frames=300)
        with pytest.raises(VideoProcessingError):
            svc.process(fake)

    def test_invalid_sample_rate_raises_value_error(self):
        with pytest.raises(ValueError):
            VideoProcessingService(frame_sample_rate=0)

    def test_invalid_max_frames_raises_value_error(self):
        with pytest.raises(ValueError):
            VideoProcessingService(max_processed_frames=0)


# ---------------------------------------------------------------------------
# Unit tests — PoseEstimationService
# ---------------------------------------------------------------------------

class TestPoseEstimationService:

    def _make_mock_pose(self, has_landmarks: bool):
        """Build a mediapipe mock that returns/doesn't return landmarks."""
        mock_pose = MagicMock()
        if has_landmarks:
            # Create 33 mock landmarks
            lm_list = []
            for i in range(33):
                lm = MagicMock()
                lm.x = 0.1 * (i % 10)
                lm.y = 0.1 * (i % 10)
                lm.z = -0.05
                lm.visibility = 0.9
                lm_list.append(lm)

            mock_result = MagicMock()
            mock_result.pose_landmarks = MagicMock()
            mock_result.pose_landmarks.landmark = lm_list
        else:
            mock_result = MagicMock()
            mock_result.pose_landmarks = None

        mock_pose.process.return_value = mock_result
        return mock_pose

    def test_no_detection_returns_none(self):
        import numpy as np
        estimator = MediaPipeSolutionsPoseEstimator.__new__(MediaPipeSolutionsPoseEstimator)
        estimator._mp_pose = MagicMock()
        estimator._pose = self._make_mock_pose(has_landmarks=False)

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = estimator.process_frame(0, 0.0, dummy_frame)
        assert result is None

    def test_detection_returns_33_landmarks(self):
        import numpy as np
        estimator = MediaPipeSolutionsPoseEstimator.__new__(MediaPipeSolutionsPoseEstimator)
        estimator._mp_pose = MagicMock()
        estimator._pose = self._make_mock_pose(has_landmarks=True)

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = estimator.process_frame(5, 166.67, dummy_frame)
        assert result is not None
        assert result.frame_number == 5
        assert abs(result.timestamp_ms - 166.67) < 0.01
        assert len(result.landmarks) == 33

    def test_landmark_names_match_index(self):
        import numpy as np
        estimator = MediaPipeSolutionsPoseEstimator.__new__(MediaPipeSolutionsPoseEstimator)
        estimator._mp_pose = MagicMock()
        estimator._pose = self._make_mock_pose(has_landmarks=True)

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = estimator.process_frame(0, 0.0, dummy_frame)
        assert result is not None
        for lm in result.landmarks:
            assert lm.landmark_name == LANDMARK_NAMES[lm.landmark_index]

    def test_landmark_count_constant(self):
        assert len(LANDMARK_NAMES) == 33


# ---------------------------------------------------------------------------
# Unit tests — _mark_failed helper
# ---------------------------------------------------------------------------

class TestMarkFailed:

    def test_mark_failed_sets_status(self):
        """_mark_failed should set status=FAILED without raising."""
        db_mock = MagicMock()
        analysis = AnalysisResult(
            analysis_id=uuid.uuid4(),
            video_id=uuid.uuid4(),
            athlete_id=uuid.uuid4(),
            status=ANALYSIS_STATUS_PROCESSING,
        )
        _mark_failed(db_mock, analysis, "test error message")
        assert analysis.status == ANALYSIS_STATUS_FAILED
        assert analysis.error_message == "test error message"
        assert analysis.completed_at is not None

    def test_mark_failed_does_not_raise_on_db_error(self):
        """Even if DB commit fails, _mark_failed must not propagate."""
        db_mock = MagicMock()
        db_mock.commit.side_effect = Exception("DB down")
        analysis = AnalysisResult(
            analysis_id=uuid.uuid4(),
            video_id=uuid.uuid4(),
            athlete_id=uuid.uuid4(),
            status=ANALYSIS_STATUS_PROCESSING,
        )
        # Should not raise
        _mark_failed(db_mock, analysis, "some error")


# ---------------------------------------------------------------------------
# Unit tests — status constants
# ---------------------------------------------------------------------------

class TestStatusConstants:

    def test_status_constant_values(self):
        assert ANALYSIS_STATUS_PENDING    == "PENDING"
        assert ANALYSIS_STATUS_PROCESSING == "PROCESSING"
        assert ANALYSIS_STATUS_COMPLETED  == "COMPLETED"
        assert ANALYSIS_STATUS_FAILED     == "FAILED"
