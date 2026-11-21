import calendar
import sqlite3
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, status

from ..database import fetch_all, get_db
from ..schemas import DailyMemoCreate, DailyMemoOut
from ..utils import get_or_404

router = APIRouter(prefix="/api/memos", tags=["daily-memos"])

Period = Literal["day", "week", "month"]


def _week_start(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = 'week_start'"
    ).fetchone()
    try:
        value = int(row["value"]) if row is not None else 1
    except (TypeError, ValueError):
        value = 1
    return value if 1 <= value <= 7 else 1


def _period_range(
    conn: sqlite3.Connection, period: Period, on_date: date
) -> tuple[date, date]:
    if period == "week":
        week_start = _week_start(conn)
        diff = (on_date.isoweekday() - week_start) % 7
        start = on_date - timedelta(days=diff)
        return start, start + timedelta(days=6)
    if period == "month":
        start = on_date.replace(day=1)
        last_day = calendar.monthrange(on_date.year, on_date.month)[1]
        return start, on_date.replace(day=last_day)
    return on_date, on_date


def _get_memo(conn: sqlite3.Connection, memo_id: int) -> dict:
    return get_or_404(conn, "daily_memos", memo_id, "备忘录不存在")


def _list_memos_by_date(
    conn: sqlite3.Connection, memo_date: date
) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT * FROM daily_memos
        WHERE memo_date = ? AND deleted_at IS NULL
        ORDER BY id
        """,
        (memo_date.isoformat(),),
    )


@router.get(
    "",
    response_model=list[DailyMemoOut],
    summary="按天/周/月列出备忘录",
    description=(
        "period=day 返回 date 当天；period=week 按 app_meta.week_start 计算所在周；"
        "period=month 返回 date 所在自然月。结果按日期、创建顺序升序。"
        "备忘录只允许新增，不支持修改和删除，同一天可以有多条。"
    ),
)
def list_memos(
    period: Period = Query("day", description="时间范围：day / week / month"),
    on_date: date = Query(..., alias="date", description="基准日期，YYYY-MM-DD"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    start, end = _period_range(conn, period, on_date)
    return fetch_all(
        conn,
        """
        SELECT * FROM daily_memos
        WHERE memo_date BETWEEN ? AND ? AND deleted_at IS NULL
        ORDER BY memo_date, id
        """,
        (start.isoformat(), end.isoformat()),
    )


@router.get(
    "/by-date/{memo_date}",
    response_model=list[DailyMemoOut],
    summary="按日期获取备忘录",
    description="返回该日期的全部备忘录，按创建顺序升序；没有记录时返回空数组。",
)
def get_memo_by_date(
    memo_date: date,
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return _list_memos_by_date(conn, memo_date)


@router.post(
    "",
    response_model=DailyMemoOut,
    status_code=status.HTTP_201_CREATED,
    summary="新增备忘录",
    description=(
        "新增一条备忘录，同一天可以有多条。创建后不支持修改和删除。"
    ),
)
def create_memo(
    payload: DailyMemoCreate,
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    cursor = conn.execute(
        "INSERT INTO daily_memos(memo_date, content) VALUES (?, ?)",
        (payload.memo_date.isoformat(), payload.content),
    )
    conn.commit()
    return _get_memo(conn, int(cursor.lastrowid))
