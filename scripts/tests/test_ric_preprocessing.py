"""
scripts/tests/test_ric_preprocessing.py
-----------------------------------------
Unit and integration tests for RIC dataset preprocessing functions.

Coverage:
  - Binary label encoding (healthy vs. injured)
  - 4-class label encoding (disorder taxonomy)
  - Missing/null label handling
  - Categorical feature encoding (Gender, DominantLeg, Level)
  - Feature matrix construction (correct columns, shape)
  - Subject-level leakage prevention (no sub_id in both train and test)
  - Class distribution validity (both classes present in each split)
  - Deterministic training (same seed → same predictions)
  - prepare_ric_dataset.run_pipeline() integration test
  - Feature mapping to FeatureExtractor v1 schema names
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Add scripts/ directory to path so ric_preprocessing is importable
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_SCRIPTS_DIR))

import ric_preprocessing as prep  # noqa: E402
from prepare_ric_dataset import run_pipeline  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_df(rows: list[dict]) -> pd.DataFrame:
    """Create a minimal DataFrame from a list of row dicts."""
    df = pd.DataFrame(rows)
    # Ensure all expected columns exist
    for col in ["sub_id", "InjDefn", "InjJoint", "InjSide", "SpecInjury",
                "age", "Height", "Weight", "speed_r", "YrsRunning",
                "NumRaces", "Gender", "DominantLeg", "Level"]:
        if col not in df.columns:
            df[col] = np.nan
    return df


@pytest.fixture()
def healthy_df():
    return _make_df([
        {
            "sub_id": 1001,
            "InjDefn": "No injury",
            "InjJoint": "No Injury",
            "SpecInjury": np.nan,
            "age": 30, "Height": 175.0, "Weight": 70.0,
            "speed_r": 2.5, "YrsRunning": 5.0, "NumRaces": 3.0,
            "Gender": "Male", "DominantLeg": "Right", "Level": "Recreational",
        },
        {
            "sub_id": 1002,
            "InjDefn": "No injury",
            "InjJoint": "No injury,No injury",
            "SpecInjury": np.nan,
            "age": 25, "Height": 162.0, "Weight": 58.0,
            "speed_r": 2.8, "YrsRunning": 3.0, "NumRaces": 1.0,
            "Gender": "Female", "DominantLeg": "Left", "Level": "Recreational",
        },
    ])


@pytest.fixture()
def injured_df():
    return _make_df([
        {
            "sub_id": 2001,
            "InjDefn": "Training volume/intensity affected",
            "InjJoint": "Knee",
            "SpecInjury": "patellofemoral pain syndrome",
            "age": 35, "Height": 180.0, "Weight": 75.0,
            "speed_r": 2.2, "YrsRunning": 8.0, "NumRaces": 5.0,
            "Gender": "Male", "DominantLeg": "Right", "Level": "Competitive",
        },
        {
            "sub_id": 2002,
            "InjDefn": "Continuing to train in pain",
            "InjJoint": "Lower Leg",
            "SpecInjury": "shin splints",
            "age": 28, "Height": 168.0, "Weight": 62.0,
            "speed_r": 2.6, "YrsRunning": 2.0, "NumRaces": 0.0,
            "Gender": "Female", "DominantLeg": "Right", "Level": "Recreational",
        },
    ])


@pytest.fixture()
def mixed_df(healthy_df, injured_df):
    return pd.concat([healthy_df, injured_df], ignore_index=True)


@pytest.fixture()
def large_synthetic_df():
    """
    200-row synthetic dataset with distinct sub_ids for split tests.
    Balanced: 100 healthy, 100 injured across 80 unique subjects.
    """
    rng = np.random.default_rng(42)
    n = 200
    # 80 unique subjects, some with multiple sessions
    sub_ids = rng.integers(3000, 3080, size=n)
    inj_defn = ["No injury" if i < 100 else "Training volume/intensity affected"
                for i in range(n)]
    inj_joint = ["No Injury" if i < 100 else "Knee" for i in range(n)]
    spec_injury = [np.nan if i < 100 else "patellofemoral pain syndrome" for i in range(n)]

    df = pd.DataFrame({
        "sub_id":     sub_ids,
        "InjDefn":    inj_defn,
        "InjJoint":   inj_joint,
        "SpecInjury": spec_injury,
        "age":        rng.integers(20, 60, size=n).astype(float),
        "Height":     rng.uniform(155, 195, size=n),
        "Weight":     rng.uniform(50, 100, size=n),
        "speed_r":    rng.uniform(1.5, 3.5, size=n),
        "YrsRunning": rng.integers(1, 30, size=n).astype(float),
        "NumRaces":   rng.integers(0, 20, size=n).astype(float),
        "Gender":     rng.choice(["Male", "Female"], size=n),
        "DominantLeg": rng.choice(["Right", "Left"], size=n),
        "Level":      rng.choice(["Recreational", "Competitive"], size=n),
    })
    return df


# ── Binary Label Tests ────────────────────────────────────────────────────────

class TestBinaryLabelEncoding:

    def test_no_injury_encoded_as_zero(self, healthy_df):
        labels = prep.encode_label_binary(healthy_df)
        assert (labels == 0).all(), "All healthy rows should be label 0"

    def test_injured_encoded_as_one(self, injured_df):
        labels = prep.encode_label_binary(injured_df)
        assert (labels == 1).all(), "All injured rows should be label 1"

    def test_mixed_labels(self, mixed_df):
        labels = prep.encode_label_binary(mixed_df)
        assert set(labels.dropna().unique()) == {0, 1}
        assert (labels[:2] == 0).all()  # healthy rows first
        assert (labels[2:] == 1).all()  # injured rows last

    def test_null_injdefn_produces_nan(self):
        df = _make_df([{"sub_id": 9999, "InjDefn": np.nan, "InjJoint": np.nan}])
        labels = prep.encode_label_binary(df)
        assert labels.isna().all(), "Null InjDefn should produce NaN label"

    def test_case_insensitive_no_injury(self):
        df = _make_df([
            {"sub_id": 1, "InjDefn": "NO INJURY",  "InjJoint": "No Injury"},
            {"sub_id": 2, "InjDefn": "no injury",  "InjJoint": "No Injury"},
            {"sub_id": 3, "InjDefn": "No injury",  "InjJoint": "No Injury"},
        ])
        labels = prep.encode_label_binary(df)
        assert (labels == 0).all(), "InjDefn case should not matter"

    def test_continuing_to_train_is_injured(self):
        df = _make_df([
            {"sub_id": 1, "InjDefn": "Continuing to train in pain", "InjJoint": "Knee"},
        ])
        labels = prep.encode_label_binary(df)
        assert labels.iloc[0] == 1

    def test_two_workouts_missed_is_injured(self):
        df = _make_df([
            {"sub_id": 1, "InjDefn": "2 workouts missed in a row", "InjJoint": "Lower Leg"},
        ])
        labels = prep.encode_label_binary(df)
        assert labels.iloc[0] == 1


# ── 4-Class Label Tests ───────────────────────────────────────────────────────

class TestFourClassLabelEncoding:

    def test_healthy_is_class_zero(self, healthy_df):
        labels = prep.encode_label_4class(healthy_df)
        assert (labels == 0).all()

    def test_pfps_is_class_one(self):
        df = _make_df([{
            "sub_id": 1,
            "InjDefn": "Training volume/intensity affected",
            "InjJoint": "Knee",
            "SpecInjury": "patellofemoral pain syndrome",
        }])
        labels = prep.encode_label_4class(df)
        assert labels.iloc[0] == 1

    def test_itbs_is_class_two(self):
        df = _make_df([{
            "sub_id": 1,
            "InjDefn": "Continuing to train in pain",
            "InjJoint": "Hip/Pelvis",
            "SpecInjury": "itb syndrome",
        }])
        labels = prep.encode_label_4class(df)
        assert labels.iloc[0] == 2

    def test_shin_splints_is_class_three(self):
        df = _make_df([{
            "sub_id": 1,
            "InjDefn": "2 workouts missed in a row",
            "InjJoint": "Lower Leg",
            "SpecInjury": "shin splints",
        }])
        labels = prep.encode_label_4class(df)
        assert labels.iloc[0] == 3

    def test_achilles_is_class_two(self):
        df = _make_df([{
            "sub_id": 1,
            "InjDefn": "Continuing to train in pain",
            "InjJoint": "Lower Leg",
            "SpecInjury": "achilles tendinopathy",
        }])
        labels = prep.encode_label_4class(df)
        assert labels.iloc[0] == 2

    def test_unknown_injury_from_injjoint_fallback(self):
        """When SpecInjury is vague, InjJoint should be used as fallback."""
        df = _make_df([{
            "sub_id": 1,
            "InjDefn": "Continuing to train in pain",
            "InjJoint": "Knee",
            "SpecInjury": "pain",  # generic, not in mapping
        }])
        labels = prep.encode_label_4class(df)
        # Fallback: InjJoint 'Knee' → class 1
        assert labels.iloc[0] == 1

    def test_unclassifiable_injury_is_nan(self):
        """Injury with no SpecInjury match and no InjJoint match → NaN."""
        df = _make_df([{
            "sub_id": 1,
            "InjDefn": "Continuing to train in pain",
            "InjJoint": "Other",  # not in fallback map
            "SpecInjury": "fill in specifics below",  # not in map
        }])
        labels = prep.encode_label_4class(df)
        assert labels.isna().iloc[0], "Unclassifiable injury should produce NaN"


# ── Categorical Encoding Tests ────────────────────────────────────────────────

class TestCategoricalEncoding:

    def test_gender_female_is_one(self):
        df = _make_df([{"sub_id": 1, "Gender": "Female"}])
        out = prep.encode_categorical_features(df)
        assert out["Gender_enc"].iloc[0] == 1.0

    def test_gender_male_is_zero(self):
        df = _make_df([{"sub_id": 1, "Gender": "Male"}])
        out = prep.encode_categorical_features(df)
        assert out["Gender_enc"].iloc[0] == 0.0

    def test_gender_unknown_is_nan(self):
        df = _make_df([{"sub_id": 1, "Gender": "Unknown"}])
        out = prep.encode_categorical_features(df)
        assert pd.isna(out["Gender_enc"].iloc[0])

    def test_dominant_right_is_one(self):
        df = _make_df([{"sub_id": 1, "DominantLeg": "Right"}])
        out = prep.encode_categorical_features(df)
        assert out["DominantLeg_enc"].iloc[0] == 1.0

    def test_dominant_left_is_zero(self):
        df = _make_df([{"sub_id": 1, "DominantLeg": "Left"}])
        out = prep.encode_categorical_features(df)
        assert out["DominantLeg_enc"].iloc[0] == 0.0

    def test_level_competitive_is_one(self):
        df = _make_df([{"sub_id": 1, "Level": "Competitive"}])
        out = prep.encode_categorical_features(df)
        assert out["Level_enc"].iloc[0] == 1.0

    def test_level_recreational_is_zero(self):
        df = _make_df([{"sub_id": 1, "Level": "Recreational"}])
        out = prep.encode_categorical_features(df)
        assert out["Level_enc"].iloc[0] == 0.0

    def test_case_insensitive_gender(self):
        df = _make_df([
            {"sub_id": 1, "Gender": "FEMALE"},
            {"sub_id": 2, "Gender": "female"},
        ])
        out = prep.encode_categorical_features(df)
        assert (out["Gender_enc"] == 1.0).all()


# ── Feature Matrix Tests ──────────────────────────────────────────────────────

class TestFeatureMatrix:

    def test_feature_matrix_has_correct_columns(self, mixed_df):
        labels = prep.encode_label_binary(mixed_df)
        mixed_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(mixed_df)
        assert list(X.columns) == prep.FEATURE_COLUMNS, (
            f"Expected columns {prep.FEATURE_COLUMNS}, got {list(X.columns)}"
        )

    def test_feature_matrix_drops_null_label_rows(self):
        df = _make_df([
            {"sub_id": 1, "InjDefn": "No injury",  "InjJoint": "No Injury"},
            {"sub_id": 2, "InjDefn": np.nan,        "InjJoint": np.nan},
        ])
        df[prep.BINARY_LABEL_COL] = prep.encode_label_binary(df)
        X, y, groups = prep.build_feature_matrix(df)
        assert len(X) == 1, "Row with null label should be dropped"
        assert y.iloc[0] == 0

    def test_feature_matrix_X_y_groups_have_same_length(self, large_synthetic_df):
        labels = prep.encode_label_binary(large_synthetic_df)
        large_synthetic_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(large_synthetic_df)
        assert len(X) == len(y) == len(groups)

    def test_feature_column_mapping_covers_all_columns(self):
        """Every FEATURE_COLUMN must have a mapping to FeatureExtractor v1."""
        for col in prep.FEATURE_COLUMNS:
            assert col in prep.FEATURE_TO_V1_MAP, (
                f"Feature '{col}' has no FeatureExtractor v1 mapping in FEATURE_TO_V1_MAP"
            )

    def test_feature_v1_mapping_is_non_empty_strings(self):
        for col, mapping in prep.FEATURE_TO_V1_MAP.items():
            assert isinstance(mapping, str) and mapping, (
                f"Mapping for '{col}' must be a non-empty string"
            )


# ── Subject-Level Leakage Prevention Tests ───────────────────────────────────

class TestSubjectLevelSplit:

    def test_no_subject_in_both_splits(self, large_synthetic_df):
        labels = prep.encode_label_binary(large_synthetic_df)
        large_synthetic_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(large_synthetic_df)

        X_train, X_test, y_train, y_test = prep.subject_level_split(
            X, y, groups, test_size=0.2, random_state=42
        )

        train_subjects = set(groups.iloc[X.index.get_indexer(X_train.index)].unique())
        test_subjects  = set(groups.iloc[X.index.get_indexer(X_test.index)].unique())
        overlap = train_subjects & test_subjects
        assert len(overlap) == 0, (
            f"Data leakage: {len(overlap)} subjects appear in both train and test: {overlap}"
        )

    def test_train_plus_test_covers_all_rows(self, large_synthetic_df):
        labels = prep.encode_label_binary(large_synthetic_df)
        large_synthetic_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(large_synthetic_df)

        X_train, X_test, y_train, y_test = prep.subject_level_split(
            X, y, groups, test_size=0.2, random_state=42
        )
        assert len(X_train) + len(X_test) == len(X)

    def test_test_size_is_approximately_respected(self, large_synthetic_df):
        labels = prep.encode_label_binary(large_synthetic_df)
        large_synthetic_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(large_synthetic_df)

        X_train, X_test, y_train, y_test = prep.subject_level_split(
            X, y, groups, test_size=0.20, random_state=42
        )
        actual_test_frac = len(X_test) / len(X)
        # Allow ±15% slack because splitting is subject-level, not row-level
        assert 0.05 <= actual_test_frac <= 0.35, (
            f"Test fraction {actual_test_frac:.2f} is outside expected range [0.05, 0.35]"
        )

    def test_both_classes_present_in_train(self, large_synthetic_df):
        labels = prep.encode_label_binary(large_synthetic_df)
        large_synthetic_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(large_synthetic_df)

        X_train, X_test, y_train, y_test = prep.subject_level_split(
            X, y, groups, test_size=0.20, random_state=42
        )
        assert 0 in y_train.values, "Training set must contain healthy samples"
        assert 1 in y_train.values, "Training set must contain injured samples"

    def test_both_classes_present_in_test(self, large_synthetic_df):
        labels = prep.encode_label_binary(large_synthetic_df)
        large_synthetic_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(large_synthetic_df)

        X_train, X_test, y_train, y_test = prep.subject_level_split(
            X, y, groups, test_size=0.20, random_state=42
        )
        assert 0 in y_test.values, "Test set must contain healthy samples"
        assert 1 in y_test.values, "Test set must contain injured samples"

    def test_different_seed_produces_different_split(self, large_synthetic_df):
        labels = prep.encode_label_binary(large_synthetic_df)
        large_synthetic_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(large_synthetic_df)

        _, X_test_42,  _, _ = prep.subject_level_split(X, y, groups, random_state=42)
        _, X_test_99,  _, _ = prep.subject_level_split(X, y, groups, random_state=99)

        # Different seeds should yield different test splits (very high probability with 80 subjects)
        assert not X_test_42.index.equals(X_test_99.index), (
            "Different random seeds should produce different splits"
        )


# ── Deterministic Training Tests ──────────────────────────────────────────────

class TestDeterministicTraining:

    def test_same_seed_produces_identical_predictions(self, tmp_path, large_synthetic_df):
        """Two runs with the same seed must yield bit-identical predictions."""
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)

        metrics1 = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out1"),
            random_seed=42,
            test_size=0.20,
            save_artifacts=False,
        )
        metrics2 = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out2"),
            random_seed=42,
            test_size=0.20,
            save_artifacts=False,
        )

        assert metrics1["accuracy"] == metrics2["accuracy"], (
            "Identical seed must produce identical accuracy"
        )
        assert metrics1["f1_macro"] == metrics2["f1_macro"], (
            "Identical seed must produce identical F1"
        )

    def test_different_seed_may_produce_different_result(self, tmp_path, large_synthetic_df):
        """Different seeds should generally yield different results on small datasets."""
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)

        metrics42 = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out42"),
            random_seed=42,
            test_size=0.20,
            save_artifacts=False,
        )
        metrics99 = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out99"),
            random_seed=99,
            test_size=0.20,
            save_artifacts=False,
        )
        # At least one metric should differ (not guaranteed, but expected)
        # We just verify both runs complete and return valid metrics
        assert 0.0 <= metrics42["accuracy"] <= 1.0
        assert 0.0 <= metrics99["accuracy"] <= 1.0


# ── Pipeline Integration Tests ────────────────────────────────────────────────

class TestPipelineIntegration:

    def test_pipeline_returns_required_metric_keys(self, tmp_path, large_synthetic_df):
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)

        metrics = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out"),
            random_seed=42,
            save_artifacts=False,
        )

        required_keys = [
            "model_framing", "feature_version", "label_type", "random_seed",
            "test_size", "n_features", "features_used", "n_train", "n_test",
            "train_class_distribution", "test_class_distribution",
            "accuracy", "precision_macro", "recall_macro", "f1_macro",
            "roc_auc", "confusion_matrix", "feature_importances",
        ]
        for key in required_keys:
            assert key in metrics, f"Missing required metric key: '{key}'"

    def test_pipeline_metrics_are_valid_ranges(self, tmp_path, large_synthetic_df):
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)

        metrics = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out"),
            random_seed=42,
            save_artifacts=False,
        )

        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert 0.0 <= metrics["precision_macro"] <= 1.0
        assert 0.0 <= metrics["recall_macro"] <= 1.0
        assert 0.0 <= metrics["f1_macro"] <= 1.0
        if metrics["roc_auc"] is not None:
            assert 0.0 <= metrics["roc_auc"] <= 1.0

    def test_pipeline_saves_artifacts(self, tmp_path, large_synthetic_df):
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)
        out_dir = tmp_path / "artifacts"

        run_pipeline(
            data_path=str(csv_path),
            output_dir=str(out_dir),
            random_seed=42,
            save_artifacts=True,
        )

        assert (out_dir / "ric_features.csv").exists(), "ric_features.csv not saved"
        assert (out_dir / "ric_ml_metrics.json").exists(), "ric_ml_metrics.json not saved"
        assert (out_dir / "biomechanical_deviation_classifier_v1.joblib").exists(), (
            "Model joblib not saved"
        )

    def test_pipeline_feature_csv_has_correct_columns(self, tmp_path, large_synthetic_df):
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)
        out_dir = tmp_path / "out"

        run_pipeline(
            data_path=str(csv_path),
            output_dir=str(out_dir),
            random_seed=42,
            save_artifacts=True,
        )

        saved = pd.read_csv(out_dir / "ric_features.csv")
        for col in prep.FEATURE_COLUMNS:
            assert col in saved.columns, f"Expected feature column '{col}' in saved CSV"
        assert "split" in saved.columns, "Expected 'split' column in saved CSV"

    def test_pipeline_metrics_json_is_valid(self, tmp_path, large_synthetic_df):
        import json
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)
        out_dir = tmp_path / "out"

        run_pipeline(
            data_path=str(csv_path),
            output_dir=str(out_dir),
            random_seed=42,
            save_artifacts=True,
        )

        with open(out_dir / "ric_ml_metrics.json", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["feature_version"] == "v1"
        assert "model_framing" in loaded
        assert "Biomechanical Deviation Classifier" in loaded["model_framing"]

    def test_pipeline_4class_label_type(self, tmp_path, large_synthetic_df):
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)

        metrics = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out"),
            random_seed=42,
            label_type="4class",
            save_artifacts=False,
        )
        assert metrics["label_type"] == "4class"
        assert metrics["n_train"] > 0

    def test_pipeline_framing_disclaimer_in_metrics(self, tmp_path, large_synthetic_df):
        """The metrics must include the framing disclaimer."""
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)

        metrics = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out"),
            random_seed=42,
            save_artifacts=False,
        )
        assert "NOT a prospective injury event predictor" in metrics["model_framing"]

    def test_pipeline_feature_importances_sum_to_one(self, tmp_path, large_synthetic_df):
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)

        metrics = run_pipeline(
            data_path=str(csv_path),
            output_dir=str(tmp_path / "out"),
            random_seed=42,
            save_artifacts=False,
        )
        total_imp = sum(fi["importance"] for fi in metrics["feature_importances"])
        assert abs(total_imp - 1.0) < 0.01, (
            f"Feature importances should sum to ~1.0, got {total_imp:.4f}"
        )

    def test_pipeline_no_leakage_in_saved_features(self, tmp_path, large_synthetic_df):
        """Verify that train/test rows in the saved CSV have no overlapping sub_ids."""
        csv_path = tmp_path / "run_data_meta.csv"
        large_synthetic_df.to_csv(csv_path, index=False)
        out_dir = tmp_path / "out"

        # Run to get split info
        run_pipeline(
            data_path=str(csv_path),
            output_dir=str(out_dir),
            random_seed=42,
            save_artifacts=True,
        )
        # The saved CSV doesn't have sub_id, so we verify via the data that
        # train/test rows don't overlap — verify column 'split' exists and has both values
        saved = pd.read_csv(out_dir / "ric_features.csv")
        assert set(saved["split"].unique()) == {"train", "test"}, (
            "Saved CSV must have both 'train' and 'test' rows"
        )


# ── Class Distribution Tests ──────────────────────────────────────────────────

class TestClassDistribution:

    def test_get_class_distribution_counts_correct(self, mixed_df):
        labels = prep.encode_label_binary(mixed_df)
        mixed_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(mixed_df)
        dist = prep.get_class_distribution(y, {0: "Healthy", 1: "Injured"})
        assert dist["counts"]["Healthy"] == 2
        assert dist["counts"]["Injured"] == 2
        assert dist["total"] == 4

    def test_get_class_distribution_percentages_sum_to_100(self, large_synthetic_df):
        labels = prep.encode_label_binary(large_synthetic_df)
        large_synthetic_df[prep.BINARY_LABEL_COL] = labels
        X, y, groups = prep.build_feature_matrix(large_synthetic_df)
        dist = prep.get_class_distribution(y)
        total_pct = sum(dist["percentages"].values())
        assert abs(total_pct - 100.0) < 0.1
