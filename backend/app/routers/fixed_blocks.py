import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..database import fetch_all, fetch_one, get_db
from ..schemas import FixedBlockCreate, FixedBlockOut, FixedBlockUpdate
from ..utils import (
    date_to_db,
    get_or_404,
    get_timezone,
    restore_row,
    soft_delete,
    update_row,
)

router = APIRouter(prefix="/api/fixed-blocks", tags=["fixed-blocks"])


def _merged_create(row: dict, changes: dict) -> FixedBlockCreate:
    merged = {field: row[field] for field in FixedBlockCreate.model_fields}
    merged.update(changes)
    return FixedBlockCreate(**merged)


def _get_fixed_block(conn: sqlite3.Connection, block_id: int) -> dict:
    return get_or_404(conn, "fixed_blocks", block_id, "固定块不存在")


@router.get(
    "",
    response_model=list[FixedBlockOut],
    summary="列出固定块",
    description=(
        "返回每日、每周、每月的固定块，按重复类型和时间排序。"
        "默认不返回软删除记录，include_deleted=true 可查看。"
    ),
)
def list_fixed_blocks(
    recurrence: str | None = Query(
        None, pattern="^(daily|weekly|monthly)$", description="按重复类型筛选"
    ),
    active_only: bool = Query(False, description="只返回启用固定块"),
    include_deleted: bool = Query(False, description="包含软删除固定块"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    where: list[str] = []
    params: list[object] = []
    if not include_deleted:
        where.append("deleted_at IS NULL")
    if recurrence is not None:
        where.append("recurrence = ?")
        params.append(recurrence)
    if active_only:
        where.append("is_active = 1")

    sql = "SELECT * FROM fixed_blocks"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY recurrence, recurrence_value, start_minute, id"
    return fetch_all(conn, sql, tuple(params))


@router.post(
    "",
    response_model=FixedBlockOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建固定块",
    description=(
        "daily 的 recurrence_value 必须为空；weekly 为 1..7（ISO，1=周一）；"
        "monthly 为 1..31。不支持跨午夜。"
    ),
    responses={422: {"description": "重复规则或时间范围非法"}},
)
def create_fixed_block(
    payload: FixedBlockCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    effective_from = payload.effective_from or datetime.now(
        get_timezone(conn)
    ).date()
    if payload.effective_to is not None and effective_from > payload.effective_to:
        raise HTTPException(
            status_code=422, detail="effective_from 不能晚于 effective_to"
        )
    cursor = conn.execute(
        """
        INSERT INTO fixed_blocks(
          title, recurrence, recurrence_value, start_minute, end_minute,
          effective_from, effective_to, overlap_priority, allow_task_schedule,
          remark, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.title,
            payload.recurrence,
            payload.recurrence_value,
            payload.start_minute,
            payload.end_minute,
            date_to_db(effective_from),
            date_to_db(payload.effective_to),
            payload.overlap_priority,
            int(payload.allow_task_schedule),
            payload.remark,
            int(payload.is_active),
        ),
    )
    conn.commit()
    row = fetch_one(conn, "SELECT * FROM fixed_blocks WHERE id = ?", (cursor.lastrowid,))
    assert row is not None
    return row


@router.get(
    "/{block_id}",
    response_model=FixedBlockOut,
    summary="获取固定块",
    responses={404: {"description": "固定块不存在或已删除"}},
)
def get_fixed_block(
    block_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return _get_fixed_block(conn, block_id)


@router.patch(
    "/{block_id}",
    response_model=FixedBlockOut,
    summary="更新固定块",
    description="只更新传入的字段；修改后的重复规则和时间范围必须仍然合法；已删除的块不可更新。",
    responses={404: {"description": "固定块不存在或已删除"}, 422: {"description": "字段组合非法"}},
)
def update_fixed_block(
    block_id: int,
    payload: FixedBlockUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    row = get_or_404(conn, "fixed_blocks", block_id, "固定块不存在")
    changes = payload.model_dump(exclude_unset=True)
    if "effective_from" in changes and changes["effective_from"] is None:
        raise HTTPException(status_code=422, detail="effective_from 不能为 null")
    _merged_create(row, changes)
    update_row(conn, "fixed_blocks", block_id, changes)
    return _get_fixed_block(conn, block_id)


@router.delete(
    "/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除固定块",
    description="只写入 deleted_at；其例外记录保留，恢复固定块后继续生效。",
    responses={404: {"description": "固定块不存在"}},
)
def delete_fixed_block(
    block_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    soft_delete(conn, "fixed_blocks", block_id, "固定块不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{block_id}/restore",
    response_model=FixedBlockOut,
    summary="恢复固定块",
    description="把 deleted_at 置空。",
    responses={404: {"description": "固定块不存在"}},
)
def restore_fixed_block(
    block_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    restore_row(conn, "fixed_blocks", block_id, "固定块不存在")
    return _get_fixed_block(conn, block_id)
