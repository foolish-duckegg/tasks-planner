import sqlite3
from datetime import date

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


def compute_fixed_occurrences(
    conn: sqlite3.Connection,
    on_date: date,
) -> list[dict]:
    date_str = on_date.isoformat()
    iso_weekday = on_date.isoweekday()
    day_of_month = on_date.day

    blocks = fetch_all(
        conn,
        """
        SELECT *
        FROM fixed_blocks
        WHERE is_active = 1
          AND deleted_at IS NULL
          AND (effective_from IS NULL OR effective_from <= ?)
          AND (effective_to   IS NULL OR effective_to   >= ?)
          AND (
                recurrence = 'daily'
            OR (recurrence = 'weekly'  AND recurrence_value = ?)
            OR (recurrence = 'monthly' AND recurrence_value = ?)
          )
        ORDER BY overlap_priority DESC, id
        """,
        (date_str, date_str, iso_weekday, day_of_month),
    )

    occurrences: list[dict] = []
    for block in blocks:
        exceptions = fetch_all(
            conn,
            """
            SELECT *
            FROM fixed_block_exceptions
            WHERE fixed_block_id = ?
              AND is_active = 1
              AND deleted_at IS NULL
              AND (effective_from IS NULL OR effective_from <= ?)
              AND (effective_to   IS NULL OR effective_to   >= ?)
              AND (skip_date      IS NULL OR skip_date      = ?)
              AND (weekday        IS NULL OR weekday        = ?)
              AND (day_of_month   IS NULL OR day_of_month   = ?)
            ORDER BY id
            """,
            (
                block["id"],
                date_str,
                date_str,
                date_str,
                iso_weekday,
                day_of_month,
            ),
        )

        cuts: list[tuple[int, int]] = []
        for exception in exceptions:
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
