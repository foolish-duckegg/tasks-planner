import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..database import fetch_all, fetch_one, get_db
from ..schemas import PriorityLevelCreate, PriorityLevelOut, PriorityLevelUpdate
from ..utils import get_or_404, restore_row, soft_delete, update_row

router = APIRouter(prefix="/api/priorities", tags=["priority-levels"])


@router.get(
    "",
    response_model=list[PriorityLevelOut],
    summary="列出优先级",
    description=(
        "按 level 升序返回，level=1 最高。"
        "默认不返回软删除记录，include_deleted=true 可查看。"
    ),
)
def list_priorities(
    active_only: bool = Query(False, description="只返回启用优先级"),
    include_deleted: bool = Query(False, description="包含软删除优先级"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    sql = "SELECT * FROM priority_levels WHERE 1 = 1"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY level, id"
    return fetch_all(conn, sql)


@router.post(
    "",
    response_model=PriorityLevelOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建优先级",
    description="level 在未删除记录中必须唯一，1 表示最高优先级。",
    responses={409: {"description": "level 已存在"}},
)
def create_priority(
    payload: PriorityLevelCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    cursor = conn.execute(
        """
        INSERT INTO priority_levels(level, name, usage, remark, color, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.level,
            payload.name,
            payload.usage,
            payload.remark,
            payload.color,
            int(payload.is_active),
        ),
    )
    conn.commit()
    row = fetch_one(
        conn, "SELECT * FROM priority_levels WHERE id = ?", (cursor.lastrowid,)
    )
    assert row is not None
    return row


@router.get(
    "/{priority_id}",
    response_model=PriorityLevelOut,
    summary="获取优先级",
    responses={404: {"description": "优先级不存在或已删除"}},
)
def get_priority(
    priority_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return get_or_404(conn, "priority_levels", priority_id, "优先级不存在")


@router.patch(
    "/{priority_id}",
    response_model=PriorityLevelOut,
    summary="更新优先级",
    description="只更新传入的字段；level 在未删除记录中冲突会返回 409。",
    responses={404: {"description": "优先级不存在或已删除"}, 409: {"description": "level 已存在"}},
)
def update_priority(
    priority_id: int,
    payload: PriorityLevelUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    get_or_404(conn, "priority_levels", priority_id, "优先级不存在")
    update_row(
        conn,
        "priority_levels",
        priority_id,
        payload.model_dump(exclude_unset=True),
    )
    row = fetch_one(
        conn, "SELECT * FROM priority_levels WHERE id = ?", (priority_id,)
    )
    assert row is not None
    return row


@router.delete(
    "/{priority_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除优先级",
    description="只写入 deleted_at，任务上的历史引用保留。",
    responses={404: {"description": "优先级不存在"}},
)
def delete_priority(
    priority_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    soft_delete(conn, "priority_levels", priority_id, "优先级不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{priority_id}/restore",
    response_model=PriorityLevelOut,
    summary="恢复优先级",
    description="把 deleted_at 置空；level 冲突时返回 409。",
    responses={404: {"description": "优先级不存在"}, 409: {"description": "level 已被占用"}},
)
def restore_priority(
    priority_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        restore_row(conn, "priority_levels", priority_id, "优先级不存在")
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=409, detail="该 level 已被其他未删除优先级占用"
        ) from exc
    row = fetch_one(
        conn, "SELECT * FROM priority_levels WHERE id = ?", (priority_id,)
    )
    assert row is not None
    return row
