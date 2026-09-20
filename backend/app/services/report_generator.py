"""
app/services/report_generator.py
--------------------------------
Assembles comprehensive, production-ready report data payloads from stored database records.
Reuses existing calculations (Risk scores, LESS items, Features, Recommendations, Injury History).
Does NOT invent data or perform redundant ML inference.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.athlete import Athlete
from app.models.user import User, RoleEnum
from app.models.video import Video
from app.models.analysis_result import AnalysisResult
from app.models.analysis_feature import AnalysisFeature
from app.models.analysis_less import AnalysisLESS
from app.models.injury_history import InjuryHistory
from app.schemas.reports import (
    ReportTypeEnum,
    ReportAthleteInfo,
    ReportAssessmentInfo,
    FullReportPayload,
    InjuryRiskReportData,
    BiomechanicalReportData,
    MovementReportData,
    AthletePerformanceReportData,
    RehabilitationReportData,
    RiskFactorItem,
    AsymmetryItem,
    LESSFindingItem,
    AssessmentHistoryItem,
    InjuryHistoryEntry,
)


def _format_val(val, default="Data unavailable"):
    if val is None or val == "":
        return default
    return val


def get_athlete_info(athlete: Athlete, db: Session) -> ReportAthleteInfo:
    user = db.query(User).filter(User.user_id == athlete.user_id).first()
    coach_name = "Data unavailable"
    if athlete.coach_id:
        coach_user = db.query(User).filter(User.user_id == athlete.coach_id).first()
        if coach_user:
            coach_name = coach_user.name

    return ReportAthleteInfo(
        athlete_id=athlete.athlete_id,
        user_id=athlete.user_id,
        name=user.name if user else "Athlete",
        email=user.email if user else None,
        sport=_format_val(athlete.sport),
        position=_format_val(athlete.position),
        age=_format_val(athlete.age),
        height=_format_val(athlete.height),
        weight=_format_val(athlete.weight),
        dominant_leg=_format_val(athlete.dominant_leg),
        injury_status=_format_val(athlete.injury_status, default="Healthy"),
        coach_name=coach_name,
        weekly_training_load=_format_val(athlete.weekly_training_load or athlete.training_load),
        current_fatigue_level=_format_val(athlete.current_fatigue_level),
        has_injury_history=_format_val(athlete.has_injury_history),
    )


def get_assessment_info(video: Optional[Video], analysis: Optional[AnalysisResult]) -> Optional[ReportAssessmentInfo]:
    if not video:
        return None

    return ReportAssessmentInfo(
        video_id=video.video_id,
        analysis_id=analysis.analysis_id if analysis else None,
        title=video.title or video.original_filename or "Video Assessment",
        original_filename=video.original_filename,
        assessment_date=analysis.completed_at if (analysis and analysis.completed_at) else video.uploaded_at,
        processing_status=video.processing_status,
        analysis_status=analysis.status if analysis else (video.processing_status or "PENDING"),
        fps=_format_val(analysis.fps if analysis else video.fps),
        duration_seconds=_format_val(analysis.duration_seconds if analysis else video.duration),
        frames_processed=_format_val(analysis.frames_processed if analysis else None),
        resolution=_format_val(f"{analysis.width}x{analysis.height}" if (analysis and analysis.width and analysis.height) else video.resolution),
    )


def build_injury_risk_report(
    athlete: Athlete,
    video: Optional[Video],
    analysis: Optional[AnalysisResult],
    db: Session,
) -> InjuryRiskReportData:
    overall_score = _format_val(analysis.overall_risk_score if analysis else None)
    risk_level = _format_val(analysis.risk_level if analysis else None)

    factors: list[RiskFactorItem] = []
    recommendations_data = None

    if analysis and analysis.status == "COMPLETED":
        # Extract 5-factor breakdown using existing scoring service
        try:
            from app.services.risk_scoring_service import RiskScoringService
            risk_svc = RiskScoringService()
            breakdown = risk_svc.get_breakdown(analysis.analysis_id, db)
            
            factors.append(
                RiskFactorItem(
                    factor_key="biomechanics",
                    factor_name="Biomechanical Movement Pattern (S_bio)",
                    contribution_score=breakdown.s_bio,
                    status="Elevated" if breakdown.s_bio >= 50 else "Normal",
                    description="Kinematic alignment and landing motion screening score.",
                )
            )
            factors.append(
                RiskFactorItem(
                    factor_key="history",
                    factor_name="Injury History Factor (S_hist)",
                    contribution_score=breakdown.s_hist,
                    status="Elevated" if breakdown.s_hist >= 50 else "Normal",
                    description="Prior documented injuries and musculoskeletal history.",
                )
            )
            factors.append(
                RiskFactorItem(
                    factor_key="asymmetry",
                    factor_name="Bilateral Asymmetry (S_asym)",
                    contribution_score=breakdown.s_asym,
                    status="Elevated" if breakdown.s_asym >= 50 else "Normal",
                    description="Left-vs-right kinematic symmetry divergence.",
                )
            )
            factors.append(
                RiskFactorItem(
                    factor_key="load",
                    factor_name="Acute Training Load (S_load)",
                    contribution_score=breakdown.s_load if breakdown.s_load_available else "Data unavailable",
                    status="Elevated" if (breakdown.s_load_available and breakdown.s_load >= 50) else ("Available" if breakdown.s_load_available else "Data unavailable"),
                    description="Weekly athlete workload AU (Sessions × Duration × RPE).",
                )
            )
            factors.append(
                RiskFactorItem(
                    factor_key="fatigue",
                    factor_name="Reported Fatigue Level (S_fatigue)",
                    contribution_score=breakdown.s_fatigue if breakdown.s_fatigue_available else "Data unavailable",
                    status="Elevated" if (breakdown.s_fatigue_available and breakdown.s_fatigue >= 50) else ("Available" if breakdown.s_fatigue_available else "Data unavailable"),
                    description="Subjective fatigue scale (1-10) factor weighting.",
                )
            )
        except Exception:
            pass

        # Extract recommendations from existing engine
        try:
            from app.services.recommendation_engine import CorrectiveRecommendationEngine
            rec_plan = CorrectiveRecommendationEngine.generate_for_analysis(analysis.analysis_id, db)
            if rec_plan:
                recommendations_data = rec_plan.model_dump()
        except Exception:
            pass

    return InjuryRiskReportData(
        overall_risk_score=overall_score,
        risk_level=risk_level,
        risk_factors=factors,
        recommendations=recommendations_data,
        assessment_summary=(
            f"Overall Injury Risk Level is classified as {risk_level} (Score: {overall_score}/100) based on automated screening."
            if (analysis and analysis.overall_risk_score is not None)
            else "Assessment results are pending or data is unavailable."
        ),
    )


def build_biomechanical_report(
    athlete: Athlete,
    video: Optional[Video],
    analysis: Optional[AnalysisResult],
    db: Session,
) -> BiomechanicalReportData:
    feature_dict = {}
    less_score = "Data unavailable"
    less_max = "Data unavailable"
    less_class = "Data unavailable"
    asymmetries: list[AsymmetryItem] = []

    if analysis:
        # Fetch features
        feat_rec = db.query(AnalysisFeature).filter(AnalysisFeature.analysis_id == analysis.analysis_id).first()
        if feat_rec and feat_rec.features:
            feature_dict = feat_rec.features

            # Extract left vs right knee metrics for asymmetries if available
            kl_mean = feature_dict.get("knee_angle_left_mean")
            kr_mean = feature_dict.get("knee_angle_right_mean")
            if kl_mean is not None and kr_mean is not None:
                diff = round(abs(kl_mean - kr_mean), 1)
                asymmetries.append(
                    AsymmetryItem(
                        body_region="Knee Flexion (Mean Angle)",
                        left_value=round(kl_mean, 1),
                        right_value=round(kr_mean, 1),
                        asymmetry_percentage=diff,
                        status="Asymmetric" if diff > 10 else "Symmetric",
                    )
                )

            kl_rom = feature_dict.get("knee_rom_left")
            kr_rom = feature_dict.get("knee_rom_right")
            if kl_rom is not None and kr_rom is not None:
                diff_rom = round(abs(kl_rom - kr_rom), 1)
                asymmetries.append(
                    AsymmetryItem(
                        body_region="Knee Range of Motion (ROM)",
                        left_value=round(kl_rom, 1),
                        right_value=round(kr_rom, 1),
                        asymmetry_percentage=diff_rom,
                        status="Asymmetric" if diff_rom > 12 else "Symmetric",
                    )
                )

        # Fetch LESS record
        less_rec = db.query(AnalysisLESS).filter(AnalysisLESS.analysis_id == analysis.analysis_id).first()
        if less_rec:
            less_score = less_rec.score
            less_max = less_rec.max_computable_score
            less_class = less_rec.classification

    return BiomechanicalReportData(
        symmetry_score=_format_val(analysis.symmetry_score if analysis else None),
        fatigue_score=_format_val(analysis.fatigue_score if analysis else None),
        movement_quality=_format_val(analysis.movement_quality if analysis else None),
        joint_alignment=_format_val(analysis.joint_alignment if analysis else None),
        trunk_lean=_format_val(analysis.trunk_lean if analysis else None),
        knee_valgus=_format_val(analysis.knee_valgus if analysis else None),
        hip_stability=_format_val(analysis.hip_stability if analysis else None),
        stride_length=_format_val(analysis.stride_length if analysis else None),
        asymmetries=asymmetries,
        detailed_features=feature_dict,
        less_score=less_score,
        less_max=less_max,
        less_classification=less_class,
        interpretation_notes=(
            f"Biomechanical screening captures kinematic angles and landing motion. LESS score: {less_score}/{less_max} ({less_class})."
            if less_score != "Data unavailable"
            else "Biomechanical motion metrics extracted from pose landmarks."
        ),
    )


def build_movement_report(
    athlete: Athlete,
    video: Optional[Video],
    analysis: Optional[AnalysisResult],
    db: Session,
) -> MovementReportData:
    less_items: list[LESSFindingItem] = []
    less_score = "Data unavailable"
    less_max = "Data unavailable"
    less_class = "Data unavailable"
    deviations: list[str] = []
    actions: list[str] = []

    if analysis:
        less_rec = db.query(AnalysisLESS).filter(AnalysisLESS.analysis_id == analysis.analysis_id).first()
        if less_rec:
            less_score = less_rec.score
            less_max = less_rec.max_computable_score
            less_class = less_rec.classification
            if less_rec.items:
                for item in less_rec.items:
                    less_items.append(
                        LESSFindingItem(
                            item_number=item.get("item_number", 0),
                            item_name=item.get("item_name", ""),
                            status=item.get("status", "NOT_COMPUTABLE"),
                            score=item.get("score"),
                            measured_value=_format_val(item.get("measured_value")),
                            criterion_threshold=item.get("criterion_threshold"),
                            unit=item.get("unit"),
                            reason=item.get("reason"),
                        )
                    )
                    if item.get("status") == "ERROR":
                        deviations.append(f"{item.get('item_name')}: {item.get('reason', 'Movement deviation noted')}")

        # Fetch recommendations for action items
        try:
            from app.services.recommendation_engine import CorrectiveRecommendationEngine
            rec_plan = CorrectiveRecommendationEngine.generate_for_analysis(analysis.analysis_id, db)
            if rec_plan:
                for rec in rec_plan.exercise_recommendations + rec_plan.mobility_recommendations:
                    actions.append(f"[{rec.priority.upper()}] {rec.title}: {rec.description}")
        except Exception:
            pass

    return MovementReportData(
        movement_name=video.title or video.original_filename or "Jump-Landing Assessment" if video else "Movement Assessment",
        pose_tracking_status="Completed" if (analysis and analysis.status == "COMPLETED") else (analysis.status if analysis else "Data unavailable"),
        frames_analyzed=_format_val(analysis.frames_processed if analysis else None),
        less_total_score=less_score,
        less_max_score=less_max,
        less_classification=less_class,
        less_items=less_items,
        movement_deviations=deviations if deviations else ["No substantial movement deviations flagged."],
        corrective_actions=actions if actions else ["Follow standard athletic conditioning warm-up."],
        analysis_status=analysis.status if analysis else "PENDING",
    )


def build_athlete_performance_report(
    athlete: Athlete,
    db: Session,
) -> AthletePerformanceReportData:
    analyses = (
        db.query(AnalysisResult)
        .filter(
            AnalysisResult.athlete_id == athlete.athlete_id,
            AnalysisResult.status == "COMPLETED",
        )
        .order_by(AnalysisResult.created_at.desc())
        .all()
    )

    history_items: list[AssessmentHistoryItem] = []
    latest_score = "Data unavailable"
    latest_level = "Data unavailable"
    risk_change = "Data unavailable"

    for i, an in enumerate(analyses):
        video = db.query(Video).filter(Video.video_id == an.video_id).first()
        less_rec = db.query(AnalysisLESS).filter(AnalysisLESS.analysis_id == an.analysis_id).first()
        
        if i == 0:
            latest_score = _format_val(an.overall_risk_score)
            latest_level = _format_val(an.risk_level)

        history_items.append(
            AssessmentHistoryItem(
                video_id=an.video_id,
                date=an.completed_at or an.created_at,
                title=video.title or video.original_filename or f"Assessment #{len(analyses) - i}" if video else "Assessment",
                risk_score=_format_val(an.overall_risk_score),
                risk_level=_format_val(an.risk_level),
                less_score=_format_val(less_rec.score if less_rec else None),
                symmetry_score=_format_val(an.symmetry_score),
            )
        )

    if len(analyses) >= 2 and analyses[0].overall_risk_score is not None and analyses[1].overall_risk_score is not None:
        diff = round(analyses[0].overall_risk_score - analyses[1].overall_risk_score, 1)
        risk_change = f"{'+' if diff > 0 else ''}{diff}"

    return AthletePerformanceReportData(
        total_assessments=len(analyses),
        latest_risk_score=latest_score,
        latest_risk_level=latest_level,
        risk_change=risk_change,
        training_sessions_per_week=_format_val(athlete.training_sessions_per_week),
        average_session_duration=_format_val(athlete.average_session_duration),
        average_session_rpe=_format_val(athlete.average_session_rpe),
        weekly_training_load=_format_val(athlete.weekly_training_load or athlete.training_load),
        current_fatigue_level=_format_val(athlete.current_fatigue_level),
        assessment_history=history_items,
        performance_summary=(
            f"Athlete has completed {len(analyses)} assessments. Current risk screening classification is {latest_level}."
            if len(analyses) > 0
            else "No completed assessments found for this athlete."
        ),
    )


def build_rehabilitation_report(
    athlete: Athlete,
    analysis: Optional[AnalysisResult],
    db: Session,
) -> RehabilitationReportData:
    # Fetch injury records
    injuries = (
        db.query(InjuryHistory)
        .filter(InjuryHistory.athlete_id == athlete.athlete_id)
        .order_by(InjuryHistory.injury_date.desc())
        .all()
    )

    injury_records = [
        InjuryHistoryEntry(
            injury_type=_format_val(inj.injury_type),
            body_part=_format_val(inj.body_part),
            severity=_format_val(inj.severity),
            injury_date=_format_val(inj.injury_date),
            recovery_date=_format_val(inj.recovery_date),
            status=_format_val(inj.status),
            remarks=_format_val(inj.remarks),
        )
        for inj in injuries
    ]

    # Calculate days since last assessment
    needs_reassessment = True
    days_since = "Data unavailable"
    latest_analysis = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.athlete_id == athlete.athlete_id, AnalysisResult.status == "COMPLETED")
        .order_by(AnalysisResult.created_at.desc())
        .first()
    )
    if latest_analysis:
        dt = latest_analysis.completed_at or latest_analysis.created_at
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - dt
            days_since = delta.days
            needs_reassessment = delta.days >= 14

    movement_issues: list[str] = []
    rec_dict = None
    target_analysis = analysis or latest_analysis

    if target_analysis:
        less_rec = db.query(AnalysisLESS).filter(AnalysisLESS.analysis_id == target_analysis.analysis_id).first()
        if less_rec and less_rec.items:
            for it in less_rec.items:
                if it.get("status") == "ERROR":
                    movement_issues.append(f"{it.get('item_name')}: {it.get('reason', 'Deviated pattern')}")

        try:
            from app.services.recommendation_engine import CorrectiveRecommendationEngine
            rec_plan = CorrectiveRecommendationEngine.generate_for_analysis(target_analysis.analysis_id, db)
            if rec_plan:
                rec_dict = rec_plan.model_dump()
        except Exception:
            pass

    return RehabilitationReportData(
        current_injury_status=_format_val(athlete.injury_status, default="Healthy"),
        needs_reassessment=needs_reassessment,
        days_since_last_assessment=days_since,
        injury_records=injury_records,
        movement_issues=movement_issues if movement_issues else ["No active movement dysfunctions detected."],
        corrective_recommendations=rec_dict,
        rehabilitation_notes=_format_val(athlete.coach_notes),
        reassessment_recommendation=(
            "Reassessment recommended (over 14 days since last screening or active recovery protocol)."
            if needs_reassessment
            else "Current movement profile within recent baseline. Continue recovery schedule."
        ),
    )


def generate_report_payload(
    report_type: ReportTypeEnum,
    athlete_id: UUID,
    video_id: Optional[UUID],
    current_user: User,
    db: Session,
) -> FullReportPayload:
    """
    Main entry point for generating any of the 5 report payloads.
    """
    athlete = db.query(Athlete).filter(Athlete.athlete_id == athlete_id).first()
    if not athlete:
        raise ValueError(f"Athlete {athlete_id} not found.")

    video: Optional[Video] = None
    analysis: Optional[AnalysisResult] = None

    if video_id:
        video = db.query(Video).filter(Video.video_id == video_id, Video.athlete_id == athlete_id).first()
        if video:
            analysis = (
                db.query(AnalysisResult)
                .filter(AnalysisResult.video_id == video.video_id)
                .order_by(AnalysisResult.created_at.desc())
                .first()
            )
    else:
        # Default to latest video and analysis for this athlete if available
        video = (
            db.query(Video)
            .filter(Video.athlete_id == athlete_id)
            .order_by(Video.uploaded_at.desc())
            .first()
        )
        if video:
            analysis = (
                db.query(AnalysisResult)
                .filter(AnalysisResult.video_id == video.video_id)
                .order_by(AnalysisResult.created_at.desc())
                .first()
            )

    athlete_info = get_athlete_info(athlete, db)
    assessment_info = get_assessment_info(video, analysis)

    report_labels = {
        ReportTypeEnum.INJURY_RISK: ("Injury Risk Screening Report", "Comprehensive 5-Factor Risk & Biomechanical Screening"),
        ReportTypeEnum.BIOMECHANICAL: ("Biomechanical Assessment Report", "Pose Estimation, Kinematics & Asymmetry Analysis"),
        ReportTypeEnum.MOVEMENT: ("Movement Analysis Report", "Landing Error Scoring System (LESS) & Motion Patterns"),
        ReportTypeEnum.ATHLETE_PERFORMANCE: ("Athlete Performance & Workload Report", "Longitudinal Assessment History & Training Workload"),
        ReportTypeEnum.REHABILITATION: ("Rehabilitation & Recovery Report", "Injury History, Recovery Status & Corrective Protocols"),
    }

    type_label, title_label = report_labels.get(
        report_type, (report_type.value, "PreHab AI Assessment Report")
    )

    if report_type == ReportTypeEnum.INJURY_RISK:
        data = build_injury_risk_report(athlete, video, analysis, db)
    elif report_type == ReportTypeEnum.BIOMECHANICAL:
        data = build_biomechanical_report(athlete, video, analysis, db)
    elif report_type == ReportTypeEnum.MOVEMENT:
        data = build_movement_report(athlete, video, analysis, db)
    elif report_type == ReportTypeEnum.ATHLETE_PERFORMANCE:
        data = build_athlete_performance_report(athlete, db)
    elif report_type == ReportTypeEnum.REHABILITATION:
        data = build_rehabilitation_report(athlete, analysis, db)
    else:
        raise ValueError(f"Unsupported report type: {report_type}")

    return FullReportPayload(
        report_type=report_type,
        report_type_label=type_label,
        report_title=title_label,
        generated_at=datetime.utcnow(),
        generated_by_name=current_user.name,
        generated_by_role=current_user.role.value,
        athlete=athlete_info,
        assessment=assessment_info,
        data=data,
    )
