from pathlib import Path

# pyrefly: ignore [missing-import]
from fastapi import FastAPI, Depends, status
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
# pyrefly: ignore [missing-import]
from sqlalchemy import text

from app.config import settings
from app.database import get_db
from app.api.auth import router as auth_router
from app.api.athletes import router as athletes_router
from app.api.videos import router as videos_router
from app.api.injury_history import router as injury_history_router
from app.api.notifications import router as notifications_router
from app.api.reports import router as reports_router
from app.api.consent import router as consent_router
from app.api.report_sharing import router as report_sharing_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Authentication Routes under both /api/v1 and root
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(auth_router)

# Include Athlete Routes under both /api/v1 and root
app.include_router(athletes_router, prefix=settings.API_V1_STR)
app.include_router(athletes_router)

# Include Video Routes under both /api/v1 and root
app.include_router(videos_router, prefix=settings.API_V1_STR)
app.include_router(videos_router)

# Include Injury History Routes under both /api/v1 and root
app.include_router(injury_history_router, prefix=settings.API_V1_STR)
app.include_router(injury_history_router)

# Include Notification Routes under both /api/v1 and root
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router)

# Include Report Routes under both /api/v1 and root
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(reports_router)

# Include Consent Routes under both /api/v1 and root
app.include_router(consent_router, prefix=settings.API_V1_STR)
app.include_router(consent_router)

# Include Report Sharing Routes under both /api/v1 and root
app.include_router(report_sharing_router, prefix=settings.API_V1_STR)
app.include_router(report_sharing_router)


# ── Static file serving for uploaded videos ──────────────────────────────────
from app.core.storage import UPLOAD_DIR

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint providing basic API health and metadata.
    """
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "status": "online",
    }


@app.get("/health", tags=["Health"], status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint verifying application status and database connectivity.
    """
    db_status = "healthy"
    try:
        # Execute lightweight ping query
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
    }
