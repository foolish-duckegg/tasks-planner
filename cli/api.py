"""Tiny stdlib HTTP client and lookup helpers for the tasks-planner API."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_API = os.environ.get("TASKS_PLANNER_API", "http://127.0.0.1:56649/api")


class ApiError(Exception):
    def __init__(self, status: int, detail: Any, method: str, url: str) -> None:
        super().__init__(f"{method} {url} -> {status}: {detail}")
        self.status = status
        self.detail = detail
        self.method = method
        self.url = url


def _encode_query(params: dict[str, Any] | None) -> str:
    if not params:
        return ""
    pairs: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, bool):
            pairs.append((key, "true" if value else "false"))
        elif isinstance(value, (list, tuple)):
            for item in value:
                pairs.append((key, str(item)))
        else:
            pairs.append((key, str(value)))
    return ("?" + urllib.parse.urlencode(pairs)) if pairs else ""


class ApiClient:
    def __init__(self, base_url: str = DEFAULT_API, timeout: float = 20.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,
    ) -> Any:
        url = self.base_url + "/" + path.lstrip("/") + _encode_query(params)
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            detail: Any
            try:
                parsed = json.loads(raw.decode("utf-8")) if raw else None
                detail = parsed.get("detail", parsed) if isinstance(parsed, dict) else parsed
            except (ValueError, UnicodeDecodeError):
                detail = raw.decode("utf-8", "replace")
            raise ApiError(exc.code, detail, method.upper(), url) from exc
        except urllib.error.URLError as exc:
            raise ApiError(0, f"cannot reach {self.base_url}: {exc.reason}", method.upper(), url) from exc
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise ApiError(0, f"invalid JSON response: {exc}", method.upper(), url) from exc

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: Any = None) -> Any:
        return self.request("POST", path, body=body)

    def put(self, path: str, body: Any = None) -> Any:
        return self.request("PUT", path, body=body)

    def patch(self, path: str, body: Any = None) -> Any:
        return self.request("PATCH", path, body=body)

    def delete(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self.request("DELETE", path, params=params)


_STATUS_CACHE: dict[int, list[dict[str, Any]]] = {}
_PRIORITY_CACHE: dict[int, list[dict[str, Any]]] = {}


def _cache_key(client: ApiClient) -> int:
    return id(client)


def list_statuses(client: ApiClient) -> list[dict[str, Any]]:
    key = _cache_key(client)
    if key not in _STATUS_CACHE:
        _STATUS_CACHE[key] = client.get("/statuses")
    return _STATUS_CACHE[key]


def list_priorities(client: ApiClient) -> list[dict[str, Any]]:
    key = _cache_key(client)
    if key not in _PRIORITY_CACHE:
        _PRIORITY_CACHE[key] = client.get("/priorities")
    return _PRIORITY_CACHE[key]


def resolve_status(client: ApiClient, value: str | int) -> dict[str, Any]:
    """Resolve an id, code or name to a status record."""
    statuses = list_statuses(client)
    text = str(value).strip()
    if text.isdigit():
        wanted = int(text)
        for item in statuses:
            if item["id"] == wanted:
                return item
    lowered = text.lower()
    for item in statuses:
        if str(item["code"]).lower() == lowered:
            return item
    for item in statuses:
        if str(item["name"]).lower() == lowered:
            return item
    choices = ", ".join(f"{item['id']}:{item['code']}" for item in statuses)
    raise ValueError(f"unknown status {value!r}; available: {choices}")


def resolve_priority(client: ApiClient, value: str | int) -> dict[str, Any]:
    """Resolve an id, level or name to a priority record."""
    priorities = list_priorities(client)
    text = str(value).strip()
    if text.isdigit():
        wanted = int(text)
        for item in priorities:
            if item["id"] == wanted:
                return item
        for item in priorities:
            if item["level"] == wanted:
                return item
    lowered = text.lower()
    for item in priorities:
        if str(item["name"]).lower() == lowered:
            return item
    choices = ", ".join(f"{item['id']}:{item['name']}(L{item['level']})" for item in priorities)
    raise ValueError(f"unknown priority {value!r}; available: {choices}")


def invalidate_lookups() -> None:
    _STATUS_CACHE.clear()
    _PRIORITY_CACHE.clear()
