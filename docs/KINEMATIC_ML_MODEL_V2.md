# Kinematic Random Forest ML Model v2 Documentation

## 1. Problem Definition
The Kinematic Random Forest ML Model v2 isolates biomechanical movement pattern evaluation from demographic/metadata variables (e.g., age, height, weight, gender, experience) and dynamic workload/fatigue indicators. It evaluates video-derived joint kinematic features (Range of Motion, trunk inclination, joint asymmetry, joint velocity, and total spatial displacement) to produce a normalized Biomechanical Deviation Score ($S_{bio} \in [0.0, 100.0]$) representing movement pattern deviation relative to normal reference cohorts.

> [!NOTE]
> **Clinical Disclaimer**: This is a prototype risk-assessment system and is not a medical diagnosis or clinically validated injury prediction system.

---

## 2. Dataset
- **Dataset Name**: Synthetic Kinematic Dataset v2
- **Sample Count**: 1,200 samples (600 Class 0 / 600 Class 1)
- **Data Source**: Generated from biomechanical literature reference distributions. Raw 3D motion capture files (~21.7 GB) from the original Running Injury Clinic (RIC) dataset were unavailable in the local environment; dataset generation parameters are explicitly documented.

> [!WARNING]
> **Synthetic Data Notice**: The model was trained and evaluated using synthetic data based on reference kinematic distributions and therefore reported performance does not establish clinical validity.

---

## 3. Label Definition
- **Target Label**: `0` = Uninjured / Normal Biomechanics, `1` = High Biomechanical Deviation / Concurrent Injury Status
- **Description**: Concurrent biomechanical deviation / injury-status classification. It measures present movement pattern differences, NOT prospective future injury prediction.

---

## 4. Feature Definitions (9 Video-Derived Features)

| Feature Name | Landmarks Used | Formula / Math Definition | Unit | Aggregation | Missing Behavior |
|---|---|---|---|---|---|
| `knee_rom_mean` | Hip (23,24), Knee (25,26), Ankle (27,28) | $(ROM_{knee,left} + ROM_{knee,right}) / 2.0$ | Degrees (°) | Mean | Null / Error if unavailable |
| `hip_rom_mean` | Shoulder (11,12), Hip (23,24), Knee (25,26) | $(ROM_{hip,left} + ROM_{hip,right}) / 2.0$ | Degrees (°) | Mean | Null / Error if unavailable |
| `ankle_rom_mean` | Knee (25,26), Ankle (27,28), Foot (31,32) | $(ROM_{ankle,left} + ROM_{ankle,right}) / 2.0$ | Degrees (°) | Mean | Null / Error if unavailable |
| `trunk_angle_mean` | Shoulder (11,12), Hip (23,24) | Inclination angle relative to image vertical $(0, -1, 0)$ | Degrees (°) | Mean | Null / Error if unavailable |
| `knee_asymmetry` | Knee ROMs | $|ROM_{knee,left} - ROM_{knee,right}|$ | Degrees (°) | Absolute Delta | Null / Error if unavailable |
| `hip_asymmetry` | Hip ROMs | $|ROM_{hip,left} - ROM_{hip,right}|$ | Degrees (°) | Absolute Delta | Null / Error if unavailable |
| `ankle_asymmetry` | Ankle ROMs | $|ROM_{ankle,left} - ROM_{ankle,right}|$ | Degrees (°) | Absolute Delta | Null / Error if unavailable |
| `mean_joint_velocity` | Mid-Hip trajectory over frames | $\frac{1}{N} \sum \frac{\Delta d}{\Delta t}$ | m/s (or spatial/s) | Mean Velocity | Null / Error if unavailable |
| `total_joint_displacement` | Mid-Hip trajectory over frames | $\sum \Delta d$ | meters (or spatial) | Sum | Null / Error if unavailable |

---

## 5. Training Pipeline
- **Script**: `scripts/train_kinematic_model.py`
- **Random Seed**: `42` (Deterministic)
- **Split**: 80% Train (960 samples) / 20% Test (240 samples), Stratified
- **Validation**: 5-Fold Stratified Cross-Validation (Mean CV F1: `0.9990`)

---

## 6. Model Architecture & Hyperparameters
- **Classifier**: `RandomForestClassifier`
- **Hyperparameters**:
  - `n_estimators`: 200
  - `max_depth`: 10
  - `min_samples_leaf`: 5
  - `class_weight`: `"balanced"`
  - `random_state`: 42

---

## 7. Evaluation Metrics

| Metric | Score |
|---|---|
| Test Accuracy | 1.0000 |
| Test Precision | 1.0000 |
| Test Recall | 1.0000 |
| Test F1 Score | 1.0000 |
| Macro F1 | 1.0000 |
| ROC-AUC | 1.0000 |

---

## 8. Feature Importances

| Feature | Importance |
|---|---|
| `total_joint_displacement` | 0.2844 |
| `knee_asymmetry` | 0.2409 |
| `trunk_angle_mean` | 0.1708 |
| `ankle_asymmetry` | 0.1145 |
| `hip_asymmetry` | 0.0958 |
| `ankle_rom_mean` | 0.0520 |
| `mean_joint_velocity` | 0.0157 |
| `hip_rom_mean` | 0.0142 |
| `knee_rom_mean` | 0.0117 |

---

## 9. Inference Pipeline & Missing-Data Behavior
1. **Video** → OpenCV frame extraction → MediaPipe Pose 33-landmark 3D tracking.
2. **Feature Extractor** (`FeatureExtractor.extract_features_from_landmarks`) calculates per-frame joint angles, ROMs, asymmetries, velocities, and displacements.
3. **Schema Validation** (`RiskScoringService.map_features`):
   - Validates all 9 explicit kinematic features exist, are numeric, and finite (`math.isfinite`).
   - If validation fails or video lacks required pose landmarks: Returns `(None, reason_str)` triggering `ML_UNAVAILABLE` state (`s_bio=None`, `s_bio_available=False`).
   - **No Artificial 50.0 Fallback**: Missing ML factor is dynamically excluded from 5-factor risk scoring engine via Dynamic Weight Renormalization.
4. **Biomechanical Score Calculation**:
   $$S_{bio} = \min(100.0, \max(0.0, P(\text{deviation}) \times 100.0))$$

---

## 10. Saved Model Artifacts
- **Model Binary**: `scripts/artifacts/biomechanical_deviation_classifier_v2.joblib`
- **Model Metadata**: `scripts/artifacts/biomechanical_deviation_classifier_v2_metadata.json`
- **Version**: `v2.0.0`
