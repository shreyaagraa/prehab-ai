"""
tests/test_landmarks_api.py
---------------------------
Integration tests for GET /videos/{video_id}/landmarks endpoint.

Validates:
1. Exact analysis_id scoping
2. Returning time-indexed frames with 33 landmarks
3. Ownership and RBAC security
4. has_pose_data flags
5. Empty / missing landmarks handling
"""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import (
    AnalysisResult,
    ANALYSIS_STATUS_COMPLETED,
)
from app.models.pose_landmark import PoseLandmark
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)
_TEST_PASSWORD = "LandmarkTest@123!"


def _create_user_and_athlete(name: str, email: str, role: RoleEnum = RoleEnum.ATHLETE) -> tuple[User, Athlete | None]:
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

        athlete = None
        if role == RoleEnum.ATHLETE:
            athlete = Athlete(
                athlete_id=uuid.uuid4(),
                user_id=user.user_id,
                sport="Basketball",
                position="Guard",
                age=22,
                height=188.0,
                weight=82.0,
            )
            db.add(athlete)
            db.commit()
            db.refresh(athlete)

        return user, athlete
    finally:
        db.close()


from datetime import datetime, timedelta, timezone
from app.config import settings

def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(
        subject=str(user.user_id),
        role=user.role.value,
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_delta=timedelta(minutes=30),
        additional_claims={"email": user.email},
    )
    return {"Authorization": f"Bearer {token}"}



class TestLandmarksAPI:
    def test_get_landmarks_with_exact_analysis_id(self):
        user, athlete = _create_user_and_athlete("Pose User 1", f"pose1_{uuid.uuid4().hex[:8]}@test.com")
        headers = _auth_header(user)

        db = SessionLocal()
        try:
            video = Video(
                video_id=uuid.uuid4(),
                athlete_id=athlete.athlete_id,
                original_filename="jump.mp4",
                video_url="/uploads/jump.mp4",
                processing_status="uploaded",
            )
            db.add(video)
            db.commit()

            # Create Analysis 1 (Old)
            analysis1 = AnalysisResult(
                analysis_id=uuid.uuid4(),
                video_id=video.video_id,
                athlete_id=athlete.athlete_id,
                status=ANALYSIS_STATUS_COMPLETED,
                fps=30.0,
                width=1920,
                height=1080,
                frames_processed=1,
            )
            db.add(analysis1)
            db.commit()

            # Landmarks for Analysis 1 (1 frame, 2 joints for testing)
            lm1 = PoseLandmark(
                landmark_id=uuid.uuid4(),
                analysis_id=analysis1.analysis_id,
                frame_number=0,
                timestamp_ms=0.0,
                landmark_index=0,
                landmark_name="NOSE",
                x=0.5,
                y=0.2,
                z=-0.1,
                visibility=0.99,
            )
            db.add(lm1)
            db.commit()

            # Create Analysis 2 (Newer assessment of same video)
            analysis2 = AnalysisResult(
                analysis_id=uuid.uuid4(),
                video_id=video.video_id,
                athlete_id=athlete.athlete_id,
                status=ANALYSIS_STATUS_COMPLETED,
                fps=60.0,
                width=1280,
                height=720,
                frames_processed=2,
            )
            db.add(analysis2)
            db.commit()

            # Landmarks for Analysis 2 (2 frames)
            lm2_f0 = PoseLandmark(
                landmark_id=uuid.uuid4(),
                analysis_id=analysis2.analysis_id,
                frame_number=0,
                timestamp_ms=0.0,
                landmark_index=11,
                landmark_name="LEFT_SHOULDER",
                x=0.45,
                y=0.35,
                z=0.0,
                visibility=0.95,
            )
            lm2_f1 = PoseLandmark(
                landmark_id=uuid.uuid4(),
                analysis_id=analysis2.analysis_id,
                frame_number=5,
                timestamp_ms=83.33,
                landmark_index=11,
                landmark_name="LEFT_SHOULDER",
                x=0.46,
                y=0.36,
                z=0.01,
                visibility=0.96,
            )
            db.add_all([lm2_f0, lm2_f1])
            db.commit()

            # Query without analysis_id -> defaults to latest (Analysis 2)
            resp = client.get(f"/api/v1/videos/{video.video_id}/landmarks", headers=headers)
            assert resp.status_code == 200, resp.text
            data = resp.json()
            assert data["analysis_id"] == str(analysis2.analysis_id)
            assert data["fps"] == 60.0
            assert data["total_frames"] == 2
            assert data["has_pose_data"] is True
            assert len(data["frames"]) == 2
            assert data["frames"][0]["frame_number"] == 0
            assert data["frames"][1]["frame_number"] == 5

            # Query specifically with exact analysis_id=analysis1.analysis_id
            resp1 = client.get(
                f"/api/v1/videos/{video.video_id}/landmarks?analysis_id={analysis1.analysis_id}",
                headers=headers,
            )
            assert resp1.status_code == 200, resp1.text
            data1 = resp1.json()
            assert data1["analysis_id"] == str(analysis1.analysis_id)
            assert data1["fps"] == 30.0
            assert data1["total_frames"] == 1
            assert data1["frames"][0]["landmarks"][0]["landmark_name"] == "NOSE"

        finally:
            db.close()

    def test_get_landmarks_ownership_security(self):
        user_a, athlete_a = _create_user_and_athlete("Athlete A", f"a_{uuid.uuid4().hex[:8]}@test.com")
        user_b, athlete_b = _create_user_and_athlete("Athlete B", f"b_{uuid.uuid4().hex[:8]}@test.com")
        coach_user, _ = _create_user_and_athlete("Coach", f"coach_{uuid.uuid4().hex[:8]}@test.com", role=RoleEnum.COACH)

        db = SessionLocal()
        try:
            video_a = Video(
                video_id=uuid.uuid4(),
                athlete_id=athlete_a.athlete_id,
                original_filename="a.mp4",
                video_url="/uploads/a.mp4",
                processing_status="uploaded",
            )
            db.add(video_a)
            db.commit()

            analysis_a = AnalysisResult(
                analysis_id=uuid.uuid4(),
                video_id=video_a.video_id,
                athlete_id=athlete_a.athlete_id,
                status=ANALYSIS_STATUS_COMPLETED,
            )
            db.add(analysis_a)
            db.commit()

            # Athlete B tries to access Athlete A's landmarks -> 403
            headers_b = _auth_header(user_b)
            resp = client.get(f"/api/v1/videos/{video_a.video_id}/landmarks", headers=headers_b)
            assert resp.status_code == 403

            # Coach tries to access Athlete A's landmarks -> 200
            headers_coach = _auth_header(coach_user)
            resp_coach = client.get(f"/api/v1/videos/{video_a.video_id}/landmarks", headers=headers_coach)
            assert resp_coach.status_code == 200
            assert resp_coach.json()["has_pose_data"] is False  # No landmarks added yet

        finally:
            db.close()

    def test_nonexistent_analysis_or_video_returns_404(self):
        user, athlete = _create_user_and_athlete("Test 404 User", f"u404_{uuid.uuid4().hex[:8]}@test.com")
        headers = _auth_header(user)

        random_vid = uuid.uuid4()
        resp = client.get(f"/api/v1/videos/{random_vid}/landmarks", headers=headers)
        assert resp.status_code == 404

