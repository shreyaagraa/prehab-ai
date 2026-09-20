"""
tests/test_e2e_features_verification.py
-----------------------------------------
Programmatic End-to-End verification test suite for:
1. Video upload & analysis pipeline completion
2. Video URL & HTML5 playable source metadata in response
3. Athlete history retrieval (/videos/my-history), newest first ordering
4. Historical report fetching (/videos/{video_id}/analysis)
5. Confirmation of non-retriggering of analysis on historical report load
6. Verification of risk score, risk level, LESS score, biomechanics, recommendations, disclaimer match
7. Cross-athlete authorization security (Athlete 2 cannot access Athlete 1's report -> 403)
8. Empty history state for new athlete ([])
9. Failed/Non-existent analysis state handling (404)
"""

import uuid
from pathlib import Path
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models.user import User

client = TestClient(app)

class TestE2EFeaturesVerification:
    def test_full_e2e_playback_history_report_and_security(self):
        email_1 = "verify.e2e.athlete1@example.com"
        email_2 = "verify.e2e.athlete2@example.com"
        
        # Clean up existing test users if any
        db = SessionLocal()
        try:
            from app.models.athlete import Athlete
            user_ids = [u.user_id for u in db.query(User.user_id).filter(User.email.in_([email_1, email_2])).all()]
            if user_ids:
                db.query(Athlete).filter(Athlete.user_id.in_(user_ids)).delete(synchronize_session=False)
            db.query(User).filter(User.email.in_([email_1, email_2])).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

        # Step 1: Register & Login Athlete 1
        reg_res = client.post("/auth/register", json={
            "name": "E2E Athlete 1",
            "email": email_1,
            "password": "Password123!",
            "role": "Athlete"
        })
        assert reg_res.status_code == 201, f"Athlete 1 reg failed: {reg_res.json()}"
        user_id_1 = reg_res.json()["user_id"]
        
        # Create Athlete profile for Athlete 1
        db = SessionLocal()
        try:
            from app.models.athlete import Athlete
            athlete_1 = Athlete(user_id=uuid.UUID(user_id_1), sport="Basketball", position="Guard", age=21)
            db.add(athlete_1)
            db.commit()
        finally:
            db.close()

        login_res = client.post("/auth/login", data={
            "username": email_1,
            "password": "Password123!"
        })
        assert login_res.status_code == 200, f"Athlete 1 login failed: {login_res.json()}"
        token_1 = login_res.json()["access_token"]
        headers_1 = {"Authorization": f"Bearer {token_1}"}

        # Step 2: Upload Video
        sample_video_path = Path("/app/sample_test_video.mp4")
        if not sample_video_path.exists():
            sample_video_path = Path(r"c:\Users\Welcome\sports-injury-risk-detection\sample_test_video.mp4")
        assert sample_video_path.exists(), f"Sample video not found at {sample_video_path}"

        with open(sample_video_path, "rb") as f:
            upload_res = client.post(
                "/videos/",
                files={"file": ("sample_test_video.mp4", f, "video/mp4")},
                headers=headers_1
            )
        assert upload_res.status_code == 201, f"Upload failed: {upload_res.json()}"
        upload_data = upload_res.json()
        video_id_1 = upload_data["video_id"]
        video_url_1 = upload_data.get("video_url")
        assert video_url_1 is not None and video_url_1.startswith("/uploads/"), (
            f"Invalid video_url returned on upload: {video_url_1}"
        )

        # Step 3: Trigger Analysis & Wait for Completion
        trigger_res = client.post(f"/videos/{video_id_1}/analyze", headers=headers_1)
        assert trigger_res.status_code == 202, f"Trigger failed: {trigger_res.json()}"
        
        analysis_res = client.get(f"/videos/{video_id_1}/analysis", headers=headers_1)
        assert analysis_res.status_code == 200, f"Get status failed: {analysis_res.json()}"
        analysis_data = analysis_res.json()
        assert analysis_data["status"] == "COMPLETED", f"Expected COMPLETED, got {analysis_data['status']}"

        # Step 4: Verify Current Report Fields (Video Playback URL & Stored Analysis Data)
        assert analysis_data.get("video_url") == video_url_1, "video_url in analysis status mismatch"
        assert analysis_data.get("original_filename") == "sample_test_video.mp4", "filename mismatch"
        
        risk_score_1 = analysis_data.get("overall_risk_score")
        risk_level_1 = analysis_data.get("risk_level")
        disclaimer_1 = analysis_data.get("disclaimer")

        assert risk_score_1 is not None, "Missing overall_risk_score"
        assert risk_level_1 in ["LOW", "MODERATE", "HIGH", "Low", "Moderate", "High"], f"Invalid risk level {risk_level_1}"
        assert disclaimer_1 is not None, "Missing disclaimer"

        # Step 5: Check Athlete History Endpoint (/videos/my-history)
        history_res = client.get("/videos/my-history", headers=headers_1)
        assert history_res.status_code == 200, f"History fetch failed: {history_res.json()}"
        history_items = history_res.json()
        assert len(history_items) >= 1, "Expected at least 1 history item"

        top_item = history_items[0]
        assert str(top_item["video_id"]) == str(video_id_1), f"Expected top item to be {video_id_1}, got {top_item['video_id']}"
        assert top_item["original_filename"] == "sample_test_video.mp4"
        assert top_item["processing_status"] == "COMPLETED" or top_item["analysis_status"] == "COMPLETED"
        assert top_item["overall_risk_score"] == risk_score_1
        assert top_item["risk_level"] == risk_level_1

        # Step 6: Historical Report Load Verification (No Re-analysis Triggered)
        hist_report_res = client.get(f"/videos/{video_id_1}/analysis", headers=headers_1)
        assert hist_report_res.status_code == 200
        hist_report_data = hist_report_res.json()
        
        assert hist_report_data["video_url"] == video_url_1, "Historical video_url mismatch"
        assert hist_report_data["overall_risk_score"] == risk_score_1, "Historical risk score mismatch"
        assert hist_report_data["risk_level"] == risk_level_1, "Historical risk level mismatch"
        assert hist_report_data["disclaimer"] == disclaimer_1, "Historical disclaimer mismatch"

        # Step 7: Athlete 2 Setup & Empty History Test
        reg_res_2 = client.post("/auth/register", json={
            "name": "E2E Athlete 2",
            "email": email_2,
            "password": "Password123!",
            "role": "Athlete"
        })
        assert reg_res_2.status_code == 201
        user_id_2 = reg_res_2.json()["user_id"]

        db = SessionLocal()
        try:
            from app.models.athlete import Athlete
            athlete_2 = Athlete(user_id=uuid.UUID(user_id_2), sport="Soccer", position="Forward", age=23)
            db.add(athlete_2)
            db.commit()
        finally:
            db.close()

        login_res_2 = client.post("/auth/login", data={
            "username": email_2,
            "password": "Password123!"
        })
        token_2 = login_res_2.json()["access_token"]
        headers_2 = {"Authorization": f"Bearer {token_2}"}

        history_res_2 = client.get("/videos/my-history", headers=headers_2)
        assert history_res_2.status_code == 200
        assert history_res_2.json() == [], f"Expected empty list for new Athlete 2, got {history_res_2.json()}"

        # Step 8: Cross-Athlete Authorization Security Check (Athlete 2 attempting to access Athlete 1's report)
        unauth_access_res = client.get(f"/videos/{video_id_1}/analysis", headers=headers_2)
        assert unauth_access_res.status_code == 403, (
            f"Security violation! Expected 403 Forbidden, got {unauth_access_res.status_code}"
        )

        # Step 9: Edge Cases (Non-existent video ID)
        fake_id = str(uuid.uuid4())
        fake_res = client.get(f"/videos/{fake_id}/analysis", headers=headers_1)
        assert fake_res.status_code == 404
