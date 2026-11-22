import sqlite3
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from ..database import fetch_all, get_db
from ..schemas import FixedOccurrenceOut

router = APIRouter(prefix="/api/plan", tags=["planning"])


def _merge_intervals(
    intervals: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged: list[list[int]] = [list(intervals[0])]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def _subtract(
    start: int,
    end: int,
    cuts: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = [(start, end)]
    for cut_start, cut_end in cuts:
        next_segments: list[tuple[int, int]] = []
        for seg_start, seg_end in segments:
            if cut_end <= seg_start or cut_start >= seg_end:
                next_segments.append((seg_start, seg_end))
                continue
            if seg_start < cut_start:
                next_segments.append((seg_start, cut_start))
            if cut_end < seg_end:
                next_segments.append((cut_end, seg_end))
        segments = next_segments
    return segments


def _load_active_blocks(conn: sqlite3.Connection) -> list[dict]:
    return fetch_all(
        conn,
        """
        SELECT *
        FROM fixed_blocks
        WHERE is_active = 1
          AND deleted_at IS NULL
        ORDER BY overlap_priority DESC, id
        """,
    )


def _load_active_exceptions(
    conn: sqlite3.Connection,
) -> dict[int, list[dict]]:
    rows = fetch_all(
        conn,
        """
        SELECT *
        FROM fixed_block_exceptions
        WHERE is_active = 1
          AND deleted_at IS NULL
        ORDER BY id
        """,
    )
    grouped: dict[int, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["fixed_block_id"], []).append(row)
    return grouped


def _block_matches(block: dict, on_date: date) -> bool:
    date_str = on_date.isoformat()
    effective_from = block["effective_from"]
    if effective_from is not None and effective_from > date_str:
        return False
    effective_to = block["effective_to"]
    if effective_to is not None and effective_to < date_str:
        return False
    recurrence = block["recurrence"]
    if recurrence == "daily":
        return True
    if recurrence == "weekly":
        return block["recurrence_value"] == on_date.isoweekday()
    if recurrence == "monthly":
        return block["recurrence_value"] == on_date.day
    return False


def _exception_cuts(
    block: dict,
    exceptions: list[dict],
    on_date: date,
) -> list[tuple[int, int]]:
    date_str = on_date.isoformat()
    iso_weekday = on_date.isoweekday()
    day_of_month = on_date.day
    cuts: list[tuple[int, int]] = []
    for exception in exceptions:
        if (
            exception["effective_from"] is not None
            and exception["effective_from"] > date_str
        ):
            continue
        if (
            exception["effective_to"] is not None
            and exception["effective_to"] < date_str
        ):
            continue
        if (
            exception["skip_date"] is not None
            and exception["skip_date"] != date_str
        ):
            continue
        if (
            exception["weekday"] is not None
            and exception["weekday"] != iso_weekday
        ):
            continue
        if (
            exception["day_of_month"] is not None
            and exception["day_of_month"] != day_of_month
        ):
            continue
        if (
            exception["start_minute"] is None
            or exception["end_minute"] is None
        ):
            cuts.append((block["start_minute"], block["end_minute"]))
            continue
        cut_start = max(block["start_minute"], exception["start_minute"])
        cut_end = min(block["end_minute"], exception["end_minute"])
        if cut_start < cut_end:
            cuts.append((cut_start, cut_end))
    return cuts


def _occurrences_for_date(
    blocks: list[dict],
    exceptions_by_block: dict[int, list[dict]],
    on_date: date,
) -> list[dict]:
    occurrences: list[dict] = []
    for block in blocks:
        if not _block_matches(block, on_date):
            continue
        cuts = _exception_cuts(
            block, exceptions_by_block.get(block["id"], []), on_date
        )
        for seg_start, seg_end in _subtract(
            block["start_minute"], block["end_minute"], _merge_intervals(cuts)
        ):
            occurrences.append(
                {
                    "fixed_block_id": block["id"],
                    "title": block["title"],
                    "date": on_date,
                    "start_minute": seg_start,
                    "end_minute": seg_end,
                    "overlap_priority": block["overlap_priority"],
                    "allow_task_schedule": bool(block["allow_task_schedule"]),
                    "remark": block["remark"],
                }
            )

    occurrences.sort(
        key=lambda item: (
            item["start_minute"],
            -item["overlap_priority"],
            item["fixed_block_id"],
        )
    )
    return occurrences


def compute_fixed_occurrences(
    conn: sqlite3.Connection,
    on_date: date,
) -> list[dict]:
    return _occurrences_for_date(
        _load_active_blocks(conn),
        _load_active_exceptions(conn),
        on_date,
    )


def compute_fixed_occurrences_range(
    conn: sqlite3.Connection,
    start: date,
    end: date,
) -> list[dict]:
    blocks = _load_active_blocks(conn)
    exceptions_by_block = _load_active_exceptions(conn)
    occurrences: list[dict] = []
    current = start
    while current <= end:
        occurrences.extend(
            _occurrences_for_date(blocks, exceptions_by_block, current)
        )
        current += timedelta(days=1)
    return occurrences


@router.get(
    "/fixed-occurrences",
    response_model=list[FixedOccurrenceOut],
    summary="计算某天实际发生的固定块",
    description=(
        "按 daily/weekly/monthly 规则匹配固定块，并应用生效日期和例外。"
        "例外只跳过：未填时段时跳过整个块，填写时段时只跳过重叠部分，"
        "因此同一固定块可能返回多段。时间段为左闭右开。"
    ),
)
def fixed_occurrences(
    on_date: date = Query(..., alias="date", description="日期，YYYY-MM-DD"),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[dict]:
    return compute_fixed_occurrences(conn, on_date)
