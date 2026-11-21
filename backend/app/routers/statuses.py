import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..database import fetch_all, fetch_one, get_db
from ..schemas import TaskStatusCreate, TaskStatusOut, TaskStatusUpdate
from ..utils import get_or_404, restore_row, soft_delete, update_row

router = APIRouter(prefix="/api/statuses", tags=["task-statuses"])

BUILTIN_STATUS_IDS = {1, 2, 3, 4, 5}


@router.get(
    "",
    response_model=list[TaskStatusOut],
    summary="列出任务状态",
    description=(
        "返回任务状态表，按 sort_order、id 排序。"
        "默认不返回软删除记录，include_deleted=true 可查看。"
    ),
)
def list_statuses(
    active_only: bool = Query(False, description="只返回启用状态"),
    include_deleted: bool = Query(False, description="包含软删除状态"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    sql = "SELECT * FROM task_statuses WHERE 1 = 1"
    if not include_deleted:
        sql += " AND deleted_at IS NULL"
    if active_only:
        sql += " AND is_active = 1"
    sql += " ORDER BY sort_order, id"
    return fetch_all(conn, sql)


@router.post(
    "",
    response_model=TaskStatusOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建任务状态",
    description="code 在未删除记录中必须唯一，创建后不可修改。",
    responses={409: {"description": "code 已存在"}},
)
def create_status(
    payload: TaskStatusCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    cursor = conn.execute(
        """
        INSERT INTO task_statuses(
            code, name, sort_order, remark, is_active, is_initial_filter
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            payload.code,
            payload.name,
            payload.sort_order,
            payload.remark,
            int(payload.is_active),
            int(payload.is_initial_filter),
        ),
    )
    conn.commit()
    row = fetch_one(
        conn, "SELECT * FROM task_statuses WHERE id = ?", (cursor.lastrowid,)
    )
    assert row is not None
    return row


@router.get(
    "/{status_id}",
    response_model=TaskStatusOut,
    summary="获取任务状态",
    responses={404: {"description": "状态不存在或已删除"}},
)
def get_status(
    status_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return get_or_404(conn, "task_statuses", status_id, "任务状态不存在")


@router.patch(
    "/{status_id}",
    response_model=TaskStatusOut,
    summary="更新任务状态",
    description="只更新传入的字段；code 不可修改；已软删除的状态不可更新。",
    responses={404: {"description": "状态不存在或已删除"}},
)
def update_status(
    status_id: int,
    payload: TaskStatusUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    get_or_404(conn, "task_statuses", status_id, "任务状态不存在")
    update_row(
        conn,
        "task_statuses",
        status_id,
        payload.model_dump(exclude_unset=True),
    )
    row = fetch_one(
        conn, "SELECT * FROM task_statuses WHERE id = ?", (status_id,)
    )
    assert row is not None
    return row


@router.delete(
    "/{status_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除任务状态",
    description="内置状态不可删除（请用 is_active 停用）；自定义状态只写入 deleted_at。",
    responses={404: {"description": "状态不存在"}, 409: {"description": "内置状态不可删除"}},
)
def delete_status(
    status_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    if status_id in BUILTIN_STATUS_IDS:
        raise HTTPException(status_code=409, detail="内置状态不能删除，请用 is_active 停用")
    soft_delete(conn, "task_statuses", status_id, "任务状态不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{status_id}/restore",
    response_model=TaskStatusOut,
    summary="恢复任务状态",
    description="把 deleted_at 置空；code 冲突时返回 409。",
    responses={404: {"description": "状态不存在"}, 409: {"description": "code 已被占用"}},
)
def restore_status(
    status_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    try:
        restore_row(conn, "task_statuses", status_id, "任务状态不存在")
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=409, detail="该 code 已被其他未删除状态占用"
        ) from exc
    row = fetch_one(
        conn, "SELECT * FROM task_statuses WHERE id = ?", (status_id,)
    )
    assert row is not None
    return row
