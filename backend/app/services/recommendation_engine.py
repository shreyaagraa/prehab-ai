"""
app/services/recommendation_engine.py
--------------------------------------
Corrective Recommendation Engine v1 for PreHab AI.

Converts detected biomechanical movement patterns, Landing Error Scoring System (LESS)
findings, joint asymmetries, training workload, and fatigue indicators into structured,
personalized, non-medical corrective training suggestions.

Core Architectural Principles:
1. Rule-based, deterministic, and fully explainable (No unvalidated hallucinations).
2. Traceability: Every recommendation links [Detected Issue] -> [Metric/Evidence] -> [Rule] -> [Corrective Plan] -> [Priority].
3. Decoupled Priority: Recommendation priority (LOW, MEDIUM, HIGH) is determined by specific movement deviation severity, not just the overall risk score.
4. Non-Medical Framing: Formulated strictly as athletic performance, movement quality, and injury prevention guidance, not medical diagnosis or treatment.
5. Missing-Data Resilient: Unavailable metrics are skipped rather than triggering false-positive recommendations.
"""
from __future__ import annotations

import logging
from typing import Any, Sequence
import uuid

from sqlalchemy.orm import Session

from app.models.analysis_result import AnalysisResult
from app.models.analysis_feature import AnalysisFeature
from app.models.analysis_less import AnalysisLESS
from app.models.athlete import Athlete
from app.models.injury_history import InjuryHistory
from app.services.risk_scoring_service import RiskScoringService

logger = logging.getLogger(__name__)

# ==============================================================================
# Centralized Configurable Thresholds & Constants
# ==============================================================================

# Asymmetry thresholds (Degrees difference between Left and Right ROM)
THRESHOLD_ASYMMETRY_HIGH_DEG: float = 15.0
THRESHOLD_ASYMMETRY_MED_DEG: float = 10.0

# Knee Valgus & Alignment
THRESHOLD_KNEE_ASYM_VALGUS_DEG: float = 12.0
THRESHOLD_HIP_ASYM_DEG: float = 12.0

# Trunk inclination (Degrees from vertical)
THRESHOLD_TRUNK_MEAN_ANGLE_DEG: float = 25.0
THRESHOLD_TRUNK_MAX_ANGLE_DEG: float = 40.0

# Ankle Mobility (Degrees of mean sagittal ROM)
THRESHOLD_ANKLE_ROM_LOW_DEG: float = 25.0
THRESHOLD_ANKLE_ROM_CRITICAL_DEG: float = 18.0

# LESS Landing Quality Score
THRESHOLD_LESS_ELEVATED_SCORE: int = 5
THRESHOLD_LESS_HIGH_SCORE: int = 7

# Training Workload (Arbitrary Units = Sessions * Duration * RPE)
THRESHOLD_WORKLOAD_HIGH_AU: float = 2000.0
THRESHOLD_WORKLOAD_CRITICAL_AU: float = 2800.0

# Fatigue scale (1-10 self reported)
THRESHOLD_FATIGUE_MED: float = 6.0
THRESHOLD_FATIGUE_HIGH: float = 8.0

# Overall Biomechanical Risk thresholds
THRESHOLD_RISK_SCORE_HIGH: float = 70.0
THRESHOLD_RISK_SCORE_CRITICAL: float = 85.0

# Standard Non-Medical Screening Disclaimer
DEFAULT_DISCLAIMER = (
    "PreHab AI provides general movement technique, mobility, and training suggestions "
    "based on automated video analysis. These recommendations are not a medical diagnosis "
    "or prescription. Athletes experiencing pain, discomfort, or recovering from an injury "
    "should consult a qualified healthcare or sports medicine professional."
)


# ==============================================================================
# Curated Recommendation Library
# ==============================================================================

RECOMMENDATION_LIBRARY = {
    # ── 1. Knee Valgus / Medial Knee Alignment ─────────────────────────────
    "rec_knee_valgus_strength": {
        "id": "rec_knee_valgus_strength",
        "issue": "knee_valgus",
        "category": "strengthening",
        "title": "Gluteus Medius & Hip Abductor Strengthening",
        "description": "Strengthen lateral hip stabilizers (gluteus medius, minimus) to prevent dynamic inward knee collapse (valgus) during landing and cutting.",
        "why": "Detected medial knee displacement (knee valgus) relative to the ankle during initial contact or maximum knee flexion.",
        "exercises": [
            "Lateral band walks with mini-band around knees (3 sets of 12 steps each way)",
            "Side-lying clamshells with resistance band (3 sets of 15 reps/side)",
            "Single-leg glute bridge with 2-second hold at peak (3 sets of 10 reps/side)",
        ],
        "frequency": "3-4 sessions / week",
        "duration": "10-12 minutes per session",
        "safety_note": "Keep pelvis level and avoid rotating torso during lateral band movements.",
    },
    "rec_knee_valgus_exercise": {
        "id": "rec_knee_valgus_exercise",
        "issue": "knee_valgus",
        "category": "exercise",
        "title": "Dynamic Knee Tracking & Squat Alignment Drills",
        "description": "Neuromuscular re-education drills to train knee tracking directly over the second toe during descent and landing.",
        "why": "Movement analysis identified inward knee trajectory during deceleration.",
        "exercises": [
            "Mirror-guided bodyweight squats with external tactile cues",
            "Slow eccentric single-leg box touch-downs (3 sets of 8 reps/leg)",
            "Banded squat-to-stand emphasizing knees pushing out against resistance",
        ],
        "frequency": "3 sessions / week",
        "duration": "8-10 minutes per session",
        "safety_note": "Ensure knees do not collapse inwards inside the line of the toes at any point in the movement.",
    },
    "rec_knee_valgus_mobility": {
        "id": "rec_knee_valgus_mobility",
        "issue": "knee_valgus",
        "category": "mobility",
        "title": "Hip Adductor & TFL Soft Tissue Mobilization",
        "description": "Release overactive hip adductors and tensor fasciae latae to allow optimal gluteal recruitment.",
        "why": "Tight adductor complex can contribute to medial knee pull during dynamic loading.",
        "exercises": [
            "Foam roll inner thighs / hip adductors (60 seconds per side)",
            "Half-kneeling dynamic groin adductor rock-backs (10 reps per side)",
            "Standing dynamic lateral lunges with focus on hip hinge",
        ],
        "frequency": "Daily / pre-training warm-up",
        "duration": "5-8 minutes",
        "safety_note": "Perform mobility gently without aggressive stretching into joint pain.",
    },

    # ── 2. Landing Mechanics / Stiff Deceleration ──────────────────────────
    "rec_landing_mechanics_exercise": {
        "id": "rec_landing_mechanics_exercise",
        "issue": "poor_landing_mechanics",
        "category": "exercise",
        "title": "Controlled Deceleration & Soft Landing Mechanics",
        "description": "Progressive jump-landing drills emphasizing soft toe-to-heel transition, deep knee/hip flexion, and quiet ground contact.",
        "why": "Detected stiff-legged landing or insufficient sagittal plane knee/hip flexion displacement on impact.",
        "exercises": [
            "Snap-down to athletic landing position with 3-second hold (3 sets of 6 reps)",
            "Low box drop-to-stick landing (15-20cm box, emphasize silent impact, 3 sets of 5 reps)",
            "Forward bound to double-leg stick landing with deep knee absorption",
        ],
        "frequency": "2-3 sessions / week",
        "duration": "10-15 minutes",
        "safety_note": "Focus on 'soft and silent' landings. Do not increase box height until landing mechanics are fully controlled.",
    },
    "rec_landing_mechanics_strength": {
        "id": "rec_landing_mechanics_strength",
        "issue": "poor_landing_mechanics",
        "category": "strengthening",
        "title": "Eccentric Lower-Limb Absorption Strength",
        "description": "Build eccentric quadriceps and hamstring capacity to safely absorb multi-joint ground reaction forces.",
        "why": "Insufficient eccentric absorption increases impact shock transmission to knee ligaments.",
        "exercises": [
            "Tempo goblet squats (4 seconds down, 1 second pause, explosive up - 4 sets of 8 reps)",
            "Nordic hamstring curls / eccentric slider hamstring curls (3 sets of 6 reps)",
            "Dumbbell Romanian deadlifts with slow eccentric phase (3 sets of 10 reps)",
        ],
        "frequency": "2 sessions / week",
        "duration": "15 minutes",
        "safety_note": "Maintain neutral spinal posture throughout all eccentric loading exercises.",
    },

    # ── 3. Hip Instability / Weak Gluteal Drive ────────────────────────────
    "rec_hip_instability_strength": {
        "id": "rec_hip_instability_strength",
        "issue": "hip_instability",
        "category": "strengthening",
        "title": "Posterior Chain & Gluteus Maximus Activation",
        "description": "Targeted strengthening of the gluteal complex to stabilize the pelvis and enhance sagittal hip flexion absorption.",
        "why": "Detected reduced hip flexion range of motion or hip kinematic asymmetry during movement analysis.",
        "exercises": [
            "Barbell or dumbbell hip thrusts with 2-second squeeze at top (4 sets of 10 reps)",
            "Single-leg Romanian deadlift with kettlebell (3 sets of 8 reps/side)",
            "Quadruped bird-dog with resistance band (3 sets of 10 reps/side)",
        ],
        "frequency": "2-3 sessions / week",
        "duration": "12-15 minutes",
        "safety_note": "Drive through heels and squeeze glutes at the top of thrusts without hyperextending lumbar spine.",
    },
    "rec_hip_mobility": {
        "id": "rec_hip_mobility",
        "issue": "hip_instability",
        "category": "mobility",
        "title": "Hip Flexor & Capsule Dynamic Mobility",
        "description": "Improve anterior hip flexibility and multi-planar hip joint mobility to facilitate full hip flexion during descent.",
        "why": "Restricted hip mobility limits landing depth and forces compensatory knee loading.",
        "exercises": [
            "Half-kneeling hip flexor stretch with overhead side reach (30-45 sec/side)",
            "90/90 hip rotation mobility flows (8 transitions per side)",
            "World's greatest stretch with thoracic rotation (5 reps/side)",
        ],
        "frequency": "Daily / pre-training",
        "duration": "6-8 minutes",
        "safety_note": "Engage abdominals during hip flexor stretches to prevent anterior pelvic tilt.",
    },

    # ── 4. Trunk Instability / Excessive Trunk Lean ─────────────────────────
    "rec_trunk_stability_strength": {
        "id": "rec_trunk_stability_strength",
        "issue": "trunk_instability",
        "category": "strengthening",
        "title": "Core Stability & Anti-Lateral Flexion Training",
        "description": "Develop isometric core endurance and anti-rotational strength to maintain an athletic forward trunk lean without lateral sway.",
        "why": "Detected excessive lateral trunk flexion or upright/extended trunk posture during landing phase.",
        "exercises": [
            "Side plank with top leg elevated (3 sets of 25-30 seconds/side)",
            "Pallof press with resistance band (3 sets of 12 reps/side with 2s hold)",
            "Dead bug with opposite arm/leg extension (3 sets of 10 reps/side)",
        ],
        "frequency": "3 sessions / week",
        "duration": "10-12 minutes",
        "safety_note": "Breathe normally and maintain a rigid spine without allowing ribs to flare.",
    },
    "rec_trunk_coordination_exercise": {
        "id": "rec_trunk_coordination_exercise",
        "issue": "trunk_instability",
        "category": "exercise",
        "title": "Trunk-Pelvis Dynamic Deceleration Cues",
        "description": "Practice coordinating trunk inclination with hip flexion for balanced center-of-mass distribution during landing.",
        "why": "Erect trunk posture places greater strain on the anterior cruciate ligament during landing.",
        "exercises": [
            "Drop landing into slight forward trunk lean (shoulders over knees, knees over toes)",
            "Medicine ball deceleration catches in athletic stance (3 sets of 8 reps)",
        ],
        "frequency": "2-3 sessions / week",
        "duration": "8-10 minutes",
        "safety_note": "Ensure trunk flexion occurs at the hips, not by rounding the thoracic or lumbar spine.",
    },

    # ── 5. Left/Right Joint Asymmetry ──────────────────────────────────────
    "rec_asymmetry_exercise": {
        "id": "rec_asymmetry_exercise",
        "issue": "bilateral_asymmetry",
        "category": "exercise",
        "title": "Unilateral Neuromuscular Control & Balance",
        "description": "Single-leg stability and proprioceptive training to eliminate side-to-side strength and range of motion discrepancies.",
        "why": "Detected significant kinematic range of motion asymmetry between left and right lower limbs.",
        "exercises": [
            "Single-leg stance balance on unstable surface / foam pad (3 sets of 30 sec/leg)",
            "Single-leg clockwise/counter-clockwise clock reach drills (2 sets/leg)",
            "Single-leg lateral hops with stick landing on the weaker limb (3 sets of 6 reps/leg)",
        ],
        "frequency": "3 sessions / week",
        "duration": "10-12 minutes",
        "safety_note": "Perform exercises on both limbs, always starting with the less dominant or less stable side.",
    },
    "rec_asymmetry_strength": {
        "id": "rec_asymmetry_strength",
        "issue": "bilateral_asymmetry",
        "category": "strengthening",
        "title": "Isolated Single-Limb Strength Correction",
        "description": "Targeted unilateral resistance training to balance strength differences between limbs without bilateral compensation.",
        "why": "Bilateral asymmetry indicates one limb is absorbing disproportionate load during dynamic actions.",
        "exercises": [
            "Bulgarian split squats with dumbbells (3 sets of 8-10 reps/leg)",
            "Single-leg eccentric step-downs from low bench (3 sets of 8 reps/leg)",
            "Single-leg seated or standing calf raises (3 sets of 12 reps/leg)",
        ],
        "frequency": "2 sessions / week",
        "duration": "12-15 minutes",
        "safety_note": "Match the load and reps of the stronger limb to the capacity of the developing limb.",
    },

    # ── 6. Limited Ankle Mobility ──────────────────────────────────────────
    "rec_ankle_mobility": {
        "id": "rec_ankle_mobility",
        "issue": "limited_ankle_mobility",
        "category": "mobility",
        "title": "Ankle Dorsiflexion Mobilization & Calf Release",
        "description": "Targeted talocrural joint mobilization and gastrocnemius/soleus stretching to restore full ankle dorsiflexion.",
        "why": "Detected reduced ankle range of motion or flat-foot landing, which restricts natural lower-limb shock absorption.",
        "exercises": [
            "Knee-to-wall weight-bearing ankle mobilization (2 sets of 12 pulses/side)",
            "Banded talus joint distraction mobilization (60 seconds/side)",
            "Standing wall calf stretch with straight knee and bent knee (45 seconds each/side)",
        ],
        "frequency": "Daily / pre-session",
        "duration": "6-8 minutes",
        "safety_note": "Keep heel flat on the floor during knee-to-wall drills without lifting.",
    },
    "rec_ankle_stability": {
        "id": "rec_ankle_stability",
        "issue": "limited_ankle_mobility",
        "category": "exercise",
        "title": "Ankle Proprioception & Dynamic Stability",
        "description": "Strengthen dynamic ankle evertors and peroneals to support stable landing mechanics.",
        "why": "Restricted ankle mobility compromises foot placement and increases distal knee compensations.",
        "exercises": [
            "Banded ankle eversion and inversion resistance drills (3 sets of 15 reps/side)",
            "Multi-directional single-leg hop-and-holds on turf",
        ],
        "frequency": "2-3 sessions / week",
        "duration": "8 minutes",
        "safety_note": "Perform on flat, even surfaces before progressing to dynamic hops.",
    },
}


# ==============================================================================
# Corrective Recommendation Engine Class
# ==============================================================================

class CorrectiveRecommendationEngine:
    """
    Evaluates biomechanical features, LESS results, joint symmetry, training load,
    and fatigue to formulate a personalized Corrective Action Plan.
    """

    @classmethod
    def generate_recommendations(
        cls,
        features: dict[str, Any] | None = None,
        less_items: list[dict[str, Any]] | None = None,
        less_result: dict[str, Any] | None = None,
        risk_score: float | None = None,
        risk_level: str | None = None,
        training_data: dict[str, Any] | None = None,
        injury_records: list[dict[str, Any]] | None = None,
        analysis_id: uuid.UUID | None = None,
        video_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Generate structured corrective action plan from input data.
        """
        features = features or {}
        training_data = training_data or {}
        injury_records = injury_records or []

        # Index LESS items by item_number for fast, robust lookup
        less_map: dict[int, dict[str, Any]] = {}
        if less_items:
            for item in less_items:
                num = item.get("item_number")
                if num is not None:
                    less_map[num] = item

        # Detected issues container
        detected_issues: list[dict[str, Any]] = []
        priority_areas: set[str] = set()

        # ── 1. Detect Knee Valgus / Medial Knee Position ───────────────────
        item5 = less_map.get(5)   # Medial knee at IC
        item15 = less_map.get(15) # Knee valgus at MKF
        knee_asym = features.get("knee_asymmetry")

        has_valgus_ic = item5 and item5.get("status") == "ERROR"
        has_valgus_mkf = item15 and item15.get("status") == "ERROR"
        has_knee_asym_high = knee_asym is not None and knee_asym >= THRESHOLD_KNEE_ASYM_VALGUS_DEG

        if has_valgus_ic or has_valgus_mkf or has_knee_asym_high:
            evidence_parts = []
            if has_valgus_ic:
                evidence_parts.append("LESS Item 5 (Medial knee position at IC)")
            if has_valgus_mkf:
                evidence_parts.append("LESS Item 15 (Knee valgus at max flexion)")
            if has_knee_asym_high:
                evidence_parts.append(f"Knee ROM asymmetry ({knee_asym}° >= {THRESHOLD_KNEE_ASYM_VALGUS_DEG}°)")

            # Priority determination
            if (has_valgus_ic and has_valgus_mkf) or (has_valgus_ic and has_knee_asym_high):
                valgus_priority = "high"
            elif has_valgus_ic or has_valgus_mkf:
                valgus_priority = "medium"
            else:
                valgus_priority = "low"

            detected_issues.append({
                "issue": "knee_valgus",
                "priority": valgus_priority,
                "evidence": " & ".join(evidence_parts),
                "reason": "Medial knee trajectory exceeds stability thresholds during deceleration phase.",
                "rules": ["rec_knee_valgus_strength", "rec_knee_valgus_exercise", "rec_knee_valgus_mobility"],
            })
            priority_areas.add("Knee Stability & Alignment")

        # ── 2. Detect Landing Mechanics / Stiff Deceleration ───────────────
        item1 = less_map.get(1)   # Knee flexion at IC (<30 deg)
        item4 = less_map.get(4)   # Flat foot / heel strike landing
        item12 = less_map.get(12) # Knee flexion displacement (<45 deg)
        less_score = less_result.get("score") if less_result else None
        less_class = (less_result.get("classification") or "") if less_result else ""

        has_stiff_ic = item1 and item1.get("status") == "ERROR"
        has_flat_foot = item4 and item4.get("status") == "ERROR"
        has_stiff_disp = item12 and item12.get("status") == "ERROR"
        has_elevated_less = "ELEVATED" in less_class.upper() or (less_score is not None and less_score >= THRESHOLD_LESS_ELEVATED_SCORE)

        if has_stiff_ic or has_stiff_disp or (has_flat_foot and has_elevated_less):
            evidence_parts = []
            if has_stiff_disp:
                evidence_parts.append("LESS Item 12 (Reduced knee flexion displacement <45°)")
            if has_stiff_ic:
                evidence_parts.append("LESS Item 1 (Knee flexion at IC <30°)")
            if has_flat_foot:
                evidence_parts.append("LESS Item 4 (Flat foot / heel contact landing)")
            if has_elevated_less:
                evidence_parts.append(f"Elevated LESS Score ({less_score})")

            if has_stiff_disp and (has_stiff_ic or (less_score and less_score >= THRESHOLD_LESS_HIGH_SCORE)):
                landing_priority = "high"
            elif has_stiff_disp or has_stiff_ic:
                landing_priority = "medium"
            else:
                landing_priority = "low"

            detected_issues.append({
                "issue": "poor_landing_mechanics",
                "priority": landing_priority,
                "evidence": " & ".join(evidence_parts),
                "reason": "Insufficient sagittal joint absorption during ground impact creates high peak joint loads.",
                "rules": ["rec_landing_mechanics_exercise", "rec_landing_mechanics_strength"],
            })
            priority_areas.add("Landing Mechanics & Deceleration")

        # ── 3. Detect Hip Instability / Reduced Hip Flexion ────────────────
        item2 = less_map.get(2)   # Hip flexion at IC (thigh in line with trunk)
        item13 = less_map.get(13) # Hip flexion displacement (<=0 deg)
        hip_asym = features.get("hip_asymmetry")
        hip_sym_score = features.get("hip_symmetry_score")

        has_hip_ic = item2 and item2.get("status") == "ERROR"
        has_hip_disp = item13 and item13.get("status") == "ERROR"
        has_hip_asym_high = hip_asym is not None and hip_asym >= THRESHOLD_HIP_ASYM_DEG
        has_hip_sym_low = hip_sym_score is not None and hip_sym_score < 75.0

        if has_hip_ic or has_hip_disp or has_hip_asym_high or has_hip_sym_low:
            evidence_parts = []
            if has_hip_disp:
                evidence_parts.append("LESS Item 13 (Insufficient hip flexion displacement)")
            if has_hip_ic:
                evidence_parts.append("LESS Item 2 (Thigh in line with trunk at IC)")
            if has_hip_asym_high:
                evidence_parts.append(f"Hip ROM asymmetry ({hip_asym}° >= 12.0°)")
            if has_hip_sym_low:
                evidence_parts.append(f"Hip symmetry index ({hip_sym_score:.1f}% < 75%)")

            if (has_hip_ic and has_hip_disp) or (hip_asym is not None and hip_asym >= THRESHOLD_ASYMMETRY_HIGH_DEG):
                hip_priority = "high"
            elif has_hip_disp or has_hip_ic or has_hip_asym_high:
                hip_priority = "medium"
            else:
                hip_priority = "low"

            detected_issues.append({
                "issue": "hip_instability",
                "priority": hip_priority,
                "evidence": " & ".join(evidence_parts),
                "reason": "Limited hip flexion recruitment or hip asymmetry impairs posterior chain energy absorption.",
                "rules": ["rec_hip_instability_strength", "rec_hip_mobility"],
            })
            priority_areas.add("Hip Stability & Posterior Chain")

        # ── 4. Detect Trunk Instability / Excessive Trunk Lean ─────────────
        item3 = less_map.get(3)   # Trunk flexion at IC (vertical/extended)
        item6 = less_map.get(6)   # Lateral trunk flexion (>2 deg)
        item14 = less_map.get(14) # Trunk flexion displacement (<=0 deg)
        trunk_mean = features.get("trunk_angle_mean")
        trunk_max = features.get("trunk_angle_max")

        has_trunk_lat = item6 and item6.get("status") == "ERROR"
        has_trunk_vert = item3 and item3.get("status") == "ERROR"
        has_trunk_disp = item14 and item14.get("status") == "ERROR"
        has_trunk_angle_high = (
            (trunk_mean is not None and trunk_mean >= THRESHOLD_TRUNK_MEAN_ANGLE_DEG)
            or (trunk_max is not None and trunk_max >= THRESHOLD_TRUNK_MAX_ANGLE_DEG)
        )

        if has_trunk_lat or has_trunk_vert or has_trunk_disp or has_trunk_angle_high:
            evidence_parts = []
            if has_trunk_lat:
                evidence_parts.append("LESS Item 6 (Lateral trunk lean > 2.0°)")
            if has_trunk_vert:
                evidence_parts.append("LESS Item 3 (Erect / extended trunk at IC)")
            if has_trunk_disp:
                evidence_parts.append("LESS Item 14 (Trunk flexion does not increase)")
            if has_trunk_angle_high:
                evidence_parts.append(f"High peak trunk inclination ({trunk_max or trunk_mean}°)")

            if (has_trunk_lat and has_trunk_angle_high) or (has_trunk_lat and has_trunk_disp):
                trunk_priority = "high"
            elif has_trunk_lat or has_trunk_vert or has_trunk_disp:
                trunk_priority = "medium"
            else:
                trunk_priority = "low"

            detected_issues.append({
                "issue": "trunk_instability",
                "priority": trunk_priority,
                "evidence": " & ".join(evidence_parts),
                "reason": "Trunk misalignment or lateral deviation shifts dynamic center-of-mass away from base of support.",
                "rules": ["rec_trunk_stability_strength", "rec_trunk_coordination_exercise"],
            })
            priority_areas.add("Core / Trunk Stability")

        # ── 5. Detect Left / Right Bilateral Asymmetry ─────────────────────
        ankle_asym = features.get("ankle_asymmetry")
        knee_sym_score = features.get("knee_symmetry_score")
        ankle_sym_score = features.get("ankle_symmetry_score")
        s_asym = training_data.get("s_asym")

        has_asym_high = (
            (knee_asym is not None and knee_asym >= THRESHOLD_ASYMMETRY_HIGH_DEG)
            or (hip_asym is not None and hip_asym >= THRESHOLD_ASYMMETRY_HIGH_DEG)
            or (ankle_asym is not None and ankle_asym >= THRESHOLD_ASYMMETRY_HIGH_DEG)
            or (s_asym is not None and s_asym >= 60.0)
        )
        has_asym_med = (
            (knee_asym is not None and knee_asym >= THRESHOLD_ASYMMETRY_MED_DEG)
            or (hip_asym is not None and hip_asym >= THRESHOLD_ASYMMETRY_MED_DEG)
            or (ankle_asym is not None and ankle_asym >= THRESHOLD_ASYMMETRY_MED_DEG)
            or (s_asym is not None and s_asym >= 40.0)
            or (knee_sym_score is not None and knee_sym_score < 80.0)
            or (ankle_sym_score is not None and ankle_sym_score < 80.0)
        )

        if has_asym_high or has_asym_med:
            evidence_parts = []
            if knee_asym and knee_asym >= THRESHOLD_ASYMMETRY_MED_DEG:
                evidence_parts.append(f"Knee Asymmetry ({knee_asym}°)")
            if hip_asym and hip_asym >= THRESHOLD_ASYMMETRY_MED_DEG:
                evidence_parts.append(f"Hip Asymmetry ({hip_asym}°)")
            if ankle_asym and ankle_asym >= THRESHOLD_ASYMMETRY_MED_DEG:
                evidence_parts.append(f"Ankle Asymmetry ({ankle_asym}°)")
            if s_asym and s_asym >= 40.0:
                evidence_parts.append(f"Asymmetry Factor Score ({s_asym:.1f})")

            asym_priority = "high" if has_asym_high else "medium"

            detected_issues.append({
                "issue": "bilateral_asymmetry",
                "priority": asym_priority,
                "evidence": " & ".join(evidence_parts),
                "reason": "Bilateral joint range-of-motion asymmetry exceeds balanced tolerance limits.",
                "rules": ["rec_asymmetry_exercise", "rec_asymmetry_strength"],
            })
            priority_areas.add("Bilateral Symmetry")

        # ── 6. Detect Limited Ankle Mobility ───────────────────────────────
        ankle_rom_mean = features.get("ankle_rom_mean")
        has_ankle_flat = item4 and item4.get("status") == "ERROR"
        has_ankle_rom_low = ankle_rom_mean is not None and ankle_rom_mean < THRESHOLD_ANKLE_ROM_LOW_DEG

        if has_ankle_rom_low or (has_ankle_flat and not has_stiff_disp):
            evidence_parts = []
            if has_ankle_rom_low:
                evidence_parts.append(f"Mean Ankle ROM ({ankle_rom_mean}° < {THRESHOLD_ANKLE_ROM_LOW_DEG}°)")
            if has_ankle_flat:
                evidence_parts.append("LESS Item 4 (Flat foot landing pattern)")

            ankle_priority = "high" if (ankle_rom_mean is not None and ankle_rom_mean < THRESHOLD_ANKLE_ROM_CRITICAL_DEG) else "medium"

            detected_issues.append({
                "issue": "limited_ankle_mobility",
                "priority": ankle_priority,
                "evidence": " & ".join(evidence_parts),
                "reason": "Restricted sagittal ankle dorsiflexion restricts natural lower-limb shock absorption.",
                "rules": ["rec_ankle_mobility", "rec_ankle_stability"],
            })
            priority_areas.add("Ankle Mobility")

        # ── 7. Formulate Categorized Recommendation Items ─────────────────
        exercise_recs: list[dict[str, Any]] = []
        mobility_recs: list[dict[str, Any]] = []
        strengthening_recs: list[dict[str, Any]] = []
        added_rule_ids: set[str] = set()

        for issue_info in detected_issues:
            issue_priority = issue_info["priority"]
            issue_evidence = issue_info["evidence"]
            issue_reason = issue_info["reason"]

            for rule_id in issue_info["rules"]:
                if rule_id in added_rule_ids:
                    continue
                rule_template = RECOMMENDATION_LIBRARY.get(rule_id)
                if not rule_template:
                    continue

                rec_item = {
                    "id": rule_template["id"],
                    "issue": rule_template["issue"],
                    "category": rule_template["category"],
                    "title": rule_template["title"],
                    "description": rule_template["description"],
                    "why": rule_template["why"],
                    "evidence": issue_evidence,
                    "exercises": list(rule_template["exercises"]),
                    "priority": issue_priority,
                    "frequency": rule_template["frequency"],
                    "duration": rule_template["duration"],
                    "safety_note": rule_template["safety_note"],
                    "reason": issue_reason,
                }

                added_rule_ids.add(rule_id)

                cat = rule_template["category"]
                if cat == "exercise":
                    exercise_recs.append(rec_item)
                elif cat == "mobility":
                    mobility_recs.append(rec_item)
                elif cat == "strengthening":
                    strengthening_recs.append(rec_item)

        # ── 8. Formulate Recovery Plan ────────────────────────────────────
        recovery_plan: list[dict[str, Any]] = []

        # Inputs for recovery
        fatigue_val = training_data.get("fatigue_level")
        s_fatigue = training_data.get("s_fatigue")
        workload_au = training_data.get("training_load")
        s_load = training_data.get("s_load")

        is_high_fatigue = (fatigue_val is not None and fatigue_val >= THRESHOLD_FATIGUE_HIGH) or (s_fatigue is not None and s_fatigue >= 70.0)
        is_med_fatigue = (fatigue_val is not None and fatigue_val >= THRESHOLD_FATIGUE_MED) or (s_fatigue is not None and s_fatigue >= 50.0)
        is_high_workload = (workload_au is not None and workload_au >= THRESHOLD_WORKLOAD_HIGH_AU) or (s_load is not None and s_load >= 65.0)

        risk_level_upper = (risk_level or "").upper()

        if is_high_fatigue or is_high_workload or risk_level_upper in ["HIGH", "CRITICAL"]:
            rec_priority = "high" if (is_high_fatigue or risk_level_upper == "CRITICAL") else "medium"
            recovery_plan.append({
                "title": "Fatigue & Workload Recovery Protocol",
                "focus": "Active Recovery & Neuromuscular Rest",
                "recommendation": "Prioritize dedicated recovery windows and reduce cumulative high-impact training volume until readiness normalizes.",
                "priority": rec_priority,
                "guidelines": [
                    "Target 8-9 hours of quality sleep to facilitate tissue repair and central nervous system recovery.",
                    "Integrate 20-30 minutes of low-impact active recovery (swimming, stationary cycling, light mobility) instead of high-impact drills.",
                    "Incorporate contrast water therapy or soft-tissue self-myofascial release following intense training sessions.",
                ],
            })
            priority_areas.add("Workload & Fatigue Recovery")
        elif is_med_fatigue or risk_level_upper == "MODERATE":
            recovery_plan.append({
                "title": "Standard Recovery & Tissue Maintenance",
                "focus": "Daily Recovery Routines",
                "recommendation": "Maintain consistent recovery habits and ensure adequate rest intervals between high-intensity movement sessions.",
                "priority": "low",
                "guidelines": [
                    "Ensure adequate hydration and post-workout protein/carbohydrate replenishment within 45 minutes of training.",
                    "Complete a structured 10-minute cooldown including dynamic joint decompressive stretches.",
                    "Monitor subjective fatigue and soreness prior to entering high-velocity athletic testing.",
                ],
            })
        else:
            recovery_plan.append({
                "title": "Baseline Performance Maintenance",
                "focus": "Routine Recovery Practices",
                "recommendation": "Continue normal athletic training schedule while observing standard recovery and warm-up practices.",
                "priority": "low",
                "guidelines": [
                    "Maintain standard pre-training dynamic warm-ups and post-training cooldowns.",
                    "Sustain baseline hydration, nutrition, and sleep hygiene practices.",
                ],
            })

        # ── 9. Formulate Training Modifications ───────────────────────────
        training_modifications: list[dict[str, Any]] = []

        if has_valgus_ic or has_valgus_mkf or has_stiff_disp:
            training_modifications.append({
                "title": "Plyometric & Landing Volume Modulation",
                "action": "Reduce maximal-intensity drop jump volume by 25-30% while embedding movement technique drills.",
                "rationale": "Allows neuromuscular adaptation and safe landing pattern consolidation without accumulating excessive peak joint impact.",
                "priority": "high" if (has_valgus_ic and has_stiff_disp) else "medium",
                "suggestions": [
                    "Replace high-box drop jumps with low-box stick landings focusing on soft, aligned knee-over-toe deceleration.",
                    "Perform deceleration and jumping drills at the beginning of sessions when fatigue is lowest.",
                ],
            })

        if has_asym_high or has_asym_med:
            training_modifications.append({
                "title": "Unilateral Training Integration",
                "action": "Allocate 40% of lower-body resistance volume to unilateral (single-leg) exercises.",
                "rationale": "Prevents bilateral compensation patterns and systematically brings the developing limb to parity.",
                "priority": "high" if has_asym_high else "medium",
                "suggestions": [
                    "Program Bulgarian split squats, single-leg Romanian deadlifts, and single-leg calf raises prior to bilateral squats.",
                    "Match repetitions and loads to the capacity of the less stable limb.",
                ],
            })

        if is_high_workload:
            training_modifications.append({
                "title": "Acute-to-Chronic Workload Management",
                "action": "Implement a planned microcycle deload: cap training sessions at RPE 6-7 for the next 5-7 days.",
                "rationale": "Calculated weekly training load exceeds recommended baseline parameters.",
                "priority": "high" if (workload_au and workload_au >= THRESHOLD_WORKLOAD_CRITICAL_AU) else "medium",
                "suggestions": [
                    "Replace one high-intensity tactical session with a technique and mobility workshop.",
                    "Cap total session durations to 60-75 minutes maximum.",
                ],
            })

        # Calculate total actionable recommendations count
        total_count = len(exercise_recs) + len(mobility_recs) + len(strengthening_recs) + len(recovery_plan) + len(training_modifications)

        return {
            "analysis_id": analysis_id,
            "video_id": video_id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "priority_areas": sorted(list(priority_areas)),
            "exercise_recommendations": exercise_recs,
            "mobility_recommendations": mobility_recs,
            "strengthening_recommendations": strengthening_recs,
            "recovery_plan": recovery_plan,
            "training_modifications": training_modifications,
            "total_recommendations": total_count,
            "disclaimer": DEFAULT_DISCLAIMER,
        }

    @classmethod
    def generate_for_analysis(cls, analysis_id: uuid.UUID, db: Session) -> dict[str, Any]:
        """
        Database helper to fetch all relevant records and generate recommendations dynamically.
        """
        analysis = db.get(AnalysisResult, analysis_id)
        if not analysis:
            return {
                "analysis_id": analysis_id,
                "video_id": None,
                "risk_score": None,
                "risk_level": None,
                "priority_areas": [],
                "exercise_recommendations": [],
                "mobility_recommendations": [],
                "strengthening_recommendations": [],
                "recovery_plan": [],
                "training_modifications": [],
                "total_recommendations": 0,
                "disclaimer": DEFAULT_DISCLAIMER,
            }

        # 1. Fetch Features
        features_dict: dict[str, Any] = {}
        feat_rec = db.query(AnalysisFeature).filter(AnalysisFeature.analysis_id == analysis_id).first()
        if feat_rec and isinstance(feat_rec.features, dict):
            features_dict = feat_rec.features

        # 2. Fetch LESS Results
        less_items: list[dict[str, Any]] = []
        less_res_dict: dict[str, Any] = {}
        less_rec = db.query(AnalysisLESS).filter(AnalysisLESS.analysis_id == analysis_id).first()
        if less_rec:
            less_res_dict = {
                "score": less_rec.score,
                "max_computable_score": less_rec.max_computable_score,
                "classification": less_rec.classification,
            }
            if isinstance(less_rec.items, list):
                less_items = less_rec.items

        # 3. Fetch Athlete Profile & Training Load
        athlete = db.get(Athlete, analysis.athlete_id)
        training_data: dict[str, Any] = {}
        if athlete:
            training_data = {
                "sport": athlete.sport,
                "position": athlete.position,
                "sessions_per_week": athlete.training_sessions_per_week,
                "session_duration": athlete.average_session_duration,
                "session_rpe": athlete.average_session_rpe,
                "training_load": athlete.weekly_training_load if athlete.weekly_training_load is not None else athlete.training_load,
                "fatigue_level": athlete.current_fatigue_level,
                "has_injury_history": athlete.has_injury_history,
            }

        # 4. Fetch 5-factor breakdown if computed
        try:
            risk_svc = RiskScoringService()
            breakdown = risk_svc.get_breakdown(analysis_id, db)
            training_data["s_bio"] = breakdown.s_bio
            training_data["s_hist"] = breakdown.s_hist
            training_data["s_asym"] = breakdown.s_asym
            training_data["s_load"] = breakdown.s_load
            training_data["s_fatigue"] = breakdown.s_fatigue
        except Exception:  # noqa: BLE001
            pass

        # 5. Fetch Injury History
        injury_records: list[dict[str, Any]] = []
        if athlete:
            inj_rows = db.query(InjuryHistory).filter(InjuryHistory.athlete_id == athlete.athlete_id).all()
            for inj in inj_rows:
                injury_records.append({
                    "injury_type": inj.injury_type,
                    "body_part": inj.body_part,
                    "status": inj.status,
                    "injury_date": inj.injury_date.isoformat() if inj.injury_date else None,
                })

        return cls.generate_recommendations(
            features=features_dict,
            less_items=less_items,
            less_result=less_res_dict,
            risk_score=analysis.overall_risk_score,
            risk_level=analysis.risk_level,
            training_data=training_data,
            injury_records=injury_records,
            analysis_id=analysis.analysis_id,
            video_id=analysis.video_id,
        )
