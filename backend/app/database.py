import sqlite3
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from .config import DATA_DIR, DB_PATH, SCHEMA_PATH
from .utils import localize_rows, localize_timestamps

_APP_TABLES = frozenset(
    {"fixed_blocks", "tasks", "task_statuses", "day_blocks", "daily_memos"}
)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(
        DB_PATH,
        timeout=5,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


# ---------------------------------------------------------------------------
# 数据库迁移：schema_migrations 记录已执行版本，按 version 升序执行
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone()
        is not None
    )


def _ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
          version    INTEGER PRIMARY KEY,
          name       TEXT NOT NULL,
          applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )


def _applied_versions(conn: sqlite3.Connection) -> set[int]:
    return {
        row[0] for row in conn.execute("SELECT version FROM schema_migrations")
    }


def _record_migration(
    conn: sqlite3.Connection, migration: Migration
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO schema_migrations(version, name, applied_at)
        VALUES (?, ?, datetime('now'))
        """,
        (migration.version, migration.name),
    )


def _legacy_schema_version(conn: sqlite3.Connection) -> int:
    if not _table_exists(conn, "app_meta"):
        return 1
    row = conn.execute(
        "SELECT value FROM app_meta WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        return 1
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return 1


def _schema_looks_current(
    conn: sqlite3.Connection, tables: set[str]
) -> bool:
    if "fixed_blocks" in tables and _fixed_blocks_needs_rebuild(conn):
        return False
    if "fixed_block_occurrence_logs" not in tables:
        return False
    return True


def _sync_schema_version(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "app_meta"):
        return
    conn.execute(
        "INSERT OR IGNORE INTO app_meta(key, value) VALUES ('schema_version', ?)",
        (str(CURRENT_SCHEMA_VERSION),),
    )
    conn.execute(
        "UPDATE app_meta SET value = ? WHERE key = 'schema_version'",
        (str(CURRENT_SCHEMA_VERSION),),
    )


# ---------------------------------------------------------------------------
# V2：fixed_blocks.effective_from 非空 + 固定块 occurrence 状态表
# ---------------------------------------------------------------------------
def _fixed_blocks_needs_rebuild(conn: sqlite3.Connection) -> bool:
    for row in conn.execute("PRAGMA table_info(fixed_blocks)"):
        if row[1] == "effective_from":
            return not bool(row[3])
    return False


def _rebuild_fixed_blocks(conn: sqlite3.Connection) -> None:
    conn.execute("DROP TABLE IF EXISTS fixed_blocks_new")
    conn.execute(
        """
        CREATE TABLE fixed_blocks_new (
          id               INTEGER PRIMARY KEY AUTOINCREMENT,
          title            TEXT    NOT NULL CHECK (length(trim(title)) > 0),
          recurrence       TEXT    NOT NULL CHECK (recurrence IN ('daily', 'weekly', 'monthly')),
          recurrence_value INTEGER,
          start_minute     INTEGER NOT NULL CHECK (start_minute BETWEEN 0 AND 1439),
          end_minute       INTEGER NOT NULL CHECK (end_minute BETWEEN 1 AND 1440),
          effective_from   TEXT    NOT NULL,
          effective_to     TEXT,
          overlap_priority INTEGER NOT NULL DEFAULT 0,
          allow_task_schedule INTEGER NOT NULL DEFAULT 1 CHECK (allow_task_schedule IN (0, 1)),
          remark           TEXT,
          is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
          deleted_at       TEXT,
          created_at       TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
          CHECK (end_minute > start_minute),
          CHECK (
            (recurrence = 'daily'   AND recurrence_value IS NULL) OR
            (recurrence = 'weekly'  AND recurrence_value IS NOT NULL
                                    AND recurrence_value BETWEEN 1 AND 7) OR
            (recurrence = 'monthly' AND recurrence_value IS NOT NULL
                                    AND recurrence_value BETWEEN 1 AND 31)
          ),
          CHECK (effective_to IS NULL OR effective_from <= effective_to)
        )
        """
    )
    conn.execute(
        """
        INSERT INTO fixed_blocks_new(
          id, title, recurrence, recurrence_value, start_minute, end_minute,
          effective_from, effective_to, overlap_priority, allow_task_schedule,
          remark, is_active, deleted_at, created_at, updated_at
        )
        SELECT
          id, title, recurrence, recurrence_value, start_minute, end_minute,
          COALESCE(effective_from, substr(created_at, 1, 10), date('now')),
          effective_to, overlap_priority, allow_task_schedule,
          remark, is_active, deleted_at, created_at, updated_at
        FROM fixed_blocks
        """
    )
    conn.execute("DROP TABLE fixed_blocks")
    conn.execute(
        "ALTER TABLE fixed_blocks_new RENAME TO fixed_blocks"
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fixed_blocks_recurrence
          ON fixed_blocks(recurrence, recurrence_value, start_minute)
        """
    )


def _create_occurrence_logs(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fixed_block_occurrence_logs (
          id              INTEGER PRIMARY KEY AUTOINCREMENT,
          fixed_block_id  INTEGER NOT NULL REFERENCES fixed_blocks(id) ON DELETE CASCADE,
          occurrence_date TEXT    NOT NULL
                          CHECK (occurrence_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
          status          TEXT    NOT NULL CHECK (status IN ('done', 'skipped', 'missed')),
          note            TEXT,
          deleted_at      TEXT,
          created_at      TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_fixed_block_occurrence_logs
          ON fixed_block_occurrence_logs(fixed_block_id, occurrence_date)
          WHERE deleted_at IS NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fixed_block_occurrence_logs_date
          ON fixed_block_occurrence_logs(occurrence_date)
          WHERE deleted_at IS NULL
        """
    )


def _migrate_v2(conn: sqlite3.Connection) -> None:
    tables = _table_names(conn)
    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            if "fixed_blocks" in tables:
                columns = {
                    row[1]
                    for row in conn.execute(
                        "PRAGMA table_info(fixed_blocks)"
                    )
                }
                if (
                    "allow_task_schedule" not in columns
                    and "allow_override" in columns
                ):
                    conn.execute(
                        "ALTER TABLE fixed_blocks "
                        "RENAME COLUMN allow_override TO allow_task_schedule"
                    )
                conn.execute(
                    """
                    UPDATE fixed_blocks
                    SET effective_from = COALESCE(
                      substr(created_at, 1, 10), date('now')
                    )
                    WHERE effective_from IS NULL
                    """
                )
                if _fixed_blocks_needs_rebuild(conn):
                    _rebuild_fixed_blocks(conn)
                _create_occurrence_logs(conn)

            if "task_statuses" in tables:
                status_columns = {
                    row[1]
                    for row in conn.execute(
                        "PRAGMA table_info(task_statuses)"
                    )
                }
                if "is_initial_filter" not in status_columns:
                    conn.execute(
                        "ALTER TABLE task_statuses ADD COLUMN "
                        "is_initial_filter INTEGER NOT NULL DEFAULT 1 "
                        "CHECK (is_initial_filter IN (0, 1))"
                    )
                    conn.execute(
                        "UPDATE task_statuses SET is_initial_filter = 0 "
                        "WHERE code IN ('done', 'cancelled')"
                    )

            conn.execute("DROP INDEX IF EXISTS ux_daily_memos_date_active")
            _sync_schema_version(conn)
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")

    problems = conn.execute("PRAGMA foreign_key_check").fetchall()
    if problems:
        raise RuntimeError(f"迁移 v2 外键校验失败: {problems}")


# 新增迁移时按 version 升序追加；每个迁移只执行一次，并写入 schema_migrations。
# 同步把 docs/schema.sql 里 app_meta.schema_version 的初始值改成最新版本。
MIGRATIONS: tuple[Migration, ...] = (
    Migration(2, "fixed_block_tracking", _migrate_v2),
)

CURRENT_SCHEMA_VERSION = max(migration.version for migration in MIGRATIONS)


def _migrate(conn: sqlite3.Connection) -> None:
    tables = _table_names(conn)
    _ensure_migrations_table(conn)

    applied = _applied_versions(conn)
    if applied and max(applied) > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"数据库 schema 版本 {max(applied)} 高于当前程序 "
            f"{CURRENT_SCHEMA_VERSION}，请升级程序"
        )

    legacy = _legacy_schema_version(conn)
    if legacy > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(
            f"数据库 schema 版本 {legacy} 高于当前程序 "
            f"{CURRENT_SCHEMA_VERSION}，请升级程序"
        )

    if not (tables & _APP_TABLES):
        # 全新数据库：schema.sql 会直接创建最新结构，记录所有迁移即可
        for migration in MIGRATIONS:
            _record_migration(conn, migration)
        conn.commit()
        return

    if not applied:
        # 兼容旧库：没有迁移记录时，以 app_meta.schema_version 作为起点
        if legacy >= CURRENT_SCHEMA_VERSION and not _schema_looks_current(
            conn, tables
        ):
            legacy = 1
        for migration in MIGRATIONS:
            if migration.version <= legacy:
                _record_migration(conn, migration)
                applied.add(migration.version)

    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        migration.apply(conn)
        _record_migration(conn, migration)
        applied.add(migration.version)

    _sync_schema_version(conn)
    conn.commit()


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    try:
        _migrate(conn)
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        _sync_schema_version(conn)
        conn.commit()
    finally:
        conn.close()


def get_db() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def fetch_one(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any] | None:
    row = conn.execute(sql, params).fetchone()
    if row is None:
        return None
    return localize_timestamps(conn, dict(row))


def fetch_all(
    conn: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    return localize_rows(conn, rows)
