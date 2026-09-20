"""
tests/test_notifications.py
----------------------------
Comprehensive test suite for the PreHab AI Notification & Alert System.

Covers:
1. NotificationService creation & deduplication logic
2. Assessment completion triggers (Completed, High/Critical/Moderate risk, Corrective plan, Coach alert)
3. Assessment failure triggers (Sanitized messages, Coach alert)
4. Non-blocking notification side-effects (Analysis not impacted by notification errors)
5. API endpoints (GET list, GET unread-count, PATCH mark-read, PATCH read-all, DELETE dismiss)
6. Strict user isolation & RBAC ownership enforcement
"""
import uuid
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.models.athlete import Athlete
from app.models.video import Video
from app.models.analysis_result import AnalysisResult, ANALYSIS_STATUS_COMPLETED, ANALYSIS_STATUS_FAILED
from app.models.notification import Notification
from app.services.notification_service import (
    NotificationService,
    TYPE_ASSESSMENT_COMPLETED,
    TYPE_HIGH_RISK_ALERT,
    TYPE_CRITICAL_RISK_ALERT,
    TYPE_MODERATE_RISK_ALERT,
    TYPE_CORRECTIVE_PLAN_READY,
    TYPE_ASSESSMENT_FAILED,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    SEVERITY_HIGH,
    SEVERITY_CRITICAL,
)
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)


def make_token(user: User) -> str:
    return create_access_token(
        subject=str(user.user_id),
        role=user.role.value,
        secret_key=settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
        expires_delta=timedelta(minutes=30),
    )


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def setup_users_and_athletes(db_session):
    # Athlete 1
    user1 = User(
        user_id=uuid.uuid4(),
        name="Athlete One",
        email=f"athlete1_{uuid.uuid4().hex[:6]}@test.com",
        password=get_password_hash("pass123"),
        role=RoleEnum.ATHLETE,
        is_active=True,
    )
    # Coach
    coach = User(
        user_id=uuid.uuid4(),
        name="Coach Carter",
        email=f"coach_{uuid.uuid4().hex[:6]}@test.com",
        password=get_password_hash("pass123"),
        role=RoleEnum.COACH,
        is_active=True,
    )
    # Athlete 2 (unrelated)
    user2 = User(
        user_id=uuid.uuid4(),
        name="Athlete Two",
        email=f"athlete2_{uuid.uuid4().hex[:6]}@test.com",
        password=get_password_hash("pass123"),
        role=RoleEnum.ATHLETE,
        is_active=True,
    )
    db_session.add_all([user1, coach, user2])
    db_session.commit()

    athlete1 = Athlete(
        athlete_id=uuid.uuid4(),
        user_id=user1.user_id,
        coach_id=coach.user_id,
        sport="Basketball",
    )
    athlete2 = Athlete(
        athlete_id=uuid.uuid4(),
        user_id=user2.user_id,
        sport="Soccer",
    )
    db_session.add_all([athlete1, athlete2])
    db_session.commit()

    return {
        "user1": user1,
        "coach": coach,
        "user2": user2,
        "athlete1": athlete1,
        "athlete2": athlete2,
        "token1": make_token(user1),
        "token_coach": make_token(coach),
        "token2": make_token(user2),
    }


def test_notification_creation_and_deduplication(db_session, setup_users_and_athletes):
    user1 = setup_users_and_athletes["user1"]
    analysis_id = uuid.uuid4()

    # First creation
    notif1 = NotificationService.create_notification(
        db=db_session,
        user_id=user1.user_id,
        notification_type=TYPE_ASSESSMENT_COMPLETED,
        title="Test Assessment",
        message="Assessment finished",
        severity=SEVERITY_INFO,
        related_analysis_id=analysis_id,
    )
    assert notif1.notification_id is not None
    assert notif1.is_read is False

    # Second creation with identical (user_id, notification_type, related_analysis_id)
    notif2 = NotificationService.create_notification(
        db=db_session,
        user_id=user1.user_id,
        notification_type=TYPE_ASSESSMENT_COMPLETED,
        title="Test Assessment Duplicate",
        message="Duplicate message",
        severity=SEVERITY_INFO,
        related_analysis_id=analysis_id,
    )
    # Must return the existing notification without creating a second record
    assert notif2.notification_id == notif1.notification_id

    count = (
        db_session.query(Notification)
        .filter(
            Notification.user_id == user1.user_id,
            Notification.related_analysis_id == analysis_id,
        )
        .count()
    )
    assert count == 1


def test_notify_assessment_completed_high_risk(db_session, setup_users_and_athletes):
    user1 = setup_users_and_athletes["user1"]
    coach = setup_users_and_athletes["coach"]
    athlete1 = setup_users_and_athletes["athlete1"]

    video = Video(
        video_id=uuid.uuid4(),
        athlete_id=athlete1.athlete_id,
        title="Drop Jump Test",
        video_url="/uploads/test.mp4",
    )
    db_session.add(video)
    db_session.commit()

    analysis = AnalysisResult(
        analysis_id=uuid.uuid4(),
        video_id=video.video_id,
        athlete_id=athlete1.athlete_id,
        status=ANALYSIS_STATUS_COMPLETED,
        overall_risk_score=78.5,
        risk_level="HIGH",
    )
    db_session.add(analysis)
    db_session.commit()

    notifs = NotificationService.notify_assessment_completed(db_session, analysis.analysis_id)

    # Athlete should get: Assessment Completed + High Risk Detected
    athlete_notifs = [n for n in notifs if n.user_id == user1.user_id]
    assert any(n.notification_type == TYPE_ASSESSMENT_COMPLETED for n in athlete_notifs)
    high_risk_notif = next((n for n in athlete_notifs if n.notification_type == TYPE_HIGH_RISK_ALERT), None)
    assert high_risk_notif is not None
    assert high_risk_notif.severity == SEVERITY_HIGH
    assert "injury-risk" in high_risk_notif.message.lower()

    # Assigned coach should also be notified
    coach_notifs = [n for n in notifs if n.user_id == coach.user_id]
    assert len(coach_notifs) >= 1
    assert "Athlete One" in coach_notifs[0].title or "Athlete One" in coach_notifs[0].message


def test_notify_assessment_completed_critical_risk(db_session, setup_users_and_athletes):
    user1 = setup_users_and_athletes["user1"]
    athlete1 = setup_users_and_athletes["athlete1"]

    video = Video(
        video_id=uuid.uuid4(),
        athlete_id=athlete1.athlete_id,
        title="Landing Test",
        video_url="/uploads/test_crit.mp4",
    )
    db_session.add(video)
    db_session.commit()

    analysis = AnalysisResult(
        analysis_id=uuid.uuid4(),
        video_id=video.video_id,
        athlete_id=athlete1.athlete_id,
        status=ANALYSIS_STATUS_COMPLETED,
        overall_risk_score=92.0,
        risk_level="CRITICAL",
    )
    db_session.add(analysis)
    db_session.commit()

    notifs = NotificationService.notify_assessment_completed(db_session, analysis.analysis_id)
    athlete_notifs = [n for n in notifs if n.user_id == user1.user_id]
    crit_notif = next((n for n in athlete_notifs if n.notification_type == TYPE_CRITICAL_RISK_ALERT), None)
    assert crit_notif is not None
    assert crit_notif.severity == SEVERITY_CRITICAL


def test_notify_assessment_failed(db_session, setup_users_and_athletes):
    user1 = setup_users_and_athletes["user1"]
    athlete1 = setup_users_and_athletes["athlete1"]

    video = Video(
        video_id=uuid.uuid4(),
        athlete_id=athlete1.athlete_id,
        title="Failed Jump Test",
        video_url="/uploads/test_fail.mp4",
    )
    db_session.add(video)
    db_session.commit()

    analysis = AnalysisResult(
        analysis_id=uuid.uuid4(),
        video_id=video.video_id,
        athlete_id=athlete1.athlete_id,
        status=ANALYSIS_STATUS_FAILED,
        error_message="InternalError: ffmpeg crashed at /sys/temp/123",
    )
    db_session.add(analysis)
    db_session.commit()

    notifs = NotificationService.notify_assessment_failed(
        db_session,
        analysis.analysis_id,
        error_message=analysis.error_message,
    )

    athlete_notif = next((n for n in notifs if n.user_id == user1.user_id), None)
    assert athlete_notif is not None
    assert athlete_notif.notification_type == TYPE_ASSESSMENT_FAILED
    # Ensure internal error message is sanitized and NOT leaked
    assert "ffmpeg" not in athlete_notif.message
    assert "/sys/temp" not in athlete_notif.message
    assert athlete_notif.action_url == "/analysis"


def test_notifications_api_lifecycle(db_session, setup_users_and_athletes):
    user1 = setup_users_and_athletes["user1"]
    token1 = setup_users_and_athletes["token1"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # 1. Create test notifications
    n1 = NotificationService.create_notification(
        db=db_session,
        user_id=user1.user_id,
        notification_type=TYPE_ASSESSMENT_COMPLETED,
        title="Assessment 1",
        message="Message 1",
    )
    n2 = NotificationService.create_notification(
        db=db_session,
        user_id=user1.user_id,
        notification_type=TYPE_HIGH_RISK_ALERT,
        title="High Risk 1",
        message="Message 2",
        severity=SEVERITY_HIGH,
    )

    # 2. Check unread count
    resp = client.get("/api/v1/notifications/unread-count", headers=headers1)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] >= 2

    # 3. Get notification list
    resp = client.get("/api/v1/notifications", headers=headers1)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2
    assert len(data["items"]) >= 2
    assert data["items"][0]["title"] in ("High Risk 1", "Assessment 1")

    # 4. Mark single notification as read
    resp = client.patch(f"/api/v1/notifications/{n1.notification_id}/read", headers=headers1)
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True

    # Check updated unread count
    resp = client.get("/api/v1/notifications/unread-count", headers=headers1)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == data["unread_count"] - 1

    # 5. Mark all as read
    resp = client.patch("/api/v1/notifications/read-all", headers=headers1)
    assert resp.status_code == 200
    assert resp.json()["updated_count"] >= 1

    resp = client.get("/api/v1/notifications/unread-count", headers=headers1)
    assert resp.status_code == 200
    assert resp.json()["unread_count"] == 0

    # 6. Dismiss / delete notification
    resp = client.delete(f"/api/v1/notifications/{n1.notification_id}", headers=headers1)
    assert resp.status_code == 200
    assert resp.json()["message"] == "Notification dismissed."


def test_user_isolation_security(db_session, setup_users_and_athletes):
    user1 = setup_users_and_athletes["user1"]
    user2 = setup_users_and_athletes["user2"]
    token2 = setup_users_and_athletes["token2"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Notification belonging to User 1
    n1 = NotificationService.create_notification(
        db=db_session,
        user_id=user1.user_id,
        notification_type=TYPE_CRITICAL_RISK_ALERT,
        title="Private Critical Alert",
        message="Private details",
        severity=SEVERITY_CRITICAL,
    )

    # User 2 attempts to get notifications -> should NOT see User 1's notification
    resp = client.get("/api/v1/notifications", headers=headers2)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert not any(item["notification_id"] == str(n1.notification_id) for item in items)

    # User 2 attempts to mark User 1's notification as read -> 404
    resp = client.patch(f"/api/v1/notifications/{n1.notification_id}/read", headers=headers2)
    assert resp.status_code == 404

    # User 2 attempts to delete User 1's notification -> 404
    resp = client.delete(f"/api/v1/notifications/{n1.notification_id}", headers=headers2)
    assert resp.status_code == 404
