-- tasks-planner schema (SQLite)
-- 约定：
--   * 时间点用「距离 00:00 的分钟数」INTEGER 存储（0..1440），避免时区/格式解析
--   * 日期用本地日期 'YYYY-MM-DD'，时间戳用 UTC datetime('now')
--   * 软删除：业务表用 deleted_at 标记；唯一索引只约束 deleted_at IS NULL 的记录
--   * 单用户本地守护进程模型；若将来多用户，各表补 user_id
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ---------------------------------------------------------------------------
-- 元信息：schema 版本 / 时区 / 周起始日
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS app_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT OR IGNORE INTO app_meta(key, value) VALUES
  ('schema_version', '2'),
  ('timezone', 'Asia/Shanghai'),
  ('week_start', '1');          -- ISO: 1=周一

-- ---------------------------------------------------------------------------
-- 迁移记录：启动时只执行 version 大于已记录版本的迁移
--   业务代码中的 MIGRATIONS 负责写入本表；schema.sql 只保证表存在
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
  version    INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ---------------------------------------------------------------------------
-- 优先级表：用户可编辑；任务通过外键引用，不写死枚举
--   level: 1 最高，数字越大越低
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS priority_levels (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  level      INTEGER NOT NULL CHECK (level >= 1),
  name       TEXT    NOT NULL,              -- 显示名，如 P0 / 高
  usage      TEXT,                          -- 用法说明（什么情况下用）
  remark     TEXT,                          -- 备注
  color      TEXT,                          -- 前端色值，可空
  is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  deleted_at TEXT,                          -- 软删除时间（UTC），NULL = 未删除
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_priority_levels_level_active
  ON priority_levels(level) WHERE deleted_at IS NULL;

INSERT OR IGNORE INTO priority_levels(id, level, name, usage, remark) VALUES
  (1, 1, 'P0', '紧急且重要，必须当天处理', '如线上故障'),
  (2, 2, 'P1', '重要，本周内推进', NULL),
  (3, 3, 'P2', '常规任务，按计划做', NULL),
  (4, 4, 'P3', '有空再做，可随时延后', NULL);

-- ---------------------------------------------------------------------------
-- 任务状态表：内置状态固定 id，尽量用 is_active 停用而不是删除
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_statuses (
  id         INTEGER PRIMARY KEY,
  code       TEXT NOT NULL,                 -- todo / doing / blocked / done / cancelled
  name       TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  remark     TEXT,
  is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  is_initial_filter INTEGER NOT NULL DEFAULT 1 CHECK (is_initial_filter IN (0, 1)),
  deleted_at TEXT,                          -- 软删除时间（UTC），NULL = 未删除
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_task_statuses_code_active
  ON task_statuses(code) WHERE deleted_at IS NULL;

INSERT OR IGNORE INTO task_statuses(id, code, name, sort_order, remark, is_initial_filter) VALUES
  (1, 'todo',      '待办',   10, NULL,             1),
  (2, 'doing',     '进行中', 20, NULL,             1),
  (3, 'blocked',   '阻塞',   30, '被外部依赖阻塞', 1),
  (4, 'done',      '已完成', 40, NULL,             0),
  (5, 'cancelled', '已取消', 50, NULL,             0);

-- ---------------------------------------------------------------------------
-- 任务
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tasks (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  title             TEXT    NOT NULL CHECK (length(trim(title)) > 0),
  priority_level_id INTEGER REFERENCES priority_levels(id) ON DELETE RESTRICT,
  status_id         INTEGER NOT NULL DEFAULT 1 REFERENCES task_statuses(id) ON DELETE RESTRICT,
  deadline_at       TEXT,                  -- UTC ISO 时间，NULL = 无截止时间
  progress          TEXT,                  -- 进度，文字描述
  remark            TEXT,                  -- 备注
  created_at        TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at        TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at      TEXT,
  deleted_at        TEXT                   -- 软删除时间（UTC），NULL = 未删除
);

CREATE INDEX IF NOT EXISTS idx_tasks_deadline
  ON tasks(deadline_at) WHERE deadline_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_status_priority
  ON tasks(status_id, priority_level_id);

-- ---------------------------------------------------------------------------
-- 每日基础时间划分（全局唯一模板，每天都一样）
--   各块互不重叠；未覆盖的间隙视为未规划时间
--   应用层还应校验「无重叠」，DB 用触发器兜底
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS day_blocks (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  start_minute INTEGER NOT NULL CHECK (start_minute BETWEEN 0 AND 1439),
  end_minute   INTEGER NOT NULL CHECK (end_minute BETWEEN 1 AND 1440),
  label        TEXT,                       -- 如「上午工作」「午休」
  kind         TEXT,                       -- 自定义分类：work/rest/sleep/free...
  remark       TEXT,
  is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  deleted_at   TEXT,                       -- 软删除时间（UTC），NULL = 未删除
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (end_minute > start_minute)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_day_blocks_start
  ON day_blocks(start_minute) WHERE deleted_at IS NULL;

CREATE TRIGGER IF NOT EXISTS trg_day_blocks_no_overlap_ins
BEFORE INSERT ON day_blocks
FOR EACH ROW
WHEN NEW.is_active = 1 AND NEW.deleted_at IS NULL AND EXISTS (
  SELECT 1 FROM day_blocks b
  WHERE b.is_active = 1
    AND b.deleted_at IS NULL
    AND NEW.start_minute < b.end_minute
    AND NEW.end_minute   > b.start_minute
)
BEGIN
  SELECT RAISE(ABORT, 'day_blocks overlap');
END;

CREATE TRIGGER IF NOT EXISTS trg_day_blocks_no_overlap_upd
BEFORE UPDATE OF start_minute, end_minute, is_active, deleted_at ON day_blocks
FOR EACH ROW
WHEN NEW.is_active = 1 AND NEW.deleted_at IS NULL AND EXISTS (
  SELECT 1 FROM day_blocks b
  WHERE b.is_active = 1
    AND b.deleted_at IS NULL
    AND b.id <> OLD.id
    AND NEW.start_minute < b.end_minute
    AND NEW.end_minute   > b.start_minute
)
BEGIN
  SELECT RAISE(ABORT, 'day_blocks overlap');
END;

-- ---------------------------------------------------------------------------
-- 固定块：每日 / 每周 / 每月重复，优先级高于 day_blocks
--   recurrence_value 的含义由 recurrence 决定：
--     daily   -> NULL
--     weekly  -> 1..7 (ISO, 1=周一)，多个星期几就建多行
--     monthly -> 1..31，月份不存在该日则当月跳过
--   allow_task_schedule: 是否允许在该固定块时段内添加任务排期；0 = 不允许
--   effective_from: 生效起始日期（含），必填，默认由 API/CLI 取当天
--   effective_to:   生效结束日期（含），NULL = 不限制
--   overlap_priority: 固定块之间冲突时的裁决（越大越优先），平时为 0
--   不支持跨午夜，跨天请拆成两行
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fixed_blocks (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  title            TEXT    NOT NULL CHECK (length(trim(title)) > 0),
  recurrence       TEXT    NOT NULL CHECK (recurrence IN ('daily', 'weekly', 'monthly')),
  recurrence_value INTEGER,
  start_minute     INTEGER NOT NULL CHECK (start_minute BETWEEN 0 AND 1439),
  end_minute       INTEGER NOT NULL CHECK (end_minute BETWEEN 1 AND 1440),
  effective_from   TEXT    NOT NULL,       -- 'YYYY-MM-DD'，必填
  effective_to     TEXT,                   -- 'YYYY-MM-DD'
  overlap_priority INTEGER NOT NULL DEFAULT 0,
  allow_task_schedule INTEGER NOT NULL DEFAULT 1 CHECK (allow_task_schedule IN (0, 1)),
  remark           TEXT,
  is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  deleted_at       TEXT,                   -- 软删除时间（UTC），NULL = 未删除
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
  CHECK (effective_from IS NULL OR effective_to IS NULL OR effective_from <= effective_to)
);

CREATE INDEX IF NOT EXISTS idx_fixed_blocks_recurrence
  ON fixed_blocks(recurrence, recurrence_value, start_minute);

-- ---------------------------------------------------------------------------
-- 固定块例外：在指定日期范围内跳过某个固定块
--   匹配条件（全部满足才命中；NULL 表示不限制）：
--     effective_from/to  日期范围，含端点
--     skip_date          具体日期 'YYYY-MM-DD'
--     weekday            ISO 星期 1..7
--     day_of_month       每月几号 1..31
--   日期条件全为 NULL 时，表示范围内该固定块的每次发生都命中
--   start_minute/end_minute:
--     都为空    跳过整个固定块
--     都填写    只跳过与该时段重叠的部分
--   显式例外直接生效，不受 fixed_blocks.allow_task_schedule 影响
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fixed_block_exceptions (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  fixed_block_id INTEGER NOT NULL REFERENCES fixed_blocks(id) ON DELETE CASCADE,
  effective_from TEXT,                     -- 'YYYY-MM-DD'
  effective_to   TEXT,                     -- 'YYYY-MM-DD'
  skip_date      TEXT,                     -- 'YYYY-MM-DD'
  weekday        INTEGER CHECK (weekday BETWEEN 1 AND 7),
  day_of_month   INTEGER CHECK (day_of_month BETWEEN 1 AND 31),
  start_minute   INTEGER CHECK (start_minute BETWEEN 0 AND 1439),
  end_minute     INTEGER CHECK (end_minute BETWEEN 1 AND 1440),
  remark         TEXT,
  is_active      INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
  deleted_at     TEXT,                     -- 软删除时间（UTC），NULL = 未删除
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (effective_from IS NULL OR effective_to IS NULL OR effective_from <= effective_to),
  CHECK (
    (start_minute IS NULL AND end_minute IS NULL) OR
    (start_minute IS NOT NULL AND end_minute IS NOT NULL AND end_minute > start_minute)
  )
);

CREATE INDEX IF NOT EXISTS idx_fixed_block_exceptions_block
  ON fixed_block_exceptions(fixed_block_id, effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_fixed_block_exceptions_date
  ON fixed_block_exceptions(skip_date);

-- ---------------------------------------------------------------------------
-- 固定块发生实例状态：记录某个固定块在某一天的实际状态
--   occurrence_date 是具体日期，和 fixed_blocks 的重复规则无关；
--   固定块被例外整次跳过时不会产生 occurrence，也就不需要状态。
--   status: done=已完成，skipped=主动跳过，missed=未完成/漏掉
--   没有记录 = 未标记；同一 (fixed_block_id, occurrence_date) 只保留一条有效记录
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fixed_block_occurrence_logs (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  fixed_block_id  INTEGER NOT NULL REFERENCES fixed_blocks(id) ON DELETE CASCADE,
  occurrence_date TEXT    NOT NULL
                  CHECK (occurrence_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  status          TEXT    NOT NULL CHECK (status IN ('done', 'skipped', 'missed')),
  note            TEXT,
  deleted_at      TEXT,                    -- 软删除时间（UTC），NULL = 未删除
  created_at      TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_fixed_block_occurrence_logs
  ON fixed_block_occurrence_logs(fixed_block_id, occurrence_date)
  WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_fixed_block_occurrence_logs_date
  ON fixed_block_occurrence_logs(occurrence_date)
  WHERE deleted_at IS NULL;

-- ---------------------------------------------------------------------------
-- 每日备忘录：同一天可以有多条
--   memo_date 为本地日期 'YYYY-MM-DD'；只允许新增，不提供修改/删除接口。
--   deleted_at 为预留字段。
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS daily_memos (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  memo_date  TEXT    NOT NULL
             CHECK (memo_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  content    TEXT    NOT NULL CHECK (length(trim(content)) > 0),
  deleted_at TEXT,                          -- 预留字段，NULL = 未删除
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_daily_memos_date
  ON daily_memos(memo_date);

-- ---------------------------------------------------------------------------
-- [可选] 任务排期：把任务放进某天的某个时间段
--   不选也可先用 tasks + 截止时间；需要日历/时间轴视图时启用
--   allow_override: 0 = 锁定，不允许被更高优先级任务自动挤占
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS task_schedules (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id        INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  plan_date      TEXT    NOT NULL,           -- 本地日期 'YYYY-MM-DD'
  start_minute   INTEGER NOT NULL CHECK (start_minute BETWEEN 0 AND 1439),
  end_minute     INTEGER NOT NULL CHECK (end_minute BETWEEN 1 AND 1440),
  status         TEXT NOT NULL DEFAULT 'planned'
                 CHECK (status IN ('planned', 'done', 'skipped')),
  allow_override INTEGER NOT NULL DEFAULT 1 CHECK (allow_override IN (0, 1)),
  note           TEXT,
  deleted_at     TEXT,                       -- 软删除时间（UTC），NULL = 未删除
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now')),
  CHECK (end_minute > start_minute)
);

CREATE INDEX IF NOT EXISTS idx_task_schedules_date
  ON task_schedules(plan_date, start_minute);
CREATE INDEX IF NOT EXISTS idx_task_schedules_task
  ON task_schedules(task_id);
