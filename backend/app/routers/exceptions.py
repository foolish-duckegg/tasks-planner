import sqlite3

from fastapi import APIRouter, Depends, Query, Response, status

from ..database import fetch_all, fetch_one, get_db
from ..schemas import (
    FixedBlockExceptionCreate,
    FixedBlockExceptionOut,
    FixedBlockExceptionUpdate,
)
from ..utils import date_to_db, get_or_404, restore_row, soft_delete, update_row

nested_router = APIRouter(
    prefix="/api/fixed-blocks/{fixed_block_id}/exceptions",
    tags=["fixed-block-exceptions"],
)
router = APIRouter(
    prefix="/api/fixed-block-exceptions",
    tags=["fixed-block-exceptions"],
)


def _merged_create(row: dict, changes: dict) -> FixedBlockExceptionCreate:
    merged = {
        field: row[field] for field in FixedBlockExceptionCreate.model_fields
    }
    merged.update(changes)
    return FixedBlockExceptionCreate(**merged)


def _get_exception(conn: sqlite3.Connection, exception_id: int) -> dict:
    return get_or_404(
        conn, "fixed_block_exceptions", exception_id, "固定块例外不存在"
    )


@nested_router.get(
    "",
    response_model=list[FixedBlockExceptionOut],
    summary="列出某个固定块的例外",
    description="默认不返回软删除记录，include_deleted=true 可查看。",
    responses={404: {"description": "固定块不存在或已删除"}},
)
def list_exceptions(
    fixed_block_id: int,
    active_only: bool = Query(False, description="只返回启用例外"),
    include_deleted: bool = Query(False, description="包含软删除例外"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    get_or_404(conn, "fixed_blocks", fixed_block_id, "固定块不存在")
    sql = "SELECT * FROM fixed_block_exceptions WHERE fixed_block_id = ?"
    params: list[object] = [fixed_block_id]
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY id"
    return fetch_all(conn, sql, tuple(params))


@nested_router.post(
    "",
    response_model=FixedBlockExceptionOut,
    status_code=status.HTTP_201_CREATED,
    summary="为固定块新建例外",
    description=(
        "例外只表示跳过。start_minute/end_minute 都为空时跳过整个固定块；"
        "都填写时只跳过与该时段重叠的部分。日期条件全部为空时，"
        "表示生效范围内每次发生都跳过。"
    ),
    responses={404: {"description": "固定块不存在或已删除"}, 422: {"description": "字段组合非法"}},
)
def create_exception(
    fixed_block_id: int,
    payload: FixedBlockExceptionCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    get_or_404(conn, "fixed_blocks", fixed_block_id, "固定块不存在")
    cursor = conn.execute(
        """
        INSERT INTO fixed_block_exceptions(
          fixed_block_id, effective_from, effective_to, skip_date,
          weekday, day_of_month, start_minute, end_minute, remark, is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            fixed_block_id,
            date_to_db(payload.effective_from),
            date_to_db(payload.effective_to),
            date_to_db(payload.skip_date),
            payload.weekday,
            payload.day_of_month,
            payload.start_minute,
            payload.end_minute,
            payload.remark,
            int(payload.is_active),
        ),
    )
    conn.commit()
    row = fetch_one(
        conn,
        "SELECT * FROM fixed_block_exceptions WHERE id = ?",
        (cursor.lastrowid,),
    )
    assert row is not None
    return row


@router.get(
    "",
    response_model=list[FixedBlockExceptionOut],
    summary="列出固定块例外",
    description=(
        "可按 fixed_block_id 筛选。默认不返回软删除记录，"
        "也不返回父固定块已删除的记录；include_deleted=true 可全部查看。"
    ),
)
def list_all_exceptions(
    fixed_block_id: int | None = Query(None, description="固定块 ID"),
    active_only: bool = Query(False, description="只返回启用例外"),
    include_deleted: bool = Query(False, description="包含软删除例外及父块已删除的例外"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    where: list[str] = []
    params: list[object] = []
    if fixed_block_id is not None:
        where.append("fixed_block_id = ?")
        params.append(fixed_block_id)
    if not include_deleted:
        where.append("deleted_at IS NULL")
        where.append(
            "fixed_block_id IN (SELECT id FROM fixed_blocks WHERE deleted_at IS NULL)"
        )
    if active_only:
        where.append("is_active = 1")
    sql = "SELECT * FROM fixed_block_exceptions"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fixed_block_id, id"
    return fetch_all(conn, sql, tuple(params))


@router.get(
    "/{exception_id}",
    response_model=FixedBlockExceptionOut,
    summary="获取固定块例外",
    responses={404: {"description": "例外不存在或已删除"}},
)
def get_exception(
    exception_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return _get_exception(conn, exception_id)


@router.patch(
    "/{exception_id}",
    response_model=FixedBlockExceptionOut,
    summary="更新固定块例外",
    description="只更新传入的字段；更新后的时段和日期范围必须合法；已删除的例外不可更新。",
    responses={404: {"description": "例外不存在或已删除"}, 422: {"description": "字段组合非法"}},
)
def update_exception(
    exception_id: int,
    payload: FixedBlockExceptionUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    row = get_or_404(
        conn, "fixed_block_exceptions", exception_id, "固定块例外不存在"
    )
    changes = payload.model_dump(exclude_unset=True)
    _merged_create(row, changes)
    update_row(conn, "fixed_block_exceptions", exception_id, changes)
    return _get_exception(conn, exception_id)


@router.delete(
    "/{exception_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除固定块例外",
    description="只写入 deleted_at。",
    responses={404: {"description": "例外不存在"}},
)
def delete_exception(
    exception_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    soft_delete(conn, "fixed_block_exceptions", exception_id, "固定块例外不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{exception_id}/restore",
    response_model=FixedBlockExceptionOut,
    summary="恢复固定块例外",
    description="把 deleted_at 置空。",
    responses={404: {"description": "例外不存在"}},
)
def restore_exception(
    exception_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    restore_row(
        conn, "fixed_block_exceptions", exception_id, "固定块例外不存在"
    )
    return _get_exception(conn, exception_id)
