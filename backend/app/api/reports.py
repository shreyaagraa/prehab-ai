"""
app/api/reports.py
------------------
FastAPI router for the Reports & Export System.
Enforces strict RBAC and coach-athlete authorization.
Provides report options, report preview data, and genuine PDF & Excel exports.
"""
from __future__ import annotations

import urllib.parse
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.analysis_less import AnalysisLESS
from app.models.analysis_result import AnalysisResult
from app.models.athlete import Athlete
from app.models.user import RoleEnum, User
from app.models.video import Video
from app.schemas.reports import (
    FullReportPayload,
    ReportListItem,
    ReportOptionsResponse,
    ReportSelectableAssessment,
    ReportSelectableAthlete,
    ReportTypeEnum,
    ReportTypeOption,
)
from app.services.excel_exporter import generate_excel_report
from app.services.pdf_exporter import generate_pdf_report
from app.services.report_generator import generate_report_payload

router = APIRouter(
    prefix="/reports",
    tags=["Reports & Exports"],
)


def _verify_athlete_access(athlete_id: UUID, current_user: User, db: Session) -> Athlete:
    """
    Enforces server-side authorization:
    - Athlete: May ONLY access their own athlete profile/reports.
    - Coach: May ONLY access athletes assigned to them (athlete.coach_id == current_user.user_id).
    - Physiotherapist / Sports Scientist / Administrator: Authorized access.
    """
    athlete = db.query(Athlete).filter(Athlete.athlete_id == athlete_id).first()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Athlete with ID '{athlete_id}' was not found.",
        )

    if current_user.role == RoleEnum.ATHLETE:
        if athlete.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access another athlete's reports.",
            )
    elif current_user.role == RoleEnum.COACH:
        if athlete.coach_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access reports for an athlete not assigned to you.",
            )

    # Check athlete-controlled report sharing permissions for staff roles
    if current_user.role in (RoleEnum.COACH, RoleEnum.PHYSIOTHERAPIST, RoleEnum.SPORTS_SCIENTIST):
        from app.models.report_share import ReportShare
        role_code_map = {
            RoleEnum.COACH: "Coach",
            RoleEnum.PHYSIOTHERAPIST: "Physiotherapist",
            RoleEnum.SPORTS_SCIENTIST: "SportsScientist",
        }
        target_role = role_code_map.get(current_user.role)
        if target_role:
            share_rec = (
                db.query(ReportShare)
                .filter(
                    ReportShare.athlete_id == athlete.athlete_id,
                    ReportShare.target_role == target_role,
                )
                .first()
            )
            if share_rec and not share_rec.is_authorized:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access to athlete reports for {target_role} has been revoked by the athlete/guardian.",
                )

    return athlete


@router.get(
    "/options",
    response_model=ReportOptionsResponse,
    summary="Get selectable athletes, assessments, and report types for Report Center",
)
def get_report_options(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> ReportOptionsResponse:
    """
    Returns athletes and assessments accessible to the authenticated user.
    """
    # 1. Fetch accessible athletes
    if current_user.role == RoleEnum.ATHLETE:
        athletes_query = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).all()
    elif current_user.role == RoleEnum.COACH:
        athletes_query = db.query(Athlete).filter(Athlete.coach_id == current_user.user_id).all()
    elif current_user.role in (
        RoleEnum.ADMINISTRATOR,
        RoleEnum.PHYSIOTHERAPIST,
        RoleEnum.SPORTS_SCIENTIST,
    ):
        athletes_query = db.query(Athlete).all()
    else:
        athletes_query = []

    accessible_athlete_ids = [a.athlete_id for a in athletes_query]

    # Build selectable athlete items
    athlete_items: list[ReportSelectableAthlete] = []
    for a in athletes_query:
        u = db.query(User).filter(User.user_id == a.user_id).first()
        c_name = None
        if a.coach_id:
            cu = db.query(User).filter(User.user_id == a.coach_id).first()
            if cu:
                c_name = cu.name
        athlete_items.append(
            ReportSelectableAthlete(
                athlete_id=a.athlete_id,
                name=u.name if u else "Athlete",
                sport=a.sport,
                position=a.position,
                coach_id=a.coach_id,
                coach_name=c_name,
                injury_status=a.injury_status,
            )
        )

    # 2. Fetch accessible assessments
    assessment_items: list[ReportSelectableAssessment] = []
    if accessible_athlete_ids:
        videos = (
            db.query(Video)
            .filter(Video.athlete_id.in_(accessible_athlete_ids))
            .order_by(Video.uploaded_at.desc())
            .all()
        )
        for v in videos:
            analysis = (
                db.query(AnalysisResult)
                .filter(AnalysisResult.video_id == v.video_id)
                .order_by(AnalysisResult.created_at.desc())
                .first()
            )
            less_score = None
            if analysis:
                less_rec = db.query(AnalysisLESS).filter(AnalysisLESS.analysis_id == analysis.analysis_id).first()
                if less_rec:
                    less_score = less_rec.score

            assessment_items.append(
                ReportSelectableAssessment(
                    video_id=v.video_id,
                    athlete_id=v.athlete_id,
                    title=v.title or v.original_filename or "Video Assessment",
                    original_filename=v.original_filename,
                    uploaded_at=v.uploaded_at,
                    analysis_status=analysis.status if analysis else (v.processing_status or "PENDING"),
                    risk_score=analysis.overall_risk_score if analysis else None,
                    risk_level=analysis.risk_level if analysis else None,
                    less_score=less_score,
                )
            )

    # 3. Available report types
    report_type_options = [
        ReportTypeOption(
            type=ReportTypeEnum.INJURY_RISK,
            label="Injury Risk Report",
            description="Overall risk score, 5-factor contribution breakdown, and corrective recommendations.",
        ),
        ReportTypeOption(
            type=ReportTypeEnum.BIOMECHANICAL,
            label="Biomechanical Assessment Report",
            description="Kinematic features, joint angles, bilateral asymmetry, and pose metrics.",
        ),
        ReportTypeOption(
            type=ReportTypeEnum.MOVEMENT,
            label="Movement Analysis Report",
            description="Landing Error Scoring System (LESS) approximation and movement deviation findings.",
        ),
        ReportTypeOption(
            type=ReportTypeEnum.ATHLETE_PERFORMANCE,
            label="Athlete Performance Report",
            description="Longitudinal assessment progression, training load metrics, and workload history.",
        ),
        ReportTypeOption(
            type=ReportTypeEnum.REHABILITATION,
            label="Rehabilitation Report",
            description="Recovery status, documented injury records, reassessment tracking, and rehabilitation notes.",
        ),
    ]

    return ReportOptionsResponse(
        athletes=athlete_items,
        assessments=assessment_items,
        report_types=report_type_options,
    )


@router.get(
    "/data",
    response_model=FullReportPayload,
    summary="Generate and preview JSON data for a report",
)
def get_report_data(
    report_type: ReportTypeEnum = Query(..., description="Type of report to generate"),
    athlete_id: UUID = Query(..., description="ID of the target athlete"),
    video_id: Optional[UUID] = Query(None, description="Optional specific video/assessment ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FullReportPayload:
    """
    Generates structured report data payload after verifying caller permissions.
    """
    _verify_athlete_access(athlete_id, current_user, db)

    try:
        payload = generate_report_payload(
            report_type=report_type,
            athlete_id=athlete_id,
            video_id=video_id,
            current_user=current_user,
            db=db,
        )
        return payload
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/export/pdf",
    summary="Export report as a formatted PDF document",
)
def export_pdf_report(
    report_type: ReportTypeEnum = Query(..., description="Type of report to export"),
    athlete_id: UUID = Query(..., description="ID of the target athlete"),
    video_id: Optional[UUID] = Query(None, description="Optional specific video/assessment ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates and streams a professional PDF document with PreHab AI branding.
    """
    _verify_athlete_access(athlete_id, current_user, db)

    try:
        payload = generate_report_payload(
            report_type=report_type,
            athlete_id=athlete_id,
            video_id=video_id,
            current_user=current_user,
            db=db,
        )
        pdf_bytes = generate_pdf_report(payload)

        safe_athlete_name = "".join(c for c in payload.athlete.name if c.isalnum() or c in (" ", "_", "-")).strip()
        filename = f"PreHabAI_{payload.report_type.value}_{safe_athlete_name}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        encoded_filename = urllib.parse.quote(filename)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}",
        )


@router.get(
    "/export/excel",
    summary="Export report as a structured .xlsx spreadsheet",
)
def export_excel_report(
    report_type: ReportTypeEnum = Query(..., description="Type of report to export"),
    athlete_id: UUID = Query(..., description="ID of the target athlete"),
    video_id: Optional[UUID] = Query(None, description="Optional specific video/assessment ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates and streams a multi-sheet .xlsx workbook.
    """
    _verify_athlete_access(athlete_id, current_user, db)

    try:
        payload = generate_report_payload(
            report_type=report_type,
            athlete_id=athlete_id,
            video_id=video_id,
            current_user=current_user,
            db=db,
        )
        xlsx_bytes = generate_excel_report(payload)

        safe_athlete_name = "".join(c for c in payload.athlete.name if c.isalnum() or c in (" ", "_", "-")).strip()
        filename = f"PreHabAI_{payload.report_type.value}_{safe_athlete_name}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"
        encoded_filename = urllib.parse.quote(filename)

        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{encoded_filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Excel report: {str(e)}",
        )


@router.get(
    "/list",
    response_model=list[ReportListItem],
    summary="List generated and available assessment reports for table display",
)
def list_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[ReportListItem]:
    """
    Returns list of reports for recent assessments accessible to the caller.
    """
    if current_user.role == RoleEnum.ATHLETE:
        athletes = db.query(Athlete).filter(Athlete.user_id == current_user.user_id).all()
    elif current_user.role == RoleEnum.COACH:
        athletes = db.query(Athlete).filter(Athlete.coach_id == current_user.user_id).all()
    elif current_user.role in (
        RoleEnum.ADMINISTRATOR,
        RoleEnum.PHYSIOTHERAPIST,
        RoleEnum.SPORTS_SCIENTIST,
    ):
        athletes = db.query(Athlete).all()
    else:
        athletes = []

    items: list[ReportListItem] = []

    for a in athletes:
        user = db.query(User).filter(User.user_id == a.user_id).first()
        ath_name = user.name if user else "Athlete"

        videos = (
            db.query(Video)
            .filter(Video.athlete_id == a.athlete_id)
            .order_by(Video.uploaded_at.desc())
            .all()
        )

        for v in videos:
            analysis = (
                db.query(AnalysisResult)
                .filter(AnalysisResult.video_id == v.video_id)
                .order_by(AnalysisResult.created_at.desc())
                .first()
            )

            # Default report type for standard video assessment
            rep_type = ReportTypeEnum.INJURY_RISK
            rep_label = "Injury Risk Report"
            if current_user.role == RoleEnum.PHYSIOTHERAPIST:
                rep_type = ReportTypeEnum.REHABILITATION
                rep_label = "Rehabilitation Report"
            elif current_user.role == RoleEnum.SPORTS_SCIENTIST:
                rep_type = ReportTypeEnum.BIOMECHANICAL
                rep_label = "Biomechanical Report"

            items.append(
                ReportListItem(
                    video_id=v.video_id,
                    analysis_id=analysis.analysis_id if analysis else None,
                    athlete_id=a.athlete_id,
                    athlete_name=ath_name,
                    sport=a.sport,
                    report_type=rep_type,
                    report_type_label=rep_label,
                    date=analysis.completed_at if (analysis and analysis.completed_at) else v.uploaded_at,
                    status=analysis.status if analysis else (v.processing_status or "PENDING"),
                    risk_score=analysis.overall_risk_score if analysis else None,
                    risk_level=analysis.risk_level if analysis else None,
                )
            )

    return items
