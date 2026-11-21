export interface TaskStatus {
  id: number
  code: string
  name: string
  sort_order: number
  remark: string | null
  is_active: boolean
  is_initial_filter: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface TaskStatusCreate {
  code: string
  name: string
  sort_order?: number
  remark?: string | null
  is_active?: boolean
  is_initial_filter?: boolean
}

export interface TaskStatusUpdate {
  name?: string
  sort_order?: number
  remark?: string | null
  is_active?: boolean
  is_initial_filter?: boolean
}

export interface PriorityLevel {
  id: number
  level: number
  name: string
  usage: string | null
  remark: string | null
  color: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface PriorityLevelCreate {
  level: number
  name: string
  usage?: string | null
  remark?: string | null
  color?: string | null
  is_active?: boolean
}

export interface PriorityLevelUpdate {
  level?: number
  name?: string
  usage?: string | null
  remark?: string | null
  color?: string | null
  is_active?: boolean
}

export interface Task {
  id: number
  title: string
  priority_level_id: number | null
  status_id: number
  deadline_at: string | null
  progress: string | null
  remark: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  completed_at: string | null
  status_code: string
  status_name: string
  priority_level: number | null
  priority_name: string | null
  priority_color: string | null
}

export interface TaskCreate {
  title: string
  priority_level_id?: number | null
  status_id?: number
  deadline_at?: string | null
  progress?: string | null
  remark?: string | null
}

export interface TaskUpdate {
  title?: string
  priority_level_id?: number | null
  status_id?: number
  deadline_at?: string | null
  progress?: string | null
  remark?: string | null
}

export interface DayBlock {
  id: number
  start_minute: number
  end_minute: number
  label: string | null
  kind: string | null
  remark: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface DayBlockCreate {
  start_minute: number
  end_minute: number
  label?: string | null
  kind?: string | null
  remark?: string | null
  is_active?: boolean
}

export interface DayBlockUpdate {
  start_minute?: number
  end_minute?: number
  label?: string | null
  kind?: string | null
  remark?: string | null
  is_active?: boolean
}

export interface DayBlockBulkReplace {
  blocks: DayBlockCreate[]
}

export interface FixedBlock {
  id: number
  title: string
  recurrence: 'daily' | 'weekly' | 'monthly'
  recurrence_value: number | null
  start_minute: number
  end_minute: number
  effective_from: string | null
  effective_to: string | null
  overlap_priority: number
  allow_task_schedule: boolean
  remark: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface FixedBlockCreate {
  title: string
  recurrence: 'daily' | 'weekly' | 'monthly'
  recurrence_value?: number | null
  start_minute: number
  end_minute: number
  effective_from?: string | null
  effective_to?: string | null
  overlap_priority?: number
  allow_task_schedule?: boolean
  remark?: string | null
  is_active?: boolean
}

export interface FixedBlockUpdate {
  title?: string
  recurrence?: 'daily' | 'weekly' | 'monthly'
  recurrence_value?: number | null
  start_minute?: number
  end_minute?: number
  effective_from?: string | null
  effective_to?: string | null
  overlap_priority?: number
  allow_task_schedule?: boolean
  remark?: string | null
  is_active?: boolean
}

export interface FixedBlockException {
  id: number
  fixed_block_id: number
  effective_from: string | null
  effective_to: string | null
  skip_date: string | null
  weekday: number | null
  day_of_month: number | null
  start_minute: number | null
  end_minute: number | null
  remark: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface FixedBlockExceptionCreate {
  effective_from?: string | null
  effective_to?: string | null
  skip_date?: string | null
  weekday?: number | null
  day_of_month?: number | null
  start_minute?: number | null
  end_minute?: number | null
  remark?: string | null
  is_active?: boolean
}

export type FixedBlockExceptionUpdate = Partial<FixedBlockExceptionCreate>

export interface TaskSchedule {
  id: number
  task_id: number
  task_title: string
  plan_date: string
  start_minute: number
  end_minute: number
  status: 'planned' | 'done' | 'skipped'
  allow_override: boolean
  note: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface TaskScheduleCreate {
  task_id: number
  plan_date: string
  start_minute: number
  end_minute: number
  status?: 'planned' | 'done' | 'skipped'
  allow_override?: boolean
  note?: string | null
}

export interface TaskScheduleUpdate {
  task_id?: number
  plan_date?: string
  start_minute?: number
  end_minute?: number
  status?: 'planned' | 'done' | 'skipped'
  allow_override?: boolean
  note?: string | null
}

export interface DailyMemo {
  id: number
  memo_date: string
  content: string
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface DailyMemoCreate {
  memo_date: string
  content: string
}

export type MemoPeriod = 'day' | 'week' | 'month'

export interface MemoListParams {
  period?: MemoPeriod
  date: string
}

export interface FixedOccurrence {
  fixed_block_id: number
  title: string
  date: string
  start_minute: number
  end_minute: number
  overlap_priority: number
  allow_task_schedule: boolean
  remark: string | null
}

export interface TaskListParams {
  status_code?: string[] | null
  priority_level_id?: number[] | null
  q?: string | null
  deadline_from?: string | null
  deadline_to?: string | null
  include_deleted?: boolean
  limit?: number
  offset?: number
}

export interface LookupListParams {
  active_only?: boolean
  include_deleted?: boolean
}

export interface FixedBlockListParams extends LookupListParams {
  recurrence?: 'daily' | 'weekly' | 'monthly' | null
}

export interface ScheduleListParams {
  date?: string | null
  task_id?: number | null
  status?: 'planned' | 'done' | 'skipped' | null
  include_deleted?: boolean
}

export type MetaMap = Record<string, string>
