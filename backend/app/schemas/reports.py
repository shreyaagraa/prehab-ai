"""
app/schemas/reports.py
----------------------
Pydantic schemas for the Reports & Export System.
"""
from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportTypeEnum(str, Enum):
    INJURY_RISK = "INJURY_RISK"
    BIOMECHANICAL = "BIOMECHANICAL"
    MOVEMENT = "MOVEMENT"
    ATHLETE_PERFORMANCE = "ATHLETE_PERFORMANCE"
    REHABILITATION = "REHABILITATION"


class ReportAthleteInfo(BaseModel):
    athlete_id: UUID
    user_id: UUID
    name: str
    email: Optional[str] = None
    sport: Optional[str] = "Data unavailable"
    position: Optional[str] = "Data unavailable"
    age: Optional[Union[int, str]] = "Data unavailable"
    height: Optional[Union[float, str]] = "Data unavailable"
    weight: Optional[Union[float, str]] = "Data unavailable"
    dominant_leg: Optional[str] = "Data unavailable"
    injury_status: Optional[str] = "Data unavailable"
    coach_name: Optional[str] = "Data unavailable"
    weekly_training_load: Optional[Union[float, str]] = "Data unavailable"
    current_fatigue_level: Optional[Union[int, str]] = "Data unavailable"
    has_injury_history: Optional[str] = "Data unavailable"

    model_config = ConfigDict(from_attributes=True)


class ReportAssessmentInfo(BaseModel):
    video_id: UUID
    analysis_id: Optional[UUID] = None
    title: Optional[str] = None
    original_filename: Optional[str] = None
    assessment_date: Optional[datetime] = None
    processing_status: Optional[str] = None
    analysis_status: Optional[str] = None
    fps: Optional[Union[float, int, str]] = "Data unavailable"
    duration_seconds: Optional[Union[float, str]] = "Data unavailable"
    frames_processed: Optional[Union[int, str]] = "Data unavailable"
    resolution: Optional[str] = "Data unavailable"

    model_config = ConfigDict(from_attributes=True)


# ── 1. INJURY RISK REPORT DATA ─────────────────────────────────────────────
class RiskFactorItem(BaseModel):
    factor_key: str
    factor_name: str
    contribution_score: Optional[Union[float, str]] = "Data unavailable"
    status: str
    description: str


class InjuryRiskReportData(BaseModel):
    overall_risk_score: Optional[Union[float, str]] = "Data unavailable"
    risk_level: Optional[str] = "Data unavailable"
    risk_factors: List[RiskFactorItem] = Field(default_factory=list)
    recommendations: Optional[Dict[str, Any]] = None
    assessment_summary: str = "Assessment screening complete."
    disclaimer: str = (
        "AI Screening Notice: PreHab AI risk scores are screening and biomechanical evaluation outputs "
        "derived from video pose estimation. They do not constitute a clinical medical diagnosis or prescriptive medical care."
    )


# ── 2. BIOMECHANICAL ASSESSMENT REPORT DATA ────────────────────────────────
class BiomechanicalMetricItem(BaseModel):
    metric_name: str
    value: Optional[Union[float, str]] = "Data unavailable"
    unit: str = ""
    interpretation: str = "Data unavailable"


class AsymmetryItem(BaseModel):
    body_region: str
    left_value: Optional[Union[float, str]] = "Data unavailable"
    right_value: Optional[Union[float, str]] = "Data unavailable"
    asymmetry_percentage: Optional[Union[float, str]] = "Data unavailable"
    status: str = "Normal"


class BiomechanicalReportData(BaseModel):
    symmetry_score: Optional[Union[float, str]] = "Data unavailable"
    fatigue_score: Optional[Union[float, str]] = "Data unavailable"
    movement_quality: Optional[Union[float, str]] = "Data unavailable"
    joint_alignment: Optional[Union[float, str]] = "Data unavailable"
    trunk_lean: Optional[Union[float, str]] = "Data unavailable"
    knee_valgus: Optional[Union[float, str]] = "Data unavailable"
    hip_stability: Optional[Union[float, str]] = "Data unavailable"
    stride_length: Optional[Union[float, str]] = "Data unavailable"
    asymmetries: List[AsymmetryItem] = Field(default_factory=list)
    detailed_features: Dict[str, Any] = Field(default_factory=dict)
    less_score: Optional[Union[int, str]] = "Data unavailable"
    less_max: Optional[Union[int, str]] = "Data unavailable"
    less_classification: Optional[str] = "Data unavailable"
    interpretation_notes: str = "Biomechanical assessment analysis derived from pose tracking."


# ── 3. MOVEMENT ANALYSIS REPORT DATA ───────────────────────────────────────
class LESSFindingItem(BaseModel):
    item_number: int
    item_name: str
    status: str       # PASS | ERROR | NOT_COMPUTABLE
    score: Optional[int] = None
    measured_value: Optional[Union[float, str]] = "Data unavailable"
    criterion_threshold: Optional[Any] = None
    unit: Optional[str] = None
    reason: Optional[str] = None


class MovementReportData(BaseModel):
    movement_name: str = "Movement Assessment"
    pose_tracking_status: str = "Completed"
    frames_analyzed: Optional[Union[int, str]] = "Data unavailable"
    less_total_score: Optional[Union[int, str]] = "Data unavailable"
    less_max_score: Optional[Union[int, str]] = "Data unavailable"
    less_classification: Optional[str] = "Data unavailable"
    less_items: List[LESSFindingItem] = Field(default_factory=list)
    movement_deviations: List[str] = Field(default_factory=list)
    corrective_actions: List[str] = Field(default_factory=list)
    analysis_status: str = "COMPLETED"


# ── 4. ATHLETE PERFORMANCE REPORT DATA ─────────────────────────────────────
class AssessmentHistoryItem(BaseModel):
    video_id: UUID
    date: Optional[datetime] = None
    title: Optional[str] = None
    risk_score: Optional[Union[float, str]] = "Data unavailable"
    risk_level: Optional[str] = "Data unavailable"
    less_score: Optional[Union[int, str]] = "Data unavailable"
    symmetry_score: Optional[Union[float, str]] = "Data unavailable"


class AthletePerformanceReportData(BaseModel):
    total_assessments: int = 0
    latest_risk_score: Optional[Union[float, str]] = "Data unavailable"
    latest_risk_level: Optional[str] = "Data unavailable"
    risk_change: Optional[Union[float, str]] = "Data unavailable"
    training_sessions_per_week: Optional[Union[int, str]] = "Data unavailable"
    average_session_duration: Optional[Union[int, str]] = "Data unavailable"
    average_session_rpe: Optional[Union[float, str]] = "Data unavailable"
    weekly_training_load: Optional[Union[float, str]] = "Data unavailable"
    current_fatigue_level: Optional[Union[int, str]] = "Data unavailable"
    assessment_history: List[AssessmentHistoryItem] = Field(default_factory=list)
    performance_summary: str = "Longitudinal athlete profile and assessment progression."


# ── 5. REHABILITATION REPORT DATA ──────────────────────────────────────────
class InjuryHistoryEntry(BaseModel):
    injury_type: Optional[str] = "Data unavailable"
    body_part: Optional[str] = "Data unavailable"
    severity: Optional[str] = "Data unavailable"
    injury_date: Optional[Union[date, datetime, str]] = "Data unavailable"
    recovery_date: Optional[Union[date, datetime, str]] = "Data unavailable"
    status: Optional[str] = "Data unavailable"
    remarks: Optional[str] = "Data unavailable"


class RehabilitationReportData(BaseModel):
    current_injury_status: Optional[str] = "Data unavailable"
    needs_reassessment: bool = False
    days_since_last_assessment: Optional[Union[int, str]] = "Data unavailable"
    injury_records: List[InjuryHistoryEntry] = Field(default_factory=list)
    movement_issues: List[str] = Field(default_factory=list)
    corrective_recommendations: Optional[Dict[str, Any]] = None
    rehabilitation_notes: Optional[str] = "Data unavailable"
    reassessment_recommendation: str = "Follow rehabilitation protocol and reassess as indicated."


# ── TOP-LEVEL REPORT CONTAINER ─────────────────────────────────────────────
class FullReportPayload(BaseModel):
    report_type: ReportTypeEnum
    report_type_label: str
    report_title: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by_name: str
    generated_by_role: str
    athlete: ReportAthleteInfo
    assessment: Optional[ReportAssessmentInfo] = None
    data: Union[
        InjuryRiskReportData,
        BiomechanicalReportData,
        MovementReportData,
        AthletePerformanceReportData,
        RehabilitationReportData,
        Dict[str, Any],
    ]
    disclaimer: str = (
        "AI Screening Notice: PreHab AI risk assessments are biomechanical screening tools and do not constitute "
        "medical diagnosis or treatment prescription. Consult licensed healthcare practitioners for clinical medical evaluation."
    )

    model_config = ConfigDict(from_attributes=True)


# ── API OPTIONS & LIST SCHEMAS ─────────────────────────────────────────────
class ReportSelectableAthlete(BaseModel):
    athlete_id: UUID
    name: str
    sport: Optional[str] = None
    position: Optional[str] = None
    coach_id: Optional[UUID] = None
    coach_name: Optional[str] = None
    injury_status: Optional[str] = None


class ReportSelectableAssessment(BaseModel):
    video_id: UUID
    athlete_id: UUID
    title: Optional[str] = None
    original_filename: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    analysis_status: Optional[str] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    less_score: Optional[int] = None


class ReportTypeOption(BaseModel):
    type: ReportTypeEnum
    label: str
    description: str


class ReportOptionsResponse(BaseModel):
    athletes: List[ReportSelectableAthlete]
    assessments: List[ReportSelectableAssessment]
    report_types: List[ReportTypeOption]


class ReportListItem(BaseModel):
    video_id: Optional[UUID] = None
    analysis_id: Optional[UUID] = None
    athlete_id: UUID
    athlete_name: str
    sport: Optional[str] = None
    report_type: ReportTypeEnum
    report_type_label: str
    date: Optional[datetime] = None
    status: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
