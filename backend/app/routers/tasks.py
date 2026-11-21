import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..database import fetch_all, fetch_one, get_db
from ..schemas import TaskCreate, TaskOut, TaskUpdate
from ..utils import (
    dt_to_db,
    get_or_404,
    get_timezone,
    now_utc,
    restore_row,
    soft_delete,
    update_row,
)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

CLOSED_STATUS_CODES = ("done", "cancelled")

TASK_SELECT = """
SELECT t.*,
       s.code AS status_code,
       s.name AS status_name,
       p.level AS priority_level,
       p.name AS priority_name,
       p.color AS priority_color
FROM tasks t
JOIN task_statuses s ON s.id = t.status_id
LEFT JOIN priority_levels p ON p.id = t.priority_level_id
"""

TASK_ORDER = """
        ORDER BY
          p.level IS NULL,
          p.level,
          t.deadline_at IS NULL,
          t.deadline_at,
          t.id DESC
"""


def _task_filters(
    *,
    status_code: list[str] | None,
    priority_level_id: list[int] | None,
    q: str | None,
    deadline_from: datetime | None,
    deadline_to: datetime | None,
    include_deleted: bool,
    tz: ZoneInfo,
) -> tuple[list[str], list[object]]:
    where: list[str] = []
    params: list[object] = []

    if not include_deleted:
        where.append("t.deleted_at IS NULL")
    if status_code:
        placeholders = ", ".join("?" for _ in status_code)
        where.append(f"s.code IN ({placeholders})")
        params.extend(status_code)
    if priority_level_id:
        placeholders = ", ".join("?" for _ in priority_level_id)
        where.append(f"t.priority_level_id IN ({placeholders})")
        params.extend(priority_level_id)
    if q:
        where.append("(t.title LIKE ? OR t.progress LIKE ? OR t.remark LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])
    if deadline_from is not None:
        where.append("t.deadline_at >= ?")
        params.append(dt_to_db(deadline_from, tz))
    if deadline_to is not None:
        where.append("t.deadline_at <= ?")
        params.append(dt_to_db(deadline_to, tz))

    return where, params


def _get_task(
    conn: sqlite3.Connection, task_id: int, include_deleted: bool = False
) -> dict:
    sql = TASK_SELECT + " WHERE t.id = ?"
    if not include_deleted:
        sql += " AND t.deleted_at IS NULL"
    row = fetch_one(conn, sql, (task_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return row


def _require_status(conn: sqlite3.Connection, status_id: int) -> dict:
    row = fetch_one(
        conn,
        "SELECT id, code FROM task_statuses WHERE id = ? AND deleted_at IS NULL",
        (status_id,),
    )
    if row is None:
        raise HTTPException(status_code=422, detail="status_id 对应的任务状态不存在")
    return row


def _require_priority(conn: sqlite3.Connection, priority_id: int | None) -> None:
    if priority_id is None:
        return
    row = fetch_one(
        conn,
        "SELECT id FROM priority_levels WHERE id = ? AND deleted_at IS NULL",
        (priority_id,),
    )
    if row is None:
        raise HTTPException(
            status_code=422, detail="priority_level_id 对应的优先级不存在"
        )


@router.get(
    "",
    response_model=list[TaskOut],
    summary="列出任务",
    description=(
        "按优先级、截止时间排序（无截止时间排最后）。"
        "status_code 传状态 code，如 todo、doing、blocked，可重复传多个（OR 关系）。"
        "priority_level_id 同样可重复传多个（OR 关系）。"
        "默认不返回软删除任务，include_deleted=true 可查看。"
    ),
)
def list_tasks(
    status_code: list[str] | None = Query(
        None, description="状态 code，可重复传多个（OR 关系），如 todo"
    ),
    priority_level_id: list[int] | None = Query(
        None, description="优先级 ID，可重复传多个（OR 关系）"
    ),
    q: str | None = Query(None, description="搜索标题、进度、备注"),
    deadline_from: datetime | None = Query(None, description="截止时间下限，ISO 8601"),
    deadline_to: datetime | None = Query(None, description="截止时间上限，ISO 8601"),
    include_deleted: bool = Query(False, description="包含软删除任务"),
    limit: int = Query(100, ge=1, le=500, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    tz = get_timezone(conn)
    where, params = _task_filters(
        status_code=status_code,
        priority_level_id=priority_level_id,
        q=q,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        include_deleted=include_deleted,
        tz=tz,
    )

    sql = TASK_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += TASK_ORDER + " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return fetch_all(conn, sql, tuple(params))


@router.get(
    "/unscheduled",
    response_model=list[TaskOut],
    summary="列出未排期任务",
    description=(
        "未排期任务指没有任何未删除任务排期的任务，与任务状态无关。"
        "默认排除已完成、已取消的任务，支持优先级、关键词和截止时间筛选。"
    ),
)
def list_unscheduled_tasks(
    priority_level_id: list[int] | None = Query(
        None, description="优先级 ID，可重复传多个（OR 关系）"
    ),
    q: str | None = Query(None, description="搜索标题、进度、备注"),
    deadline_from: datetime | None = Query(None, description="截止时间下限，ISO 8601"),
    deadline_to: datetime | None = Query(None, description="截止时间上限，ISO 8601"),
    include_deleted: bool = Query(False, description="包含软删除任务"),
    limit: int = Query(500, ge=1, le=500, description="返回条数"),
    offset: int = Query(0, ge=0, description="偏移量"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    tz = get_timezone(conn)
    where, params = _task_filters(
        status_code=None,
        priority_level_id=priority_level_id,
        q=q,
        deadline_from=deadline_from,
        deadline_to=deadline_to,
        include_deleted=include_deleted,
        tz=tz,
    )
    where.append(
        "NOT EXISTS ("
        "SELECT 1 FROM task_schedules ts "
        "WHERE ts.task_id = t.id AND ts.deleted_at IS NULL"
        ")"
    )
    placeholders = ", ".join("?" for _ in CLOSED_STATUS_CODES)
    where.append(f"s.code NOT IN ({placeholders})")
    params.extend(CLOSED_STATUS_CODES)

    sql = TASK_SELECT + " WHERE " + " AND ".join(where)
    sql += TASK_ORDER + " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return fetch_all(conn, sql, tuple(params))


@router.post(
    "",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建任务",
    description="创建任务；状态为 done（内置 id=4）时自动写入 completed_at。",
    responses={422: {"description": "状态或优先级不存在"}},
)
def create_task(
    payload: TaskCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    status_row = _require_status(conn, payload.status_id)
    _require_priority(conn, payload.priority_level_id)
    completed_at = now_utc() if status_row["code"] == "done" else None
    tz = get_timezone(conn)

    cursor = conn.execute(
        """
        INSERT INTO tasks(
          title, priority_level_id, status_id, deadline_at,
          progress, remark, completed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.title,
            payload.priority_level_id,
            payload.status_id,
            dt_to_db(payload.deadline_at, tz),
            payload.progress,
            payload.remark,
            completed_at,
        ),
    )
    conn.commit()
    return _get_task(conn, int(cursor.lastrowid))


@router.get(
    "/{task_id}",
    response_model=TaskOut,
    summary="获取任务",
    responses={404: {"description": "任务不存在或已删除"}},
)
def get_task(
    task_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return _get_task(conn, task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskOut,
    summary="更新任务",
    description=(
        "只更新传入的字段。状态切换到 done 时补 completed_at，"
        "切出 done 时清空 completed_at；已软删除的任务不可更新。"
    ),
    responses={404: {"description": "任务不存在或已删除"}, 422: {"description": "状态或优先级不存在"}},
)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    current = get_or_404(conn, "tasks", task_id, "任务不存在")
    changes = payload.model_dump(exclude_unset=True)

    if "title" in changes and changes["title"] is None:
        raise HTTPException(status_code=422, detail="title 不能为 null")
    if "status_id" in changes:
        if changes["status_id"] is None:
            raise HTTPException(status_code=422, detail="status_id 不能为 null")
        new_status = _require_status(conn, int(changes["status_id"]))
        if new_status["code"] == "done":
            if current["completed_at"] is None:
                changes["completed_at"] = now_utc()
        else:
            changes["completed_at"] = None
    if "priority_level_id" in changes:
        _require_priority(conn, changes["priority_level_id"])

    update_row(conn, "tasks", task_id, changes)
    return _get_task(conn, task_id)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除任务",
    description="只写入 deleted_at；任务排期保留，恢复任务后重新可见。",
    responses={404: {"description": "任务不存在"}},
)
def delete_task(
    task_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    soft_delete(conn, "tasks", task_id, "任务不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{task_id}/restore",
    response_model=TaskOut,
    summary="恢复任务",
    description="把 deleted_at 置空；若任务未删除则原样返回。",
    responses={404: {"description": "任务不存在"}},
)
def restore_task(
    task_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    restore_row(conn, "tasks", task_id, "任务不存在")
    return _get_task(conn, task_id)
