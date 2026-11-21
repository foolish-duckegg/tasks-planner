import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import __version__
from .config import CORS_ORIGINS, DB_PATH, STATIC_DIR
from .database import init_db
from .routers import (
    day_blocks,
    exceptions,
    fixed_blocks,
    memos,
    meta,
    plan,
    priorities,
    statuses,
    task_schedules,
    tasks,
)

logger = logging.getLogger("tasks-planner")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("tasks-planner database ready: %s", DB_PATH)
    yield


app = FastAPI(
    title="tasks-planner API",
    description=(
        "本地任务与时间规划服务。\n\n"
        "约定：时间点使用距离 00:00 的分钟数（0..1440），"
        "区间为左闭右开；日期使用 YYYY-MM-DD；时间戳以 UTC 存储，"
        "响应时按 app_meta.timezone 转为本地时间。删除均为软删除。"
    ),
    version=__version__,
    lifespan=lifespan,
    openapi_tags=[
        {"name": "meta", "description": "健康检查与 app_meta 配置"},
        {"name": "task-statuses", "description": "任务状态表"},
        {"name": "priority-levels", "description": "用户自定义优先级"},
        {"name": "tasks", "description": "任务 CRUD"},
        {"name": "day-blocks", "description": "每日基础时间划分模板"},
        {"name": "fixed-blocks", "description": "每日/每周/每月固定块"},
        {"name": "fixed-block-exceptions", "description": "固定块的跳过例外"},
        {"name": "task-schedules", "description": "任务排期"},
        {"name": "daily-memos", "description": "每日备忘录，一天一行，支持按天/周/月查询"},
        {"name": "planning", "description": "按日期计算固定块实际发生情况"},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(sqlite3.IntegrityError)
async def sqlite_integrity_error_handler(
    _: Request, exc: sqlite3.IntegrityError
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": f"数据库约束冲突：{exc}"},
    )


@app.exception_handler(sqlite3.Error)
async def sqlite_error_handler(_: Request, exc: sqlite3.Error) -> JSONResponse:
    logger.error("sqlite error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "数据库访问失败"})


@app.exception_handler(ValidationError)
async def pydantic_validation_error_handler(
    _: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors(include_url=False))},
    )


def _index_file() -> Path | None:
    index = STATIC_DIR / "index.html"
    return index if index.is_file() else None


if (STATIC_DIR / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=STATIC_DIR / "assets"),
        name="assets",
    )


@app.get("/", include_in_schema=False, response_model=None)
def root() -> FileResponse | RedirectResponse:
    index = _index_file()
    if index is not None:
        return FileResponse(index)
    return RedirectResponse(url="/docs")


@app.get(
    "/api/health",
    tags=["meta"],
    summary="健康检查",
    description="服务存活时返回 ok 与当前版本。",
)
def health() -> dict[str, str]:
    return {"status": "ok", "version": __version__}


app.include_router(meta.router)
app.include_router(statuses.router)
app.include_router(priorities.router)
app.include_router(tasks.router)
app.include_router(day_blocks.router)
app.include_router(fixed_blocks.router)
app.include_router(exceptions.nested_router)
app.include_router(exceptions.router)
app.include_router(task_schedules.router)
app.include_router(memos.router)
app.include_router(plan.router)


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str) -> FileResponse:
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    index = _index_file()
    if index is None:
        raise HTTPException(status_code=404, detail="前端资源未构建")

    static_root = STATIC_DIR.resolve()
    candidate = (static_root / full_path).resolve()
    if candidate.is_file() and candidate.is_relative_to(static_root):
        return FileResponse(candidate)
    return FileResponse(index)
