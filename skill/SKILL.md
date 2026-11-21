---
name: tasks-planner
description: 当用户要求管理任务、查看待办、安排日程/时间规划、创建固定日程（如周会、健身）、跳过某次固定日程、或询问某天的时间安排时使用。通过 tasks-planner 本地服务的 CLI 操作任务、优先级、状态、每日模板、固定块、例外与任务排期。
---

# tasks-planner 任务与时间规划技能

本技能用于操作本地 `tasks-planner` 服务。它是单用户、本地优先的任务与时间规划系统，包含任务、优先级、状态、每日基础模板、固定日程、任务排期和规划视图。

## 位置与连接

- 项目根目录：本仓库根目录
- CLI：`python3 cli/tp.py`（或 `./cli/tp`）
- API：`http://127.0.0.1:56649/api`
- 所有命令都可加 `--json` 获取机器可读输出。

先确认服务存活：

```bash
curl -s http://127.0.0.1:56649/api/health
```

若服务未启动，在项目根目录后台启动：

```bash
cd backend
nohup .venv/bin/python run.py > /tmp/tasks-planner-api.log 2>&1 &
```

## 核心模型

| 概念 | 说明 |
|---|---|
| 任务 task | 标题、优先级、状态、截止时间、进度文字、备注 |
| 状态 status | 内置 `todo/doing/blocked/done/cancelled`（id 1..5）。**「未排期」不是状态**，是 `GET /tasks/unscheduled` 的查询结果 |
| 优先级 priority | 用户自定义，`level=1` 最高 |
| 每日模板 day block | 每天的固定时间划分，如 09:00-12:00 工作；全库共用一份 |
| 固定块 fixed block | 每天/每周/每月重复的日程，如周会、健身；优先级高于模板与排期 |
| 例外 exception | 跳过某个固定块的某次发生，或只跳过其中一段时间 |
| 排期 schedule | 把任务放进某天某个时间段，状态 `planned/done/skipped` |
| 规划视图 plan day | 汇总某天的固定块、排期、模板、自由时间与冲突 |

优先级从低到高：`day_blocks` 模板 → `task_schedules` 排期 → `fixed_blocks` 固定块。

## 强制规则

1. **只通过 CLI / API 读写**，禁止直接修改 SQLite 数据库。
2. **解析数据时一律加 `--json`**，不要依赖人类可读表格做判断。
3. **写之前先读**：先查 `status list`、`priority list`、`task list`、`plan day`，不要猜 ID。
4. 时间参数可写 `HH:MM` 或分钟；区间为**左闭右开** `[start, end)`，结束时间可用 `24:00` / `1440`。
5. 日期统一使用 `YYYY-MM-DD`。除非用户明确说“今天/明天”，否则使用用户给出的日期。
6. 状态和优先级参数可传 ID、code 或名称：`--status done`、`--status 待办`、`--priority P1`、`--priority 2`。
7. **删除是软删除**，可用 `restore` 恢复。执行 `delete` 前必须先向用户确认。
8. 内置状态 `1..5` 不可删除；需要隐藏时用 `status update ID --inactive`。
9. **排期接口会校验冲突**（`backend/app/routers/task_schedules.py::_ensure_no_conflicts`）：与 `allow_task_schedule=0` 的固定块或同日其他排期重叠时返回 `409`。排期前后都跑一次 `plan day`，那是复核不是唯一检查。
10. 不要把任务排进 `fixed_occurrences` 或已有排期占用的时间段；优先使用 `free` 中的空闲段。
11. 用户的具体偏好以当前会话中的明确要求为准。

## 标准工作流

### A. 查看任务 / 回答用户

```bash
tp --json task list --open
tp --json task list --status todo
tp --json task list --status todo --status doing --priority P1 --priority P2
tp --json task unscheduled      # 未排期池：没有任何未删除排期的任务
tp --json plan day 2026-11-20
```

汇总时使用 `HH:MM` 展示时间，并标注任务 ID / 排期 ID，方便后续操作。

### B. 新建任务

```bash
tp --json priority list
tp --json status list
tp task add "完成报告" --priority P1 --deadline 2026-11-22 --progress "整理数据"
```

若用户没有指定优先级或截止时间，不要自行编造；可以创建后说明未设置。

### C. 规划某一天

1. 读取当天现状：

```bash
tp --json plan day 2026-11-20
```

2. 查看 `free` 空闲段和 `conflicts`；同时查看待办任务：

```bash
tp --json task list --open
```

3. 按优先级和截止时间选择任务与空闲段，创建排期：

```bash
tp schedule add --task 3 --date 2026-11-20 --start 09:00 --end 10:00 --note "深度工作"
```

4. 再次验证：

```bash
tp --json plan day 2026-11-20
```

5. 若出现 `conflicts`，调整排期时间或位置，直到无冲突。

### D. 固定日程

```bash
# 每周五 10:00-11:00 周会
tp fixed add --title "周会" --recurrence weekly --value 5 --start 10:00 --end 11:00

# 每天 23:00-23:30 复盘
tp fixed add --title "每日复盘" --recurrence daily --start 23:00 --end 23:30

# 每月 1 日 09:00-10:00
tp fixed add --title "月度规划" --recurrence monthly --value 1 --start 09:00 --end 10:00
```

`weekly` 的 `--value` 是 ISO 星期（1=周一 … 7=周日）；`monthly` 是日号 1..31。

### E. 跳过某次固定日程

```bash
# 只跳过 2026-12-25 的周会
tp exception add --fixed-block 1 --skip-date 2026-12-25 --remark "圣诞节"

# 每周五都跳过周会
tp exception add --fixed-block 1 --weekday 5

# 国庆期间全部跳过
tp exception add --fixed-block 1 --from 2026-10-01 --to 2026-10-07 --remark "国庆"
```

不填 `--start/--end` 表示跳过整个固定块；填写时只跳过与固定块重叠的部分。

### F. 完成 / 调整任务

```bash
tp task done 3
tp task start 4
tp task update 4 --progress "已完成初稿"
tp task update 5 --deadline 2026-11-30
```

## 常用命令速查

```bash
# 任务
tp task list [--status CODE]... [--priority P1]... [-q 关键词] [--open] [--all]
tp task unscheduled [--priority P1]... [-q 关键词] [--deadline-from/--deadline-to DATE]
tp task get ID
tp task add "标题" [--priority P0] [--status doing] [--deadline DATE] [--progress ...]
tp task update ID [--title ...] [--priority ...] [--status ...] [--deadline ...]
tp task done|start|cancel ID
tp task delete|restore ID

# 状态 / 优先级
tp status list
tp priority list
tp priority create --level 5 --name P4 --usage "..."

# 每日模板
tp dayblock list
tp dayblock add --start 09:00 --end 12:00 --label "上午工作" --kind work
tp dayblock replace --data '[{"start_minute":540,"end_minute":720,"label":"上午工作"}]'

# 固定块
tp fixed list
tp fixed add --title "周会" --recurrence weekly --value 5 --start 10:00 --end 11:00
tp fixed update ID --overlap-priority 10
tp fixed delete|restore ID

# 例外
tp exception list [--fixed-block ID]
tp exception add --fixed-block ID [--skip-date DATE] [--weekday N] [--day-of-month N] \
                 [--from DATE] [--to DATE] [--start HH:MM --end HH:MM]
tp exception delete|restore ID

# 排期
tp schedule list [--date DATE] [--task ID] [--status planned|done|skipped]
tp schedule add --task ID --date DATE --start HH:MM --end HH:MM [--note ...]
tp schedule update ID [--date ...] [--start ...] [--end ...] [--status ...]
tp schedule delete|restore ID

# 规划视图
tp plan day DATE

# 任意接口
tp raw GET /tasks --param limit=5
tp raw PATCH /tasks/1 --data '{"progress":"50%"}'
```

完整参数见 `cli/README.md`。

## 常见错误处理

| 现象 | 原因与处理 |
|---|---|
| `API error (0): cannot reach ...` | 服务未启动；按上文启动并检查 `/api/health` |
| `422 status_id 对应的任务状态不存在` | 状态 ID 错误；重新 `status list` 并用 code/名称 |
| `422 priority_level_id 对应的优先级不存在` | 优先级 ID 错误；重新 `priority list` |
| `409 数据库约束冲突：day_blocks overlap` | 模板时间块重叠；改用 `dayblock replace` 重排 |
| `404 任务不存在` | 任务已软删除；需要时先 `task restore ID` |
| `conflicts: schedule ... overlaps fixed block` | 排期压到固定块；移动到 `free` 的空闲段 |

## 汇报要求

- 对用户使用简洁的中文，展示时间用 `HH:MM`。
- 列出本次创建/修改的对象 ID，例如 `task #3`、`schedule #7`。
- 排期完成后说明是否与固定块或既有排期冲突。
- 除非用户要求，不要直接粘贴大段原始 JSON。
