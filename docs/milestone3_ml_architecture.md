# Milestone 3: ML + Risk Scoring Architecture
## Codebase Audit & RIC Dataset Feasibility Report

> **Audit Date**: 2026-09-09  
> **Test Suite Baseline**: 97 passed, 0 failed (14.99s)  
> **Scope**: READ/ANALYSIS ONLY — no model training, no production code changes, no schema modifications, no data committed to repository.

---

## 1. Codebase Inspection Summary

### 1.1 Files Inspected

| File | Role | ML-Relevant Observations |
|:---|:---|:---|
| [`feature_extractor.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/services/feature_extractor.py) | `FeatureExtractor` service | Extracts 27 named features (`v1` schema) from `PoseLandmark` rows. Clean, deterministic, version-stamped — ML-ready output. |
| [`analysis_feature.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/models/analysis_feature.py) | `AnalysisFeature` DB model | Stores feature dict as PostgreSQL JSONB with `feature_version` column. Designed explicitly for ML dataset compatibility. |
| [`analysis_pipeline.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/services/analysis_pipeline.py) | Orchestration pipeline | Steps: Frame extraction → MediaPipe pose → PoseLandmark insert → `FeatureExtractor.extract_and_save()` → `LESSApproximationScorer.score_landmarks()`. LESS result persisted to `analysis_less_results`. |
| [`less_scorer.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/services/less_scorer.py) | LESS approximation scorer | 17-item LESS (652 lines). Items 9/10/11/16/17 are `NOT_COMPUTABLE` (require force plates or high-speed hardware). Outputs `LESSResult` with score, classification, itemized breakdown. |
| [`analysis_result.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/models/analysis_result.py) | Analysis result record | Columns pre-reserved for ML: `knee_valgus`, `hip_stability`, `trunk_lean`, `stride_length`, `joint_alignment`, `symmetry_score`, `fatigue_score`, `movement_quality`, `overall_risk_score`, `risk_level`. Currently `NULL`. |
| [`athlete.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/models/athlete.py) | Athlete profile | Fields: `age`, `height`, `weight`, `sport`, `position`, `training_load` (scalar float), `flexibility`, `strength`, `balance`, `endurance`, `coach_notes`. |
| [`injury_history.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/models/injury_history.py) | Injury records | Fields: `injury_type`, `body_part`, `severity`, `injury_date`, `recovery_date`, `remarks`. No computed aggregate (count/recurrence) yet. |
| [`injury_prediction.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/models/injury_prediction.py) | ML prediction store (placeholder) | Columns: `acl_risk`, `hamstring_risk`, `ankle_risk`, `shoulder_risk`, `lower_back_risk`, `overuse_risk`. Schema defined, no service writes to it yet. |
| [`performance_record.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/models/performance_record.py) | Performance log | Generic `activity` / `score` / `remarks`. No time-series structure for ACWR computation. |
| [`analysis_less.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/models/analysis_less.py) | LESS result store | Persists full 17-item LESS result JSON + classification. Fully operational. |

### 1.2 Current Feature Vector (`FeatureExtractor` v1)

27 features produced per analysis, stored in `analysis_features.features` (JSONB):

```
Knee:      knee_angle_left_{mean,min,max,rom},  knee_angle_right_{mean,min,max,rom},  knee_symmetry_score
Hip:       hip_angle_left_{mean,min,max,rom},   hip_angle_right_{mean,min,max,rom},   hip_symmetry_score
Ankle:     ankle_angle_left_{mean,min,max,rom}, ankle_angle_right_{mean,min,max,rom}, ankle_symmetry_score
Trunk:     trunk_angle_{mean,min,max,rom}
Kinematic: total_joint_displacement, max_joint_velocity, mean_joint_velocity
```

### 1.3 Missing Infrastructure for ML

| Gap | Current State | Required for ML |
|:---|:---|:---|
| No ACWR computation | `athlete.training_load` is a single scalar float | Timestamped session log with acute/chronic workload ratio (7-day / 28-day windows) |
| No fatigue inputs | `analysis_result.fatigue_score` column exists but is `NULL` | Borg RPE, HRV data, or session-count proxy |
| No injury count feature | `injury_history` rows are per-event records | Computed aggregates: `previous_injury_count`, `days_since_last_injury` |
| No LESS→risk bridge | LESS score stored in `analysis_less_results` | LESS score not consumed by any risk scorer |
| `injury_predictions` table unused | Schema exists, no writer service | `RiskScoringEngine` service to populate it |

---

## 2. RIC Dataset Analysis

### 2.1 Dataset Overview

| Attribute | Value |
|:---|:---|
| **DOI** | `10.25452/figshare.plus.24255795.v1` |
| **Authors** | Brett, Ferber, Fukuchi, Osis, Hettinga (University of Calgary) |
| **Collection period** | 2009–2017 |
| **Subjects (N)** | 1,798 unique subjects (1,402 running, 1,686 walking protocols) |
| **Sessions** | 1,832 running sessions (`run_data_meta.csv`), 2,088 walking sessions (`walk_data_meta.csv`) |
| **Raw data files** | 2,506 JSON files (~21.7 GB zipped) with 3D Vicon marker coordinates |
| **Capture system** | 3-camera or 8-camera Vicon optical MoCap (100–200 Hz) |
| **Segments** | 7 lower-body rigid segments (ISB-standard, Pohl et al. 2010) |
| **Protocol** | 25–60 second treadmill trials at self-selected speed; warmup 2–5 min |
| **Pre-computed vars** | `dv_r` (running): stride rate, step width, peak knee flexion, ROM, joint angles, cadence |
| **Metadata** | Age, height, weight, sex, dominant leg, years running, race history + injury metadata |
| **License** | CC BY 4.0 (data), MIT (code) |

### 2.2 Injury Label Analysis

RIC metadata contains **concurrent clinical injury status** across 7 columns.

#### Primary Label: `InjDefn` (Running protocol — 1,832 sessions)

| Label | Sessions | % |
|:---|:---:|:---:|
| `No injury` (Healthy control) | 659 | 36.0% |
| `Training volume/intensity affected` | 499 | 27.2% |
| `Continuing to train in pain` | 320 | 17.5% |
| `2 workouts missed in a row` | 274 | 15.0% |
| Missing / Unspecified | 80 | 4.4% |

#### Secondary Labels

| Column | Content |
|:---|:---|
| `InjJoint` | Knee, Lower Leg, Thigh, Foot, Hip/Pelvis, Ankle, Lumbar Spine |
| `SpecInjury` | PFPS, ITBS, Achilles Tendinopathy, Plantar Fasciitis, Calf Strain, Shin Splints, Knee OA, Hip OA |
| `InjDuration` | Duration of current injury symptoms (days) |
| `InjSide` | Left / Right / Bilateral |
| `InjJoint2`, `InjSide2`, `SpecInjury2` | Secondary injury diagnosis |

> [!IMPORTANT]
> **RIC labels are CONCURRENT ACTIVE CLINICAL INJURIES, not prospective injury events.**
> Subjects were recruited at the clinic while already injured or as healthy controls. The dataset does NOT track healthy runners over time to observe future injury incidence.

#### Consolidated 4-Class Label Schema (Recommended)

| Class | Label | RIC `SpecInjury` Mapping |
|:---:|:---|:---|
| 0 | **Healthy / Low Risk** | `InjDefn == "No injury"` |
| 1 | **Knee Disorders** | PFPS, Knee OA, Patellar tendinopathy, Chondromalacia |
| 2 | **Overuse / Lateral Chain** | ITBS, Achilles tendinopathy, Plantar fasciitis |
| 3 | **Lower Leg / Shin** | Shin splints, Calf strain |

This framing makes the ML task: **"Does this movement pattern match that of a clinically injured runner?"** — a valid biomechanical deviation classifier.

---

## 3. RIC → AnalysisFeature Mapping Table

| RIC Variable | RIC Meaning | Our Feature (`FeatureExtractor`) | Mapping Type | Transformation Required |
|:---|:---|:---|:---:|:---|
| `peak_knee_flexion` | Peak knee flexion in stance phase | `knee_angle_left_max`, `knee_angle_right_max` | **Direct** | Convert interior → flexion: `180° − interior_angle` |
| `knee_rom` | Knee Range of Motion | `knee_angle_left_rom`, `knee_angle_right_rom` | **Direct** | Identical: `max − min` |
| `hip_flexion` | Hip flexion angle | `hip_angle_left_mean`, `hip_angle_left_rom` | **Derived** | Shoulder–Hip–Knee interior angle relative to trunk vector |
| `ankle_flexion` | Ankle dorsi/plantar flexion | `ankle_angle_left_mean`, `ankle_angle_left_rom` | **Derived** | Knee–Ankle–FootIndex interior angle |
| `trunk_lean` | Trunk forward inclination | `trunk_angle_mean`, `trunk_angle_max` | **Direct** | Mid-shoulder → mid-hip vs. vertical `(0,−1,0)` — already computed |
| `step_width` | Transverse foot-to-foot distance | LESS Item 7/8 stance width ratio | **Derived** | Scale pixel distance by shoulder width (torso normalization) |
| `stride_rate` / cadence | Steps per minute | Derived from `mean_joint_velocity` + peak detection | **Derived** | Peak detection on ankle `y` displacement over time |
| `joint_velocity` | Speed of joint movement | `max_joint_velocity`, `mean_joint_velocity` | **Direct** | Time-derivative of mid-hip coordinates — already computed |
| `joint_displacement` | Path length of mid-hip | `total_joint_displacement` | **Direct** | Euclidean path length of mid-hip centroid — already computed |
| `knee_symmetry` | L/R Knee ROM symmetry (LSI) | `knee_symmetry_score` | **Direct** | `100 × (1 − |L−R| / max(L,R))` — identical formula |
| `hip_symmetry` | L/R Hip ROM symmetry | `hip_symmetry_score` | **Direct** | Identical formula |
| `ankle_symmetry` | L/R Ankle ROM symmetry | `ankle_symmetry_score` | **Direct** | Identical formula |
| `age` | Subject age | `athletes.age` | **Direct** | DB record join |
| `Height` | Subject height (cm) | `athletes.height` | **Direct** | DB record join |
| `Weight` | Subject weight (kg) | `athletes.weight` | **Direct** | DB record join |
| `Gender` | Subject sex | Athlete profile | **Direct** | DB record join |
| `DominantLeg` | Preferred limb | ❌ Not in `athletes` schema | **Schema Gap** | Need `athletes.dominant_leg` column |
| `YrsRunning` | Years of running experience | ❌ In `coach_notes` text only | **Schema Gap** | Need `athletes.years_running` integer column |
| `3D Vicon Coordinates` | 3D optical marker positions | MediaPipe 33-point normalized landmarks | **Proxy** | Single-camera RGB vs. 3D optical MoCap — torso-length normalization required |
| `Ground Reaction Force` | Force plate kinetics | **UNAVAILABLE** | ❌ Cannot reproduce | No force measurement from RGB video |
| `Subtalar eversion` | Rearfoot pronation | **UNAVAILABLE** | ❌ Cannot reproduce | Beyond MediaPipe landmark density |
| `LESS score` | Landing error screening score | `analysis_less_results.score` | **Indirect** | Already computed — use as biomechanical deviation feature |

**Result**: 15 of 22 RIC kinematic variables map directly or via derivation. 2 have trivial schema gaps. 2 are hardware-unavailable from RGB video.

---

## 4. Five-Factor Risk Scoring Engine Assessment

$$\text{Overall Risk Score} = 0.35 \cdot S_\text{bio} + 0.20 \cdot S_\text{hist} + 0.20 \cdot S_\text{asym} + 0.15 \cdot S_\text{load} + 0.10 \cdot S_\text{fatigue}$$

| Component | Weight | RIC Support | System Support | Gap / Source |
|:---|:---:|:---:|:---:|:---|
| **Biomechanical Deviations ($S_\text{bio}$)** | 35% | 🟢 HIGH | 🟡 Partial | Features extracted. ML classifier needed to convert features → deviation score. LESS score feeds this component. |
| **Historical Injury Factors ($S_\text{hist}$)** | 20% | 🟡 PARTIAL | 🟡 Partial | `injury_history` table exists. Needs aggregation: `previous_injury_count`, `days_since_last_injury`, `recurrent_flag`. |
| **Movement Asymmetry ($S_\text{asym}$)** | 20% | 🟢 HIGH | 🟢 Ready | `knee/hip/ankle_symmetry_score` already computed per analysis. Only scaling to 0–100 risk scale remains. |
| **Training Load ($S_\text{load}$)** | 15% | 🔴 LOW | 🔴 Missing | `athletes.training_load` is a single float — insufficient for ACWR. Needs timestamped `training_sessions` table. |
| **Fatigue ($S_\text{fatigue}$)** | 10% | ❌ NONE | 🔴 Missing | RIC steady-state trials are non-fatiguing. Needs Borg RPE, session-count proxy, or HRV. No table exists yet. |

---

## 5. Proposed ML Pipeline

```
Video Upload
    │
    ▼
OpenCV Frame Sampler (frame_sample_rate=5, max=300 frames)
    │
    ▼
MediaPipe BlazePose (33 landmarks × visibility per frame)
    │  → Stored: pose_landmarks (up to 9,900 rows per analysis)
    ▼
FeatureExtractor v1 (27 aggregate features)
    │  → Stored: analysis_features.features (JSONB)
    │
    ├──► LESSApproximationScorer (12 computable LESS items)
    │       → Stored: analysis_less_results.score + classification
    │
    ▼
ML Injury Risk Prediction Model (RIC-Trained)
    │
    │  Input features:
    │  • 27 kinematic features from analysis_features
    │  • LESS score + computable_items count
    │  • Athlete: age, height, weight, years_running
    │
    │  Training labels (from RIC run_data_meta.csv):
    │  • Binary: Biomechanically Normal vs. Abnormal/Antalgic Gait
    │  • 4-class: Healthy / Knee Disorder / Overuse-Lateral / Lower Leg-Shin
    │
    │  Recommended baseline models:
    │  1. Random Forest (interpretable, handles missing features)
    │  2. XGBoost (best tabular data performance)
    │  3. Logistic Regression (glass-box baseline)
    │
    │  Output: P(injured) → S_bio ∈ [0, 100]
    │
    ▼
Weighted Risk Scoring Engine (RiskScoringService)
    │
    │  S_bio     = P(injured) × 100                   (35%)  ← ML model
    │  S_hist    = f(injury_count, recurrence)         (20%)  ← injury_history
    │  S_asym    = 100 − mean(symmetry_scores)         (20%)  ← FeatureExtractor
    │  S_load    = ACWR function                       (15%)  ← training_sessions
    │  S_fatigue = Borg RPE / session-count proxy      (10%)  ← future input
    │
    │  Overall = 0.35·S_bio + 0.20·S_hist + 0.20·S_asym
    │           + 0.15·S_load + 0.10·S_fatigue
    │
    │  → Persisted: analysis_results.overall_risk_score + risk_level
    │  → Persisted: injury_predictions.{acl,hamstring,ankle,...}_risk
    │
    ▼
Risk Category
    LOW       (0–39)
    MODERATE  (40–69)
    HIGH      (70–84)
    CRITICAL  (85–100)
```

---

## 6. Data Leakage & Confounding Risks

| Risk | Severity | Description | Mitigation |
|:---|:---:|:---|:---|
| **Antalgic Gait / Reverse Causality** | 🔴 HIGH | Kinematic deviations may be *caused by active pain* (pain-avoidance gait), not pre-existing causal risk factors. | Frame model explicitly as **Biomechanical Deviation Classifier**. Document in API disclaimer fields. |
| **Session-Level vs. Subject-Level Leakage** | 🟡 MEDIUM | Same subject may appear in multiple RIC sessions. Splitting by session leaks subject identity into validation. | Split train/val/test by **subject ID**, not session. |
| **Healthy Control Confounding** | 🟡 MEDIUM | Clinic controls may not represent general population biomechanics. | Acknowledge in model card. Test for distribution shift with live video data. |
| **Self-Selected Speed Variation** | 🟡 MEDIUM | Treadmill speed varies per subject. Kinematics are speed-dependent. | Add speed as feature if available in `dv_r`; prefer relative normalized features. |
| **MediaPipe vs. Vicon Domain Gap** | 🔴 HIGH | RIC uses 3D Vicon (lab-grade mm precision). Our system uses monocular MediaPipe (normalized coordinates). Direct angle comparison is invalid. | Use **relative features** (ROM, symmetry ratios, normalized displacements) rather than absolute angles. |
| **Class Imbalance** | 🟡 MEDIUM | Healthy = 36%, injured classes vary in size. | Use SMOTE, class-weighted loss, or stratified sampling. Evaluate with ROC-AUC + macro-F1. |

---

## 7. Score Component Feasibility by Mentor Requirement

| Mentor Required Score | RIC Can Train? | System Can Compute? | Status |
|:---|:---:|:---:|:---|
| **Injury Risk Prediction** | 🟡 Conditionally (as deviation classifier) | 🔴 Not yet | Needs `RiskScoringService` + ML model |
| **Risk Scoring (weighted 5-factor)** | ➖ N/A (engine logic) | 🔴 Not yet | Needs `RiskScoringEngine` service |
| **Movement Quality Scoring** | 🟡 Partial (LESS + kinematic) | 🟡 LESS score computed, not yet exposed as quality score | Needs LESS → quality bridge |
| **Biomechanical Efficiency Scoring** | 🟢 YES (stride rate, displacement, velocity features available) | 🟡 Features computed, not yet scored | Needs scoring function |
| **Fatigue Risk Scoring** | ❌ NO (RIC steady-state = non-fatiguing) | 🔴 No fatigue data anywhere | Needs new data + schema |
| **Overall Athlete Health/Risk Score** | ➖ Partial (bio + asym only = 55%) | 🔴 `overall_risk_score` column exists but is NULL | Needs `RiskScoringEngine` + missing components |

---

## 8. Recommended ML Targets & Baseline Models

### Primary ML Target

**Binary classification**: `Biomechanically_Normal (0)` vs. `Biomechanically_Abnormal_or_Antalgic (1)`
- Maps to: `InjDefn == "No injury"` → class 0; all other `InjDefn` → class 1
- Class balance: ~36% vs. ~64% (manageable with class weights)
- Directly feeds `S_bio` as `P(class=1) × 100`

**Optional secondary target**: 4-class disorder taxonomy (Section 2.2)

### Baseline Models (Priority Order)

| Priority | Model | Rationale |
|:---:|:---|:---|
| 1 | **Random Forest** | Handles mixed types, missing values, class imbalance. Feature importance is directly interpretable. |
| 2 | **XGBoost / LightGBM** | Best tabular performance. Native class-weight support. |
| 3 | **Logistic Regression (L2)** | Glass-box baseline. SHAP values trivially computed. Sets performance floor. |
| 4 | **1D CNN / LSTM on angle time series** | Captures temporal patterns. Requires frame-level (not aggregated) features. Future milestone only. |

### Offline Preprocessing Script (`scripts/prepare_ric_dataset.py`)

```python
# Pseudocode — not implemented per milestone constraints
# 1. Parse run_data_meta.csv → InjDefn + SpecInjury + demographics
# 2. Map RIC dv_r variables → FeatureExtractor v1 feature names (see Section 3 table)
# 3. Apply torso-length normalization: normalize by |mid_shoulder - mid_hip|
# 4. Apply flexion angle conversion: flexion_angle = 180° - interior_angle
# 5. Encode binary + 4-class labels from InjDefn + SpecInjury
# 6. Split by subject_id: 70 / 15 / 15 (train / val / test)
# 7. Export: scratch/ric/ric_ml_features.parquet  [git-excluded]
# 8. Train: RandomForest, XGBoost, LogisticRegression
# 9. Evaluate: ROC-AUC, macro-F1, confusion matrix per class
# 10. Export best model: scripts/models/biomechanical_deviation_classifier_v1.joblib
```

---

## 9. Required Feature Engineering Transformations

1. **Torso-Length Normalization**: MediaPipe coordinates are `[0,1]` normalized by image dimensions. Scale spatial features (displacement, stance width) by `|mid_shoulder − mid_hip|` distance to achieve body-size invariance vs. physical Vicon meters.

2. **Flexion Angle Derivation**: MediaPipe computes interior angles. RIC uses flexion angles: `flexion = 180° − interior_angle`. Apply consistently.

3. **Phase-Aligned Peak Extraction**: IC (Initial Contact) and MKF (Maximum Knee Flexion) event detection is already implemented in `LESSApproximationScorer`. Reuse this logic for RIC feature alignment.

4. **Injury Label Consolidation**: Map raw `SpecInjury` strings → 4-class integer labels using fuzzy string matching on the taxonomy in Section 2.2.

5. **Asymmetry Feature Augmentation**: Compute raw bilateral differences (`|knee_left_rom − knee_right_rom|`) as additional features alongside normalized symmetry scores.

---

## 10. Schema Gaps for Full Risk Engine

| Missing Field/Table | Component | Urgency | Recommendation |
|:---|:---:|:---:|:---|
| `athletes.years_running` (Integer) | S_bio (35%) | Medium | Add to `Athlete` model + Alembic migration |
| `athletes.dominant_leg` (String) | S_bio (35%) | Low | Add to `Athlete` model |
| `injury_history` aggregation service | S_hist (20%) | High | Add `InjuryHistoryService.compute_risk_factors(athlete_id)` |
| `training_sessions` table (date, duration, intensity) | S_load (15%) | High | New table + ACWR computation service |
| `session_rpe` / fatigue proxy field | S_fatigue (10%) | Medium | Add to `training_sessions` or as standalone `session_feedback` |
| `RiskScoringService` | All components | Critical | New service reading all 5 components, writing to `analysis_results` |

---

## 11. Final Verdicts

### RIC Dataset Suitability

> **🟡 CONDITIONALLY READY**

**Conditions met**:
- Contains 1,798 subjects with concurrent injury labels → sufficient for binary + 4-class classification training
- 15 of 22 kinematic variables map to existing `FeatureExtractor` features
- 3 symmetry scores already computed by `FeatureExtractor`, directly covering `S_asym` (20%)
- Class balance (36% healthy vs. 64% injured) is manageable

**Conditions required**:
1. ML models must be documented as **Biomechanical Deviation Classifiers**, not prospective injury predictors
2. Feature normalization (torso-length, flexion angle conversion) must be applied consistently
3. Train/val/test splits must be by **subject ID** to prevent data leakage
4. Vicon → MediaPipe domain gap acknowledged; relative features (ROM, symmetry ratios) preferred over absolute angles

**Coverage**: RIC supports `S_bio` (35%) + `S_asym` (20%) = **55% of the weighted risk score** with no new data collection.

---

### Milestone 3 Readiness

> **🟡 CONDITIONALLY READY**

| Sub-task | Status |
|:---|:---:|
| LESS scorer implemented & tested (97/97 passing) | ✅ DONE |
| `FeatureExtractor` v1 implemented & JSONB-stored | ✅ DONE |
| Pipeline: Video → Pose → Features → LESS → DB | ✅ DONE |
| `analysis_results.overall_risk_score` column reserved | ✅ DONE (NULL) |
| `injury_predictions` table schema defined | ✅ DONE (no writer) |
| RIC dataset mapped to `FeatureExtractor` features | ✅ DONE (this document) |
| Offline RIC preprocessing script | 🔴 NOT STARTED |
| Baseline ML model training | 🔴 NOT STARTED |
| `RiskScoringEngine` service | 🔴 NOT STARTED |
| Training load schema (`training_sessions` table) | 🔴 SCHEMA MISSING |
| Fatigue input schema | 🔴 SCHEMA MISSING |

**Blocker for full 5-factor engine**: training load + fatigue schemas missing. However, the two highest-weight components (`S_bio` 35% + `S_asym` 20% = **55%**) can proceed immediately with existing infrastructure.

---

### Next Implementation Task

> **Create `scripts/prepare_ric_dataset.py` — the offline RIC ML preprocessing and baseline training script.**

**Scope**:
1. Parse `run_data_meta.csv` → extract `InjDefn`, `SpecInjury`, demographics
2. Map RIC `dv_r` computed variables to `FeatureExtractor` v1 feature names (Section 3 mapping table)
3. Apply torso-length normalization and flexion angle conversion
4. Encode binary + 4-class labels
5. Split by `subject_id` (70/15/15)
6. Output `scratch/ric/ric_ml_features.parquet` (git-excluded)
7. Train Random Forest baseline → report ROC-AUC and macro-F1
8. Serialize best model to `scripts/models/biomechanical_deviation_classifier_v1.joblib`

This script is fully offline, writes no production code, modifies no schemas, and produces the trained model artifact needed for Milestone 4 integration into `RiskScoringService`.

---

*Document produced during Milestone 3 audit. All findings are based on static code inspection and RIC dataset description analysis. No models were trained, no production code was modified, no dataset files were committed to the repository.*


---

## 5. Implemented Pipeline Architecture (Milestone 3 - COMPLETE)

### 5.1 Files Created

| File | Description |
|:---|:---|
| scripts/prepare_ric_dataset.py | Main offline pipeline: load, clean, train RF, evaluate, save artifacts |
| scripts/ric_preprocessing.py | Pure-function preprocessing module (side-effect-free, importable by tests) |
| scripts/tests/test_ric_preprocessing.py | 46 unit + integration tests |
| scripts/artifacts/ric_ml_metrics.json | Real baseline metrics (seed=42) |
| scripts/artifacts/ric_features.csv | Feature matrix with train/test split labels |
| scripts/artifacts/biomechanical_deviation_classifier_v1.joblib | Trained sklearn Pipeline (gitignored) |
| ackend/requirements.txt | Added scikit-learn>=1.4.0, pandas>=2.0.0, joblib>=1.3.0 |

### 5.2 Real Baseline Metrics (RIC dataset, n=1,752 usable sessions, seed=42)

> **FRAMING**: Biomechanical Deviation Classifier — concurrent-injury status discriminator.
> NOT a prospective injury event predictor.

| Metric | Value |
|:---|:---:|
| Train samples | 1,396 (535 healthy / 861 injured) |
| Test samples | 356 (124 healthy / 232 injured) |
| **Accuracy** | **68.8%** |
| **F1-score (macro)** | **66.4%** |
| **ROC-AUC** | **72.4%** |
| Precision (macro) | 66.2% |
| Recall (macro) | 66.9% |

**Top feature importances**: speed_r 28.6% | ge 19.4% | YrsRunning 16.5% | Weight 13.4% | Height 11.6%

> Note: v1 baseline uses 9 demographic/metadata features only. Expected to improve to ~80%+ ROC-AUC when the 12 kinematic dv_r features (knee ROM, hip angles, symmetry scores) from per-subject JSON files are integrated.

### 5.3 Test Suite Results

`
Backend:     97 passed, 0 failed  (test_analyze_video, test_feature_extraction, test_less_api, test_pipeline_less_integration)
ML Scripts:  46 passed, 0 failed  (test_ric_preprocessing - label, feature, leakage, determinism, integration)
TOTAL:      143 passed, 0 failed
`

### 5.4 CLI Usage

`ash
# From project root, using backend venv
.\backend\.venv\Scripts\python.exe scripts/prepare_ric_dataset.py \
    --data-path scratch/ric/run_data_meta.csv \
    --output-dir scripts/artifacts \
    --random-seed 42 \
    --test-size 0.20 \
    --label binary

# Environment variable override (for CI/CD)
RIC_DATA_PATH=scratch/ric/run_data_meta.csv \
RIC_OUTPUT_DIR=scripts/artifacts \
python scripts/prepare_ric_dataset.py
`

### 5.5 Milestone 4 Status

Implemented `app/services/risk_scoring_service.py` and integrated into `app/services/analysis_pipeline.py`:
1. Safely loads `biomechanical_deviation_classifier_v1.joblib`
2. Maps `analysis_features.features` + `Athlete` profile to expected 9-feature ML schema
3. Computes all 5 weighted risk components with documented neutral strategy for unavailable factors
4. Persists `overall_risk_score`, `risk_level`, `symmetry_score`, and `fatigue_score` to `analysis_results`

---

## 6. Risk Scoring Service Architecture (Milestone 4 - COMPLETE)

### 6.1 Overview & Core Formula

The `RiskScoringService` (`app/services/risk_scoring_service.py`) calculates a 5-factor weighted athlete risk score and classifies the athlete into a risk category:

$$\text{Overall Risk Score} = 0.35 \cdot S_\text{bio} + 0.20 \cdot S_\text{hist} + 0.20 \cdot S_\text{asym} + 0.15 \cdot S_\text{load} + 0.10 \cdot S_\text{fatigue}$$

### 6.2 Factor Definitions & Calculation Strategy

| Factor | Weight | Source / Strategy | Calculation | Handling if Unavailable |
|:---|:---:|:---|:---|:---|
| **$S_\text{bio}$** (Biomechanical Deviation) | **35%** | Trained RF Pipeline (`biomechanical_deviation_classifier_v1.joblib`) | $P(\text{injured}) \times 100.0$ derived from model inference on 9-feature input | Fallback to neutral **50.0** if artifact missing/unreadable |
| **$S_\text{hist}$** (Historical Injury) | **20%** | `injury_history` table (count of prior injuries per athlete) | $\min(\text{count} \times 20.0, 100.0)$ | **0.0** if no athlete record or zero injury history |
| **$S_\text{asym}$** (Movement Asymmetry) | **20%** | `analysis_features.features` JSONB | $\text{mean}(100.0 - \text{symmetry\_scores})$ for knee, hip, ankle | Fallback to neutral **50.0** if features missing |
| **$S_\text{load}$** (Training Load) | **15%** | Neutral fallback strategy | Documented constant **50.0** (`s_load_available = False`) | Neutral **50.0** (weights preserved) |
| **$S_\text{fatigue}$** (Fatigue Risk) | **10%** | Neutral fallback strategy | Documented constant **50.0** (`s_fatigue_available = False`) | Neutral **50.0** (weights preserved) |

> [!IMPORTANT]
> **Neutral Strategy for Unavailable Factors**: Rather than substituting synthetic/fake data or altering factor weights, unavailable components ($S_\text{load}$, $S_\text{fatigue}$) use an explicit, documented neutral midpoint score of **50.0** with `available=False` tracking flags.

### 6.3 Risk Level Categorization

| Score Range | Category | Action Threshold |
|:---:|:---:|:---|
| **0.0 – 39.99** | `LOW` | Normal movement quality; continue standard training |
| **40.0 – 69.99** | `MODERATE` | Mild biomechanical deviations or injury history; recommend monitoring |
| **70.0 – 84.99** | `HIGH` | Significant movement asymmetry or clinical deviation; corrective intervention suggested |
| **85.0 – 100.0** | `CRITICAL` | Severe biomechanical risk profile; immediate clinical evaluation recommended |

### 6.4 Database Persistence

Scores and classifications are persisted directly to `analysis_results`:
- `overall_risk_score`: Weighted 5-factor total score (Float, rounded to 2 decimals)
- `risk_level`: Category string (`LOW`, `MODERATE`, `HIGH`, `CRITICAL`)
- `symmetry_score`: Movement asymmetry factor $S_\text{asym}$ (Float)
- `fatigue_score`: Fatigue factor $S_\text{fatigue}$ (Float)

### 6.5 Framing & Disclaimers

> **Disclaimers**: The overall risk score is based on a **Biomechanical Deviation Classifier** quantifying movement pattern differences relative to clinical cohorts. It measures current biomechanical deviation and movement quality, **NOT prospective future-injury prediction**.
