import sqlite3
from collections.abc import Iterator
from typing import Any

from .config import DATA_DIR, DB_PATH, SCHEMA_PATH
from .utils import localize_rows, localize_timestamps


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(
        DB_PATH,
        timeout=5,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }

    if "fixed_blocks" in tables:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(fixed_blocks)")
        }
        if "allow_task_schedule" not in columns and "allow_override" in columns:
            conn.execute(
                "ALTER TABLE fixed_blocks "
                "RENAME COLUMN allow_override TO allow_task_schedule"
            )

    if "task_statuses" in tables:
        status_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(task_statuses)")
        }
        if "is_initial_filter" not in status_columns:
            conn.execute(
                "ALTER TABLE task_statuses ADD COLUMN is_initial_filter "
                "INTEGER NOT NULL DEFAULT 1 CHECK (is_initial_filter IN (0, 1))"
            )
            conn.execute(
                "UPDATE task_statuses SET is_initial_filter = 0 "
                "WHERE code IN ('done', 'cancelled')"
            )

    conn.execute("DROP INDEX IF EXISTS ux_daily_memos_date_active")


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    try:
        _migrate(conn)
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return None
    return localize_timestamps(conn, dict(row))


def fetch_all(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    return localize_rows(conn, rows)
