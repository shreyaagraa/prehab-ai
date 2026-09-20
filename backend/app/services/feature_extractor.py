"""
app/services/feature_extractor.py
-----------------------------------
Biomechanical feature extraction service.

Calculates kinematic joint angles, displacement, approximate velocities,
range of motion (ROM), and left/right symmetry from stored pose_landmarks.

Features are aggregated into a deterministic feature dictionary with
`feature_version = "v1"`.

Topology indices (MediaPipe Pose):
  11: LEFT_SHOULDER,  12: RIGHT_SHOULDER
  23: LEFT_HIP,       24: RIGHT_HIP
  25: LEFT_KNEE,      26: RIGHT_KNEE
  27: LEFT_ANKLE,     28: RIGHT_ANKLE
  31: LEFT_FOOT_INDEX, 32: RIGHT_FOOT_INDEX
"""
from __future__ import annotations

import math
import uuid
from typing import Sequence
from sqlalchemy.orm import Session

from app.models.pose_landmark import PoseLandmark
from app.models.analysis_feature import AnalysisFeature

MIN_VISIBILITY = 0.5
FEATURE_VERSION = "v2"


def calculate_3d_angle(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
    p3: tuple[float, float, float],
) -> float | None:
    """
    Calculate 3D interior angle at vertex p2 formed by vectors (p1-p2) and (p3-p2).

    Parameters
    ----------
    p1, p2, p3 : tuple[float, float, float]
        (x, y, z) spatial coordinates.

    Returns
    -------
    float | None
        Angle in degrees [0.0, 180.0], or None if points are collinear/degenerate.
    """
    v1 = (p1[0] - p2[0], p1[1] - p2[1], p1[2] - p2[2])
    v2 = (p3[0] - p2[0], p3[1] - p2[1], p3[2] - p2[2])

    mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2 + v1[2] ** 2)
    mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2 + v2[2] ** 2)

    if mag1 < 1e-6 or mag2 < 1e-6:
        return None

    dot = v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]
    cos_theta = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return math.degrees(math.acos(cos_theta))


def calculate_trunk_angle(
    left_shoulder: tuple[float, float, float],
    right_shoulder: tuple[float, float, float],
    left_hip: tuple[float, float, float],
    right_hip: tuple[float, float, float],
) -> float | None:
    """
    Calculate trunk inclination angle from vertical (0, -1, 0 in image coordinates).
    """
    mid_shoulder = (
        (left_shoulder[0] + right_shoulder[0]) / 2.0,
        (left_shoulder[1] + right_shoulder[1]) / 2.0,
        (left_shoulder[2] + right_shoulder[2]) / 2.0,
    )
    mid_hip = (
        (left_hip[0] + right_hip[0]) / 2.0,
        (left_hip[1] + right_hip[1]) / 2.0,
        (left_hip[2] + right_hip[2]) / 2.0,
    )

    trunk_vec = (
        mid_shoulder[0] - mid_hip[0],
        mid_shoulder[1] - mid_hip[1],
        mid_shoulder[2] - mid_hip[2],
    )
    mag = math.sqrt(trunk_vec[0] ** 2 + trunk_vec[1] ** 2 + trunk_vec[2] ** 2)
    if mag < 1e-6:
        return None

    # Vertical vector pointing UP in image space (0, -1, 0)
    dot = trunk_vec[0] * 0.0 + trunk_vec[1] * (-1.0) + trunk_vec[2] * 0.0
    cos_theta = max(-1.0, min(1.0, dot / mag))
    return math.degrees(math.acos(cos_theta))


def calculate_symmetry_score(left_val: float | None, right_val: float | None) -> float | None:
    """
    Calculate symmetry score in percent [0.0, 100.0].
    Symmetry = 100 * (1 - |Left - Right| / max(Left, Right)).
    """
    if left_val is None or right_val is None:
        return None
    denom = max(abs(left_val), abs(right_val))
    if denom < 1e-6:
        return 100.0
    diff = abs(left_val - right_val)
    score = max(0.0, 100.0 * (1.0 - (diff / denom)))
    return round(score, 2)


class FeatureExtractor:
    """
    Service for calculating biomechanical features from PoseLandmark rows.
    """

    @classmethod
    def extract_features_from_landmarks(
        cls,
        landmarks: Sequence[PoseLandmark],
        min_visibility: float = MIN_VISIBILITY,
    ) -> dict[str, float | None]:
        """
        Group landmarks by frame_number and calculate kinematic metrics.

        Returns
        -------
        dict[str, float | None]
            Feature vector dictionary keyed by feature name.
        """
        # 1. Group landmarks by frame_number
        frames_map: dict[int, dict[int, PoseLandmark]] = {}
        frame_timestamps: dict[int, float] = {}

        for lm in landmarks:
            f_num = lm.frame_number
            if f_num not in frames_map:
                frames_map[f_num] = {}
                frame_timestamps[f_num] = lm.timestamp_ms
            frames_map[f_num][lm.landmark_index] = lm

        sorted_frames = sorted(frames_map.keys())

        # Collections for per-frame joint angles
        knee_left_angles: list[float] = []
        knee_right_angles: list[float] = []
        hip_left_angles: list[float] = []
        hip_right_angles: list[float] = []
        ankle_left_angles: list[float] = []
        ankle_right_angles: list[float] = []
        trunk_angles: list[float] = []

        # Tracking joint displacement and velocity for mid-hip
        displacements: list[float] = []
        velocities: list[float] = []

        prev_mid_hip: tuple[float, float, float] | None = None
        prev_time_s: float | None = None

        for f_num in sorted_frames:
            lm_dict = frames_map[f_num]

            def get_point(idx: int) -> tuple[float, float, float] | None:
                lm = lm_dict.get(idx)
                if lm is None or lm.visibility < min_visibility:
                    return None
                return (lm.x, lm.y, lm.z)

            # --- Knee Angles ---
            l_hip, l_knee, l_ankle = get_point(23), get_point(25), get_point(27)
            r_hip, r_knee, r_ankle = get_point(24), get_point(26), get_point(28)

            if l_hip and l_knee and l_ankle:
                ang = calculate_3d_angle(l_hip, l_knee, l_ankle)
                if ang is not None:
                    knee_left_angles.append(ang)

            if r_hip and r_knee and r_ankle:
                ang = calculate_3d_angle(r_hip, r_knee, r_ankle)
                if ang is not None:
                    knee_right_angles.append(ang)

            # --- Hip Angles ---
            l_sh, r_sh = get_point(11), get_point(12)
            if l_sh and l_hip and l_knee:
                ang = calculate_3d_angle(l_sh, l_hip, l_knee)
                if ang is not None:
                    hip_left_angles.append(ang)

            if r_sh and r_hip and r_knee:
                ang = calculate_3d_angle(r_sh, r_hip, r_knee)
                if ang is not None:
                    hip_right_angles.append(ang)

            # --- Ankle Angles ---
            l_foot, r_foot = get_point(31), get_point(32)
            if l_knee and l_ankle and l_foot:
                ang = calculate_3d_angle(l_knee, l_ankle, l_foot)
                if ang is not None:
                    ankle_left_angles.append(ang)

            if r_knee and r_ankle and r_foot:
                ang = calculate_3d_angle(r_knee, r_ankle, r_foot)
                if ang is not None:
                    ankle_right_angles.append(ang)

            # --- Trunk Angle ---
            if l_sh and r_sh and l_hip and r_hip:
                tr_ang = calculate_trunk_angle(l_sh, r_sh, l_hip, r_hip)
                if tr_ang is not None:
                    trunk_angles.append(tr_ang)

            # --- Kinematic Displacement & Velocity ---
            if l_hip and r_hip:
                curr_mid_hip = (
                    (l_hip[0] + r_hip[0]) / 2.0,
                    (l_hip[1] + r_hip[1]) / 2.0,
                    (l_hip[2] + r_hip[2]) / 2.0,
                )
                curr_time_s = frame_timestamps[f_num] / 1000.0

                if prev_mid_hip is not None and prev_time_s is not None:
                    dt = curr_time_s - prev_time_s
                    dist = math.sqrt(
                        (curr_mid_hip[0] - prev_mid_hip[0]) ** 2 +
                        (curr_mid_hip[1] - prev_mid_hip[1]) ** 2 +
                        (curr_mid_hip[2] - prev_mid_hip[2]) ** 2
                    )
                    displacements.append(dist)
                    if dt > 1e-4:
                        velocities.append(dist / dt)

                prev_mid_hip = curr_mid_hip
                prev_time_s = curr_time_s

        # Helper for aggregate metrics
        def stats(vals: list[float]) -> tuple[float | None, float | None, float | None, float | None]:
            if not vals:
                return None, None, None, None
            mn = round(sum(vals) / len(vals), 2)
            mi = round(min(vals), 2)
            ma = round(max(vals), 2)
            rom = round(ma - mi, 2)
            return mn, mi, ma, rom

        kl_mn, kl_mi, kl_ma, kl_rom = stats(knee_left_angles)
        kr_mn, kr_mi, kr_ma, kr_rom = stats(knee_right_angles)
        hl_mn, hl_mi, hl_ma, hl_rom = stats(hip_left_angles)
        hr_mn, hr_mi, hr_ma, hr_rom = stats(hip_right_angles)
        al_mn, al_mi, al_ma, al_rom = stats(ankle_left_angles)
        ar_mn, ar_mi, ar_ma, ar_rom = stats(ankle_right_angles)
        tr_mn, tr_mi, tr_ma, tr_rom = stats(trunk_angles)

        knee_sym = calculate_symmetry_score(kl_rom, kr_rom)
        hip_sym = calculate_symmetry_score(hl_rom, hr_rom)
        ankle_sym = calculate_symmetry_score(al_rom, ar_rom)

        total_disp = round(sum(displacements), 4) if displacements else 0.0
        max_vel = round(max(velocities), 4) if velocities else 0.0
        mean_vel = round(sum(velocities) / len(velocities), 4) if velocities else 0.0

        knee_rom_mn = round((kl_rom + kr_rom) / 2.0, 2) if kl_rom is not None and kr_rom is not None else (kl_rom or kr_rom)
        hip_rom_mn = round((hl_rom + hr_rom) / 2.0, 2) if hl_rom is not None and hr_rom is not None else (hl_rom or hr_rom)
        ankle_rom_mn = round((al_rom + ar_rom) / 2.0, 2) if al_rom is not None and ar_rom is not None else (al_rom or ar_rom)

        knee_asym = round(abs(kl_rom - kr_rom), 2) if kl_rom is not None and kr_rom is not None else None
        hip_asym = round(abs(hl_rom - hr_rom), 2) if hl_rom is not None and hr_rom is not None else None
        ankle_asym = round(abs(al_rom - ar_rom), 2) if al_rom is not None and ar_rom is not None else None

        feature_vector: dict[str, float | None] = {
            # Explicit V2 Kinematic Vector Features
            "knee_rom_mean": knee_rom_mn,
            "hip_rom_mean": hip_rom_mn,
            "ankle_rom_mean": ankle_rom_mn,
            "trunk_angle_mean": tr_mn,
            "knee_asymmetry": knee_asym,
            "hip_asymmetry": hip_asym,
            "ankle_asymmetry": ankle_asym,
            "mean_joint_velocity": mean_vel,
            "total_joint_displacement": total_disp,

            # Knee Detailed
            "knee_angle_left_mean": kl_mn,
            "knee_angle_left_min": kl_mi,
            "knee_angle_left_max": kl_ma,
            "knee_angle_left_rom": kl_rom,
            "knee_angle_right_mean": kr_mn,
            "knee_angle_right_min": kr_mi,
            "knee_angle_right_max": kr_ma,
            "knee_angle_right_rom": kr_rom,
            "knee_symmetry_score": knee_sym,

            # Hip Detailed
            "hip_angle_left_mean": hl_mn,
            "hip_angle_left_min": hl_mi,
            "hip_angle_left_max": hl_ma,
            "hip_angle_left_rom": hl_rom,
            "hip_angle_right_mean": hr_mn,
            "hip_angle_right_min": hr_mi,
            "hip_angle_right_max": hr_ma,
            "hip_angle_right_rom": hr_rom,
            "hip_symmetry_score": hip_sym,

            # Ankle Detailed
            "ankle_angle_left_mean": al_mn,
            "ankle_angle_left_min": al_mi,
            "ankle_angle_left_max": al_ma,
            "ankle_angle_left_rom": al_rom,
            "ankle_angle_right_mean": ar_mn,
            "ankle_angle_right_min": ar_mi,
            "ankle_angle_right_max": ar_ma,
            "ankle_angle_right_rom": ar_rom,
            "ankle_symmetry_score": ankle_sym,

            # Trunk Detailed
            "trunk_angle_min": tr_mi,
            "trunk_angle_max": tr_ma,
            "trunk_angle_rom": tr_rom,

            # Kinematics
            "max_joint_velocity": max_vel,
        }

        return feature_vector

    @classmethod
    def extract_and_save(
        cls,
        analysis_id: uuid.UUID,
        db: Session,
        min_visibility: float = MIN_VISIBILITY,
    ) -> AnalysisFeature | None:
        """
        Query pose_landmarks for analysis_id, compute features, and save AnalysisFeature.
        """
        landmarks = (
            db.query(PoseLandmark)
            .filter(PoseLandmark.analysis_id == analysis_id)
            .all()
        )
        if not landmarks:
            return None

        features_dict = cls.extract_features_from_landmarks(landmarks, min_visibility=min_visibility)

        # Upsert AnalysisFeature record
        feature_record = (
            db.query(AnalysisFeature)
            .filter(AnalysisFeature.analysis_id == analysis_id)
            .first()
        )
        if feature_record is None:
            feature_record = AnalysisFeature(
                feature_id=uuid.uuid4(),
                analysis_id=analysis_id,
                feature_version=FEATURE_VERSION,
                features=features_dict,
            )
            db.add(feature_record)
        else:
            feature_record.feature_version = FEATURE_VERSION
            feature_record.features = features_dict

        db.commit()
        db.refresh(feature_record)
        return feature_record
