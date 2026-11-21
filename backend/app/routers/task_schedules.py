import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from ..database import fetch_all, fetch_one, get_db
from ..schemas import TaskScheduleCreate, TaskScheduleOut, TaskScheduleUpdate
from ..utils import restore_row, soft_delete, update_row
from .plan import compute_fixed_occurrences

router = APIRouter(prefix="/api/task-schedules", tags=["task-schedules"])

SCHEDULE_SELECT = """
SELECT s.*, t.title AS task_title
FROM task_schedules s
JOIN tasks t ON t.id = s.task_id
"""


def _get_schedule(
    conn: sqlite3.Connection, schedule_id: int, include_deleted: bool = False
) -> dict:
    sql = SCHEDULE_SELECT + " WHERE s.id = ?"
    if not include_deleted:
        sql += " AND s.deleted_at IS NULL AND t.deleted_at IS NULL"
    row = fetch_one(conn, sql, (schedule_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="任务排期不存在")
    return row


def _require_task(conn: sqlite3.Connection, task_id: int) -> None:
    row = fetch_one(
        conn,
        "SELECT id FROM tasks WHERE id = ? AND deleted_at IS NULL",
        (task_id,),
    )
    if row is None:
        raise HTTPException(status_code=422, detail="task_id 对应的任务不存在")


def _merged_create(row: dict, changes: dict) -> TaskScheduleCreate:
    merged = {field: row[field] for field in TaskScheduleCreate.model_fields}
    merged.update(changes)
    return TaskScheduleCreate(**merged)


def _overlaps(
    first_start: int,
    first_end: int,
    second_start: int,
    second_end: int,
) -> bool:
    return first_start < second_end and second_start < first_end


def _find_conflicts(
    conn: sqlite3.Connection,
    payload: TaskScheduleCreate,
    exclude_id: int | None = None,
) -> list[dict]:
    conflicts: list[dict] = []
    for occurrence in compute_fixed_occurrences(conn, payload.plan_date):
        if occurrence["allow_task_schedule"]:
            continue
        if _overlaps(
            payload.start_minute,
            payload.end_minute,
            occurrence["start_minute"],
            occurrence["end_minute"],
        ):
            conflicts.append(
                {
                    "type": "fixed_block",
                    "fixed_block_id": occurrence["fixed_block_id"],
                    "title": occurrence["title"],
                    "start_minute": occurrence["start_minute"],
                    "end_minute": occurrence["end_minute"],
                }
            )

    sql = """
        SELECT s.id, s.task_id, s.start_minute, s.end_minute, t.title AS task_title
        FROM task_schedules s
        JOIN tasks t ON t.id = s.task_id
        WHERE s.plan_date = ?
          AND s.deleted_at IS NULL
          AND t.deleted_at IS NULL
          AND s.status <> 'skipped'
    """
    params: list[object] = [payload.plan_date.isoformat()]
    if exclude_id is not None:
        sql += " AND s.id <> ?"
        params.append(exclude_id)
    for row in fetch_all(conn, sql, tuple(params)):
        if _overlaps(
            payload.start_minute,
            payload.end_minute,
            row["start_minute"],
            row["end_minute"],
        ):
            conflicts.append(
                {
                    "type": "task_schedule",
                    "schedule_id": row["id"],
                    "task_id": row["task_id"],
                    "task_title": row["task_title"],
                    "start_minute": row["start_minute"],
                    "end_minute": row["end_minute"],
                }
            )
    return conflicts


def _ensure_no_conflicts(
    conn: sqlite3.Connection,
    payload: TaskScheduleCreate,
    exclude_id: int | None = None,
) -> None:
    if payload.status == "skipped":
        return
    conflicts = _find_conflicts(conn, payload, exclude_id)
    if conflicts:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "任务排期存在冲突",
                "conflicts": conflicts,
            },
        )


@router.get(
    "",
    response_model=list[TaskScheduleOut],
    summary="列出任务排期",
    description=(
        "按日期和开始时间排序，可同时按日期、任务、状态筛选。"
        "默认排除软删除排期及其所属任务已删除的排期。"
    ),
)
def list_schedules(
    plan_date: date | None = Query(None, alias="date", description="排期日期"),
    task_id: int | None = Query(None, description="任务 ID"),
    schedule_status: str | None = Query(
        None,
        alias="status",
        pattern="^(planned|done|skipped)$",
        description="排期状态",
    ),
    include_deleted: bool = Query(False, description="包含软删除排期"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    where: list[str] = []
    params: list[object] = []
    if not include_deleted:
        where.append("s.deleted_at IS NULL")
        where.append("t.deleted_at IS NULL")
    if plan_date is not None:
        where.append("s.plan_date = ?")
        params.append(plan_date.isoformat())
    if task_id is not None:
        where.append("s.task_id = ?")
        params.append(task_id)
    if schedule_status is not None:
        where.append("s.status = ?")
        params.append(schedule_status)

    sql = SCHEDULE_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY s.plan_date, s.start_minute, s.id"
    return fetch_all(conn, sql, tuple(params))


@router.post(
    "",
    response_model=TaskScheduleOut,
    status_code=status.HTTP_201_CREATED,
    summary="新建任务排期",
    description=(
        "把任务安排到某天的某个时间段。"
        "若与 allow_task_schedule = 0 的固定块重叠，或与同一天未删除、未跳过的其他排期重叠，"
        "返回 409 并列出冲突。"
    ),
    responses={
        422: {"description": "任务不存在或时间范围非法"},
        409: {"description": "与固定块或其他任务排期冲突"},
    },
)
def create_schedule(
    payload: TaskScheduleCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    _require_task(conn, payload.task_id)
    _ensure_no_conflicts(conn, payload)
    cursor = conn.execute(
        """
        INSERT INTO task_schedules(
          task_id, plan_date, start_minute, end_minute,
          status, allow_override, note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload.task_id,
            payload.plan_date.isoformat(),
            payload.start_minute,
            payload.end_minute,
            payload.status,
            int(payload.allow_override),
            payload.note,
        ),
    )
    conn.commit()
    return _get_schedule(conn, int(cursor.lastrowid))


@router.get(
    "/{schedule_id}",
    response_model=TaskScheduleOut,
    summary="获取任务排期",
    responses={404: {"description": "排期不存在、已删除或任务已删除"}},
)
def get_schedule(
    schedule_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    return _get_schedule(conn, schedule_id)


@router.patch(
    "/{schedule_id}",
    response_model=TaskScheduleOut,
    summary="更新任务排期",
    description=(
        "只更新传入的字段；修改后的时间范围和任务引用必须合法；已删除的排期不可更新。"
        "若更新后与 allow_task_schedule = 0 的固定块重叠，或与同一天未删除、未跳过的其他排期重叠，"
        "返回 409 并列出冲突。"
    ),
    responses={
        404: {"description": "排期不存在或已删除"},
        422: {"description": "任务不存在或字段非法"},
        409: {"description": "与固定块或其他任务排期冲突"},
    },
)
def update_schedule(
    schedule_id: int,
    payload: TaskScheduleUpdate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    row = _get_schedule(conn, schedule_id)
    changes = payload.model_dump(exclude_unset=True)
    if "task_id" in changes:
        if changes["task_id"] is None:
            raise HTTPException(status_code=422, detail="task_id 不能为 null")
        _require_task(conn, int(changes["task_id"]))
    merged = _merged_create(row, changes)
    if {"plan_date", "start_minute", "end_minute", "task_id", "status"} & changes.keys():
        _ensure_no_conflicts(conn, merged, exclude_id=schedule_id)
    update_row(conn, "task_schedules", schedule_id, changes)
    return _get_schedule(conn, schedule_id)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="软删除任务排期",
    description="只写入 deleted_at，恢复后重新出现在列表中。",
    responses={404: {"description": "排期不存在"}},
)
def delete_schedule(
    schedule_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> Response:
    soft_delete(conn, "task_schedules", schedule_id, "任务排期不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{schedule_id}/restore",
    response_model=TaskScheduleOut,
    summary="恢复任务排期",
    description="把 deleted_at 置空；若所属任务已删除，排期仍保持隐藏。",
    responses={404: {"description": "排期不存在"}},
)
def restore_schedule(
    schedule_id: int,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    restore_row(conn, "task_schedules", schedule_id, "任务排期不存在")
    return _get_schedule(conn, schedule_id, include_deleted=True)
