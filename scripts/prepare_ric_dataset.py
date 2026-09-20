"""
scripts/prepare_ric_dataset.py
-------------------------------
Offline ML preprocessing and baseline training script for the
Running Injury Clinic (RIC) Kinematic Dataset.

IMPORTANT — FRAMING DISCLAIMER
-------------------------------
The model trained by this script is a **Biomechanical Deviation Classifier**,
NOT a prospective injury predictor.

RIC subjects were assessed at the Running Injury Clinic while already injured
or as healthy controls.  Kinematics observed during active pain may reflect
pain-avoidance (antalgic) gait rather than pre-existing causal risk factors.
The model discriminates demographic + running-load profiles associated with
concurrent clinical injury status.  This is a valid use case that maps
directly to the Biomechanical Deviations (35%) component of the Risk Scoring
Engine — but must NEVER be marketed as predicting future injury events.

Usage
-----
Run from the project root (outside the backend virtualenv):

    python scripts/prepare_ric_dataset.py \\
        --data-path scratch/ric/run_data_meta.csv \\
        --output-dir scripts/artifacts \\
        --random-seed 42 \\
        --test-size 0.20

All paths are configurable; defaults are environment-variable driven so the
script works in CI without hardcoded machine-specific paths.

Environment Variables (override CLI defaults)
---------------------------------------------
    RIC_DATA_PATH     Path to run_data_meta.csv
    RIC_OUTPUT_DIR    Output directory for artifacts
    RIC_RANDOM_SEED   Integer random seed (default 42)
    RIC_TEST_SIZE     Float test fraction (default 0.20)
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ── Add project root to path so ric_preprocessing is importable ───────────────
_SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS_DIR))

import ric_preprocessing as prep  # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("prepare_ric_dataset")

# ── Defaults (overridable via env or CLI) ─────────────────────────────────────

_DEFAULT_DATA_PATH = os.environ.get(
    "RIC_DATA_PATH",
    str(Path(__file__).resolve().parent.parent / "scratch" / "ric" / "run_data_meta.csv"),
)
_DEFAULT_OUTPUT_DIR = os.environ.get(
    "RIC_OUTPUT_DIR",
    str(Path(__file__).resolve().parent / "artifacts"),
)
_DEFAULT_SEED  = int(os.environ.get("RIC_RANDOM_SEED", "42"))
_DEFAULT_TSIZE = float(os.environ.get("RIC_TEST_SIZE", "0.20"))


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare RIC dataset and train a Biomechanical Deviation Classifier "
            "(NOT a prospective injury predictor)."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-path",
        default=_DEFAULT_DATA_PATH,
        help="Path to RIC run_data_meta.csv.",
    )
    parser.add_argument(
        "--output-dir",
        default=_DEFAULT_OUTPUT_DIR,
        help="Directory where artifacts are saved.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=_DEFAULT_SEED,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=_DEFAULT_TSIZE,
        help="Fraction of subjects held out for testing.",
    )
    parser.add_argument(
        "--label",
        choices=["binary", "4class"],
        default="binary",
        help="Label type to use for training.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        default=False,
        help="Skip saving artifacts (useful for CI tests).",
    )
    return parser.parse_args()


# ── Core Pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(
    data_path: str,
    output_dir: str,
    random_seed: int = 42,
    test_size: float = 0.20,
    label_type: str = "binary",
    save_artifacts: bool = True,
) -> dict:
    """
    Execute the full preprocessing + training pipeline.

    Parameters
    ----------
    data_path : str
        Absolute/relative path to run_data_meta.csv.
    output_dir : str
        Directory where artifacts are written.
    random_seed : int
        Seed for GroupShuffleSplit and RandomForestClassifier.
    test_size : float
        Fraction of subjects in the test split.
    label_type : str
        'binary' or '4class'.
    save_artifacts : bool
        Write CSV/JSON/joblib outputs if True.

    Returns
    -------
    dict
        Full metrics dictionary (also saved to metrics.json if save_artifacts=True).
    """
    logger.info("=" * 60)
    logger.info("RIC Biomechanical Deviation Classifier — Training Pipeline")
    logger.info("=" * 60)
    logger.info("FRAMING: This is a concurrent-injury deviation CLASSIFIER,")
    logger.info("         NOT a prospective injury event predictor.")
    logger.info("=" * 60)

    # ── 1. Load data ──────────────────────────────────────────────────────────
    logger.info("Step 1: Loading data from %s", data_path)
    df_raw = prep.load_metadata(data_path)
    logger.info("  Raw shape: %s", df_raw.shape)

    # ── 2. Encode labels ──────────────────────────────────────────────────────
    logger.info("Step 2: Encoding labels (label_type=%s)", label_type)
    if label_type == "binary":
        labels = prep.encode_label_binary(df_raw)
        label_col = prep.BINARY_LABEL_COL
        label_map = {0: "Healthy (No Injury)", 1: "Injured"}
    else:
        labels = prep.encode_label_4class(df_raw)
        label_col = prep.LABEL_4CLASS_COL
        label_map = prep.LABEL_4CLASS_MAP

    df_raw[label_col] = labels

    # ── 3. Build feature matrix ───────────────────────────────────────────────
    logger.info("Step 3: Building feature matrix")
    X, y, groups = prep.build_feature_matrix(df_raw, label_col=label_col)
    logger.info("  Feature matrix shape: %s, Features: %s", X.shape, list(X.columns))

    train_dist = prep.get_class_distribution(y, label_map)
    logger.info("  Full dataset class distribution: %s", train_dist["counts"])

    # ── 4. Subject-level split (BEFORE fitting any transformer) ───────────────
    logger.info(
        "Step 4: Subject-level train/test split "
        "(test_size=%.0f%%, seed=%d)",
        test_size * 100, random_seed,
    )
    X_train, X_test, y_train, y_test = prep.subject_level_split(
        X, y, groups,
        test_size=test_size,
        random_state=random_seed,
    )

    train_class_dist = prep.get_class_distribution(y_train, label_map)
    test_class_dist  = prep.get_class_distribution(y_test,  label_map)
    logger.info("  Train class distribution: %s", train_class_dist["counts"])
    logger.info("  Test  class distribution: %s", test_class_dist["counts"])

    # ── 5. Build sklearn pipeline (median imputation → StandardScaler → RF) ───
    logger.info("Step 5: Building and training RandomForest baseline")
    logger.info("  Pipeline: MedianImputer → StandardScaler → RandomForestClassifier")
    logger.info(
        "  RandomForest: n_estimators=200, class_weight='balanced', "
        "random_state=%d",
        random_seed,
    )

    sklearn_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("clf",     RandomForestClassifier(
            n_estimators=200,
            max_depth=None,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=random_seed,
            n_jobs=-1,
        )),
    ])

    sklearn_pipeline.fit(X_train, y_train)
    logger.info("  Training complete.")

    # ── 6. Evaluate ───────────────────────────────────────────────────────────
    logger.info("Step 6: Evaluating on held-out test set")
    y_pred = sklearn_pipeline.predict(X_test)
    y_proba = sklearn_pipeline.predict_proba(X_test)

    acc   = float(accuracy_score(y_test, y_pred))
    prec  = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    rec   = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    f1    = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    # ROC-AUC: binary → single score; multiclass → OvR macro
    try:
        if label_type == "binary":
            roc_auc = float(roc_auc_score(y_test, y_proba[:, 1]))
        else:
            roc_auc = float(
                roc_auc_score(y_test, y_proba, multi_class="ovr", average="macro")
            )
    except ValueError as exc:
        logger.warning("ROC-AUC computation failed: %s", exc)
        roc_auc = None

    cm = confusion_matrix(y_test, y_pred).tolist()
    clf_report = classification_report(
        y_test, y_pred, zero_division=0, output_dict=True
    )

    logger.info("  Accuracy:        %.4f", acc)
    logger.info("  Precision (mac): %.4f", prec)
    logger.info("  Recall (mac):    %.4f", rec)
    logger.info("  F1-score (mac):  %.4f", f1)
    logger.info("  ROC-AUC:         %s", f"{roc_auc:.4f}" if roc_auc is not None else "N/A")
    logger.info("  Confusion Matrix:\n%s", np.array(cm))

    # ── 7. Feature importances ────────────────────────────────────────────────
    rf_model = sklearn_pipeline.named_steps["clf"]
    importances = rf_model.feature_importances_
    feature_importance_list = [
        {
            "feature": feat,
            "v1_mapping": prep.FEATURE_TO_V1_MAP.get(feat, feat),
            "importance": round(float(imp), 5),
        }
        for feat, imp in sorted(
            zip(prep.FEATURE_COLUMNS, importances),
            key=lambda t: -t[1],
        )
    ]

    logger.info("  Feature Importances (sorted):")
    for fi in feature_importance_list:
        logger.info("    %-18s -> %-50s %.5f", fi["feature"], fi["v1_mapping"], fi["importance"])

    # ── 8. Compose full metrics dict ──────────────────────────────────────────
    metrics: dict = {
        "model_framing": (
            "Biomechanical Deviation Classifier — "
            "concurrent-injury status discriminator. "
            "NOT a prospective injury event predictor."
        ),
        "feature_version": prep.FEATURE_VERSION,
        "label_type": label_type,
        "random_seed": random_seed,
        "test_size": test_size,
        "n_features": len(prep.FEATURE_COLUMNS),
        "features_used": prep.FEATURE_COLUMNS,
        "feature_v1_mapping": prep.FEATURE_TO_V1_MAP,
        "n_train": int(len(X_train)),
        "n_test":  int(len(X_test)),
        "train_class_distribution": train_class_dist,
        "test_class_distribution": test_class_dist,
        "accuracy":       round(acc,  4),
        "precision_macro": round(prec, 4),
        "recall_macro":    round(rec,  4),
        "f1_macro":        round(f1,   4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "confusion_matrix": cm,
        "classification_report": clf_report,
        "feature_importances": feature_importance_list,
        "sklearn_pipeline": str(sklearn_pipeline),
        "model_notes": (
            "Features are demographic metadata from run_data_meta.csv. "
            "The full kinematic dv_r features (peak_knee_flexion, knee_rom, etc.) "
            "from per-subject JSON files are not yet integrated — see "
            "docs/milestone3_ml_architecture.md Section 3 for the mapping table."
        ),
    }

    # ── 9. Save artifacts ─────────────────────────────────────────────────────
    if save_artifacts:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Save processed feature matrix (train + test combined with split labels)
        X_with_label = X.copy()
        X_with_label[label_col] = y.values
        split_col = pd.Series("train", index=X.index, name="split")
        split_col.iloc[X.index.get_indexer(X_test.index)] = "test"
        X_with_label["split"] = split_col.values
        csv_path = out_dir / "ric_features.csv"
        X_with_label.to_csv(csv_path, index=False)
        logger.info("  Saved feature CSV to %s", csv_path)

        # Save metrics JSON
        metrics_path = out_dir / "ric_ml_metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, default=str)
        logger.info("  Saved metrics JSON to %s", metrics_path)

        # Save trained pipeline
        try:
            import joblib  # noqa: PLC0415
            model_path = out_dir / "biomechanical_deviation_classifier_v1.joblib"
            joblib.dump(sklearn_pipeline, model_path)
            logger.info("  Saved model to %s", model_path)
            metrics["model_path"] = str(model_path)
        except ImportError:  # pragma: no cover
            logger.warning("joblib not available; model not saved.")

    logger.info("=" * 60)
    logger.info("Pipeline complete.")
    logger.info("=" * 60)

    return metrics


# ── Entry Point ───────────────────────────────────────────────────────────────

def main() -> None:
    args = _parse_args()
    run_pipeline(
        data_path=args.data_path,
        output_dir=args.output_dir,
        random_seed=args.random_seed,
        test_size=args.test_size,
        label_type=args.label,
        save_artifacts=not args.no_save,
    )


if __name__ == "__main__":
    main()
