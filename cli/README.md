# tasks-planner CLI

`cli/tp.py` 是 tasks-planner 本地 API 的命令行封装，只使用 Python 标准库，无需额外安装依赖。

## 快速开始

先启动后端（默认端口 56649）：

```bash
cd backend
.venv/bin/python run.py
```

再使用 CLI：

```bash
python3 cli/tp.py health
python3 cli/tp.py --json task list --open
```

也可以用包装脚本：

```bash
./cli/tp task list
```

## 全局选项

| 选项 | 说明 |
|---|---|
| `--api URL` | API 基地址，默认 `http://127.0.0.1:56649/api` |
| `--json` | 输出原始 JSON，适合脚本或 AI 解析 |
| `--timeout SEC` | 请求超时，默认 20 秒 |

环境变量：

| 变量 | 说明 |
|---|---|
| `TASKS_PLANNER_API` | 覆盖默认 API 基地址 |
| `TASKS_PLANNER_CLI_TIMEOUT` | 覆盖默认超时 |

## 时间与日期约定

- 时间可写 `HH:MM`（如 `09:30`）或分钟数（如 `570`），结束时间允许 `24:00` / `1440`。
- 区间为左闭右开 `[start, end)`。
- 日期使用 `YYYY-MM-DD`；`plan`、`schedule` 命令额外支持 `today` / `tomorrow` / `yesterday`。
- 截止时间支持完整 ISO 8601；只写 `YYYY-MM-DD` 时按当天 `23:59:59` 处理。
- 状态、优先级既可以传数字 ID，也可以传 code / 名称（如 `todo`、`待办`、`P1`）。

## 命令速查

### 健康检查与配置

```bash
tp health
tp meta get
tp meta set timezone Asia/Shanghai
```

### 状态

```bash
tp status list [--active-only] [--all]
tp status get ID
tp status create --code review --name 待评审 [--sort 15] [--remark ...] [--inactive] [--no-initial-filter]
tp status update ID [--name ...] [--sort ...] [--remark ...] [--active|--inactive] [--initial-filter|--no-initial-filter]
tp status delete ID
tp status restore ID
```

内置状态 `1..5`（`todo/doing/blocked/done/cancelled`）不可删除，只能停用。

### 优先级

```bash
tp priority list [--active-only] [--all]
tp priority get ID
tp priority create --level 1 --name P0 [--usage ...] [--remark ...] [--color '#e5484d']
tp priority update ID [--level ...] [--name ...] [--usage ...] [--color ...] [--active|--inactive]
tp priority delete ID
tp priority restore ID
```

`--priority` 参数可传 ID、level 或名称。

### 任务

```bash
tp task list [--status CODE]... [--priority P1]... [-q 关键词] \
             [--deadline-from DATE] [--deadline-to DATE] \
             [--open] [--all] [--limit 100] [--offset 0]
tp task unscheduled [--priority P1]... [-q 关键词] \
                    [--deadline-from DATE] [--deadline-to DATE] \
                    [--limit 100] [--offset 0]
tp task get ID
tp task add "标题" [--priority P1] [--status doing] [--deadline 2026-11-22] \
             [--progress ...] [--remark ...]
tp task update ID [--title ...] [--priority ...|--no-priority] [--status ...] \
                  [--deadline ...|--clear-deadline] [--progress ...|--clear-progress] \
                  [--remark ...|--clear-remark]
tp task done ID
tp task start ID
tp task cancel ID
tp task delete ID
tp task restore ID
```

`--open` 在客户端过滤掉 `done` 与 `cancelled`。

### 每日基础模板（day blocks）

```bash
tp dayblock list [--active-only] [--all]
tp dayblock add --start 09:00 --end 12:00 [--label 上午工作] [--kind work] [--remark ...] [--inactive]
tp dayblock update ID [--start ...] [--end ...] [--label ...] [--kind ...] [--remark ...] [--active|--inactive]
tp dayblock replace --file template.json
tp dayblock replace --data '[{"start_minute":540,"end_minute":720,"label":"上午工作"}]'
tp dayblock delete ID
tp dayblock restore ID
```

`replace` 会整体替换模板，启用状态的块之间不能重叠；空数组表示清空。

### 固定块（fixed blocks）

```bash
tp fixed list [--recurrence daily|weekly|monthly] [--active-only] [--all]
tp fixed get ID
tp fixed add --title 周会 --recurrence weekly --value 5 --start 10:00 --end 11:00 \
             [--from 2026-01-01] [--to 2026-12-31] [--overlap-priority 10] \
             [--no-task-schedule] [--remark ...] [--inactive]
tp fixed update ID [--title ...] [--recurrence ...] [--value ...] [--start ...] [--end ...] \
                   [--from ...] [--to ...] [--clear-effective] [--overlap-priority ...] \
                   [--allow-task-schedule|--no-task-schedule] [--remark ...] [--active|--inactive]
tp fixed delete ID
tp fixed restore ID
```

`weekly` 的 `--value` 为 ISO 星期 `1..7`（1=周一）；`monthly` 为日号 `1..31`；`daily` 不传 `--value`。传 `--no-task-schedule` 表示禁止在该固定块时段内添加任务排期。

### 固定块例外

```bash
tp exception list [--fixed-block ID] [--active-only] [--all]
tp exception get ID
tp exception add --fixed-block ID [--skip-date 2026-12-25] [--weekday 5] [--day-of-month 1] \
                 [--from DATE] [--to DATE] [--start 10:20 --end 10:40] [--remark ...] [--inactive]
tp exception update ID [--skip-date ...] [--weekday ...] [--day-of-month ...] \
                       [--from ...] [--to ...] [--start ... --end ...] [--clear-time] \
                       [--remark ...] [--active|--inactive]
tp exception delete ID
tp exception restore ID
```

不传 `--start/--end` 表示跳过整个固定块；传则只跳过重叠部分。日期条件会同时生效（AND）。

### 任务排期

```bash
tp schedule list [--date DATE] [--task ID] [--status planned|done|skipped] [--all]
tp schedule get ID
tp schedule add --task ID --date DATE --start 09:00 --end 10:00 \
                [--status planned|done|skipped] [--no-override] [--note ...]
tp schedule update ID [--task ...] [--date ...] [--start ...] [--end ...] \
                      [--status ...] [--allow-override|--no-override] \
                      [--note ...|--clear-note]
tp schedule delete ID
tp schedule restore ID
```

排期接口会校验冲突：与禁止添加排期的固定块重叠，或与同一天未删除、未跳过的其他排期重叠时返回 `409`。可先用 `plan day` 查看当天占用情况。

### 备忘录（只增）

```bash
tp memo list [--period day|week|month] [--date DATE]
tp memo add "今天先把接口做完" [--date DATE]

tp memo list --period week --date today
tp memo list --period month --date 2026-11-20
tp memo add "临时想法" --date 2026-11-20
```

`--date` 默认 `today`，也支持 `tomorrow` / `yesterday`。备忘录只能新增和查询，不能修改或删除；同一天可以有多条。

### 规划视图

```bash
tp plan day 2026-11-20
tp plan day today
tp --json plan day 2026-11-20
```

输出当天：

- `fixed_occurrences`：固定块实际发生的时间段（已应用例外）
- `schedules`：任务排期
- `day_blocks`：每日基础模板
- `free`：从模板中扣除固定块与排期后的自由时间
- `conflicts`：排期与固定块、排期与排期之间的重叠

### 任意 API

```bash
tp raw GET /tasks --param limit=5 --param status_code=todo
tp raw POST /tasks --data '{"title":"临时任务"}'
tp raw PATCH /tasks/1 --data '{"progress":"50%"}'
```

`path` 相对于 API 基地址，例如 `/tasks`、`/plan/fixed-occurrences`。

## 典型工作流

```bash
# 1. 查看现状
tp --json status list
tp --json priority list
tp --json task list --open

# 2. 建任务
tp task add "完成报告" --priority P1 --deadline 2026-11-22
tp task add "准备会议材料" --priority P2 --deadline 2026-11-21

# 3. 看某天有哪些空闲时间
tp plan day 2026-11-20

# 4. 把任务排进自由时间
tp schedule add --task 1 --date 2026-11-20 --start 09:00 --end 10:00
tp plan day 2026-11-20          # 再次确认无冲突

# 5. 完成
tp task done 1
```

## 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 成功 |
| `1` | API 返回错误（4xx/5xx）或服务不可达 |
| `2` | 参数、时间或 JSON 解析错误 |
