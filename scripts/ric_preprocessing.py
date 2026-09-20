"""
scripts/ric_preprocessing.py
-----------------------------
Pure-function preprocessing utilities for the RIC (Running Injury Clinic)
Kinematic Dataset metadata.

This module is intentionally side-effect-free: all functions accept DataFrames
and return DataFrames/arrays/dicts.  No file I/O is performed here.

Framing
-------
The ML model trained by ``prepare_ric_dataset.py`` is a
**Biomechanical Deviation Classifier**, not a prospective injury predictor.

The RIC dataset contains concurrent clinical injury status: subjects were
assessed at the clinic while already injured (or as healthy controls).
Kinematics observed during active pain may reflect pain-avoidance (antalgic)
gait rather than pre-existing causal risk factors.

Models trained on this data discriminate between movement/demographic profiles
of clinically injured and uninjured runners — a valid and defensible use case
that maps directly to the ``S_bio`` (35%) component of the weighted Risk
Scoring Engine.

FeatureExtractor v1 Mapping
---------------------------
Available metadata features and their correspondence to FeatureExtractor v1:

| CSV Column   | FeatureExtractor v1 Equivalent   | Notes                              |
|:-------------|:---------------------------------|:-----------------------------------|
| age          | athletes.age                     | Direct demographic                 |
| Height       | athletes.height                  | Direct demographic (cm)            |
| Weight       | athletes.weight                  | Direct demographic (kg)            |
| Gender       | User profile sex                 | Encoded: 0=Male, 1=Female          |
| speed_r      | mean_joint_velocity (proxy)      | Running speed correlates with gait |
| YrsRunning   | athletes.years_running (future)  | Experience proxy                   |
| NumRaces     | Training load proxy              | Activity level indicator           |
| DominantLeg  | athletes.dominant_leg (future)   | Encoded: 0=Left, 1=Right           |
| Level        | Training load proxy              | Encoded: 0=Recreational, 1=Comp.   |

Note: The full kinematic dv_r features (peak_knee_flexion, knee_rom, etc.)
are stored in per-subject JSON files (~21.7 GB) which are not available in the
current local environment.  When those files are downloaded, extend
``build_feature_matrix()`` to join them by subject filename.

RIC Feature Schema → FeatureExtractor v1 Mapping (for future dv_r extension):
  peak_knee_flexion  → knee_angle_left_max / knee_angle_right_max
  knee_rom           → knee_angle_left_rom / knee_angle_right_rom
  trunk_lean         → trunk_angle_mean / trunk_angle_max
  step_width         → LESS item 7/8 stance_width_ratio
  joint_velocity     → max_joint_velocity / mean_joint_velocity
  joint_displacement → total_joint_displacement
  knee_symmetry      → knee_symmetry_score
  hip_symmetry       → hip_symmetry_score
  ankle_symmetry     → ankle_symmetry_score
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import LabelEncoder

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

FEATURE_VERSION = "v1"

# Columns used as input features
FEATURE_COLUMNS: list[str] = [
    "age",
    "Height",
    "Weight",
    "speed_r",
    "YrsRunning",
    "NumRaces",
    "Gender_enc",      # Encoded from Gender
    "DominantLeg_enc", # Encoded from DominantLeg
    "Level_enc",       # Encoded from Level
]

# Feature names in FeatureExtractor v1 vocabulary (proxy mapping for metadata)
FEATURE_TO_V1_MAP: dict[str, str] = {
    "age":            "athletes.age",
    "Height":         "athletes.height",
    "Weight":         "athletes.weight",
    "speed_r":        "mean_joint_velocity (proxy: running speed)",
    "YrsRunning":     "athletes.years_running (future schema field)",
    "NumRaces":       "training_load (activity-level proxy)",
    "Gender_enc":     "athletes.gender",
    "DominantLeg_enc":"athletes.dominant_leg (future schema field)",
    "Level_enc":      "athletes.level (recreational vs. competitive)",
}

# Binary label: 0 = No injury, 1 = Injured
BINARY_LABEL_COL = "label_binary"

# 4-class label
LABEL_4CLASS_COL = "label_4class"

LABEL_4CLASS_MAP: dict[int, str] = {
    0: "Healthy / No Injury",
    1: "Knee Disorders",
    2: "Overuse / Lateral Chain",
    3: "Lower Leg / Shin",
}

# InjDefn values that indicate no injury
_NO_INJURY_INJDEFN: frozenset[str] = frozenset({
    "no injury",
    "no injury,no injury",
})

# Mapping from normalised SpecInjury → 4-class label int
_SPEC_INJURY_4CLASS: dict[str, int] = {
    # Class 1 – Knee Disorders
    "patellofemoral pain syndrome": 1,
    "pfps": 1,
    "knee oa": 1,
    "osteoarthritis": 1,
    "oa": 1,
    "chondromalacia": 1,
    "patellar tendinopathy": 1,
    "patellar tendinitis": 1,
    "knee osteoarthritis": 1,
    "patellofemoral": 1,
    # Class 2 – Overuse / Lateral Chain
    "itb syndrome": 2,
    "itbs": 2,
    "it band syndrome": 2,
    "iliotibial band syndrome": 2,
    "achilles tendinopathy": 2,
    "achilles tendinitis": 2,
    "achilles tendon": 2,
    "plantar fasciitis": 2,
    "plantar fasciopathy": 2,
    # Class 3 – Lower Leg / Shin
    "shin splints": 3,
    "medial tibial stress syndrome": 3,
    "mtss": 3,
    "calf strain": 3,
    "calf muscle strain": 3,
    "calf": 3,
    "tibial stress": 3,
    "stress fracture": 3,
}


# ── Loading ───────────────────────────────────────────────────────────────────

def load_metadata(csv_path: str) -> pd.DataFrame:
    """
    Load the RIC run_data_meta.csv into a DataFrame.

    Parameters
    ----------
    csv_path : str
        Absolute or relative path to ``run_data_meta.csv``.

    Returns
    -------
    pd.DataFrame
        Raw DataFrame with all 26 original columns.
    """
    df = pd.read_csv(csv_path, na_values=["NaN", "N/A", "NA", "n/a", "", " "])
    logger.info("Loaded %d rows from %s", len(df), csv_path)
    return df


# ── Label Encoding ────────────────────────────────────────────────────────────

def encode_label_binary(df: pd.DataFrame) -> pd.Series:
    """
    Encode binary injury label from ``InjDefn`` column.

    Rules (from RIC README):
      - A subject is UNINJURED if InjDefn == 'No injury' AND
        InjJoint is 'No Injury' or empty AND SpecInjury is empty.
      - We apply the simplified rule: InjDefn normalised == 'no injury' → 0
      - All other non-null InjDefn values → 1 (injured)
      - Rows where InjDefn is null → NaN (to be dropped)

    Returns
    -------
    pd.Series
        Integer series: 0 (healthy), 1 (injured), NaN (missing).
    """
    inj_defn = df["InjDefn"].fillna("").str.lower().str.strip()

    # Also check InjJoint: if 'no injury' or 'no injury,no injury' → healthy
    inj_joint = df["InjJoint"].fillna("").str.lower().str.strip()

    def _classify(row_defn: str, row_joint: str) -> float:
        if not row_defn:
            return float("nan")
        defn_clean = row_defn.replace(",", " ").strip()
        # Primary rule: InjDefn says no injury
        if defn_clean in _NO_INJURY_INJDEFN or defn_clean == "no injury":
            return 0.0
        # Catch edge case: InjDefn missing but InjJoint is clearly no injury
        if not defn_clean and row_joint in ("no injury", "no injury,no injury"):
            return 0.0
        return 1.0

    labels = pd.Series(
        [_classify(d, j) for d, j in zip(inj_defn, inj_joint)],
        index=df.index,
        name=BINARY_LABEL_COL,
    )
    n_healthy = (labels == 0).sum()
    n_injured = (labels == 1).sum()
    n_missing = labels.isna().sum()
    logger.info(
        "Binary label: %d healthy, %d injured, %d missing/dropped",
        n_healthy, n_injured, n_missing,
    )
    return labels


def encode_label_4class(df: pd.DataFrame) -> pd.Series:
    """
    Encode 4-class disorder label from ``SpecInjury`` and ``InjDefn``.

    Classes:
      0 – Healthy / No Injury
      1 – Knee Disorders (PFPS, OA, patellar tendinopathy, chondromalacia)
      2 – Overuse / Lateral Chain (ITBS, Achilles tendinopathy, plantar fasciitis)
      3 – Lower Leg / Shin (shin splints, calf strain, MTSS)
      NaN – Unclassifiable injured (mapped to binary=1 but 4-class unknown)

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``InjDefn`` and ``SpecInjury`` columns.

    Returns
    -------
    pd.Series
        Integer (0–3) or NaN.
    """
    binary_labels = encode_label_binary(df)
    spec_injury = df["SpecInjury"].fillna("").str.lower().str.strip()

    results: list[float] = []
    for i, (binary_lbl, spec) in enumerate(zip(binary_labels, spec_injury)):
        if pd.isna(binary_lbl):
            results.append(float("nan"))
            continue
        if binary_lbl == 0:
            results.append(0.0)
            continue
        # binary_lbl == 1: try to map spec injury to class 1, 2, or 3
        matched_class: int | None = None
        for keyword, cls in _SPEC_INJURY_4CLASS.items():
            if keyword in spec:
                matched_class = cls
                break
        # Use InjJoint as fallback if SpecInjury is too vague
        if matched_class is None:
            inj_joint = str(df.iloc[i].get("InjJoint", "")).lower().strip()
            if "knee" in inj_joint:
                matched_class = 1
            elif "lower leg" in inj_joint or "ankle" in inj_joint:
                matched_class = 3
            elif "hip" in inj_joint or "thigh" in inj_joint:
                matched_class = 2

        results.append(float(matched_class) if matched_class is not None else float("nan"))

    series = pd.Series(results, index=df.index, name=LABEL_4CLASS_COL)
    logger.info(
        "4-class label distribution:\n%s",
        series.value_counts(dropna=False).to_string(),
    )
    return series


# ── Feature Engineering ───────────────────────────────────────────────────────

def encode_categorical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Encode categorical columns into numeric form.

    - Gender: 'Female' → 1, 'Male' → 0, other/missing → NaN
    - DominantLeg: 'Right' → 1, 'Left' → 0, other/missing → NaN
    - Level: 'Competitive' → 1, 'Recreational' → 0, other/missing → NaN

    Returns a copy of ``df`` with three new columns:
    ``Gender_enc``, ``DominantLeg_enc``, ``Level_enc``.
    """
    out = df.copy()

    gender_map = {"female": 1.0, "male": 0.0, "f": 1.0, "m": 0.0}
    out["Gender_enc"] = (
        df["Gender"].fillna("").str.lower().str.strip().map(gender_map)
    )

    leg_map = {"right": 1.0, "left": 0.0}
    out["DominantLeg_enc"] = (
        df["DominantLeg"].fillna("").str.lower().str.strip().map(leg_map)
    )

    level_map = {"competitive": 1.0, "recreational": 0.0}
    out["Level_enc"] = (
        df["Level"].fillna("").str.lower().str.strip().map(level_map)
    )

    return out


def build_feature_matrix(
    df: pd.DataFrame,
    label_col: str = BINARY_LABEL_COL,
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Build the feature matrix ``X``, label vector ``y``, and group vector
    ``groups`` from the cleaned/encoded DataFrame.

    Steps:
    1. Encode categoricals (Gender, DominantLeg, Level).
    2. Select FEATURE_COLUMNS.
    3. Drop rows where the target label is NaN.
    4. Return (X, y, groups) where groups = sub_id for leakage-safe splitting.

    Parameters
    ----------
    df : pd.DataFrame
        Must already have ``label_col`` and original RIC columns.
    label_col : str
        Column to use as target label.

    Returns
    -------
    X : pd.DataFrame  shape (n_samples, n_features)
    y : pd.Series     shape (n_samples,)  dtype int
    groups : pd.Series  shape (n_samples,)  subject IDs for GroupShuffleSplit
    """
    df_enc = encode_categorical_features(df)
    df_enc[label_col] = df[label_col]  # propagate label column

    # Drop rows with no label
    mask = df_enc[label_col].notna()
    df_clean = df_enc[mask].copy()
    logger.info(
        "build_feature_matrix: %d rows after dropping NaN labels (%d dropped)",
        len(df_clean), (~mask).sum(),
    )

    X = df_clean[FEATURE_COLUMNS].copy()
    y = df_clean[label_col].astype(int)
    groups = df_clean["sub_id"]

    return X, y, groups


# ── Leakage-Safe Splitting ────────────────────────────────────────────────────

def subject_level_split(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    test_size: float = 0.20,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Split data into train and test sets ensuring no subject appears in both.

    Uses ``sklearn.model_selection.GroupShuffleSplit`` with ``groups=sub_id``
    to guarantee subject-level holdout.  This is the primary leakage prevention
    mechanism: splitting by session (row) would leak subject identity because
    the same runner often has multiple sessions.

    Parameters
    ----------
    X : pd.DataFrame
        Feature matrix.
    y : pd.Series
        Label vector.
    groups : pd.Series
        Subject IDs (``sub_id``) parallel to X.
    test_size : float
        Fraction of **subjects** to hold out as test set.
    random_state : int
        Random seed for reproducibility.

    Returns
    -------
    X_train, X_test, y_train, y_test : DataFrames/Series
    """
    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups=groups))

    X_train = X.iloc[train_idx]
    X_test  = X.iloc[test_idx]
    y_train = y.iloc[train_idx]
    y_test  = y.iloc[test_idx]

    # Verify no subject appears in both splits
    train_subjects = set(groups.iloc[train_idx].unique())
    test_subjects  = set(groups.iloc[test_idx].unique())
    overlap = train_subjects & test_subjects
    if overlap:  # pragma: no cover
        raise RuntimeError(
            f"Subject leakage detected: {len(overlap)} subjects in both "
            f"train and test sets. This should never happen."
        )

    logger.info(
        "Subject-level split: %d train rows (%d subjects), "
        "%d test rows (%d subjects)",
        len(X_train), len(train_subjects),
        len(X_test),  len(test_subjects),
    )
    return X_train, X_test, y_train, y_test


# ── Preprocessing Pipeline ────────────────────────────────────────────────────

def get_class_distribution(y: pd.Series, label_map: dict[int, str] | None = None) -> dict[str, Any]:
    """
    Compute class distribution as counts and percentages.

    Parameters
    ----------
    y : pd.Series
        Integer label series.
    label_map : dict, optional
        Maps class int → human-readable string.

    Returns
    -------
    dict with keys 'counts', 'percentages', 'total', 'n_classes'
    """
    counts = y.value_counts().sort_index()
    total = len(y)
    result: dict[str, Any] = {
        "total": total,
        "n_classes": int(y.nunique()),
        "counts": {},
        "percentages": {},
    }
    for cls_int, cnt in counts.items():
        label = (label_map or {}).get(int(cls_int), str(cls_int))
        result["counts"][label] = int(cnt)
        result["percentages"][label] = round(100.0 * cnt / total, 1)
    return result
