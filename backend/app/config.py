import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

SCHEMA_PATH = Path(
    os.getenv("TASKS_PLANNER_SCHEMA", str(PROJECT_ROOT / "docs" / "schema.sql"))
)
DATA_DIR = Path(
    os.getenv("TASKS_PLANNER_DATA_DIR", str(PROJECT_ROOT / "data"))
)
DB_PATH = Path(
    os.getenv("TASKS_PLANNER_DB", str(DATA_DIR / "tasks-planner.db"))
)
STATIC_DIR = Path(
    os.getenv("TASKS_PLANNER_STATIC_DIR", str(BACKEND_DIR / "app" / "static"))
)

HOST = os.getenv("TASKS_PLANNER_HOST", "127.0.0.1")
PORT = int(os.getenv("TASKS_PLANNER_PORT", "56649"))

_cors = os.getenv("TASKS_PLANNER_CORS_ORIGINS", "*").strip()
CORS_ORIGINS = ["*"] if _cors == "*" else [item.strip() for item in _cors.split(",") if item.strip()]
