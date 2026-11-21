"""Shared formatting helpers for the tasks-planner CLI."""

from __future__ import annotations

import json
import re
from typing import Any, Iterable, Sequence

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_minute(value: Any, *, end: bool = False) -> int:
    """Parse ``HH:MM`` or a plain minute number into 0..1440."""
    if isinstance(value, bool):
        raise ValueError(f"invalid time: {value!r}")
    if isinstance(value, int):
        minute = value
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("time is empty")
        if text.isdigit():
            minute = int(text)
        else:
            match = re.fullmatch(r"(\d{1,2}):(\d{2})", text)
            if not match:
                raise ValueError(
                    f"invalid time {value!r}; use HH:MM or minutes (e.g. 09:30 or 570)"
                )
            hour, minute_part = int(match.group(1)), int(match.group(2))
            if minute_part > 59:
                raise ValueError(f"invalid time {value!r}; minutes must be 0..59")
            minute = hour * 60 + minute_part
    if end and minute == 1440:
        return minute
    if not 0 <= minute <= (1440 if end else 1439):
        upper = 1440 if end else 1439
        raise ValueError(f"time {value!r} out of range 0..{upper}")
    return minute


def fmt_minute(value: Any) -> str:
    if value is None:
        return "-"
    minute = int(value)
    hour, rest = divmod(minute, 60)
    return f"{hour:02d}:{rest:02d}"


def fmt_range(start: Any, end: Any) -> str:
    return f"{fmt_minute(start)}-{fmt_minute(end)}"


def is_date(value: str) -> bool:
    return bool(_DATE_RE.fullmatch(value.strip()))


def normalize_deadline(value: str) -> str:
    """Accept a full ISO timestamp or a ``YYYY-MM-DD`` date (end of day)."""
    text = value.strip()
    if is_date(text):
        return f"{text}T23:59:59"
    return text


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def table(headers: Sequence[str], rows: Iterable[Sequence[Any]], *, max_width: int = 48) -> str:
    """Render a simple aligned text table."""
    body = [[_cell(value) for value in row] for row in rows]
    if not body:
        return "(empty)"
    widths = [len(str(header)) for header in headers]
    for row in body:
        for index, value in enumerate(row):
            if index >= len(widths):
                break
            widths[index] = max(widths[index], len(value))
    widths = [min(width, max_width) for width in widths]

    def clip(text: str, width: int) -> str:
        return text if len(text) <= width else text[: max(width - 1, 0)] + "…"

    lines = ["  ".join(clip(str(h), widths[i]).ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in body:
        cells = [clip(value, widths[i]).ljust(widths[i]) for i, value in enumerate(row) if i < len(widths)]
        lines.append("  ".join(cells))
    return "\n".join(lines)


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def print_json(value: Any) -> None:
    print(dump_json(value))


def key_values(data: dict[str, Any]) -> str:
    width = max((len(str(key)) for key in data), default=0)
    return "\n".join(f"{str(key).ljust(width)}  {_cell(value)}" for key, value in data.items())
