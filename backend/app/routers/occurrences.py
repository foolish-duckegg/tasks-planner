import sqlite3
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..database import fetch_all, fetch_one, get_db
from ..schemas import (
    FixedBlockOccurrenceLogOut,
    FixedBlockOccurrenceOut,
    FixedBlockOccurrenceStatusUpdate,
)
from ..utils import get_or_404, get_timezone
from .plan import compute_fixed_occurrences, compute_fixed_occurrences_range

router = APIRouter(
    prefix="/api/fixed-block-occurrences",
    tags=["fixed-block-occurrences"],
)


def _is_past(occurrence: dict, today: date, now_minute: int) -> bool:
    if occurrence["date"] < today:
        return True
    if occurrence["date"] > today:
        return False
    return occurrence["end_minute"] <= now_minute


def _earliest_effective_from(
    conn: sqlite3.Connection,
) -> date | None:
    row = fetch_one(
        conn,
        """
        SELECT MIN(effective_from) AS value
        FROM fixed_blocks
        WHERE is_active = 1 AND deleted_at IS NULL
        """,
    )
    if row is None or row["value"] is None:
        return None
    return date.fromisoformat(str(row["value"]))


@router.get(
    "",
    response_model=list[FixedBlockOccurrenceOut],
    summary="列出固定块发生实例及状态",
    description=(
        "按日期范围实时计算固定块发生实例，并附带该次的状态。"
        "date_from 默认取最早生效日期，date_to 默认今天。"
        "status=pending 只返回时间已过且未完成、未跳过的实例；"
        "status=unmarked 只返回没有状态记录的实例。"
    ),
)
def list_occurrences(
    date_from: date | None = Query(
        None, description="起始日期（含），默认取最早生效日期"
    ),
    date_to: date | None = Query(None, description="结束日期（含），默认今天"),
    fixed_block_id: int | None = Query(None, description="按固定块筛选"),
    occurrence_status: str | None = Query(
        None,
        alias="status",
        pattern="^(done|skipped|missed|unmarked|pending)$",
        description="done/skipped/missed/unmarked/pending",
    ),
    limit: int = Query(500, ge=1, le=5000, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    tz = get_timezone(conn)
    now = datetime.now(tz)
    today = now.date()
    if date_to is None:
        date_to = today
    if date_from is None:
        date_from = _earliest_effective_from(conn) or date_to
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from 不能晚于 date_to")

    occurrences = compute_fixed_occurrences_range(conn, date_from, date_to)
    if fixed_block_id is not None:
        occurrences = [
            item
            for item in occurrences
            if item["fixed_block_id"] == fixed_block_id
        ]

    logs = fetch_all(
        conn,
        """
        SELECT *
        FROM fixed_block_occurrence_logs
        WHERE deleted_at IS NULL
          AND occurrence_date >= ?
          AND occurrence_date <= ?
        """,
        (date_from.isoformat(), date_to.isoformat()),
    )
    log_map = {
        (row["fixed_block_id"], row["occurrence_date"]): row for row in logs
    }

    now_minute = now.hour * 60 + now.minute
    results: list[dict] = []
    for occurrence in occurrences:
        is_past = _is_past(occurrence, today, now_minute)
        log = log_map.get(
            (occurrence["fixed_block_id"], occurrence["date"].isoformat())
        )
        log_status = log["status"] if log is not None else None

        if occurrence_status == "unmarked":
            if log_status is not None:
                continue
        elif occurrence_status == "pending":
            if not is_past or log_status in ("done", "skipped"):
                continue
        elif occurrence_status is not None:
            if log_status != occurrence_status:
                continue

        results.append(
            {
                **occurrence,
                "status": log_status,
                "log_id": log["id"] if log is not None else None,
                "note": log["note"] if log is not None else None,
                "is_past": is_past,
            }
        )

    return results[offset : offset + limit]


@router.put(
    "",
    response_model=FixedBlockOccurrenceLogOut,
    summary="标记固定块某次状态",
    description="按固定块和日期 upsert 状态（done/skipped/missed）；该日期没有发生时返回 422。",
    responses={
        404: {"description": "固定块不存在或已删除"},
        422: {"description": "该日期没有发生的固定块实例"},
    },
)
def upsert_occurrence_status(
    payload: FixedBlockOccurrenceStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    block = get_or_404(
        conn, "fixed_blocks", payload.fixed_block_id, "固定块不存在"
    )
    day_occurrences = compute_fixed_occurrences(conn, payload.date)
    if not any(
        item["fixed_block_id"] == block["id"] for item in day_occurrences
    ):
        raise HTTPException(
            status_code=422, detail="该固定块在指定日期没有发生"
        )

    existing = fetch_one(
        conn,
        """
        SELECT id
        FROM fixed_block_occurrence_logs
        WHERE fixed_block_id = ? AND occurrence_date = ?
        """,
        (payload.fixed_block_id, payload.date.isoformat()),
    )
    if existing is not None:
        log_id = int(existing["id"])
        conn.execute(
            """
            UPDATE fixed_block_occurrence_logs
            SET status = ?, note = ?, deleted_at = NULL,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (payload.status, payload.note, log_id),
        )
    else:
        cursor = conn.execute(
            """
            INSERT INTO fixed_block_occurrence_logs(
              fixed_block_id, occurrence_date, status, note
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                payload.fixed_block_id,
                payload.date.isoformat(),
                payload.status,
                payload.note,
            ),
        )
        log_id = int(cursor.lastrowid)
    conn.commit()

    row = fetch_one(
        conn,
        "SELECT * FROM fixed_block_occurrence_logs WHERE id = ?",
        (log_id,),
    )
    assert row is not None
    return row


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="清除固定块某次状态",
    description="按固定块和日期软删除状态记录，使其恢复为未标记。",
    responses={404: {"description": "该次固定块没有状态记录"}},
)
def clear_occurrence_status(
    fixed_block_id: int = Query(..., description="固定块 ID"),
    on_date: date = Query(..., alias="date", description="发生日期 YYYY-MM-DD"),
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    row = fetch_one(
        conn,
        """
        SELECT id
        FROM fixed_block_occurrence_logs
        WHERE fixed_block_id = ?
          AND occurrence_date = ?
          AND deleted_at IS NULL
        """,
        (fixed_block_id, on_date.isoformat()),
    )
    if row is None:
        raise HTTPException(status_code=404, detail="该次固定块没有状态记录")
    conn.execute(
        """
        UPDATE fixed_block_occurrence_logs
        SET deleted_at = datetime('now'), updated_at = datetime('now')
        WHERE id = ?
        """,
        (row["id"],),
    )
    conn.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
