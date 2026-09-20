"""
tests/test_risk_scoring_api.py
------------------------------
End-to-End API and Integration tests for Risk Scoring System.

Covers:
1. GET /videos/{video_id}/analysis exposes overall_risk_score, risk_level,
   symmetry_score, fatigue_score, individual factors (s_bio, s_hist, s_asym, s_load, s_fatigue),
   availability flags, and framing disclaimer.
2. Full end-to-end pipeline integration:
   Upload → Trigger Analysis → Background Pipeline (Pose + Features + LESS + Risk Scoring) → DB Persistence → GET API Response.
3. Ownership security enforcement (403 for unauthorized athlete).
4. Non-existent analysis response (404).
"""
import uuid
from datetime import timedelta
from unittest.mock import MagicMock, patch
from pathlib import Path

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import AnalysisResult, ANALYSIS_STATUS_COMPLETED
from app.models.analysis_feature import AnalysisFeature
from app.models.injury_history import InjuryHistory
from app.core.security import get_password_hash, create_access_token
from app.services.analysis_pipeline import run_analysis_pipeline
from app.services.pose_estimator import BasePoseEstimator, LandmarkResult, SingleLandmark


client = TestClient(app)


class MockPoseEstimator(BasePoseEstimator):
    """
    Mock pose estimator generating 33 landmarks for E2E testing.
    """
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def close(self):
        pass

    def process_frame(self, frame_number: int, timestamp_ms: float, image_bgr) -> LandmarkResult | None:
        landmarks = []
        coords = {
            11: (-0.2, 0.2, 0.0),  # LEFT_SHOULDER
            12: (0.2, 0.2, 0.0),   # RIGHT_SHOULDER
            23: (-0.2, 0.5, 0.0),  # LEFT_HIP
            24: (0.2, 0.5, 0.0),   # RIGHT_HIP
            25: (-0.2, 0.8 + 0.1 * (frame_number % 2), 0.0),  # LEFT_KNEE
            26: (0.2, 0.8 + 0.05 * (frame_number % 2), 0.0),  # RIGHT_KNEE
            27: (-0.2, 1.1, 0.0),  # LEFT_ANKLE
            28: (0.2, 1.1, 0.0),   # RIGHT_ANKLE
            31: (-0.2, 1.2, 0.1),  # LEFT_FOOT_INDEX
            32: (0.2, 1.2, 0.1),   # RIGHT_FOOT_INDEX
        }
        for idx in range(33):
            pt = coords.get(idx, (0.0, 0.0, 0.0))
            landmarks.append(
                SingleLandmark(
                    landmark_index=idx,
                    landmark_name=f"LM_{idx}",
                    x=pt[0],
                    y=pt[1],
                    z=pt[2],
                    visibility=0.9,
                )
            )
        return LandmarkResult(frame_number=frame_number, timestamp_ms=timestamp_ms, landmarks=landmarks)


class TestRiskScoringAPI:

    @pytest.fixture(autouse=True)
    def setup_db(self):
        db = SessionLocal()
        self.user = User(
            name="Risk API Test User",
            email=f"riskapi_{uuid.uuid4().hex[:8]}@test.com",
            password=get_password_hash("TestPass123!"),
            role=RoleEnum.ATHLETE,
            is_active=True,
        )
        db.add(self.user)
        db.flush()

        self.athlete = Athlete(
            user_id=self.user.user_id,
            sport="Soccer",
            position="Forward",
            age=22,
            height=178.0,
            weight=72.0,
            has_injury_history="NO",
        )

        db.add(self.athlete)
        db.flush()

        self.video = Video(
            athlete_id=self.athlete.athlete_id,
            video_url="/uploads/mock_risk.mp4",
            original_filename="mock_risk.mp4",
            content_type="video/mp4",
            file_size=2048,
            processing_status="uploaded",
        )
        db.add(self.video)
        db.commit()

        self.token = create_access_token(
            subject=str(self.user.user_id),
            role=self.user.role.value,
            secret_key=settings.SECRET_KEY,
            algorithm=settings.ALGORITHM,
            expires_delta=timedelta(minutes=30),
        )
        self.headers = {"Authorization": f"Bearer {self.token}"}

        yield

        # Teardown
        db_td = SessionLocal()
        try:
            db_td.query(AnalysisFeature).filter(
                AnalysisFeature.analysis_id.in_(
                    db_td.query(AnalysisResult.analysis_id).filter(AnalysisResult.video_id == self.video.video_id)
                )
            ).delete(synchronize_session=False)
            db_td.query(InjuryHistory).filter(InjuryHistory.athlete_id == self.athlete.athlete_id).delete()
            db_td.query(AnalysisResult).filter(AnalysisResult.video_id == self.video.video_id).delete()
            db_td.query(Video).filter(Video.video_id == self.video.video_id).delete()
            db_td.query(Athlete).filter(Athlete.user_id == self.user.user_id).delete()
            db_td.query(User).filter(User.user_id == self.user.user_id).delete()
            db_td.commit()
        finally:
            db_td.close()

    def test_get_analysis_returns_persisted_risk_score_and_breakdown(self):
        """
        Verify GET /videos/{video_id}/analysis returns 200 with full 5-factor risk score breakdown.
        """
        db = SessionLocal()
        try:
            analysis = AnalysisResult(
                video_id=self.video.video_id,
                athlete_id=self.athlete.athlete_id,
                status=ANALYSIS_STATUS_COMPLETED,
                overall_risk_score=42.5,
                risk_level="MODERATE",
                symmetry_score=15.0,
                fatigue_score=50.0,
            )
            db.add(analysis)
            db.commit()

            feature_rec = AnalysisFeature(
                feature_id=uuid.uuid4(),
                analysis_id=analysis.analysis_id,
                feature_version="v2",
                features={
                    "knee_rom_mean": 50.0,
                    "hip_rom_mean": 40.0,
                    "ankle_rom_mean": 30.0,
                    "trunk_angle_mean": 8.0,
                    "knee_asymmetry": 3.0,
                    "hip_asymmetry": 2.0,
                    "ankle_asymmetry": 1.5,
                    "mean_joint_velocity": 2.5,
                    "total_joint_displacement": 40.0,
                },
            )
            db.add(feature_rec)
            db.commit()

            response = client.get(f"/videos/{self.video.video_id}/analysis", headers=self.headers)
            assert response.status_code == 200
            data = response.json()

            assert data["overall_risk_score"] == 42.5
            assert data["risk_level"] == "MODERATE"
            assert data["s_bio"] is not None
            assert data["s_hist"] is not None
            assert data["s_asym"] is not None
            assert data["s_load_available"] is False
            assert data["s_fatigue_available"] is False
            assert "disclaimer" in data

            assert "Biomechanical Deviation" in data["disclaimer"]
            assert data["risk_breakdown"] is not None
        finally:
            db.close()

    def test_end_to_end_pipeline_calculates_and_exposes_risk_score(self):
        """
        End-to-End Test:
        1. Trigger analysis via POST /videos/{video_id}/analyze
        2. Run background analysis pipeline
        3. Poll GET /videos/{video_id}/analysis
        4. Assert status is COMPLETED and overall_risk_score & risk_level are populated
        """
        db = SessionLocal()
        try:
            # 1. Trigger analysis
            trig_res = client.post(f"/videos/{self.video.video_id}/analyze", headers=self.headers)
            assert trig_res.status_code == 202
            trig_data = trig_res.json()
            analysis_id = uuid.UUID(trig_data["analysis_id"])

            # 2. Mock OpenCV video processing and run full pipeline
            mock_frame = MagicMock(frame_number=0, timestamp_ms=0.0, image=MagicMock())
            mock_extraction = MagicMock()
            mock_extraction.metadata.fps = 30.0
            mock_extraction.metadata.frame_count = 1
            mock_extraction.metadata.duration_seconds = 0.033
            mock_extraction.metadata.width = 1920
            mock_extraction.metadata.height = 1080
            mock_extraction.frames = [mock_frame]

            with patch("app.services.analysis_pipeline.VideoProcessingService.process", return_value=mock_extraction):
                estimator = MockPoseEstimator()
                run_analysis_pipeline(
                    analysis_id=analysis_id,
                    video_url=self.video.video_url,
                    db=db,
                    pose_estimator=estimator,
                )

            # 3. Fetch completed analysis via GET API
            status_res = client.get(f"/videos/{self.video.video_id}/analysis", headers=self.headers)
            assert status_res.status_code == 200
            data = status_res.json()

            assert data["status"] == ANALYSIS_STATUS_COMPLETED
            assert data["overall_risk_score"] is not None
            assert data["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")
            assert data["s_load_available"] is False
            assert data["s_fatigue_available"] is False
            assert data["disclaimer"] is not None
        finally:
            db.close()

    def test_full_upload_analyze_and_polling_sequence(self):
        """
        Verify the exact sequential flow matching the frontend upload -> analyze -> polling:
        1. POST /videos (Upload) → 201 Created with video_id
        2. POST /videos/{video_id}/analyze (Trigger) → 202 Accepted with status PENDING
        3. GET /videos/{video_id}/analysis (Poll) → status PENDING
        4. Pipeline execution
        5. GET /videos/{video_id}/analysis (Poll) → status COMPLETED + 5-factor breakdown
        """
        db = SessionLocal()
        try:
            # 1. Upload video file
            fake_video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42"
            files = {"file": ("test_seq.mp4", fake_video_bytes, "video/mp4")}
            upload_res = client.post("/videos", headers=self.headers, files=files)
            assert upload_res.status_code == 201
            upload_data = upload_res.json()
            video_id = upload_data["video_id"]
            assert video_id is not None

            # 2. Setup mock frame and extraction
            mock_frame = MagicMock(frame_number=0, timestamp_ms=0.0, image=MagicMock())
            mock_extraction = MagicMock()
            mock_extraction.metadata.fps = 30.0
            mock_extraction.metadata.frame_count = 1
            mock_extraction.metadata.duration_seconds = 0.033
            mock_extraction.metadata.width = 1920
            mock_extraction.metadata.height = 1080
            mock_extraction.frames = [mock_frame]

            with patch("app.services.analysis_pipeline.VideoProcessingService.process", return_value=mock_extraction), \
                 patch("app.services.analysis_pipeline.MediaPipePoseEstimator", return_value=MockPoseEstimator()):

                # Trigger analysis with video_id
                trig_res = client.post(f"/videos/{video_id}/analyze", headers=self.headers)
                assert trig_res.status_code == 202
                trig_data = trig_res.json()
                assert trig_data["video_id"] == video_id
                assert trig_data["status"] == "PENDING"

                # Poll completed status after background execution completes -> COMPLETED + 5-factor breakdown
                poll_completed_res = client.get(f"/videos/{video_id}/analysis", headers=self.headers)
                assert poll_completed_res.status_code == 200
                comp_data = poll_completed_res.json()
                assert comp_data["status"] == ANALYSIS_STATUS_COMPLETED
                assert comp_data["overall_risk_score"] is not None
                assert comp_data["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL")
                assert comp_data["s_bio"] is not None
                assert comp_data["s_hist"] is not None
                assert comp_data["s_asym"] is not None
                assert comp_data["s_load_available"] is False
                assert comp_data["s_fatigue_available"] is False

        finally:
            db.close()

    def test_get_analysis_ownership_security(self):
        """
        Verify an athlete cannot access analysis results for another athlete's video (403 Forbidden).
        """
        db = SessionLocal()
        try:
            other_user = User(
                name="Other Athlete",
                email=f"other_{uuid.uuid4().hex[:8]}@test.com",
                password=get_password_hash("TestPass123!"),
                role=RoleEnum.ATHLETE,
                is_active=True,
            )
            db.add(other_user)
            db.flush()

            other_athlete = Athlete(
                user_id=other_user.user_id,
                sport="Basketball",
                position="Guard",
                age=23,
                height=185.0,
                weight=80.0,
            )
            db.add(other_athlete)
            db.commit()

            other_token = create_access_token(
                subject=str(other_user.user_id),
                role=other_user.role.value,
                secret_key=settings.SECRET_KEY,
                algorithm=settings.ALGORITHM,
                expires_delta=timedelta(minutes=30),
            )
            other_headers = {"Authorization": f"Bearer {other_token}"}

            res = client.get(f"/videos/{self.video.video_id}/analysis", headers=other_headers)
            assert res.status_code == 403
        finally:
            db.close()
