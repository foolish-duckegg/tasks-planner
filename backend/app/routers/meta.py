import sqlite3
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_db
from ..schemas import MetaValueUpdate

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get(
    "",
    response_model=dict[str, str],
    summary="获取元信息",
    description="返回 app_meta 中的所有键值，如 schema_version、timezone、week_start。",
)
def get_meta(conn: sqlite3.Connection = Depends(get_db)) -> dict[str, str]:
    rows = conn.execute("SELECT key, value FROM app_meta ORDER BY key").fetchall()
    return {row["key"]: row["value"] for row in rows}


@router.put(
    "/{key}",
    response_model=dict[str, str],
    summary="写入元信息",
    description=(
        "key 不存在时创建，存在时覆盖。"
        "timezone 必须是 IANA 时区名（如 Asia/Shanghai）；week_start 为 1..7。"
    ),
)
def put_meta(
    key: str,
    payload: MetaValueUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict[str, str]:
    if key == "timezone":
        try:
            ZoneInfo(payload.value)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(
                status_code=422, detail="无效的 IANA 时区名"
            ) from exc
    elif key == "week_start":
        if payload.value not in {"1", "2", "3", "4", "5", "6", "7"}:
            raise HTTPException(status_code=422, detail="week_start 必须在 1..7")

    conn.execute(
        """
        INSERT INTO app_meta(key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, payload.value),
    )
    conn.commit()
    return {key: payload.value}
