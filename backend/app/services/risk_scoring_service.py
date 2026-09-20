"""
app/services/risk_scoring_service.py
------------------------------------
5-Factor Risk Scoring Engine with Dynamic Weight Renormalization.

Computes athlete risk score and risk level classification based on:
1. Biomechanical Deviations Score (S_bio, 35%): Derived from trained Random Forest pipeline or kinematic features.
2. Historical Injury Score (S_hist, 20%): Derived from recorded athlete injury history.
3. Movement Asymmetry Score (S_asym, 20%): Derived from left/right kinematic symmetry metrics.
4. Training Load Score (S_load, 15%): Derived from workload AU (sessions * duration * RPE) normalized relative to a 3000 AU prototype design threshold.
5. Fatigue Score (S_fatigue, 10%): Derived from self-reported fatigue (1-10 scale).

Dynamic Weight Renormalization
------------------------------
When factors are unavailable/unprovided, the engine excludes them completely from the calculation,
renormalizing the weights of available factors so missing data does not silently alter risk.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import uuid

import math

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models.analysis_result import AnalysisResult
from app.models.analysis_feature import AnalysisFeature
from app.models.athlete import Athlete
from app.models.injury_history import InjuryHistory

logger = logging.getLogger(__name__)

# Try importing joblib safely
try:
    import joblib  # pyrefly: ignore [missing-import]
except ImportError:
    joblib = None

# Default artifact location relative to project root
DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "scripts"
    / "artifacts"
    / "biomechanical_deviation_classifier_v2.joblib"
)

# Model's exact 9 video-derived kinematic feature columns in exact order
MODEL_FEATURE_COLUMNS = [
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

# 5-Factor Base Weights (must total 1.00)
WEIGHT_BIO: float = 0.35
WEIGHT_HIST: float = 0.20
WEIGHT_ASYM: float = 0.20
WEIGHT_LOAD: float = 0.15
WEIGHT_FATIGUE: float = 0.10

MODEL_FRAMING_DISCLAIMER = (
    "This overall risk score incorporates a Biomechanical Deviation Classifier (Kinematic RF v2) "
    "that quantifies movement pattern differences (ROM, asymmetry, velocities) relative to reference cohorts. "
    "It measures current biomechanical deviation, movement asymmetry, training workload, "
    "and self-reported fatigue — NOT future injury probability or prospective clinical diagnosis."
)


@dataclass
class RiskScoreBreakdown:
    """
    Structured breakdown of the 5-factor risk scoring calculation.
    """
    s_bio: float | None
    s_hist: float | None
    s_asym: float | None
    s_load: float | None
    s_fatigue: float | None
    s_bio_available: bool
    s_hist_available: bool
    s_asym_available: bool
    s_load_available: bool
    s_fatigue_available: bool
    overall_score: float
    risk_level: str
    model_framing: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "s_bio": self.s_bio,
            "s_hist": self.s_hist,
            "s_asym": self.s_asym,
            "s_load": self.s_load,
            "s_fatigue": self.s_fatigue,
            "s_bio_available": self.s_bio_available,
            "s_hist_available": self.s_hist_available,
            "s_asym_available": self.s_asym_available,
            "s_load_available": self.s_load_available,
            "s_fatigue_available": self.s_fatigue_available,
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "model_framing": self.model_framing,
        }


class RiskScoringService:
    """
    Service for calculating 5-factor athlete risk scores and persisting them to the database.
    """

    def __init__(self, model_path: Path | str | None = None) -> None:
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self._model = self._load_model()

    def _load_model(self) -> Any | None:
        if joblib is None:
            logger.warning("joblib library is not installed; S_bio will be unavailable.")
            return None

        if not self.model_path.exists():
            logger.warning("ML model artifact not found at %s; S_bio will be unavailable.", self.model_path)
            return None

        try:
            model = joblib.load(self.model_path)
            logger.info("Loaded v2 ML model artifact successfully from %s", self.model_path)
            return model
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load v2 ML model artifact from %s: %s", self.model_path, exc)
            return None

    def map_features(
        self,
        features_dict: dict[str, Any] | None,
        athlete: Athlete | None = None,
    ) -> tuple[pd.DataFrame | None, str | None]:
        """
        Validate and map extracted biomechanical features into the exact 9-feature kinematic vector
        schema expected by the v2 Random Forest classifier.

        Returns (DataFrame, None) if valid, or (None, reason_str) if invalid/missing/non-finite.
        """
        if not features_dict:
            return None, "No features dictionary provided"

        # 1. knee_rom_mean
        k_rom_mn = features_dict.get("knee_rom_mean")
        if k_rom_mn is None:
            l_rom = features_dict.get("knee_angle_left_rom")
            r_rom = features_dict.get("knee_angle_right_rom")
            if l_rom is not None and r_rom is not None:
                k_rom_mn = (float(l_rom) + float(r_rom)) / 2.0
            elif l_rom is not None:
                k_rom_mn = float(l_rom)
            elif r_rom is not None:
                k_rom_mn = float(r_rom)

        # 2. hip_rom_mean
        h_rom_mn = features_dict.get("hip_rom_mean")
        if h_rom_mn is None:
            l_rom = features_dict.get("hip_angle_left_rom")
            r_rom = features_dict.get("hip_angle_right_rom")
            if l_rom is not None and r_rom is not None:
                h_rom_mn = (float(l_rom) + float(r_rom)) / 2.0
            elif l_rom is not None:
                h_rom_mn = float(l_rom)
            elif r_rom is not None:
                h_rom_mn = float(r_rom)

        # 3. ankle_rom_mean
        a_rom_mn = features_dict.get("ankle_rom_mean")
        if a_rom_mn is None:
            l_rom = features_dict.get("ankle_angle_left_rom")
            r_rom = features_dict.get("ankle_angle_right_rom")
            if l_rom is not None and r_rom is not None:
                a_rom_mn = (float(l_rom) + float(r_rom)) / 2.0
            elif l_rom is not None:
                a_rom_mn = float(l_rom)
            elif r_rom is not None:
                a_rom_mn = float(r_rom)

        # 4. trunk_angle_mean
        tr_mn = features_dict.get("trunk_angle_mean")

        # 5. knee_asymmetry
        k_asym = features_dict.get("knee_asymmetry")
        if k_asym is None:
            l_rom = features_dict.get("knee_angle_left_rom")
            r_rom = features_dict.get("knee_angle_right_rom")
            if l_rom is not None and r_rom is not None:
                k_asym = abs(float(l_rom) - float(r_rom))

        # 6. hip_asymmetry
        h_asym = features_dict.get("hip_asymmetry")
        if h_asym is None:
            l_rom = features_dict.get("hip_angle_left_rom")
            r_rom = features_dict.get("hip_angle_right_rom")
            if l_rom is not None and r_rom is not None:
                h_asym = abs(float(l_rom) - float(r_rom))

        # 7. ankle_asymmetry
        a_asym = features_dict.get("ankle_asymmetry")
        if a_asym is None:
            l_rom = features_dict.get("ankle_angle_left_rom")
            r_rom = features_dict.get("ankle_angle_right_rom")
            if l_rom is not None and r_rom is not None:
                a_asym = abs(float(l_rom) - float(r_rom))

        # 8. mean_joint_velocity
        mean_vel = features_dict.get("mean_joint_velocity")

        # 9. total_joint_displacement
        total_disp = features_dict.get("total_joint_displacement")

        values_map = {
            "knee_rom_mean": k_rom_mn,
            "hip_rom_mean": h_rom_mn,
            "ankle_rom_mean": a_rom_mn,
            "trunk_angle_mean": tr_mn,
            "knee_asymmetry": k_asym,
            "hip_asymmetry": h_asym,
            "ankle_asymmetry": a_asym,
            "mean_joint_velocity": mean_vel,
            "total_joint_displacement": total_disp,
        }

        missing_keys = []
        non_finite_keys = []
        row_data = {}

        for col in MODEL_FEATURE_COLUMNS:
            val = values_map.get(col)
            if val is None or pd.isna(val):
                missing_keys.append(col)
            else:
                try:
                    f_val = float(val)
                    if not math.isfinite(f_val):
                        non_finite_keys.append(col)
                    else:
                        row_data[col] = f_val
                except (ValueError, TypeError):
                    non_finite_keys.append(col)

        if missing_keys:
            return None, f"Missing required kinematic features: {', '.join(missing_keys)}"
        if non_finite_keys:
            return None, f"Non-finite or invalid numeric values in features: {', '.join(non_finite_keys)}"

        return pd.DataFrame([row_data], columns=MODEL_FEATURE_COLUMNS), None

    def compute_s_bio(
        self,
        features_dict: dict[str, Any] | None,
        athlete: Athlete | None = None,
    ) -> tuple[float | None, bool]:
        if self._model is None:
            logger.warning("S_bio calculation skipped: ML model artifact is not available.")
            return None, False

        df, err_reason = self.map_features(features_dict, athlete)
        if df is None:
            logger.warning("S_bio ML_UNAVAILABLE: %s", err_reason)
            return None, False

        try:
            prob_injured = float(self._model.predict_proba(df)[0][1])
            s_bio = max(0.0, min(100.0, prob_injured * 100.0))
            return round(s_bio, 2), True
        except Exception as exc:  # noqa: BLE001
            logger.warning("S_bio calculation failed during model inference (%s)", exc)
            return None, False

    def compute_s_hist(self, athlete_id: uuid.UUID | None, db: Session) -> tuple[float | None, bool]:
        if athlete_id is None:
            return None, False

        athlete = db.get(Athlete, athlete_id)
        injury_records = (
            db.query(InjuryHistory)
            .filter(InjuryHistory.athlete_id == athlete_id)
            .all()
        )

        injury_count = len(injury_records)

        if athlete and athlete.has_injury_history == "NO" and injury_count == 0:
            return 0.0, True

        if injury_count > 0 or (athlete and athlete.has_injury_history == "YES"):
            currently_affected = any(getattr(r, "status", None) == "Currently affected" for r in injury_records)
            base_score = float(injury_count * 20.0) + (20.0 if currently_affected else 0.0)
            s_hist = min(base_score, 100.0)
            return round(s_hist, 2), True

        return None, False

    def compute_s_asym(self, features_dict: dict[str, Any] | None) -> tuple[float | None, bool]:
        if not features_dict:
            return None, False

        asymmetries: list[float] = []
        for key in ("knee_symmetry_score", "hip_symmetry_score", "ankle_symmetry_score"):
            sym_val = features_dict.get(key)
            if sym_val is not None:
                asymmetry_deg = max(0.0, min(100.0, 100.0 - float(sym_val)))
                asymmetries.append(asymmetry_deg)

        if not asymmetries:
            for key in ("knee_asymmetry", "hip_asymmetry", "ankle_asymmetry"):
                asym_val = features_dict.get(key)
                if asym_val is not None:
                    asymmetries.append(float(asym_val))

        if not asymmetries:
            return None, False

        s_asym = sum(asymmetries) / len(asymmetries)
        return round(s_asym, 2), True

    def compute_s_load(self, athlete: Athlete | None) -> tuple[float | None, bool]:
        if not athlete:
            return None, False

        weekly_load = athlete.weekly_training_load
        if weekly_load is None and athlete.training_load is not None:
            weekly_load = athlete.training_load

        if (
            weekly_load is None
            and athlete.training_sessions_per_week is not None
            and athlete.average_session_duration is not None
            and athlete.average_session_rpe is not None
        ):
            weekly_load = float(
                athlete.training_sessions_per_week
                * athlete.average_session_duration
                * athlete.average_session_rpe
            )

        if weekly_load is None:
            return None, False

        # Prototype workload risk indicator normalized relative to 3000 AU reference threshold
        s_load = min(100.0, round((weekly_load / 3000.0) * 100.0, 2))
        return s_load, True

    def compute_s_fatigue(self, athlete: Athlete | None) -> tuple[float | None, bool]:
        if not athlete or athlete.current_fatigue_level is None:
            return None, False

        fatigue_val = athlete.current_fatigue_level
        # Map 1-10 scale to 0.0 - 100.0 (1 -> 0, 5 -> 44.44, 10 -> 100)
        s_fatigue = round(((fatigue_val - 1.0) / 9.0) * 100.0, 2)
        return s_fatigue, True

    @staticmethod
    def calculate_risk_level(score: float) -> str:
        if score < 40.0:
            return "LOW"
        elif score < 70.0:
            return "MODERATE"
        elif score < 85.0:
            return "HIGH"
        else:
            return "CRITICAL"

    @staticmethod
    def calculate_overall_score(
        s_bio: float | None,
        s_hist: float | None,
        s_asym: float | None,
        s_load: float | None,
        s_fatigue: float | None,
        s_bio_avail: bool = True,
        s_hist_avail: bool = True,
        s_asym_avail: bool = True,
        s_load_avail: bool = True,
        s_fatigue_avail: bool = True,
    ) -> float:
        factors = [
            (s_bio, WEIGHT_BIO, s_bio_avail),
            (s_hist, WEIGHT_HIST, s_hist_avail),
            (s_asym, WEIGHT_ASYM, s_asym_avail),
            (s_load, WEIGHT_LOAD, s_load_avail),
            (s_fatigue, WEIGHT_FATIGUE, s_fatigue_avail),
        ]

        active_factors = [(score, weight) for score, weight, avail in factors if avail and score is not None]

        if not active_factors:
            return 0.0

        total_active_weight = sum(w for _, w in active_factors)
        overall = sum(score * (weight / total_active_weight) for score, weight in active_factors)
        return round(max(0.0, min(100.0, overall)), 2)

    def compute_and_persist(
        self,
        analysis_id: uuid.UUID,
        db: Session,
    ) -> RiskScoreBreakdown:
        analysis = db.get(AnalysisResult, analysis_id)
        if analysis is None:
            raise ValueError(f"AnalysisResult record with ID {analysis_id} not found.")

        athlete = db.get(Athlete, analysis.athlete_id) if analysis.athlete_id else None

        feature_record = (
            db.query(AnalysisFeature)
            .filter(AnalysisFeature.analysis_id == analysis_id)
            .first()
        )
        features_dict = feature_record.features if feature_record else None

        s_bio, s_bio_avail = self.compute_s_bio(features_dict, athlete)
        s_hist, s_hist_avail = self.compute_s_hist(analysis.athlete_id, db)
        s_asym, s_asym_avail = self.compute_s_asym(features_dict)
        s_load, s_load_avail = self.compute_s_load(athlete)
        s_fatigue, s_fatigue_avail = self.compute_s_fatigue(athlete)

        overall_score = self.calculate_overall_score(
            s_bio, s_hist, s_asym, s_load, s_fatigue,
            s_bio_avail, s_hist_avail, s_asym_avail, s_load_avail, s_fatigue_avail
        )
        risk_level = self.calculate_risk_level(overall_score)

        analysis.overall_risk_score = overall_score
        analysis.risk_level = risk_level
        analysis.symmetry_score = round(s_asym, 2) if s_asym is not None else None
        analysis.fatigue_score = round(s_fatigue, 2) if s_fatigue is not None else None

        db.commit()

        logger.info(
            "Analysis %s: Risk scoring completed — overall_score=%.2f, risk_level='%s'",
            analysis_id,
            overall_score,
            risk_level,
        )

        return RiskScoreBreakdown(
            s_bio=s_bio,
            s_hist=s_hist,
            s_asym=s_asym,
            s_load=s_load,
            s_fatigue=s_fatigue,
            s_bio_available=s_bio_avail,
            s_hist_available=s_hist_avail,
            s_asym_available=s_asym_avail,
            s_load_available=s_load_avail,
            s_fatigue_available=s_fatigue_avail,
            overall_score=overall_score,
            risk_level=risk_level,
            model_framing=MODEL_FRAMING_DISCLAIMER,
        )

    def get_breakdown(
        self,
        analysis_id: uuid.UUID,
        db: Session,
    ) -> RiskScoreBreakdown:
        analysis = db.get(AnalysisResult, analysis_id)
        if analysis is None:
            raise ValueError(f"AnalysisResult record with ID {analysis_id} not found.")

        athlete = db.get(Athlete, analysis.athlete_id) if analysis.athlete_id else None

        feature_record = (
            db.query(AnalysisFeature)
            .filter(AnalysisFeature.analysis_id == analysis_id)
            .first()
        )
        features_dict = feature_record.features if feature_record else None

        s_bio, s_bio_avail = self.compute_s_bio(features_dict, athlete)
        s_hist, s_hist_avail = self.compute_s_hist(analysis.athlete_id, db)
        s_asym, s_asym_avail = self.compute_s_asym(features_dict)
        s_load, s_load_avail = self.compute_s_load(athlete)
        s_fatigue, s_fatigue_avail = self.compute_s_fatigue(athlete)

        overall_score = (
            analysis.overall_risk_score
            if analysis.overall_risk_score is not None
            else self.calculate_overall_score(
                s_bio, s_hist, s_asym, s_load, s_fatigue,
                s_bio_avail, s_hist_avail, s_asym_avail, s_load_avail, s_fatigue_avail
            )
        )
        risk_level = (
            analysis.risk_level
            if analysis.risk_level is not None
            else self.calculate_risk_level(overall_score)
        )

        return RiskScoreBreakdown(
            s_bio=s_bio,
            s_hist=s_hist,
            s_asym=s_asym,
            s_load=s_load,
            s_fatigue=s_fatigue,
            s_bio_available=s_bio_avail,
            s_hist_available=s_hist_avail,
            s_asym_available=s_asym_avail,
            s_load_available=s_load_avail,
            s_fatigue_available=s_fatigue_avail,
            overall_score=overall_score,
            risk_level=risk_level,
            model_framing=MODEL_FRAMING_DISCLAIMER,
        )
