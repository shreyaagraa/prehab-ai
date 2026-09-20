# tests/conftest.py
import os
from sqlalchemy import create_engine, inspect, text

import app.database as database_module
from app.models import Base

# Proactively configure SQLite fallback if PostgreSQL is not available locally
try:
    with database_module.engine.connect() as conn:
        pass
except Exception:
    test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_suite_v2.db"))
    test_sqlite_engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    database_module.engine = test_sqlite_engine
    database_module.SessionLocal.configure(bind=test_sqlite_engine)

active_engine = database_module.engine
Base.metadata.create_all(bind=active_engine)

# Ensure newly added columns exist in the SQLite test database schema
inspector = inspect(active_engine)
if "notifications" in inspector.get_table_names():
    existing_cols = {c["name"] for c in inspector.get_columns("notifications")}
    with active_engine.connect() as conn:
        if "severity" not in existing_cols:
            conn.execute(text("ALTER TABLE notifications ADD COLUMN severity VARCHAR(20) DEFAULT 'INFO'"))
        if "read_at" not in existing_cols:
            conn.execute(text("ALTER TABLE notifications ADD COLUMN read_at DATETIME"))
        if "related_analysis_id" not in existing_cols:
            conn.execute(text("ALTER TABLE notifications ADD COLUMN related_analysis_id CHAR(36)"))
        if "related_video_id" not in existing_cols:
            conn.execute(text("ALTER TABLE notifications ADD COLUMN related_video_id CHAR(36)"))
        if "action_url" not in existing_cols:
            conn.execute(text("ALTER TABLE notifications ADD COLUMN action_url VARCHAR"))
        conn.commit()
