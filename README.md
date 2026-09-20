# 🏃 PreHab AI — AI-Powered Sports Injury Risk Detection & Preventive Recommendations

[![React](https://img.shields.io/badge/React-19.1-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-7.1-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-BlazePose-00C7B7?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev/edge/mediapipe/solutions/guide)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)

A computer-vision-powered platform that analyzes athlete movement from video, extracts 33 spatial body landmarks, evaluates biomechanical deviations and movement-risk factors, performs clinical Landing Error Scoring System (LESS) evaluations, and delivers an interpretable risk assessment paired with targeted corrective recommendations.

---

## 📌 Project Overview

Preventable musculoskeletal injuries—such as anterior cruciate ligament (ACL) tears, hamstring strains, and patellofemoral pain—frequently stem from undetected movement flaws, bilateral asymmetries, unmonitored training workload, and muscle fatigue. Traditional movement screening relies on specialized laboratory equipment, manual visual observation, or high-cost clinical motion capture system, making routine screening inaccessible for most athletic teams and individual athletes.

**PreHab AI** bridges this gap by providing an accessible, end-to-end movement screening platform. Using standard RGB video input (e.g., recorded on a smartphone or camera), PreHab AI extracts spatial 3D human pose landmarks, calculates frame-by-frame joint kinematics, computes a clinical LESS movement technique score, evaluates a 5-factor risk score, overlays a synchronized visual pose skeleton, and generates individualized corrective action plans.

> [!NOTE]
> **Screening Disclaimer**: PreHab AI is designed for preliminary movement-risk screening, movement technique analysis, and preventive training guidance. It is **NOT** a clinical diagnostic device and does not predict future injuries with absolute medical certainty.

---

## 🎯 Problem Statement

* **High Incidence of Preventable Injuries**: Biomechanical faults (e.g., severe knee valgus, stiff vertical landing, bilateral asymmetry) significantly elevate joint stress.
* **Subjective & Time-Intensive Evaluations**: Manual visual observation by coaches or physiotherapists is subjective, inconsistent across evaluators, and difficult to scale across full team rosters.
* **Resource & Equipment Barriers**: Professional motion capture laboratories are cost-prohibitive for schools, amateur clubs, and community athletes.
* **Unmonitored Fatigue & Workload**: Biomechanical risk changes dynamically when combined with high acute training loads or elevated fatigue.

---

## 💡 Our Solution

```text
┌────────────────────────┐
│  Athlete Video Upload  │ (MP4 / MOV / AVI / WebM up to 500 MB)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ OpenCV Video Processor │ (Frame extraction & sampling rate control)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ MediaPipe BlazePose    │ (33 3D body landmark spatial extraction)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Biomechanical Engine   │ (15+ joint angles, angular velocities, asymmetry)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ LESS Clinical Scorer   │ (9 criteria error evaluation & classification)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ 5-Factor Risk Engine   │ (Kinematic RF v2 + Load + Fatigue + History)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│ Corrective Action Plan │ (Targeted mobility, strengthening & modifications)
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│  AI Risk Report &      │
│  Synchronized Skeleton │ (Canvas overlay pinned to video playback)
└────────────────────────┘
```

---

## 🚀 Key Implemented Features

### 🎥 Video Storage & Processing Pipeline
* **Multipart Video Vault**: Accepts `.mp4`, `.mov`, `.avi`, `.webm`, and `.mkv` files up to **500 MB**.
* **Persistent Backend Storage**: Videos are stored safely on the container filesystem (`/app/uploads`), with path traversal protection and file sanitization.
* **Asynchronous Processing**: Upload returns immediately; analysis runs asynchronously via FastAPI `BackgroundTask` with polling state updates (`PENDING` → `PROCESSING` → `COMPLETED` / `FAILED`).

### 🦴 MediaPipe Pose Estimation
* **33 3D Spatial Landmarks**: Extracts spatial coordinates (`x`, `y`, `z`, `visibility`) for key joint locations across sampled video frames.
* **Database Landmark Storage**: Coordinates are stored in the PostgreSQL `pose_landmarks` table, linking frame numbers and frame timestamps (`timestamp_ms`) to the exact assessment run.

### 🧍 Synchronized AI Pose Skeleton Overlay
* **Canvas-Based Synchronized Rendering**: Renders a glowing cyan pose skeleton (`#00f0ff` / `#06b6d4`) directly over the original untouched video player using a transparent HTML5 canvas.
* **Nearest-Frame Binary Search**: Uses `video.currentTime * 1000` to look up the exact landmark frame by `timestamp_ms`, maintaining accuracy during play, pause, seeking, scrubbing, and frame stepping.
* **Letterbox & Aspect Ratio Compensation**: Adjusts coordinates dynamically based on original video resolution vs. rendered video element size, maintaining alignment during window resize and fullscreen modes.
* **Instant Client Toggle**: Interactive `AI SKELETON: ON / OFF` toggle switch operates purely client-side without re-triggering API calls or video processing.
* **Exact Assessment Scoping**: Fetches landmarks using `GET /videos/{video_id}/landmarks?analysis_id={analysis_id}`, guaranteeing historical reports render the pose data matching that specific evaluation.

### 📊 Biomechanical Feature Extraction Engine
* **Joint Kinematics**: Computes 15+ kinematic metrics per frame, including knee flexion, hip flexion, ankle dorsiflexion, trunk flexion, and trunk lateral lean angles.
* **Velocities & ROM**: Calculates joint angular velocities, total joint displacements, and range of motion (ROM) across movement sequences.
* **Bilateral Asymmetry**: Quantifies left-vs-right side-to-side movement imbalances (e.g., knee ROM asymmetry, hip asymmetry).

### 📝 Landing Error Scoring System (LESS) Engine
* **Clinical Movement Evaluation**: Evaluates 9 movement criteria (knee flexion at initial contact, max knee flexion, knee valgus at max flexion, trunk flexion, stance width, foot position, initial contact symmetry, joint landing flow).
* **Technique Classification**: Calculates total error score out of computable items and classifies movement technique into `EXCELLENT` (0–3 errors), `GOOD` (4–5 errors), `MODERATE` (6–7 errors), or `POOR` (8+ errors).

### ⚖️ 5-Factor Dynamic Injury Risk Engine
Combines 5 risk parameters into a normalized 0–100 overall risk score:
1. **$S_{bio}$ — Biomechanical Movement Risk (35%)**: Derived from a trained **Random Forest Classifier (Kinematic RF v2)** or kinematic feature analysis.
2. **$S_{hist}$ — Previous Injury History Risk (20%)**: Evaluates past joint injuries, recovery status, and severity.
3. **$S_{asym}$ — Movement Asymmetry Risk (20%)**: Measures bilateral kinematic imbalances between left and right limbs.
4. **$S_{load}$ — Training Workload Risk (15%)**: Evaluates acute workload AU (sessions × duration × RPE) relative to training thresholds.
5. **$S_{fatigue}$ — Neuromuscular Fatigue Risk (10%)**: Incorporates self-reported fatigue levels (1–10 scale).

> **Dynamic Weight Renormalization**: If certain physical inputs (e.g. injury history or fatigue) are unprovided, the engine excludes them and automatically renormalizes the weights of available factors.

### 🎯 Corrective Action Plan Engine
* **Personalized Recommendations**: Automatically maps detected biomechanical deviations and LESS errors into actionable corrective recommendations.
* **Categorized Guidance**: Generates recommendations across 5 pillars: Movement Modifications, Strengthening Exercises, Mobility Drills, Recovery Protocols, and Workload Adjustments.

### 📈 Historical AI Risk Reports & Baseline Comparison
* **Historical Report Access**: Complete assessment history available from the Dashboard and Analysis History views.
* **Automated Baseline Comparison**: Side-by-side comparison modal pairs any evaluation with the athlete's immediately preceding assessment to highlight directional progress (`Improved`, `Worsened`, `Unchanged`), score deltas, and LESS score trends.
* **Conditional AI POSE Badge**: Shows `AI POSE ✓` badges on assessment history lists only when valid landmark data exists for that analysis.

### 🔔 Role-Aware Notification Center
* **Notification Feed**: Real-time alerts for analysis completion, high-risk detection, and squad assignments (`GET /notifications`).
* **Navbar Unread Counter**: Fast badge indicator powered by `GET /notifications/unread-count`.
* **Interactivity**: Support for mark-as-read (`PATCH /notifications/{id}/read`), mark-all-read, and dismissal.

### 👥 Role-Based Access Control (RBAC) & Auth
* **5 Database Roles**: `Athlete`, `Coach`, `Physiotherapist`, `Sports Scientist`, and `Administrator`.
* **Argon2id Hashing**: High-security password hashing using `argon2-cffi`.
* **JWT Authentication**: Stateless HTTP Bearer token authentication with Axios request interceptors.
* **Google OAuth 2.0 Integration**: Third-party Google Sign-In (`POST /auth/google`) with automatic account linking and secure fallback.

---

## 🛠️ Technology Stack

| Layer | Technology | Description |
|---|---|---|
| **Frontend Framework** | React 19 / Vite 7 | Modern Single-Page Application (SPA) architecture |
| **Styling & UI** | Custom Vanilla CSS + Lucide React | Custom dark/glassmorphic design system and icons |
| **HTTP Client** | Axios | Interceptor-based API client with automatic JWT header injection |
| **Backend Framework** | FastAPI (Python 3.11+) | Asynchronous, high-performance REST API |
| **Database & ORM** | PostgreSQL 16 + SQLAlchemy 2.0 | Relational database managed with Alembic schema migrations |
| **Pose Estimation** | MediaPipe 0.10.x BlazePose | 33 3D spatial body landmark detection |
| **Video Processing** | OpenCV (`opencv-python-headless`) | Frame extraction, resolution verification, and FPS sampling |
| **Machine Learning** | scikit-learn / joblib / NumPy / pandas | Random Forest Kinematic Classifier (v2) and feature vectors |
| **Security & Auth** | Argon2id + PyJWT + Google Auth | Password hashing, JWT token verification, Google OAuth 2.0 |
| **Containerization** | Docker & Docker Compose | Multi-container environment (`compose.yaml`) |

---

## 🏗️ System Architecture

```mermaid
graph TD
    subgraph Client Layer [Frontend - React 19 SPA]
        UI[Browser UI / React Pages] -->|HTTP Requests| AX[Axios HTTP Client]
        AX -->|Bearer JWT Header| AC[Auth Context & LocalStorage]
        UI -->|Role Check| PG[ProtectedRoute & Guarded Views]
        UI -->|Canvas Render| SKELETON[AIPoseVideoPlayer - Skeleton Overlay]
    end

    subgraph API & Control Layer [Backend - FastAPI]
        ROU[FastAPI Routers: auth, athletes, videos, notifications] -->|Dependency Injection| DEP[get_current_user & Auth Guards]
        DEP -->|Role Check| RBAC[Role Validation: Athlete, Coach, Physio, Admin]
        ROU -->|Schema Validation| SCH[Pydantic v2 Schemas]
    end

    subgraph Analytics & AI Pipeline Layer
        ROU -->|POST /videos/{id}/analyze| BG[FastAPI BackgroundTask Orchestrator]
        BG --> VP[OpenCV VideoProcessor - Frame Sampling]
        VP --> PE[MediaPipe PoseEstimator - 33 3D Landmarks]
        PE --> FE[Biomechanical FeatureExtractor - Kinematics]
        FE --> LESS[LESS Scorer - 9 Clinical Criteria]
        FE --> ML[Random Forest Classifier v2 - Biomechanical Risk]
        ML --> RS[RiskScoringService - 5-Factor Risk Engine]
        RS --> REC[CorrectiveRecommendationEngine - Action Plans]
    end

    subgraph Data & Persistence Layer [PostgreSQL 16 & Storage]
        RS --> ORM[SQLAlchemy 2.0 ORM]
        ORM --> DB[(PostgreSQL Database)]
        VP --> FS[/app/uploads Docker Storage Volume]
    end

    AX -->|REST API Calls| ROU
    SKELETON -->|Fetch Landmarks| ROU
```

---

## 👥 User Roles & Access Control Matrix

| Capability / Resource | Athlete | Coach | Physiotherapist | Sports Scientist | Administrator |
|---|:---:|:---:|:---:|:---:|:---:|
| Self-Register Account (`/auth/register`) | ✅ | ✅ | ✅ | ✅ | ❌ (Seeded Only) |
| Google OAuth 2.0 Sign-In (`/auth/google`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage Own Physical Profile (`/profile`) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Upload Movement Video (`/videos`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Run Video Analysis (`/videos/{id}/analyze`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| View Personal Assessment History (`/history`) | ✅ | ❌ | ❌ | ❌ | ❌ |
| View Team Roster & Athlete Profiles (`/roster`) | ❌ | ✅ | ✅ | ✅ | ✅ |
| Provision / Update Athlete Profiles | ❌ | ✅ | ✅ | ✅ | ✅ |
| View Team Assessments & Baselines (`/assessments`) | ❌ | ✅ | ✅ | ✅ | ✅ |
| Delete Athlete Profile (`/athletes/{id}`) | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 🔌 Core API Overview

### Authentication Router (`/api/v1/auth`)
* `POST /auth/register` — Register a new account (Athlete, Coach, Physio, Sports Scientist).
* `POST /auth/login` — Authenticate credentials and receive a JWT bearer token.
* `POST /auth/google` — Sign in or register via Google OAuth 2.0 ID token.
* `GET /auth/me` — Retrieve currently authenticated user profile and role details.

### Video & Analysis Router (`/api/v1/videos`)
* `POST /videos` — Upload a movement video file (MP4, MOV, AVI, WebM; max 500 MB).
* `POST /videos/{video_id}/analyze` — Trigger asynchronous AI video analysis background task.
* `GET /videos/{video_id}/analysis` — Get latest analysis status, risk score, and breakdown.
* `GET /videos/{video_id}/landmarks?analysis_id={analysis_id}` — Get exact 33-point MediaPipe pose landmarks for visual skeleton overlay.
* `GET /videos/{video_id}/features` — Get extracted 15+ joint kinematics and asymmetry vector.
* `GET /videos/{video_id}/less` — Get Landing Error Scoring System (LESS) score & item breakdown.
* `GET /videos/{video_id}/recommendations` — Get targeted corrective action plan recommendations.
* `GET /videos/history` — Get logged-in athlete's personal assessment video history.
* `GET /videos/all-assessments` — Get team assessment list for coach/staff roles.
* `PATCH /videos/{video_id}` — Update video title or metadata.
* `DELETE /videos/{video_id}` — Remove video recording and associated analysis data.

### Athlete Profile Router (`/api/v1/athletes`)
* `GET /athletes/me` — Get current athlete's profile, training load, and baseline parameters.
* `POST /athletes/me` — Upsert athlete baseline physical profile.
* `GET /athletes` — List assigned roster athletes for coaches and medical staff.
* `POST /athletes/with-user` — Provision a new athlete account and profile (Coach/Admin).
* `PATCH /athletes/{athlete_id}` — Update athlete profile or assign coach.
* `DELETE /athletes/{athlete_id}` — Delete an athlete profile (Admin only).

### Notifications Router (`/api/v1/notifications`)
* `GET /notifications` — List paginated notifications for logged-in user.
* `GET /notifications/unread-count` — Fast count of unread notifications for badge rendering.
* `PATCH /notifications/{notification_id}/read` — Mark a single notification as read.
* `PATCH /notifications/read-all` — Mark all user notifications as read.
* `DELETE /notifications/{notification_id}` — Dismiss a notification.

---

## 📊 Database Schema Overview

PostgreSQL 16 database entities managed with SQLAlchemy 2.0 ORM and Alembic migrations:

```text
  ┌───────────┐         ┌───────────┐
  │   User    │1───────1│  Athlete  │
  └─────┬─────┘         └─────┬─────┘
        │1                    │1
        │                     │
        │N                    │N
  ┌─────┴─────┐         ┌─────┴─────┐
  │Notif'n    │         │   Video   │
  └───────────┘         └─────┬─────┘
                              │1
                              │
                              │N
                        ┌─────┴─────┐
                        │ Analysis  │
                        └─────┬─────┘
                              │
        ┌──────────────┬──────┼──────────────┬──────────────┐
        │1             │1     │1             │1             │1
        ▼              ▼      ▼              ▼              ▼
  ┌───────────┐  ┌──────────┐┌───────────┐  ┌───────────┐  ┌───────────┐
  │ Landmarks │  │ Features ││ LESS Res. │  │ Predict'n │  │ Recomms   │
  └───────────┘  └──────────┘└───────────┘  └───────────┘  └───────────┘
```

* **`users`**: Account credentials (Argon2id hash), email, role, and verification status.
* **`athletes`**: Physical parameters (`sport`, `position`, `age`, `height`, `weight`, `training_load`, `fatigue_level`, `injury_status`), linked to `users`.
* **`videos`**: Uploaded video files, file sizes, format metadata, and volume URLs.
* **`analysis_results`**: Status (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`), overall risk score (0–100), risk level classification, and 5-factor component breakdowns.
* **`pose_landmarks`**: Frame-by-frame 3D joint coordinates (`x`, `y`, `z`, `visibility`) for 33 MediaPipe body landmarks linked to specific `analysis_id`.
* **`analysis_features`**: Vector of 15+ computed joint angles, velocities, and bilateral asymmetry metrics saved as JSON.
* **`analysis_less`**: Clinical Landing Error Scoring System results (total error score, computable count, technique classification, item-by-item JSON breakdown).
* **`injury_predictions`**: Category risk probabilities (ACL, hamstring, ankle, shoulder, lower back, overuse).
* **`recommendations`**: Targeted corrective action items across mobility, strengthening, recovery, and workload modifications.
* **`notifications`**: System alerts, analysis completions, and squad status updates.
* **`injury_history`**: Recorded prior athlete injuries, affected body parts, severity, and recovery dates.

---

## ⚡ Quick Start & Setup Guide

### 🐳 Running with Docker Compose (Recommended)

Start the complete application stack (Frontend, Backend API, PostgreSQL Database) with persistent named volumes:

```bash
# 1. Clone repository
git clone https://github.com/your-username/sports-injury-risk-detection.git
cd sports-injury-risk-detection

# 2. Build and launch containers in detached mode
docker compose up -d --build

# 3. Check container status
docker compose ps
```

#### Application Endpoints:
* 🌐 **Frontend Application**: [http://localhost:5173](http://localhost:5173)
* ⚙️ **FastAPI Backend API**: [http://localhost:8000](http://localhost:8000)
* 📖 **Interactive OpenAPI / Swagger Docs**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
* 🗄️ **PostgreSQL Database**: `localhost:5432`

---

### 💻 Local Manual Setup

#### Prerequisites
* **Python**: 3.11+
* **Node.js**: 18+ and `npm`
* **PostgreSQL**: 14+ running locally

#### 1. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# Install requirements
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

#### 2. Frontend Setup
```bash
cd frontend

# Install Node modules
npm install

# Start Vite dev server
npm run dev
```

---

## ⚙️ Environment Variables Reference

Create a `.env` file in the project root or configure environment variables accordingly:

```env
# ── Backend Configuration ───────────────────────────────────────────────────
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_postgres_password
POSTGRES_DB=sports_injury_db

SECRET_KEY=your_random_64_character_jwt_secret_key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=4320

CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

# Optional Google OAuth Client ID
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com

# ── Frontend Configuration ──────────────────────────────────────────────────
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
```

> [!CAUTION]
> Never commit production passwords, `SECRET_KEY` values, or API credentials to public source control.

---

## 🧪 Testing & Verification

### Backend Automated Test Suite
Run unit, integration, and security tests using `pytest`:

```bash
cd backend

# Run all backend unit and API integration tests
pytest -v

# Run landmark API tests specifically
pytest tests/test_landmarks_api.py -v

# Run offline dataset preprocessing & model script tests
python -m pytest scripts/tests -v
```

### Frontend Build Verification
Verify production build compilation:

```bash
cd frontend
npm run build
```

---

## ⚠️ Important Limitations & Responsible AI Use

* **Screening Device Only**: PreHab AI is designed as an AI-assisted movement screening and technique analysis tool. It is **NOT** a medical diagnostic device and does not replace evaluation by a licensed physician or physical therapist.
* **Computer Vision Sensitivity**: Pose estimation accuracy depends on camera angle, distance, lighting, contrast, clothing, and video frame rate.
* **Single-Person Focus**: Visual skeleton tracking is designed for single-athlete movement analysis (e.g. jump landings, squats, cuts).
* **Non-Clinical LESS Approximation**: The computerized Landing Error Scoring System evaluates 9 key movement items based on RGB video heuristics and should be interpreted as an automated screening score rather than a clinical lab diagnostic.

---

## 🚀 Future Scope & Roadmap

* 🎥 **Multi-Camera 3D Triangulation**: Multi-angle video support for true 3D spatial joint tracking.
* ⚽ **Sport-Specific Movement Models**: Specialized ML models trained on sport-specific movement patterns (e.g., basketball jump landing, soccer cutting, sprinting).
* ⌚ **Wearable Sensor Integration**: Fusion of IMU (Inertial Measurement Unit) telemetry with video pose data.
* 📊 **Longitudinal Squad Analytics**: Longitudinal trend tracking for head coaches to monitor roster fatigue and squad risk over a multi-month season.

---

## 📂 Project Structure

```text
sports-injury-risk-detection/
├── backend/
│   ├── alembic/                # Alembic database schema migrations
│   ├── app/
│   │   ├── api/                # FastAPI endpoint routers (auth, videos, athletes, etc.)
│   │   ├── core/               # Security, storage, and dependency injection guards
│   │   ├── models/             # SQLAlchemy 2.0 database ORM entities
│   │   ├── schemas/            # Pydantic v2 validation & response schemas
│   │   ├── services/           # Pose estimation, feature extraction, LESS, ML & risk engine
│   │   ├── config.py           # Application settings & environment loader
│   │   ├── database.py         # Database session & engine setup
│   │   └── main.py             # FastAPI app initialization & CORS middleware
│   ├── tests/                  # Pytest automated test suite
│   ├── Dockerfile              # Backend container build definition
│   └── requirements.txt        # Python package dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                # Axios HTTP client API helpers
│   │   ├── components/         # AIPoseVideoPlayer, Navbar, Report Views, Modals
│   │   ├── context/            # AuthContext state provider
│   │   ├── pages/              # Dashboard, AnalysisHistory, Roster, VideoAnalysis
│   │   ├── index.css           # Custom CSS design system
│   │   └── App.jsx             # React router configuration
│   ├── Dockerfile              # Frontend container build definition
│   └── package.json            # Node.js dependencies & scripts
├── scripts/
│   ├── artifacts/              # Trained ML model joblib artifacts
│   ├── prepare_ric_dataset.py  # Dataset preprocessing & feature matrix builder
│   ├── ric_preprocessing.py    # Feature extraction utilities
│   ├── train_kinematic_model.py# Random Forest Kinematic Classifier training script
│   └── tests/                  # Dataset preprocessing unit tests
├── compose.yaml                # Multi-container Docker Compose configuration
└── README.md                   # Main project documentation
```

---

## 🏆 Why PreHab AI?

* **Accessible Movement Screening**: Enables routine movement risk evaluation using ordinary video input.
* **Transparent & Explainable AI**: Combines 33-point MediaPipe pose landmarks, 15+ joint kinematics, clinical LESS movement scores, and a 5-factor risk model.
* **Synchronized Visual Feedback**: Instant, frame-accurate canvas pose skeleton overlay for athletes and coaches.
* **Multi-Disciplinary Workflow**: Seamless collaboration between Athletes, Coaches, Physiotherapists, Sports Scientists, and Administrators.
* **Enterprise-Ready Architecture**: Built on robust Python (FastAPI), React 19, PostgreSQL 16, Argon2id security, and Docker containerization.

---

## 📄 License

This project is licensed under the MIT License — see the `LICENSE` file for details.