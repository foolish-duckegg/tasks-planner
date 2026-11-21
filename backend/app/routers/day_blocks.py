import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..database import fetch_all, fetch_one, get_db
from ..schemas import (
    DayBlockBulkReplace,
    DayBlockCreate,
    DayBlockOut,
    DayBlockUpdate,
)
from ..utils import get_or_404, restore_row, soft_delete, update_row

router = APIRouter(prefix="/api/day-blocks", tags=["day-blocks"])


def _validate_no_overlap(blocks: list[DayBlockCreate]) -> None:
    active = sorted(
        (block for block in blocks if block.is_active),
        key=lambda block: block.start_minute,
    )
    previous_end: int | None = None
    for block in active:
        if previous_end is not None and block.start_minute < previous_end:
            raise HTTPException(
                status_code=422,
                detail=(
                    "启用状态的时间块重叠："
                    f"[{block.start_minute}, {block.end_minute}) 与前一块重叠"
                ),
            )
        previous_end = block.end_minute


def _merged_create(row: dict, changes: dict) -> DayBlockCreate:
    merged = {field: row[field] for field in DayBlockCreate.model_fields}
    merged.update(changes)
    return DayBlockCreate(**merged)


def _get_day_block(conn: sqlite3.Connection, block_id: int) -> dict:
    return get_or_404(conn, "day_blocks", block_id, "时间块不存在")


@router.get(
    "",
    response_model=list[DayBlockOut],
    summary="列出每日基础时间块",
    description=(
        "返回全局每日模板，按 start_minute 排序。"
        "默认不返回软删除记录，include_deleted=true 可查看。"
    ),
)
def list_day_blocks(
    active_only: bool = Query(False, description="只返回启用时间块"),
    include_deleted: bool = Query(False, description="包含软删除时间块"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    sql = "SELECT * FROM day_blocks WHERE 1 = 1"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY start_minute, id"
    return fetch_all(conn, sql)


@router.put(
    "",
    response_model=list[DayBlockOut],
    summary="整体替换每日基础划分",
    description=(
        "用请求体中的 blocks 完整替换每日模板（旧模板软删除后重新插入）。"
        "启用状态的时间块必须互不重叠；空数组表示清空。"
    ),
    responses={422: {"description": "时间块重叠或时间范围非法"}},
)
def replace_day_blocks(
    payload: DayBlockBulkReplace,
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    _validate_no_overlap(payload.blocks)
    try:
        conn.execute(
            """
            UPDATE day_blocks
            SET deleted_at = datetime('now'), updated_at = datetime('now')
            WHERE deleted_at IS NULL
            """
        )
        for block in payload.blocks:
            conn.execute(
                """
                INSERT INTO day_blocks(
                  start_minute, end_minute, label, kind, remark, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    block.start_minute,
                    block.end_minute,
                    block.label,
                    block.kind,
                    block.remark,
                    int(block.is_active),
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return fetch_all(
        conn,
        "SELECT * FROM day_blocks WHERE deleted_at IS NULL ORDER BY start_minute, id",
    )


@router.post(
    "",
    response_model=DayBlockOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建每日时间块",
    description="启用状态的块不能与已有未删除、启用的块重叠。",
    responses={409: {"description": "与已有时间块重叠"}},
)
def create_day_block(
    payload: DayBlockCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    cursor = conn.execute(
        """
        INSERT INTO day_blocks(
          start_minute, end_minute, label, kind, remark, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.start_minute,
            payload.end_minute,
            payload.label,
            payload.kind,
            payload.remark,
            int(payload.is_active),
        ),
    )
    conn.commit()
    row = fetch_one(conn, "SELECT * FROM day_blocks WHERE id = ?", (cursor.lastrowid,))
    assert row is not None
    return row


@router.get(
    "/{block_id}",
    response_model=DayBlockOut,
    summary="获取每日时间块",
    responses={404: {"description": "时间块不存在或已删除"}},
)
def get_day_block(
    block_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return _get_day_block(conn, block_id)


@router.patch(
    "/{block_id}",
    response_model=DayBlockOut,
    summary="更新每日时间块",
    description="只更新传入的字段；修改后仍须满足时间范围和重叠约束；已删除的块不可更新。",
    responses={404: {"description": "时间块不存在或已删除"}, 409: {"description": "与已有时间块重叠"}},
)
def update_day_block(
    block_id: int,
    payload: DayBlockUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    row = get_or_404(conn, "day_blocks", block_id, "时间块不存在")
    changes = payload.model_dump(exclude_unset=True)
    _merged_create(row, changes)
    update_row(conn, "day_blocks", block_id, changes)
    return _get_day_block(conn, block_id)


@router.delete(
    "/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除每日时间块",
    description="只写入 deleted_at，不影响已经生成的记录。",
    responses={404: {"description": "时间块不存在"}},
)
def delete_day_block(
    block_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    soft_delete(conn, "day_blocks", block_id, "时间块不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{block_id}/restore",
    response_model=DayBlockOut,
    summary="恢复每日时间块",
    description="把 deleted_at 置空；若与当前启用块重叠，返回 409。",
    responses={404: {"description": "时间块不存在"}, 409: {"description": "与已有时间块重叠"}},
)
def restore_day_block(
    block_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        restore_row(conn, "day_blocks", block_id, "时间块不存在")
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=409, detail="恢复后与已有启用时间块重叠"
        ) from exc
    return _get_day_block(conn, block_id)
