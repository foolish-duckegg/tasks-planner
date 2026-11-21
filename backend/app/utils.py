import sqlite3
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

DATETIME_FIELDS = frozenset(
    {"created_at", "updated_at", "completed_at", "deadline_at", "deleted_at"}
)


def dt_to_db(
    value: datetime | None, tz: ZoneInfo | None = None
) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=tz or timezone.utc)
    value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat(sep=" ", timespec="seconds")


def date_to_db(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(
        sep=" ", timespec="seconds"
    )


def get_timezone(conn: sqlite3.Connection) -> ZoneInfo:
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = 'timezone'"
    ).fetchone()
    name = row["value"] if row is not None else "UTC"
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _to_local(value: Any, tz: ZoneInfo) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(tz)


def _localize_row(row: dict[str, Any], tz: ZoneInfo) -> None:
    for field in DATETIME_FIELDS:
        if field in row and row[field] is not None:
            row[field] = _to_local(row[field], tz)


def localize_rows(
    conn: sqlite3.Connection, rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if not rows:
        return rows
    if not any(
        field in row and row[field] is not None
        for row in rows
        for field in DATETIME_FIELDS
    ):
        return rows
    tz = get_timezone(conn)
    for row in rows:
        _localize_row(row, tz)
    return rows


def localize_timestamps(
    conn: sqlite3.Connection, row: dict[str, Any]
) -> dict[str, Any]:
    if any(field in row and row[field] is not None for field in DATETIME_FIELDS):
        _localize_row(row, get_timezone(conn))
    return row


def to_db_value(value: Any, tz: ZoneInfo | None = None) -> Any:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, datetime):
        return dt_to_db(value, tz)
    if isinstance(value, date):
        return date_to_db(value)
    return value


def normalize_changes(
    changes: dict[str, Any], tz: ZoneInfo | None = None
) -> dict[str, Any]:
    return {key: to_db_value(value, tz) for key, value in changes.items()}


def get_or_404(
    conn: sqlite3.Connection,
    table: str,
    row_id: int,
    detail: str,
) -> dict[str, Any]:
    row = conn.execute(
        f"SELECT * FROM {table} WHERE id = ? AND deleted_at IS NULL",
        (row_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=detail)
    return localize_timestamps(conn, dict(row))


def soft_delete(
    conn: sqlite3.Connection,
    table: str,
    row_id: int,
    detail: str,
) -> None:
    row = conn.execute(
        f"SELECT id, deleted_at FROM {table} WHERE id = ?", (row_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=detail)
    if row["deleted_at"] is not None:
        return
    conn.execute(
        f"""
        UPDATE {table}
        SET deleted_at = datetime('now'), updated_at = datetime('now')
        WHERE id = ?
        """,
        (row_id,),
    )
    conn.commit()


def restore_row(
    conn: sqlite3.Connection,
    table: str,
    row_id: int,
    detail: str,
) -> None:
    row = conn.execute(
        f"SELECT id, deleted_at FROM {table} WHERE id = ?", (row_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=detail)
    if row["deleted_at"] is None:
        return
    conn.execute(
        f"""
        UPDATE {table}
        SET deleted_at = NULL, updated_at = datetime('now')
        WHERE id = ?
        """,
        (row_id,),
    )
    conn.commit()


def update_row(
    conn: sqlite3.Connection,
    table: str,
    row_id: int,
    changes: dict[str, Any],
) -> None:
    if not changes:
        return
    normalized = normalize_changes(changes, get_timezone(conn))
    fields = ", ".join(f"{key} = ?" for key in normalized)
    params = [*normalized.values(), row_id]
    cursor = conn.execute(
        f"""
        UPDATE {table}
        SET {fields}, updated_at = datetime('now')
        WHERE id = ? AND deleted_at IS NULL
        """,
        params,
    )
    if cursor.rowcount == 0:
        conn.rollback()
        raise HTTPException(status_code=404, detail="记录不存在")
    conn.commit()
