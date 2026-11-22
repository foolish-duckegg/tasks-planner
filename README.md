# tasks-planner

单用户、本地优先的任务与时间规划系统。以「任务 → 优先级 / 状态 → 每日模板 → 固定日程 → 任务排期 → 规划视图」为主线，帮助你决定**今天什么时候做什么**。

包含四个部分：

- **后端**：FastAPI + SQLite，提供完整 REST API
- **前端**：Vue 3 + Element Plus，含仪表盘、任务、规划、模板、固定块、设置等页面
- **CLI**：纯标准库实现的命令行工具，适合脚本化与 AI 调用
- **AI 技能**：`skill/` 下的使用规范，让智能体安全地操作该服务

## 功能特性

- 任务管理：标题、优先级、状态、截止时间、进度、备注，支持软删除与恢复
- 自定义优先级与任务状态（内置 `todo/doing/blocked/done/cancelled`）
- 每日基础模板：把一天划分为可复用的时间段
- 固定日程：按每天 / 每周 / 每月重复，支持生效区间与重叠优先级
- 固定块追踪：记录某次固定块是完成、跳过还是未完成
- 固定块例外：跳过某一次固定日程，或只跳过其中一段
- 任务排期：把任务放进某天某个时间段，自动校验冲突
- 规划视图：汇总某天的固定块、排期、模板、空闲时间与冲突
- 未排期池：按「是否存在排期」统计，而不是靠状态维护
- 每日备忘录：只增不改，支持按天 / 周 / 月查询
- 中英文界面、深浅色主题

## 项目结构

```text
tasks-planner/
├── backend/              # FastAPI 服务
│   ├── app/
│   │   ├── main.py       # 应用入口、异常处理、路由注册
│   │   ├── config.py     # 环境变量与路径配置
│   │   ├── database.py   # SQLite 连接、初始化、迁移
│   │   ├── schemas.py    # Pydantic 请求/响应模型
│   │   ├── utils.py      # 时间与时区处理
│   │   ├── routers/      # 各业务路由
│   │   └── static/       # 前端构建产物（git 忽略）
│   ├── requirements.txt
│   └── run.py            # 启动脚本
├── frontend/             # Vue 3 单页应用
│   └── src/
│       ├── views/        # 仪表盘、任务、规划、模板、固定块、设置
│       ├── components/   # 日历、时间轴、各类表单弹窗
│       ├── api/          # axios 客户端与类型
│       ├── stores/       # Pinia 状态
│       └── i18n/         # 中英文文案
├── cli/                  # 命令行工具 tp
│   ├── tp.py             # 主程序
│   ├── api.py            # HTTP 封装
│   ├── fmt.py            # 输出格式化
│   └── README.md         # 完整命令文档
├── docs/                 # 数据库设计与建表脚本
│   ├── database.md
│   ├── schema.sql
│   └── api.json          # OpenAPI 导出
├── skill/                # AI 智能体使用规范
│   └── SKILL.md
├── .github/workflows/    # tag 触发的 Release 工作流
├── Dockerfile            # 多阶段构建：前端静态资源 + 后端
├── Makefile              # 构建与打包命令
└── data/                 # 运行时 SQLite 数据（git 忽略）
```

## 快速开始

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

启动后：

- API 根地址：<http://127.0.0.1:56649>
- Swagger：<http://127.0.0.1:56649/docs>
- ReDoc：<http://127.0.0.1:56649/redoc>
- 健康检查：<http://127.0.0.1:56649/api/health>

首次启动会自动创建数据库并执行 `docs/schema.sql`。开发时可用热重载：

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 56649 --reload
```

后台运行：

```bash
cd backend
nohup .venv/bin/python run.py > /tmp/tasks-planner-api.log 2>&1 &
```

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认运行在 <http://127.0.0.1:5173>，并通过 Vite 代理把 `/api` 转发到后端。

生产构建会把前端静态文件直接输出到 `backend/app/static/`：

```bash
cd frontend
npm install
npm run build
```

之后只启动后端即可，`/` 和所有前端路由都由同一个服务提供：

```bash
cd backend
.venv/bin/python run.py
```

也可以从项目根目录执行：

```bash
make build      # 安装依赖并构建前端
make release    # 构建前端并生成 release/tasks-planner-<version>.tar.gz
```

### 3. 使用 CLI

先确保后端已启动：

```bash
python3 cli/tp.py health
python3 cli/tp.py --json task list --open
./cli/tp task list          # 包装脚本
```

完整命令见 [`cli/README.md`](cli/README.md)。常用示例：

```bash
tp task add "完成报告" --priority P1 --deadline 2026-11-22
tp plan day today
tp schedule add --task 1 --date today --start 09:00 --end 10:00
tp task done 1
```

## 配置

后端通过环境变量覆盖默认值：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `TASKS_PLANNER_HOST` | `127.0.0.1` | 监听地址 |
| `TASKS_PLANNER_PORT` | `56649` | 监听端口 |
| `TASKS_PLANNER_DB` | `data/tasks-planner.db` | SQLite 文件路径 |
| `TASKS_PLANNER_DATA_DIR` | `data/` | 数据目录 |
| `TASKS_PLANNER_SCHEMA` | `docs/schema.sql` | 建表脚本 |
| `TASKS_PLANNER_STATIC_DIR` | `backend/app/static/` | 前端构建产物目录 |
| `TASKS_PLANNER_CORS_ORIGINS` | `*` | 逗号分隔的 CORS 来源 |

前端：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `TASKS_PLANNER_API` | `http://127.0.0.1:56649` | Vite 开发代理目标 |
| `VITE_API_BASE` | 空 | 前后端分开部署时的 API 基地址 |

CLI：

| 变量 | 说明 |
|---|---|
| `TASKS_PLANNER_API` | API 基地址，默认 `http://127.0.0.1:56649/api` |
| `TASKS_PLANNER_CLI_TIMEOUT` | 请求超时秒数，默认 20 |

## 核心概念

| 概念 | 说明 |
|---|---|
| 任务 task | 标题、优先级、状态、截止时间、进度文字、备注 |
| 状态 status | 内置 `todo/doing/blocked/done/cancelled`，可自定义，只能停用内置状态 |
| 优先级 priority | 用户自定义，`level=1` 最高 |
| 每日模板 day block | 每天相同的时间划分模板，全库共用一份 |
| 固定块 fixed block | 每天 / 每周 / 每月重复的日程，优先级高于模板与排期；`effective_from` 必填，默认当天 |
| 固定块状态 occurrence | 某次固定块的实际状态：`done` / `skipped` / `missed`，无记录表示未标记 |
| 例外 exception | 跳过某次固定块的整段或一段 |
| 排期 schedule | 把任务放入某天某个时间段，状态 `planned/done/skipped` |
| 规划视图 plan day | 汇总某天的固定块、排期、模板、空闲时间与冲突 |

时间占用优先级：`day_blocks` 模板 < `task_schedules` 排期 < `fixed_blocks` 固定块。

## API 概览

| 前缀 | 说明 |
|---|---|
| `/api/health` | 健康检查 |
| `/api/meta` | 应用配置（时区、周起始日等） |
| `/api/statuses` | 任务状态 CRUD 与恢复 |
| `/api/priorities` | 优先级 CRUD 与恢复 |
| `/api/tasks` | 任务 CRUD、恢复、未排期查询 |
| `/api/day-blocks` | 每日基础模板 |
| `/api/fixed-blocks` | 固定块 |
| `/api/fixed-blocks/{id}/exceptions`、`/api/fixed-block-exceptions` | 固定块例外 |
| `/api/fixed-block-occurrences` | 固定块发生实例状态，支持列出已过且未完成的实例 |
| `/api/task-schedules` | 任务排期，写入时校验冲突 |
| `/api/memos` | 每日备忘录，只增与查询 |
| `/api/plan/fixed-occurrences` | 计算某天实际发生的固定块 |

完整 OpenAPI 文档可访问 `/docs`，或查看 `docs/api.json`。

## 数据约定

- 时间为「距当天 00:00 的分钟数」，`00:00 = 0`，`24:00 = 1440`
- 时间区间左闭右开 `[start_minute, end_minute)`
- 日期使用本地日期字符串 `YYYY-MM-DD`
- 时间戳以 UTC 存储，输出时按 `app_meta.timezone` 转为本地时间
- 业务数据均为软删除，可通过 `restore` 接口恢复
- 启动时自动执行 `schema_migrations` 中尚未记录的迁移，旧库无需手动改表
- SQLite 使用 WAL 模式，每个连接开启外键约束

详细设计见 [`docs/database.md`](docs/database.md)，建表脚本见 [`docs/schema.sql`](docs/schema.sql)。

## 部署与发布

### 源码运行

```bash
make build
cd backend
.venv/bin/python run.py
```

访问 <http://127.0.0.1:56649> 即为前端页面；`/docs`、`/redoc` 仍然保留。未构建前端时，`/` 会回退到 `/docs`。

前端使用 history 路由，后端已处理 `/tasks`、`/planner` 等深链接刷新，并排除 `/api/*` 避免把 API 404 变成 HTML。

### 打包发布

```bash
make release
```

生成 `release/tasks-planner-<version>.tar.gz`，包含后端、已构建的前端静态文件、CLI 和文档，不包含 `.venv`、`data/` 与缓存。解压后：

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/python backend/run.py
```

### Docker

```bash
docker build -t tasks-planner .
docker run --rm -p 56649:56649 -v tasks-planner-data:/data tasks-planner
```

镜像内前端在构建阶段生成，运行阶段由后端统一托管，数据目录通过 `/data` 卷持久化。

### GitHub Release

版本号位于 `backend/app/__init__.py` 和 `frontend/package.json`，健康检查会返回当前版本：

```bash
curl http://127.0.0.1:56649/api/health
# {"status":"ok","version":"0.1.0"}
```

推送 `v*` tag 会触发 [`.github/workflows/release.yml`](.github/workflows/release.yml)，自动构建前端、生成压缩包并创建 GitHub Release：

```bash
git tag v0.1.0
git push origin v0.1.0
```

## 文档

- 数据库结构与设计：[`docs/database.md`](docs/database.md)
- CLI 完整命令：[`cli/README.md`](cli/README.md)
- AI 智能体使用规范：[`skill/SKILL.md`](skill/SKILL.md)
- OpenAPI：`docs/api.json` 或服务启动后的 `/docs`
