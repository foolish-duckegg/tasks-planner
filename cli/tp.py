#!/usr/bin/env python3
"""Command line interface for the local tasks-planner API.

Examples:
    python3 cli/tp.py health
    python3 cli/tp.py task list --status todo
    python3 cli/tp.py task add "写周报" --priority P1 --deadline 2026-11-22
    python3 cli/tp.py memo list --period week
    python3 cli/tp.py memo add "今天先把接口做完"
    python3 cli/tp.py plan day 2026-11-20
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date as date_cls
from datetime import timedelta
from typing import Any, Callable

from api import ApiClient, ApiError, invalidate_lookups, resolve_priority, resolve_status
from fmt import (
    fmt_minute,
    fmt_range,
    key_values,
    normalize_deadline,
    parse_minute,
    print_json,
    table,
)

WEEKDAYS = "一二三四五六日"
DEFAULT_API = os.environ.get("TASKS_PLANNER_API", "http://127.0.0.1:56649/api")

Renderer = Callable[[Any], str]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def emit(args: argparse.Namespace, data: Any, render: Renderer | None = None) -> None:
    if args.json or render is None:
        print_json(data)
    else:
        print(render(data))


def resolve_date(value: str) -> str:
    text = value.strip().lower()
    today = date_cls.today()
    if text in {"today", "今天"}:
        return today.isoformat()
    if text in {"tomorrow", "明天"}:
        return (today + timedelta(days=1)).isoformat()
    if text in {"yesterday", "昨天"}:
        return (today - timedelta(days=1)).isoformat()
    return value.strip()


def weekday_label(value: str) -> str:
    try:
        return "周" + WEEKDAYS[date_cls.fromisoformat(value).weekday()]
    except ValueError:
        return ""


def short_dt(value: Any) -> str:
    if not value:
        return "-"
    return str(value).replace("T", " ")[:16]


def build(client: ApiClient, method: str, path: str, payload: dict[str, Any]) -> Any:
    if not payload:
        return None
    return client.request(method, path, body=payload)


def active_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--active", dest="is_active", action="store_true", help="启用")
    parser.add_argument("--inactive", dest="is_active", action="store_false", help="停用")
    parser.set_defaults(is_active=None)


def create_active_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--inactive", dest="is_active", action="store_false", help="创建后停用")
    parser.set_defaults(is_active=True)


def initial_filter_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--initial-filter",
        dest="is_initial_filter",
        action="store_true",
        help="纳入任务列表初始筛选",
    )
    parser.add_argument(
        "--no-initial-filter",
        dest="is_initial_filter",
        action="store_false",
        help="不纳入任务列表初始筛选",
    )
    parser.set_defaults(is_initial_filter=None)


def create_initial_filter_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-initial-filter",
        dest="is_initial_filter",
        action="store_false",
        help="不纳入任务列表初始筛选",
    )
    parser.set_defaults(is_initial_filter=True)


# --------------------------------------------------------------------------- #
# renderers
# --------------------------------------------------------------------------- #


def render_task(task: dict[str, Any]) -> str:
    priority = "-"
    if task.get("priority_name") is not None:
        priority = f"{task['priority_name']} (L{task['priority_level']})"
    return key_values(
        {
            "id": task["id"],
            "title": task["title"],
            "status": f"{task['status_code']} / {task['status_name']}",
            "priority": priority,
            "deadline": short_dt(task.get("deadline_at")),
            "completed": short_dt(task.get("completed_at")),
            "progress": task.get("progress"),
            "remark": task.get("remark"),
            "deleted": short_dt(task.get("deleted_at")) if task.get("deleted_at") else "-",
        }
    )


def task_rows(tasks: list[dict[str, Any]]) -> str:
    rows = [
        [
            task["id"],
            task["status_code"],
            task.get("priority_name") or "-",
            short_dt(task.get("deadline_at")),
            task["title"],
            (task.get("progress") or "").replace("\n", " "),
        ]
        for task in tasks
    ]
    return table(["ID", "STATUS", "PRI", "DEADLINE", "TITLE", "PROGRESS"], rows)


def status_rows(items: list[dict[str, Any]]) -> str:
    return table(
        ["ID", "CODE", "NAME", "SORT", "ACTIVE", "INIT", "REMARK"],
        [
            [
                i["id"],
                i["code"],
                i["name"],
                i["sort_order"],
                i["is_active"],
                i["is_initial_filter"],
                i.get("remark"),
            ]
            for i in items
        ],
    )


def priority_rows(items: list[dict[str, Any]]) -> str:
    return table(
        ["ID", "LEVEL", "NAME", "ACTIVE", "COLOR", "USAGE"],
        [[i["id"], i["level"], i["name"], i["is_active"], i.get("color"), i.get("usage")] for i in items],
    )


def dayblock_rows(items: list[dict[str, Any]]) -> str:
    return table(
        ["ID", "START", "END", "LABEL", "KIND", "ACTIVE", "REMARK"],
        [
            [i["id"], fmt_minute(i["start_minute"]), fmt_minute(i["end_minute"]), i.get("label"), i.get("kind"), i["is_active"], i.get("remark")]
            for i in items
        ],
    )


def fixed_rows(items: list[dict[str, Any]]) -> str:
    def recurrence(item: dict[str, Any]) -> str:
        value = item.get("recurrence_value")
        if item["recurrence"] == "weekly":
            return f"weekly/{WEEKDAYS[int(value) - 1]}"
        if item["recurrence"] == "monthly":
            return f"monthly/{value}"
        return "daily"

    def effective(item: dict[str, Any]) -> str:
        start = item.get("effective_from") or "…"
        end = item.get("effective_to") or "…"
        if not item.get("effective_from") and not item.get("effective_to"):
            return "always"
        return f"{start}~{end}"

    return table(
        ["ID", "TITLE", "RECUR", "TIME", "EFFECTIVE", "OVERLAP", "ACTIVE"],
        [
            [i["id"], i["title"], recurrence(i), fmt_range(i["start_minute"], i["end_minute"]), effective(i), i["overlap_priority"], i["is_active"]]
            for i in items
        ],
    )


def exception_rows(items: list[dict[str, Any]]) -> str:
    def condition(item: dict[str, Any]) -> str:
        parts = []
        if item.get("skip_date"):
            parts.append(f"date={item['skip_date']}")
        if item.get("weekday"):
            parts.append(f"weekday={item['weekday']}")
        if item.get("day_of_month"):
            parts.append(f"dom={item['day_of_month']}")
        if item.get("effective_from") or item.get("effective_to"):
            parts.append(f"range={item.get('effective_from') or '…'}~{item.get('effective_to') or '…'}")
        return " ".join(parts) or "every occurrence"

    def skip_time(item: dict[str, Any]) -> str:
        if item.get("start_minute") is None:
            return "whole block"
        return fmt_range(item["start_minute"], item["end_minute"])

    return table(
        ["ID", "BLOCK", "CONDITION", "SKIP", "ACTIVE", "REMARK"],
        [[i["id"], i["fixed_block_id"], condition(i), skip_time(i), i["is_active"], i.get("remark")] for i in items],
    )


def schedule_rows(items: list[dict[str, Any]]) -> str:
    return table(
        ["ID", "DATE", "TIME", "STATUS", "TASK", "TITLE", "NOTE"],
        [
            [i["id"], i["plan_date"], fmt_range(i["start_minute"], i["end_minute"]), i["status"], i["task_id"], i["task_title"], i.get("note")]
            for i in items
        ],
    )


def occurrence_rows(items: list[dict[str, Any]]) -> str:
    return table(
        ["LOG", "BLOCK", "DATE", "TIME", "STATUS", "TITLE", "NOTE"],
        [
            [
                i.get("log_id") or "-",
                i["fixed_block_id"],
                i["date"],
                fmt_range(i["start_minute"], i["end_minute"]),
                i.get("status") or "unmarked",
                i["title"],
                i.get("note"),
            ]
            for i in items
        ],
    )


def render_memo(memo: dict[str, Any]) -> str:
    return key_values(
        {
            "id": memo["id"],
            "date": memo["memo_date"],
            "weekday": weekday_label(memo["memo_date"]),
            "content": memo.get("content"),
            "created": short_dt(memo.get("created_at")),
        }
    )


def memo_rows(items: list[dict[str, Any]]) -> str:
    return table(
        ["ID", "DATE", "WEEKDAY", "CONTENT"],
        [
            [
                item["id"],
                item["memo_date"],
                weekday_label(item["memo_date"]),
                (item.get("content") or "").replace("\n", " "),
            ]
            for item in items
        ],
    )


# --------------------------------------------------------------------------- #
# interval helpers (used by plan day)
# --------------------------------------------------------------------------- #


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(start, end) for start, end in merged]


def subtract_intervals(base: tuple[int, int], cuts: list[tuple[int, int]]) -> list[tuple[int, int]]:
    segments = [base]
    for cut_start, cut_end in merge_intervals(cuts):
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


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


# --------------------------------------------------------------------------- #
# command handlers
# --------------------------------------------------------------------------- #


def cmd_health(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.get("/health"))


def cmd_meta_get(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.get("/meta"), lambda data: key_values(data))


def cmd_meta_set(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.put(f"/meta/{args.key}", {"value": args.value}), lambda data: key_values(data))


def cmd_status_list(args: argparse.Namespace, client: ApiClient) -> None:
    params = {"active_only": args.active_only, "include_deleted": args.all}
    emit(args, client.get("/statuses", params), status_rows)


def cmd_status_get(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.get(f"/statuses/{args.id}"), lambda item: key_values(item))


def cmd_status_create(args: argparse.Namespace, client: ApiClient) -> None:
    payload = {
        "code": args.code,
        "name": args.name,
        "sort_order": args.sort,
        "remark": args.remark,
        "is_active": args.is_active,
        "is_initial_filter": args.is_initial_filter,
    }
    invalidate_lookups()
    emit(args, client.post("/statuses", payload), lambda item: key_values(item))


def cmd_status_update(args: argparse.Namespace, client: ApiClient) -> None:
    payload: dict[str, Any] = {}
    for field, value in (("name", args.name), ("sort_order", args.sort), ("remark", args.remark), ("is_active", args.is_active), ("is_initial_filter", args.is_initial_filter)):
        if value is not None:
            payload[field] = value
    invalidate_lookups()
    emit(args, build(client, "PATCH", f"/statuses/{args.id}", payload), lambda item: key_values(item))


def cmd_status_delete(args: argparse.Namespace, client: ApiClient) -> None:
    client.delete(f"/statuses/{args.id}")
    invalidate_lookups()
    emit(args, {"deleted": args.id}, lambda data: f"deleted status #{data['deleted']}")


def cmd_status_restore(args: argparse.Namespace, client: ApiClient) -> None:
    invalidate_lookups()
    emit(args, client.post(f"/statuses/{args.id}/restore"), lambda item: key_values(item))


def cmd_priority_list(args: argparse.Namespace, client: ApiClient) -> None:
    params = {"active_only": args.active_only, "include_deleted": args.all}
    emit(args, client.get("/priorities", params), priority_rows)


def cmd_priority_get(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.get(f"/priorities/{args.id}"), lambda item: key_values(item))


def cmd_priority_create(args: argparse.Namespace, client: ApiClient) -> None:
    payload = {
        "level": args.level,
        "name": args.name,
        "usage": args.usage,
        "remark": args.remark,
        "color": args.color,
        "is_active": args.is_active,
    }
    invalidate_lookups()
    emit(args, client.post("/priorities", payload), lambda item: key_values(item))


def cmd_priority_update(args: argparse.Namespace, client: ApiClient) -> None:
    payload: dict[str, Any] = {}
    for field, value in (
        ("level", args.level),
        ("name", args.name),
        ("usage", args.usage),
        ("remark", args.remark),
        ("color", args.color),
        ("is_active", args.is_active),
    ):
        if value is not None:
            payload[field] = value
    invalidate_lookups()
    emit(args, build(client, "PATCH", f"/priorities/{args.id}", payload), lambda item: key_values(item))


def cmd_priority_delete(args: argparse.Namespace, client: ApiClient) -> None:
    client.delete(f"/priorities/{args.id}")
    invalidate_lookups()
    emit(args, {"deleted": args.id}, lambda data: f"deleted priority #{data['deleted']}")


def cmd_priority_restore(args: argparse.Namespace, client: ApiClient) -> None:
    invalidate_lookups()
    emit(args, client.post(f"/priorities/{args.id}/restore"), lambda item: key_values(item))


def cmd_task_list(args: argparse.Namespace, client: ApiClient) -> None:
    params: dict[str, Any] = {
        "q": args.q,
        "deadline_from": normalize_deadline(args.deadline_from) if args.deadline_from else None,
        "deadline_to": normalize_deadline(args.deadline_to) if args.deadline_to else None,
        "include_deleted": args.all,
        "limit": args.limit,
        "offset": args.offset,
    }
    if args.status:
        params["status_code"] = [
            resolve_status(client, value)["code"] for value in args.status
        ]
    if args.priority:
        params["priority_level_id"] = [
            resolve_priority(client, value)["id"] for value in args.priority
        ]
    tasks = client.get("/tasks", params)
    if args.open:
        tasks = [task for task in tasks if task["status_code"] not in {"done", "cancelled"}]
    emit(args, tasks, task_rows)


def cmd_task_unscheduled(args: argparse.Namespace, client: ApiClient) -> None:
    params: dict[str, Any] = {
        "q": args.q,
        "deadline_from": normalize_deadline(args.deadline_from) if args.deadline_from else None,
        "deadline_to": normalize_deadline(args.deadline_to) if args.deadline_to else None,
        "limit": args.limit,
        "offset": args.offset,
    }
    if args.priority:
        params["priority_level_id"] = [
            resolve_priority(client, value)["id"] for value in args.priority
        ]
    emit(args, client.get("/tasks/unscheduled", params), task_rows)


def cmd_task_get(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.get(f"/tasks/{args.id}"), render_task)


def cmd_task_add(args: argparse.Namespace, client: ApiClient) -> None:
    payload: dict[str, Any] = {"title": args.title}
    if args.priority is not None:
        payload["priority_level_id"] = resolve_priority(client, args.priority)["id"]
    if args.status is not None:
        payload["status_id"] = resolve_status(client, args.status)["id"]
    if args.deadline is not None:
        payload["deadline_at"] = normalize_deadline(args.deadline)
    if args.progress is not None:
        payload["progress"] = args.progress
    if args.remark is not None:
        payload["remark"] = args.remark
    emit(args, client.post("/tasks", payload), render_task)


def cmd_task_update(args: argparse.Namespace, client: ApiClient) -> None:
    payload: dict[str, Any] = {}
    if args.title is not None:
        payload["title"] = args.title
    if args.priority is not None:
        payload["priority_level_id"] = resolve_priority(client, args.priority)["id"]
    if args.no_priority:
        payload["priority_level_id"] = None
    if args.status is not None:
        payload["status_id"] = resolve_status(client, args.status)["id"]
    if args.deadline is not None:
        payload["deadline_at"] = normalize_deadline(args.deadline)
    if args.clear_deadline:
        payload["deadline_at"] = None
    if args.progress is not None:
        payload["progress"] = args.progress
    if args.clear_progress:
        payload["progress"] = None
    if args.remark is not None:
        payload["remark"] = args.remark
    if args.clear_remark:
        payload["remark"] = None
    emit(args, build(client, "PATCH", f"/tasks/{args.id}", payload), render_task)


def cmd_task_status(args: argparse.Namespace, client: ApiClient, status: str) -> None:
    status_id = resolve_status(client, status)["id"]
    emit(args, client.patch(f"/tasks/{args.id}", {"status_id": status_id}), render_task)


def cmd_task_delete(args: argparse.Namespace, client: ApiClient) -> None:
    client.delete(f"/tasks/{args.id}")
    emit(args, {"deleted": args.id}, lambda data: f"deleted task #{data['deleted']}")


def cmd_task_restore(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.post(f"/tasks/{args.id}/restore"), render_task)


def cmd_dayblock_list(args: argparse.Namespace, client: ApiClient) -> None:
    params = {"active_only": args.active_only, "include_deleted": args.all}
    emit(args, client.get("/day-blocks", params), dayblock_rows)


def cmd_dayblock_add(args: argparse.Namespace, client: ApiClient) -> None:
    payload = {
        "start_minute": parse_minute(args.start),
        "end_minute": parse_minute(args.end, end=True),
        "label": args.label,
        "kind": args.kind,
        "remark": args.remark,
        "is_active": args.is_active,
    }
    emit(args, client.post("/day-blocks", payload), lambda item: key_values(item))


def cmd_dayblock_update(args: argparse.Namespace, client: ApiClient) -> None:
    payload: dict[str, Any] = {}
    if args.start is not None:
        payload["start_minute"] = parse_minute(args.start)
    if args.end is not None:
        payload["end_minute"] = parse_minute(args.end, end=True)
    for field, value in (("label", args.label), ("kind", args.kind), ("remark", args.remark), ("is_active", args.is_active)):
        if value is not None:
            payload[field] = value
    emit(args, build(client, "PATCH", f"/day-blocks/{args.id}", payload), lambda item: key_values(item))


def cmd_dayblock_replace(args: argparse.Namespace, client: ApiClient) -> None:
    if args.file:
        with open(args.file, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    else:
        data = json.loads(args.data)
    if isinstance(data, dict):
        if "blocks" not in data:
            raise ValueError("JSON object must contain a 'blocks' array")
        blocks = data["blocks"]
    else:
        blocks = data
    emit(args, client.put("/day-blocks", {"blocks": blocks}), dayblock_rows)


def cmd_dayblock_delete(args: argparse.Namespace, client: ApiClient) -> None:
    client.delete(f"/day-blocks/{args.id}")
    emit(args, {"deleted": args.id}, lambda data: f"deleted day block #{data['deleted']}")


def cmd_dayblock_restore(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.post(f"/day-blocks/{args.id}/restore"), lambda item: key_values(item))


def cmd_fixed_list(args: argparse.Namespace, client: ApiClient) -> None:
    params = {"recurrence": args.recurrence, "active_only": args.active_only, "include_deleted": args.all}
    emit(args, client.get("/fixed-blocks", params), fixed_rows)


def cmd_fixed_occurrences(args: argparse.Namespace, client: ApiClient) -> None:
    params = {
        "date_from": resolve_date(args.date_from) if args.date_from else None,
        "date_to": resolve_date(args.date_to) if args.date_to else None,
        "fixed_block_id": args.block,
        "status": args.status,
        "limit": args.limit,
        "offset": args.offset,
    }
    emit(args, client.get("/fixed-block-occurrences", params), occurrence_rows)


def cmd_fixed_pending(args: argparse.Namespace, client: ApiClient) -> None:
    params = {
        "date_from": resolve_date(args.date_from) if args.date_from else None,
        "date_to": resolve_date(args.date_to) if args.date_to else None,
        "fixed_block_id": args.block,
        "status": "pending",
        "limit": args.limit,
        "offset": args.offset,
    }
    emit(args, client.get("/fixed-block-occurrences", params), occurrence_rows)


def cmd_fixed_mark(args: argparse.Namespace, client: ApiClient) -> None:
    payload = {
        "fixed_block_id": args.id,
        "date": resolve_date(args.date),
        "status": args.status,
        "note": args.note,
    }
    emit(
        args,
        client.put("/fixed-block-occurrences", payload),
        lambda item: key_values(item),
    )


def cmd_fixed_unmark(args: argparse.Namespace, client: ApiClient) -> None:
    on_date = resolve_date(args.date)
    client.delete(
        "/fixed-block-occurrences",
        params={"fixed_block_id": args.id, "date": on_date},
    )
    emit(
        args,
        {"fixed_block_id": args.id, "date": on_date},
        lambda data: f"cleared fixed block #{data['fixed_block_id']} @ {data['date']}",
    )


def cmd_fixed_get(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.get(f"/fixed-blocks/{args.id}"), lambda item: key_values(item))


def fixed_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": args.title,
        "recurrence": args.recurrence,
        "recurrence_value": args.value,
        "start_minute": parse_minute(args.start) if args.start is not None else None,
        "end_minute": parse_minute(args.end, end=True) if args.end is not None else None,
        "effective_from": resolve_date(args.date_from) if args.date_from else None,
        "effective_to": resolve_date(args.date_to) if args.date_to else None,
        "overlap_priority": args.overlap_priority,
        "allow_task_schedule": args.allow_task_schedule,
        "remark": args.remark,
        "is_active": args.is_active,
    }
    return payload


def cmd_fixed_add(args: argparse.Namespace, client: ApiClient) -> None:
    payload = {key: value for key, value in fixed_payload(args).items() if value is not None}
    payload["title"] = args.title
    payload["recurrence"] = args.recurrence
    payload["start_minute"] = parse_minute(args.start)
    payload["end_minute"] = parse_minute(args.end, end=True)
    payload["overlap_priority"] = args.overlap_priority
    payload["allow_task_schedule"] = args.allow_task_schedule
    payload["is_active"] = args.is_active
    emit(args, client.post("/fixed-blocks", payload), lambda item: key_values(item))


def cmd_fixed_update(args: argparse.Namespace, client: ApiClient) -> None:
    payload: dict[str, Any] = {}
    if args.title is not None:
        payload["title"] = args.title
    if args.recurrence is not None:
        payload["recurrence"] = args.recurrence
    if args.value is not None:
        payload["recurrence_value"] = args.value
    if args.start is not None:
        payload["start_minute"] = parse_minute(args.start)
    if args.end is not None:
        payload["end_minute"] = parse_minute(args.end, end=True)
    if args.date_from is not None:
        payload["effective_from"] = resolve_date(args.date_from)
    if args.date_to is not None:
        payload["effective_to"] = resolve_date(args.date_to)
    if args.clear_effective:
        payload["effective_to"] = None
    if args.overlap_priority is not None:
        payload["overlap_priority"] = args.overlap_priority
    if args.allow_task_schedule is not None:
        payload["allow_task_schedule"] = args.allow_task_schedule
    if args.remark is not None:
        payload["remark"] = args.remark
    if args.is_active is not None:
        payload["is_active"] = args.is_active
    emit(args, build(client, "PATCH", f"/fixed-blocks/{args.id}", payload), lambda item: key_values(item))


def cmd_fixed_delete(args: argparse.Namespace, client: ApiClient) -> None:
    client.delete(f"/fixed-blocks/{args.id}")
    emit(args, {"deleted": args.id}, lambda data: f"deleted fixed block #{data['deleted']}")


def cmd_fixed_restore(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.post(f"/fixed-blocks/{args.id}/restore"), lambda item: key_values(item))


def cmd_exception_list(args: argparse.Namespace, client: ApiClient) -> None:
    params = {
        "fixed_block_id": args.fixed_block,
        "active_only": args.active_only,
        "include_deleted": args.all,
    }
    emit(args, client.get("/fixed-block-exceptions", params), exception_rows)


def cmd_exception_get(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.get(f"/fixed-block-exceptions/{args.id}"), lambda item: key_values(item))


def cmd_exception_add(args: argparse.Namespace, client: ApiClient) -> None:
    if (args.start is None) != (args.end is None):
        raise ValueError("--start and --end must be provided together")
    payload: dict[str, Any] = {
        "effective_from": args.date_from,
        "effective_to": args.date_to,
        "skip_date": args.skip_date,
        "weekday": args.weekday,
        "day_of_month": args.day_of_month,
        "start_minute": parse_minute(args.start) if args.start is not None else None,
        "end_minute": parse_minute(args.end, end=True) if args.end is not None else None,
        "remark": args.remark,
        "is_active": args.is_active,
    }
    emit(args, client.post(f"/fixed-blocks/{args.fixed_block}/exceptions", payload), lambda item: key_values(item))


def cmd_exception_update(args: argparse.Namespace, client: ApiClient) -> None:
    if (args.start is None) != (args.end is None):
        raise ValueError("--start and --end must be provided together")
    payload: dict[str, Any] = {}
    for field, value in (
        ("effective_from", args.date_from),
        ("effective_to", args.date_to),
        ("skip_date", args.skip_date),
        ("weekday", args.weekday),
        ("day_of_month", args.day_of_month),
        ("remark", args.remark),
        ("is_active", args.is_active),
    ):
        if value is not None:
            payload[field] = value
    if args.start is not None:
        payload["start_minute"] = parse_minute(args.start)
        payload["end_minute"] = parse_minute(args.end, end=True)
    if args.clear_time:
        payload["start_minute"] = None
        payload["end_minute"] = None
    emit(args, build(client, "PATCH", f"/fixed-block-exceptions/{args.id}", payload), lambda item: key_values(item))


def cmd_exception_delete(args: argparse.Namespace, client: ApiClient) -> None:
    client.delete(f"/fixed-block-exceptions/{args.id}")
    emit(args, {"deleted": args.id}, lambda data: f"deleted exception #{data['deleted']}")


def cmd_exception_restore(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.post(f"/fixed-block-exceptions/{args.id}/restore"), lambda item: key_values(item))


def cmd_schedule_list(args: argparse.Namespace, client: ApiClient) -> None:
    params = {
        "date": resolve_date(args.date) if args.date else None,
        "task_id": args.task,
        "status": args.status,
        "include_deleted": args.all,
    }
    emit(args, client.get("/task-schedules", params), schedule_rows)


def cmd_schedule_get(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.get(f"/task-schedules/{args.id}"), lambda item: key_values(item))


def cmd_schedule_add(args: argparse.Namespace, client: ApiClient) -> None:
    payload = {
        "task_id": args.task,
        "plan_date": resolve_date(args.date),
        "start_minute": parse_minute(args.start),
        "end_minute": parse_minute(args.end, end=True),
        "status": args.status,
        "allow_override": args.allow_override,
        "note": args.note,
    }
    emit(args, client.post("/task-schedules", payload), lambda item: key_values(item))


def cmd_schedule_update(args: argparse.Namespace, client: ApiClient) -> None:
    payload: dict[str, Any] = {}
    if args.task is not None:
        payload["task_id"] = args.task
    if args.date is not None:
        payload["plan_date"] = resolve_date(args.date)
    if args.start is not None:
        payload["start_minute"] = parse_minute(args.start)
    if args.end is not None:
        payload["end_minute"] = parse_minute(args.end, end=True)
    if args.status is not None:
        payload["status"] = args.status
    if args.allow_override is not None:
        payload["allow_override"] = args.allow_override
    if args.note is not None:
        payload["note"] = args.note
    if args.clear_note:
        payload["note"] = None
    emit(args, build(client, "PATCH", f"/task-schedules/{args.id}", payload), lambda item: key_values(item))


def cmd_schedule_delete(args: argparse.Namespace, client: ApiClient) -> None:
    client.delete(f"/task-schedules/{args.id}")
    emit(args, {"deleted": args.id}, lambda data: f"deleted schedule #{data['deleted']}")


def cmd_schedule_restore(args: argparse.Namespace, client: ApiClient) -> None:
    emit(args, client.post(f"/task-schedules/{args.id}/restore"), lambda item: key_values(item))


def cmd_memo_list(args: argparse.Namespace, client: ApiClient) -> None:
    params = {"period": args.period, "date": resolve_date(args.date)}
    emit(args, client.get("/memos", params), memo_rows)


def cmd_memo_add(args: argparse.Namespace, client: ApiClient) -> None:
    payload = {"memo_date": resolve_date(args.date), "content": args.content}
    emit(args, client.post("/memos", payload), render_memo)


def cmd_plan_day(args: argparse.Namespace, client: ApiClient) -> None:
    on_date = resolve_date(args.date)
    occurrences = client.get("/plan/fixed-occurrences", {"date": on_date})
    schedules = client.get("/task-schedules", {"date": on_date})
    blocks = client.get("/day-blocks", {"active_only": True})

    active_schedules = [item for item in schedules if item["status"] != "skipped"]
    occupied = [(item["start_minute"], item["end_minute"]) for item in occurrences]
    occupied += [(item["start_minute"], item["end_minute"]) for item in active_schedules]

    free: list[dict[str, int]] = []
    for block in blocks:
        for start, end in subtract_intervals((block["start_minute"], block["end_minute"]), occupied):
            free.append({"start_minute": start, "end_minute": end})

    conflicts: list[dict[str, Any]] = []
    for schedule in active_schedules:
        for occurrence in occurrences:
            if overlaps(schedule["start_minute"], schedule["end_minute"], occurrence["start_minute"], occurrence["end_minute"]) and not occurrence["allow_task_schedule"]:
                conflicts.append(
                    {
                        "type": "schedule_fixed_block",
                        "schedule_id": schedule["id"],
                        "task_id": schedule["task_id"],
                        "fixed_block_id": occurrence["fixed_block_id"],
                        "message": (
                            f"schedule #{schedule['id']} {fmt_range(schedule['start_minute'], schedule['end_minute'])} "
                            f"overlaps fixed block #{occurrence['fixed_block_id']} {fmt_range(occurrence['start_minute'], occurrence['end_minute'])}"
                        ),
                    }
                )
    for index, first in enumerate(active_schedules):
        for second in active_schedules[index + 1 :]:
            if overlaps(first["start_minute"], first["end_minute"], second["start_minute"], second["end_minute"]):
                conflicts.append(
                    {
                        "type": "schedule_schedule",
                        "schedule_id": first["id"],
                        "other_schedule_id": second["id"],
                        "message": f"schedule #{first['id']} overlaps schedule #{second['id']}",
                    }
                )

    payload = {
        "date": on_date,
        "weekday": weekday_label(on_date),
        "fixed_occurrences": occurrences,
        "schedules": schedules,
        "day_blocks": blocks,
        "free": free,
        "conflicts": conflicts,
    }

    if args.json:
        print_json(payload)
        return

    print(f"{on_date} {weekday_label(on_date)}")
    print("\n固定块")
    if occurrences:
        print(
            table(
                ["ID", "TIME", "TITLE", "PRIORITY", "SCHEDULE"],
                [[i["fixed_block_id"], fmt_range(i["start_minute"], i["end_minute"]), i["title"], i["overlap_priority"], i["allow_task_schedule"]] for i in occurrences],
            )
        )
    else:
        print("  (none)")

    print("\n任务排期")
    if schedules:
        print(schedule_rows(schedules))
    else:
        print("  (none)")

    print("\n每日模板")
    if blocks:
        print(dayblock_rows(blocks))
    else:
        print("  (none; free time cannot be inferred without day blocks)")

    print("\n自由时间")
    if not blocks:
        print("  (unknown)")
    elif free:
        print(table(["TIME", "MINUTES"], [[fmt_range(i["start_minute"], i["end_minute"]), i["end_minute"] - i["start_minute"]] for i in free]))
    else:
        print("  (none)")

    print("\n冲突")
    if conflicts:
        for conflict in conflicts:
            print(f"  ! {conflict['message']}")
    else:
        print("  (none)")


def cmd_raw(args: argparse.Namespace, client: ApiClient) -> None:
    params: dict[str, str] = {}
    for item in args.param or []:
        if "=" not in item:
            raise ValueError(f"--param expects KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        params[key] = value
    body = None
    if args.data is not None:
        body = json.loads(args.data)
    print_json(client.request(args.method, args.path, params=params or None, body=body))


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tp",
        description="tasks-planner 本地任务与时间规划 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "环境变量:\n"
            "  TASKS_PLANNER_API   API 基地址，默认 http://127.0.0.1:56649/api\n"
            "  TASKS_PLANNER_CLI_TIMEOUT  请求超时秒数，默认 20\n"
        ),
    )
    parser.add_argument("--api", default=DEFAULT_API, help="API 基地址")
    parser.add_argument("--json", action="store_true", help="输出原始 JSON")
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("TASKS_PLANNER_CLI_TIMEOUT", "20")),
        help="请求超时秒数",
    )
    sub = parser.add_subparsers(dest="group", required=True)

    sub.add_parser("health", help="健康检查")

    meta = sub.add_parser("meta", help="app_meta 配置")
    meta_sub = meta.add_subparsers(dest="action", required=True)
    meta_sub.add_parser("get", help="读取全部配置")
    meta_set = meta_sub.add_parser("set", help="写入配置")
    meta_set.add_argument("key")
    meta_set.add_argument("value")

    status = sub.add_parser("status", help="任务状态")
    status_sub = status.add_subparsers(dest="action", required=True)
    status_list = status_sub.add_parser("list", help="列出状态")
    status_list.add_argument("--active-only", action="store_true")
    status_list.add_argument("--all", action="store_true", help="包含软删除")
    status_get = status_sub.add_parser("get", help="获取状态")
    status_get.add_argument("id", type=int)
    status_create = status_sub.add_parser("create", help="新建状态")
    status_create.add_argument("--code", required=True)
    status_create.add_argument("--name", required=True)
    status_create.add_argument("--sort", type=int, default=0)
    status_create.add_argument("--remark")
    create_active_flag(status_create)
    create_initial_filter_flag(status_create)
    status_update = status_sub.add_parser("update", help="更新状态")
    status_update.add_argument("id", type=int)
    status_update.add_argument("--name")
    status_update.add_argument("--sort", type=int)
    status_update.add_argument("--remark")
    active_flags(status_update)
    initial_filter_flags(status_update)
    status_delete = status_sub.add_parser("delete", help="软删除状态")
    status_delete.add_argument("id", type=int)
    status_restore = status_sub.add_parser("restore", help="恢复状态")
    status_restore.add_argument("id", type=int)

    priority = sub.add_parser("priority", help="优先级")
    priority_sub = priority.add_subparsers(dest="action", required=True)
    priority_list = priority_sub.add_parser("list", help="列出优先级")
    priority_list.add_argument("--active-only", action="store_true")
    priority_list.add_argument("--all", action="store_true")
    priority_get = priority_sub.add_parser("get", help="获取优先级")
    priority_get.add_argument("id", type=int)
    priority_create = priority_sub.add_parser("create", help="新建优先级")
    priority_create.add_argument("--level", type=int, required=True)
    priority_create.add_argument("--name", required=True)
    priority_create.add_argument("--usage")
    priority_create.add_argument("--remark")
    priority_create.add_argument("--color")
    create_active_flag(priority_create)
    priority_update = priority_sub.add_parser("update", help="更新优先级")
    priority_update.add_argument("id", type=int)
    priority_update.add_argument("--level", type=int)
    priority_update.add_argument("--name")
    priority_update.add_argument("--usage")
    priority_update.add_argument("--remark")
    priority_update.add_argument("--color")
    active_flags(priority_update)
    priority_delete = priority_sub.add_parser("delete", help="软删除优先级")
    priority_delete.add_argument("id", type=int)
    priority_restore = priority_sub.add_parser("restore", help="恢复优先级")
    priority_restore.add_argument("id", type=int)

    task = sub.add_parser("task", help="任务")
    task_sub = task.add_subparsers(dest="action", required=True)
    task_list = task_sub.add_parser("list", help="列出任务")
    task_list.add_argument("--status", action="append", help="状态 code/name/id，可重复传多个（OR）")
    task_list.add_argument("--priority", action="append", help="优先级 id/level/name，可重复传多个（OR）")
    task_list.add_argument("--q", help="搜索标题、进度、备注")
    task_list.add_argument("--deadline-from")
    task_list.add_argument("--deadline-to")
    task_list.add_argument("--open", action="store_true", help="只显示未完成/未取消")
    task_list.add_argument("--all", action="store_true", help="包含软删除")
    task_list.add_argument("--limit", type=int, default=100)
    task_list.add_argument("--offset", type=int, default=0)
    task_unscheduled = task_sub.add_parser("unscheduled", help="列出未排期任务")
    task_unscheduled.add_argument(
        "--priority", action="append", help="优先级 id/level/name，可重复传多个（OR）"
    )
    task_unscheduled.add_argument("--q", help="搜索标题、进度、备注")
    task_unscheduled.add_argument("--deadline-from")
    task_unscheduled.add_argument("--deadline-to")
    task_unscheduled.add_argument("--limit", type=int, default=100)
    task_unscheduled.add_argument("--offset", type=int, default=0)
    task_get = task_sub.add_parser("get", help="获取任务")
    task_get.add_argument("id", type=int)
    task_add = task_sub.add_parser("add", help="新建任务")
    task_add.add_argument("title")
    task_add.add_argument("--priority", help="优先级 id/level/name")
    task_add.add_argument("--status", help="状态 code/name/id，默认 todo")
    task_add.add_argument("--deadline", help="ISO 8601；只写 YYYY-MM-DD 表示当天 23:59:59")
    task_add.add_argument("--progress")
    task_add.add_argument("--remark")
    task_update = task_sub.add_parser("update", help="更新任务")
    task_update.add_argument("id", type=int)
    task_update.add_argument("--title")
    task_update.add_argument("--priority")
    task_update.add_argument("--no-priority", action="store_true", help="清空优先级")
    task_update.add_argument("--status")
    task_update.add_argument("--deadline")
    task_update.add_argument("--clear-deadline", action="store_true")
    task_update.add_argument("--progress")
    task_update.add_argument("--clear-progress", action="store_true")
    task_update.add_argument("--remark")
    task_update.add_argument("--clear-remark", action="store_true")
    for name in ("done", "start", "cancel"):
        action = task_sub.add_parser(name, help=f"把任务标记为 {name}")
        action.add_argument("id", type=int)
    task_delete = task_sub.add_parser("delete", help="软删除任务")
    task_delete.add_argument("id", type=int)
    task_restore = task_sub.add_parser("restore", help="恢复任务")
    task_restore.add_argument("id", type=int)

    dayblock = sub.add_parser("dayblock", help="每日基础时间模板")
    dayblock_sub = dayblock.add_subparsers(dest="action", required=True)
    dayblock_list = dayblock_sub.add_parser("list", help="列出模板")
    dayblock_list.add_argument("--active-only", action="store_true")
    dayblock_list.add_argument("--all", action="store_true")
    dayblock_add = dayblock_sub.add_parser("add", help="新建时间块")
    dayblock_add.add_argument("--start", required=True, help="HH:MM 或分钟")
    dayblock_add.add_argument("--end", required=True, help="HH:MM 或分钟（允许 24:00/1440）")
    dayblock_add.add_argument("--label")
    dayblock_add.add_argument("--kind")
    dayblock_add.add_argument("--remark")
    create_active_flag(dayblock_add)
    dayblock_update = dayblock_sub.add_parser("update", help="更新时间块")
    dayblock_update.add_argument("id", type=int)
    dayblock_update.add_argument("--start")
    dayblock_update.add_argument("--end")
    dayblock_update.add_argument("--label")
    dayblock_update.add_argument("--kind")
    dayblock_update.add_argument("--remark")
    active_flags(dayblock_update)
    dayblock_replace = dayblock_sub.add_parser("replace", help="整体替换模板")
    source = dayblock_replace.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", help="包含 JSON 数组或 {\"blocks\": [...]} 的文件")
    source.add_argument("--data", help="内联 JSON")
    dayblock_delete = dayblock_sub.add_parser("delete", help="软删除时间块")
    dayblock_delete.add_argument("id", type=int)
    dayblock_restore = dayblock_sub.add_parser("restore", help="恢复时间块")
    dayblock_restore.add_argument("id", type=int)

    fixed = sub.add_parser("fixed", help="每日/每周/每月固定块")
    fixed_sub = fixed.add_subparsers(dest="action", required=True)
    fixed_list = fixed_sub.add_parser("list", help="列出固定块")
    fixed_list.add_argument("--recurrence", choices=["daily", "weekly", "monthly"])
    fixed_list.add_argument("--active-only", action="store_true")
    fixed_list.add_argument("--all", action="store_true")
    fixed_get = fixed_sub.add_parser("get", help="获取固定块")
    fixed_get.add_argument("id", type=int)
    fixed_add = fixed_sub.add_parser("add", help="新建固定块")
    fixed_add.add_argument("--title", required=True)
    fixed_add.add_argument("--recurrence", required=True, choices=["daily", "weekly", "monthly"])
    fixed_add.add_argument("--value", type=int, help="weekly: 1..7；monthly: 1..31")
    fixed_add.add_argument("--start", required=True)
    fixed_add.add_argument("--end", required=True)
    fixed_add.add_argument(
        "--from",
        dest="date_from",
        help="生效起始日期 YYYY-MM-DD，不传则默认服务端当天",
    )
    fixed_add.add_argument("--to", dest="date_to", help="生效结束日期 YYYY-MM-DD")
    fixed_add.add_argument("--overlap-priority", type=int, default=0)
    fixed_add.add_argument("--allow-task-schedule", dest="allow_task_schedule", action="store_true", help="允许在该固定块内添加任务排期")
    fixed_add.add_argument("--no-task-schedule", dest="allow_task_schedule", action="store_false", help="禁止在该固定块内添加任务排期")
    fixed_add.set_defaults(allow_task_schedule=True)
    fixed_add.add_argument("--remark")
    create_active_flag(fixed_add)
    fixed_update = fixed_sub.add_parser("update", help="更新固定块")
    fixed_update.add_argument("id", type=int)
    fixed_update.add_argument("--title")
    fixed_update.add_argument("--recurrence", choices=["daily", "weekly", "monthly"])
    fixed_update.add_argument("--value", type=int)
    fixed_update.add_argument("--start")
    fixed_update.add_argument("--end")
    fixed_update.add_argument("--from", dest="date_from")
    fixed_update.add_argument("--to", dest="date_to")
    fixed_update.add_argument("--clear-effective", "--clear-effective-to", dest="clear_effective", action="store_true", help="清空生效结束日期 effective_to")
    fixed_update.add_argument("--overlap-priority", type=int)
    fixed_update.add_argument("--allow-task-schedule", dest="allow_task_schedule", action="store_true")
    fixed_update.add_argument("--no-task-schedule", dest="allow_task_schedule", action="store_false")
    fixed_update.set_defaults(allow_task_schedule=None)
    fixed_update.add_argument("--remark")
    active_flags(fixed_update)
    fixed_delete = fixed_sub.add_parser("delete", help="软删除固定块")
    fixed_delete.add_argument("id", type=int)
    fixed_restore = fixed_sub.add_parser("restore", help="恢复固定块")
    fixed_restore.add_argument("id", type=int)
    fixed_occurrences = fixed_sub.add_parser("occurrences", help="列出固定块发生实例及状态")
    fixed_occurrences.add_argument("--from", dest="date_from", help="起始日期，默认最早生效日")
    fixed_occurrences.add_argument("--to", dest="date_to", help="结束日期，默认今天")
    fixed_occurrences.add_argument("--block", type=int, help="固定块 ID")
    fixed_occurrences.add_argument(
        "--status",
        choices=["done", "skipped", "missed", "unmarked", "pending"],
        help="按状态筛选；pending=已过时间且未完成/未跳过",
    )
    fixed_occurrences.add_argument("--limit", type=int, default=500)
    fixed_occurrences.add_argument("--offset", type=int, default=0)
    fixed_pending = fixed_sub.add_parser("pending", help="列出已过时间且未完成/未跳过的固定块")
    fixed_pending.add_argument("--from", dest="date_from", help="起始日期，默认最早生效日")
    fixed_pending.add_argument("--to", dest="date_to", help="结束日期，默认今天")
    fixed_pending.add_argument("--block", type=int, help="固定块 ID")
    fixed_pending.add_argument("--limit", type=int, default=500)
    fixed_pending.add_argument("--offset", type=int, default=0)
    fixed_mark = fixed_sub.add_parser("mark", help="标记某次固定块状态")
    fixed_mark.add_argument("id", type=int, help="固定块 ID")
    fixed_mark.add_argument("date", help="发生日期 YYYY-MM-DD，或 today/yesterday")
    fixed_mark.add_argument("status", choices=["done", "skipped", "missed"])
    fixed_mark.add_argument("--note")
    fixed_unmark = fixed_sub.add_parser("unmark", help="清除某次固定块状态")
    fixed_unmark.add_argument("id", type=int, help="固定块 ID")
    fixed_unmark.add_argument("date", help="发生日期 YYYY-MM-DD，或 today/yesterday")

    exception = sub.add_parser("exception", help="固定块例外（跳过）")
    exception_sub = exception.add_subparsers(dest="action", required=True)
    exception_list = exception_sub.add_parser("list", help="列出例外")
    exception_list.add_argument("--fixed-block", type=int)
    exception_list.add_argument("--active-only", action="store_true")
    exception_list.add_argument("--all", action="store_true")
    exception_get = exception_sub.add_parser("get", help="获取例外")
    exception_get.add_argument("id", type=int)
    exception_add = exception_sub.add_parser("add", help="为固定块新建例外")
    exception_add.add_argument("--fixed-block", type=int, required=True)
    exception_add.add_argument("--skip-date", help="只跳过该日期")
    exception_add.add_argument("--weekday", type=int, help="ISO 星期 1..7")
    exception_add.add_argument("--day-of-month", type=int, help="日号 1..31")
    exception_add.add_argument("--from", dest="date_from")
    exception_add.add_argument("--to", dest="date_to")
    exception_add.add_argument("--start", help="只跳过该时段；需与 --end 同时给出")
    exception_add.add_argument("--end")
    exception_add.add_argument("--remark")
    create_active_flag(exception_add)
    exception_update = exception_sub.add_parser("update", help="更新例外")
    exception_update.add_argument("id", type=int)
    exception_update.add_argument("--skip-date")
    exception_update.add_argument("--weekday", type=int)
    exception_update.add_argument("--day-of-month", type=int)
    exception_update.add_argument("--from", dest="date_from")
    exception_update.add_argument("--to", dest="date_to")
    exception_update.add_argument("--start")
    exception_update.add_argument("--end")
    exception_update.add_argument("--clear-time", action="store_true")
    exception_update.add_argument("--remark")
    active_flags(exception_update)
    exception_delete = exception_sub.add_parser("delete", help="软删除例外")
    exception_delete.add_argument("id", type=int)
    exception_restore = exception_sub.add_parser("restore", help="恢复例外")
    exception_restore.add_argument("id", type=int)

    schedule = sub.add_parser("schedule", help="任务排期")
    schedule_sub = schedule.add_subparsers(dest="action", required=True)
    schedule_list = schedule_sub.add_parser("list", help="列出排期")
    schedule_list.add_argument("--date")
    schedule_list.add_argument("--task", type=int)
    schedule_list.add_argument("--status", choices=["planned", "done", "skipped"])
    schedule_list.add_argument("--all", action="store_true")
    schedule_get = schedule_sub.add_parser("get", help="获取排期")
    schedule_get.add_argument("id", type=int)
    schedule_add = schedule_sub.add_parser("add", help="新建排期")
    schedule_add.add_argument("--task", type=int, required=True)
    schedule_add.add_argument("--date", required=True)
    schedule_add.add_argument("--start", required=True)
    schedule_add.add_argument("--end", required=True)
    schedule_add.add_argument("--status", choices=["planned", "done", "skipped"], default="planned")
    schedule_add.add_argument("--no-override", dest="allow_override", action="store_false", help="锁定，不允许被挤占")
    schedule_add.set_defaults(allow_override=True)
    schedule_add.add_argument("--note")
    schedule_update = schedule_sub.add_parser("update", help="更新排期")
    schedule_update.add_argument("id", type=int)
    schedule_update.add_argument("--task", type=int)
    schedule_update.add_argument("--date")
    schedule_update.add_argument("--start")
    schedule_update.add_argument("--end")
    schedule_update.add_argument("--status", choices=["planned", "done", "skipped"])
    schedule_update.add_argument("--allow-override", dest="allow_override", action="store_true")
    schedule_update.add_argument("--no-override", dest="allow_override", action="store_false")
    schedule_update.set_defaults(allow_override=None)
    schedule_update.add_argument("--note")
    schedule_update.add_argument("--clear-note", action="store_true")
    schedule_delete = schedule_sub.add_parser("delete", help="软删除排期")
    schedule_delete.add_argument("id", type=int)
    schedule_restore = schedule_sub.add_parser("restore", help="恢复排期")
    schedule_restore.add_argument("id", type=int)

    memo = sub.add_parser("memo", help="每日备忘录（只增）")
    memo_sub = memo.add_subparsers(dest="action", required=True)
    memo_list = memo_sub.add_parser("list", help="按天/周/月列出备忘录")
    memo_list.add_argument("--period", choices=["day", "week", "month"], default="day", help="时间范围，默认 day")
    memo_list.add_argument("--date", default="today", help="基准日期，默认 today")
    memo_add = memo_sub.add_parser("add", help="新增备忘录，同一天可多条")
    memo_add.add_argument("content", help="备忘录内容")
    memo_add.add_argument("--date", default="today", help="备忘录日期，默认 today")

    plan = sub.add_parser("plan", help="规划视图")
    plan_sub = plan.add_subparsers(dest="action", required=True)
    plan_day = plan_sub.add_parser("day", help="查看某天固定块、排期、模板与自由时间")
    plan_day.add_argument("date", help="YYYY-MM-DD，或 today/tomorrow/yesterday")

    raw = sub.add_parser("raw", help="直接请求任意 API 路径")
    raw.add_argument("method", choices=["GET", "POST", "PUT", "PATCH", "DELETE"])
    raw.add_argument("path", help="以 / 开头的路径，如 /tasks")
    raw.add_argument("--data", help="JSON 请求体")
    raw.add_argument("--param", action="append", help="查询参数 KEY=VALUE，可重复")

    dispatch = {
        ("health", None): cmd_health,
        ("meta", "get"): cmd_meta_get,
        ("meta", "set"): cmd_meta_set,
        ("status", "list"): cmd_status_list,
        ("status", "get"): cmd_status_get,
        ("status", "create"): cmd_status_create,
        ("status", "update"): cmd_status_update,
        ("status", "delete"): cmd_status_delete,
        ("status", "restore"): cmd_status_restore,
        ("priority", "list"): cmd_priority_list,
        ("priority", "get"): cmd_priority_get,
        ("priority", "create"): cmd_priority_create,
        ("priority", "update"): cmd_priority_update,
        ("priority", "delete"): cmd_priority_delete,
        ("priority", "restore"): cmd_priority_restore,
        ("task", "list"): cmd_task_list,
        ("task", "unscheduled"): cmd_task_unscheduled,
        ("task", "get"): cmd_task_get,
        ("task", "add"): cmd_task_add,
        ("task", "update"): cmd_task_update,
        ("task", "done"): lambda a, c: cmd_task_status(a, c, "done"),
        ("task", "start"): lambda a, c: cmd_task_status(a, c, "doing"),
        ("task", "cancel"): lambda a, c: cmd_task_status(a, c, "cancelled"),
        ("task", "delete"): cmd_task_delete,
        ("task", "restore"): cmd_task_restore,
        ("dayblock", "list"): cmd_dayblock_list,
        ("dayblock", "add"): cmd_dayblock_add,
        ("dayblock", "update"): cmd_dayblock_update,
        ("dayblock", "replace"): cmd_dayblock_replace,
        ("dayblock", "delete"): cmd_dayblock_delete,
        ("dayblock", "restore"): cmd_dayblock_restore,
        ("fixed", "list"): cmd_fixed_list,
        ("fixed", "get"): cmd_fixed_get,
        ("fixed", "add"): cmd_fixed_add,
        ("fixed", "update"): cmd_fixed_update,
        ("fixed", "delete"): cmd_fixed_delete,
        ("fixed", "restore"): cmd_fixed_restore,
        ("fixed", "occurrences"): cmd_fixed_occurrences,
        ("fixed", "pending"): cmd_fixed_pending,
        ("fixed", "mark"): cmd_fixed_mark,
        ("fixed", "unmark"): cmd_fixed_unmark,
        ("exception", "list"): cmd_exception_list,
        ("exception", "get"): cmd_exception_get,
        ("exception", "add"): cmd_exception_add,
        ("exception", "update"): cmd_exception_update,
        ("exception", "delete"): cmd_exception_delete,
        ("exception", "restore"): cmd_exception_restore,
        ("schedule", "list"): cmd_schedule_list,
        ("schedule", "get"): cmd_schedule_get,
        ("schedule", "add"): cmd_schedule_add,
        ("schedule", "update"): cmd_schedule_update,
        ("schedule", "delete"): cmd_schedule_delete,
        ("schedule", "restore"): cmd_schedule_restore,
        ("memo", "list"): cmd_memo_list,
        ("memo", "add"): cmd_memo_add,
        ("plan", "day"): cmd_plan_day,
        ("raw", None): cmd_raw,
    }
    parser.set_defaults(dispatch=dispatch)
    return parser


def normalize_argv(argv: list[str]) -> list[str]:
    """Allow global options to appear before or after the subcommand."""
    front: list[str] = []
    rest: list[str] = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--json":
            front.append(item)
            index += 1
        elif item in {"--api", "--timeout"}:
            if index + 1 >= len(argv):
                rest.append(item)
                index += 1
            else:
                front.extend([item, argv[index + 1]])
                index += 2
        elif item.startswith("--api=") or item.startswith("--timeout="):
            front.append(item)
            index += 1
        else:
            rest.append(item)
            index += 1
    return front + rest


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw_argv = sys.argv[1:] if argv is None else argv
    args = parser.parse_args(normalize_argv(raw_argv))
    dispatch: dict[tuple[str, str | None], Callable[[argparse.Namespace, ApiClient], None]] = args.dispatch
    handler = dispatch.get((args.group, getattr(args, "action", None)))
    if handler is None:
        parser.error(f"unknown command: {args.group} {getattr(args, 'action', '')}".strip())
        return 2
    client = ApiClient(args.api, timeout=args.timeout)
    try:
        handler(args, client)
    except ApiError as exc:
        print(f"API error ({exc.status}): {exc.detail}", file=sys.stderr)
        return 1
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
