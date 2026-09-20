# Corrective Recommendation Engine v1

## 1. System Overview & Purpose

The **Corrective Recommendation Engine v1** is a deterministic, rule-based decision support system designed for **PreHab AI / Sports Injury Risk Detection**. It analyzes biomechanical kinematic features, Landing Error Scoring System (LESS) approximation findings, 5-factor risk sub-scores, athlete training workload, and fatigue levels to generate personalized, explainable corrective action plans.

### Core Objectives
1. **Rule-Based & Explainable**: Every recommendation is directly linked to an objective movement defect, LESS item failure, asymmetry metric, or load indicator.
2. **Deterministic & Auditable**: No generative LLM hallucinations. Standardized exercise library with verified biomechanical targets.
3. **Decoupled Priority**: Recommendation priority (`LOW`, `MEDIUM`, `HIGH`) reflects biomechanical urgency and movement defect severity, independent of the overall composite risk score.
4. **Non-Medical Screening**: Explicitly framed as training guidance, injury risk screening, and movement quality optimization—not clinical diagnosis or medical rehabilitation.

---

## 2. Architecture & Data Flow

```
+-----------------------------------------------------------------------------------+
|                                 Input Sources                                     |
|  +---------------------+   +---------------------+   +--------------------------+ |
|  | Kinematic Features  |   |    LESS Results     |   | Athlete Profile & Load   | |
|  | (9-col ML vector +  |   | (17-item checklist, |   | (Weekly sRPE, Fatigue,   | |
|  | knee/hip/trunk/ROM) |   |  classification)    |   |  Injury History)         | |
|  +----------+----------+   +----------+----------+   +------------+-------------+ |
+-------------|-------------------------|---------------------------|---------------+
              |                         |                           |
              v                         v                           v
+-----------------------------------------------------------------------------------+
|                   CorrectiveRecommendationEngine (v1)                             |
|                                                                                   |
|  1. Knee Valgus Detector        --> LESS Item 5/15, Valgus Angle > 15°           |
|  2. Landing Mechanics Detector  --> LESS Item 12, Knee ROM < 45°, Stiff Landing   |
|  3. Hip Instability Detector    --> Hip Drop / Adduction > 12°                   |
|  4. Trunk Lean Detector         --> Lateral Trunk Flexion > 10° / Sagittal > 30° |
|  5. Joint Asymmetry Detector    --> Knee / Hip / Ankle Asymmetry > 15-20%        |
|  6. Ankle Mobility Detector     --> Ankle Dorsiflexion ROM < 20°                 |
|  7. High Workload Detector      --> Weekly Load >= 2000 AU or s_load >= 65       |
|  8. High Fatigue Detector       --> Fatigue >= 7 / s_fatigue >= 65               |
|  9. Overall Risk Modifier       --> Contextual Deloading / Movement Prep         |
|  10. Injury History Modifier    --> Targeted Secondary Prevention                |
+-----------------------------------------------------------------------------------+
              |
              v
+-----------------------------------------------------------------------------------+
|                            Structured Output                                      |
|  - Summary & Primary Focus Areas                                                  |
|  - Priority Counts (HIGH, MEDIUM, LOW)                                            |
|  - Corrective Recommendations List (Category, Priority, Evidence, Cues, Drills)   |
|  - Training Modifications (Intensity, Volume, Load Targets, Focus Phase)          |
|  - Recovery Plan (Rest Days, Sleep, Hydration, Active Recovery)                   |
|  - Non-Medical Screening Disclaimer                                               |
+-----------------------------------------------------------------------------------+
```

---

## 3. Centralized Thresholds & Detection Rules

All thresholds are centralized in `CorrectiveRecommendationEngine.THRESHOLDS` in [`backend/app/services/recommendation_engine.py`](file:///c:/Users/Welcome/sports-injury-risk-detection/backend/app/services/recommendation_engine.py).

| Detector | Metric / Feature | Unit / Scale | Configured Threshold | Trigger Condition & Biomechanical Evidence | Recommendation Generated |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Knee Valgus** | `knee_valgus_angle` / LESS Items 5 & 15 | Degrees (°) / Binary | `15.0°` | Peak valgus angle > 15° OR LESS Item 5/15 ERROR | Gluteus Medius & Hip Abductor Strengthening + Banded Squats |
| **Landing Mechanics** | `knee_flexion_rom` / LESS Item 12 | Degrees (°) / Binary | `< 45.0°` (Stiff) | Knee flexion displacement < 45° at landing | Soft-Landing Mechanics & Eccentric Quad Loading |
| **Hip Instability** | `hip_adduction_angle` / Hip Drop | Degrees (°) | `12.0°` | Peak hip adduction angle > 12° | Pelvic & Gluteal Stability Drills (Single-leg deadlifts, bridges) |
| **Trunk Lean** | `trunk_lateral_flexion` / LESS Item 6 | Degrees (°) / Binary | `10.0°` | Lateral trunk flexion > 10° OR LESS Item 6 ERROR | Core Anti-Lateral Flexion & Multi-Planar Trunk Control |
| **Joint Asymmetry** | `knee_asymmetry`, `hip_asymmetry`, `ankle_asymmetry` | Percentage (%) | `15.0%` (Warn), `25.0%` (High) | Bilateral limb difference > 15.0% | Unilateral Strength, Balance & Single-Leg Stabilization |
| **Ankle Mobility** | `ankle_dorsiflexion_rom` | Degrees (°) | `< 20.0°` | Ankle dorsiflexion ROM < 20° | Ankle Dorsiflexion Mobility & Calf Soft-Tissue Flossing |
| **High Workload** | `weekly_training_load` / `s_load` | AU (sRPE) / [0, 100] | `2000.0 AU` / `65.0` | sRPE workload >= 2,000 AU or Load Score >= 65 | Workload Management & Training Volume Deload |
| **High Fatigue** | `current_fatigue_level` / `s_fatigue` | [1, 10] / [0, 100] | `7 / 10` / `65.0` | Fatigue rating >= 7 or Fatigue Score >= 65 | Acute Fatigue Recovery & Sleep/Hydration Protocol |
| **Risk Context** | `overall_risk_score` / `risk_level` | [0, 100] / Level | `HIGH` / `CRITICAL` | Risk score >= 60 | Global Deloading, Controlled Technique Focus |
| **Injury History** | `has_injury_history` / records | Relational status | `"Yes"` | Active/recent lower-extremity injury history | Secondary Prevention & Re-injury Screening Protocols |

---

## 4. Priority Categorization & Traceability

### Priority Levels
- **`HIGH`**: Severe biomechanical defect (e.g., severe knee valgus > 20°, high bilateral asymmetry > 25%, multiple compound errors), high acute training load (> 2500 AU), or critical fatigue.
- **`MEDIUM`**: Meaningful movement quality issues (e.g., moderate valgus 15–20°, trunk lean > 10°, single LESS error), elevated fatigue (7–8/10).
- **`LOW`**: Minor technique refinements, baseline mobility maintenance, or general progression for athletes with clean landing mechanics.

### Traceability Example
Every generated recommendation includes a dedicated evidence block:
```json
{
  "id": "rec_valgus_01",
  "category": "strengthening",
  "title": "Gluteus Medius & Hip Abductor Strengthening",
  "priority": "HIGH",
  "detected_issue": "Knee Valgus (Inward Knee Collapse)",
  "evidence": "Knee valgus detected on initial contact (LESS Item 5) / peak valgus angle 18.4° (threshold > 15.0°)",
  "target_metric": "knee_valgus_angle",
  "suggested_exercises": [
    "Side-lying clam shells with resistance band (3 sets x 15 reps)",
    "Lateral band walks (3 sets x 12 steps each direction)",
    "Single-leg Romanian deadlifts (3 sets x 10 reps/side)"
  ],
  "frequency": "3-4 times per week",
  "focus_cues": [
    "Keep knees tracking over toes",
    "Engage glutes throughout movement",
    "Avoid letting knee drop inward"
  ],
  "safety_notes": "Stop if sharp joint pain occurs. Perform with controlled eccentric tempo."
}
```

---

## 5. API Endpoints

### 1. `GET /api/v1/videos/{video_id}/recommendations`
- **Role-Based Access Control (RBAC)**:
  - **Athlete**: Allowed only for videos belonging to their own profile (HTTP 403 otherwise).
  - **Coach / Staff / Admin**: Allowed for all team athletes.
- **Response**: `CorrectiveActionPlanResponse`

### 2. `GET /api/v1/videos/{video_id}/analysis`
- Returns `AnalysisStatusResponse` with `recommendations: Optional[dict]` automatically populated when analysis status is `COMPLETED`.

---

## 6. Frontend Presentation

The **Corrective Action Plan** is integrated directly into [`AnalysisReportView.jsx`](file:///c:/Users/Welcome/sports-injury-risk-detection/frontend/src/components/AnalysisReportView.jsx) and rendered on both live analyses (`/analysis`) and historical reports (`/analysis/:videoId`):
1. **Targeted Corrective Strategy Header**: Summary text and count chips for High/Medium/Low priority areas.
2. **Focus Area Badges**: Quick visual tags highlighting critical joint targets.
3. **Structured Recommendation Cards**:
   - Visual category icons (`Strengthening`, `Mobility`, `Exercise`, `Recovery`, `Training Modification`).
   - Color-coded left borders and priority badges (`HIGH` in red, `MEDIUM` in amber, `LOW` in green).
   - Biomechanical Evidence Callout Box showing the exact metric and rule triggered.
   - Recommended Exercises List with checkmarks.
   - Coaching Cues & Target Frequency.
   - Safety notes box.
4. **Training Modifications & Recovery Grid**:
   - Training intensity adjustments, volume caps, and recommended sRPE load targets.
   - Recovery protocols: rest days, sleep targets, hydration, active recovery.
5. **Non-Medical Screening Disclaimer**: Prominently displayed to ensure safe ethical use.

---

## 7. Verification & Automated Test Suite

### Pytest Coverage (`tests/test_recommendation_engine.py`)
- **18 dedicated tests**:
  - `test_01_no_detected_issues`: Validates clean mechanics generate gentle baseline maintenance.
  - `test_02_knee_valgus_detection`: Verifies valgus trigger via angle (> 15°) and LESS items 5/15.
  - `test_03_poor_landing_mechanics`: Verifies stiff landing trigger (< 45° knee ROM / LESS item 12).
  - `test_04_limited_ankle_mobility`: Verifies dorsiflexion trigger (< 20°).
  - `test_05_joint_asymmetry`: Verifies bilateral asymmetry trigger (> 15%).
  - `test_06_high_training_workload`: Verifies workload threshold (> 2000 AU).
  - `test_07_high_fatigue_indicators`: Verifies acute fatigue trigger (>= 7/10).
  - `test_08_multiple_combined_issues`: Verifies priority counts and compound issue handling.
  - `test_09_low_risk_appropriate_intensity`: Verifies low-risk athletes receive appropriate low-priority conditioning.
  - `test_10_high_risk_appropriate_modifications`: Verifies high-risk cases receive volume reductions and deloading.
  - `test_11_missing_features_no_fabrication`: Verifies missing metrics are cleanly excluded without default fabrication.
  - `test_12_deduplication`: Verifies recommendations are deduplicated by ID.
  - `test_13_schema_validation`: Verifies strict Pydantic parsing and serializability.
  - `test_14_get_recommendations_owner_success`: Verifies athlete can fetch own recommendations.
  - `test_15_get_recommendations_coach_success`: Verifies coach can access athlete recommendations.
  - `test_16_get_recommendations_forbidden_other_athlete`: Verifies strict RBAC 403 cross-athlete protection.
  - `test_17_get_recommendations_unauthorized`: Verifies 401 on missing JWT.
  - `test_18_analysis_status_attaches_recommendations`: Verifies recommendation attachment to status endpoint.

### Test Results
- **Backend Full Suite**: `158 passed` in `53.25s` (0 failures, 0 regressions).
- **Frontend Production Build**: `npm run build` completed in `19.63s` with `0 errors`.
