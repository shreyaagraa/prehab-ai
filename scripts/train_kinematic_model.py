"""
scripts/train_kinematic_model.py
---------------------------------
Reproducible training pipeline for Kinematic Random Forest Model v2.

Generates a synthetic kinematic dataset based on biomechanical joint motion
distributions (ROM, inclination, asymmetry, velocities, displacements) to train,
evaluate, and export a versioned Random Forest classifier.

Target:
Biomechanical Deviation / Concurrent Injury Status Classification (0 = Normal, 1 = Deviated/Injured)

Artifacts produced:
- scripts/artifacts/biomechanical_deviation_classifier_v2.joblib
- scripts/artifacts/biomechanical_deviation_classifier_v2_metadata.json
"""
import json
import logging
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RANDOM_SEED = 42
N_SAMPLES = 1200

# 9 Explicit Video-Derived Kinematic Features
KINEMATIC_V2_FEATURE_COLUMNS = [
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


def generate_synthetic_kinematic_dataset(
    n_samples: int = N_SAMPLES,
    seed: int = RANDOM_SEED,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Generate synthetic kinematic features based on biomechanical literature distributions.

    Class 0 (Uninjured / Normal Biomechanics):
    - Balanced ROMs, low asymmetry (< 5 degrees), normal trunk lean (< 12 degrees).

    Class 1 (High Biomechanical Deviation / Injured):
    - Elevated joint asymmetry (8-20 degrees), restricted or excessive joint ROMs,
      increased trunk lean (> 15 degrees), altered movement velocities.
    """
    np.random.seed(seed)
    n_class0 = n_samples // 2
    n_class1 = n_samples - n_class0

    # Class 0: Uninjured / Low Deviation
    knee_rom_0 = np.random.normal(loc=52.0, scale=6.0, size=n_class0)
    hip_rom_0 = np.random.normal(loc=42.0, scale=5.0, size=n_class0)
    ankle_rom_0 = np.random.normal(loc=32.0, scale=4.0, size=n_class0)
    trunk_ang_0 = np.random.normal(loc=8.5, scale=2.5, size=n_class0)
    knee_asym_0 = np.random.exponential(scale=2.5, size=n_class0)
    hip_asym_0 = np.random.exponential(scale=2.0, size=n_class0)
    ankle_asym_0 = np.random.exponential(scale=1.8, size=n_class0)
    velocity_0 = np.random.normal(loc=2.2, scale=0.3, size=n_class0)
    displacement_0 = np.random.normal(loc=35.0, scale=5.0, size=n_class0)

    # Class 1: Deviated / Injured Status
    knee_rom_1 = np.random.choice([np.random.normal(35.0, 5.0), np.random.normal(68.0, 5.0)], size=n_class1).flatten()
    knee_rom_1 = np.random.normal(loc=40.0, scale=10.0, size=n_class1)
    hip_rom_1 = np.random.normal(loc=31.0, scale=8.0, size=n_class1)
    ankle_rom_1 = np.random.normal(loc=22.0, scale=6.0, size=n_class1)
    trunk_ang_1 = np.random.normal(loc=17.0, scale=4.5, size=n_class1)
    knee_asym_1 = np.random.normal(loc=11.5, scale=4.0, size=n_class1)
    hip_asym_1 = np.random.normal(loc=9.0, scale=3.5, size=n_class1)
    ankle_asym_1 = np.random.normal(loc=7.5, scale=3.0, size=n_class1)
    velocity_1 = np.random.normal(loc=1.5, scale=0.5, size=n_class1)
    displacement_1 = np.random.normal(loc=55.0, scale=10.0, size=n_class1)

    # Combine
    X_dict = {
        "knee_rom_mean": np.clip(np.concatenate([knee_rom_0, knee_rom_1]), 10.0, 120.0),
        "hip_rom_mean": np.clip(np.concatenate([hip_rom_0, hip_rom_1]), 10.0, 90.0),
        "ankle_rom_mean": np.clip(np.concatenate([ankle_rom_0, ankle_rom_1]), 5.0, 60.0),
        "trunk_angle_mean": np.clip(np.concatenate([trunk_ang_0, trunk_ang_1]), 0.0, 45.0),
        "knee_asymmetry": np.clip(np.abs(np.concatenate([knee_asym_0, knee_asym_1])), 0.0, 40.0),
        "hip_asymmetry": np.clip(np.abs(np.concatenate([hip_asym_0, hip_asym_1])), 0.0, 35.0),
        "ankle_asymmetry": np.clip(np.abs(np.concatenate([ankle_asym_0, ankle_asym_1])), 0.0, 30.0),
        "mean_joint_velocity": np.clip(np.concatenate([velocity_0, velocity_1]), 0.1, 10.0),
        "total_joint_displacement": np.clip(np.concatenate([displacement_0, displacement_1]), 1.0, 150.0),
    }

    y = np.concatenate([np.zeros(n_class0, dtype=int), np.ones(n_class1, dtype=int)])
    X = pd.DataFrame(X_dict, columns=KINEMATIC_V2_FEATURE_COLUMNS)

    return X, pd.Series(y, name="target")


def train_and_evaluate() -> None:
    logger.info("Generating synthetic kinematic dataset (N=%d, seed=%d)...", N_SAMPLES, RANDOM_SEED)
    X, y = generate_synthetic_kinematic_dataset(n_samples=N_SAMPLES, seed=RANDOM_SEED)

    # Train / Test Split (Stratified 80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_SEED, stratify=y
    )

    logger.info("Dataset shape: Train=%s, Test=%s", X_train.shape, X_test.shape)

    # Hyperparameters
    hyperparams = {
        "n_estimators": 200,
        "max_depth": 10,
        "min_samples_leaf": 5,
        "class_weight": "balanced",
        "random_state": RANDOM_SEED,
    }

    clf = RandomForestClassifier(**hyperparams)

    # Stratified K-Fold Cross-Validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    cv_scores = cross_val_score(clf, X_train, y_train, cv=cv, scoring="f1")
    logger.info("5-Fold CV F1 Scores: %s (Mean: %.4f, Std: %.4f)", cv_scores.round(4), cv_scores.mean(), cv_scores.std())

    # Fit final model
    clf.fit(X_train, y_train)

    # Evaluate on Test set
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    roc_auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred).tolist()

    logger.info("Test Evaluation:")
    logger.info("Accuracy:  %.4f", acc)
    logger.info("Precision: %.4f", prec)
    logger.info("Recall:    %.4f", rec)
    logger.info("F1 Score:  %.4f", f1)
    logger.info("Macro F1:  %.4f", macro_f1)
    logger.info("ROC-AUC:   %.4f", roc_auc)
    logger.info("Confusion Matrix: %s", cm)

    # Feature Importances
    importances = dict(zip(KINEMATIC_V2_FEATURE_COLUMNS, clf.feature_importances_.round(4).tolist()))
    logger.info("Feature Importances: %s", importances)

    # Save Model Artifact
    artifact_dir = Path(__file__).resolve().parent / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    model_path = artifact_dir / "biomechanical_deviation_classifier_v2.joblib"
    joblib.dump(clf, model_path)
    logger.info("Saved v2 model artifact to %s", model_path)

    # Save Metadata JSON
    metadata = {
        "model_version": "v2.0.0",
        "model_type": "RandomForestClassifier",
        "training_date": datetime.utcnow().isoformat() + "Z",
        "feature_names": KINEMATIC_V2_FEATURE_COLUMNS,
        "feature_order": KINEMATIC_V2_FEATURE_COLUMNS,
        "target_definition": "Biomechanical deviation / concurrent injury-status classification",
        "dataset_name": "Synthetic Kinematic Dataset v2",
        "sample_count": len(X),
        "class_distribution": {"0": int((y == 0).sum()), "1": int((y == 1).sum())},
        "evaluation_metrics": {
            "accuracy": round(acc, 4),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "macro_f1": round(macro_f1, 4),
            "roc_auc": round(roc_auc, 4),
        },
        "cv_f1_mean": round(cv_scores.mean(), 4),
        "cv_f1_std": round(cv_scores.std(), 4),
        "confusion_matrix": cm,
        "feature_importances": importances,
        "random_seed": RANDOM_SEED,
        "hyperparameters": {k: str(v) if not isinstance(v, (int, float, bool, str)) else v for k, v in hyperparams.items()},
        "is_synthetic": True,
        "limitations": (
            "The model was trained and evaluated using a synthetic dataset generated from "
            "biomechanical reference distributions and therefore reported performance does not establish "
            "clinical validity. This is a prototype risk-assessment system and is not a medical diagnosis "
            "or clinically validated injury prediction system."
        ),
    }

    metadata_path = artifact_dir / "biomechanical_deviation_classifier_v2_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Saved v2 model metadata to %s", metadata_path)


if __name__ == "__main__":
    train_and_evaluate()
