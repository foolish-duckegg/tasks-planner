import { http } from './client'
import type {
  DailyMemo,
  DailyMemoCreate,
  DayBlock,
  DayBlockBulkReplace,
  DayBlockCreate,
  DayBlockUpdate,
  FixedBlock,
  FixedBlockCreate,
  FixedBlockException,
  FixedBlockExceptionCreate,
  FixedBlockExceptionUpdate,
  FixedBlockListParams,
  FixedBlockUpdate,
  FixedOccurrence,
  LookupListParams,
  MemoListParams,
  MetaMap,
  PriorityLevel,
  PriorityLevelCreate,
  PriorityLevelUpdate,
  ScheduleListParams,
  Task,
  TaskCreate,
  TaskListParams,
  TaskSchedule,
  TaskScheduleCreate,
  TaskScheduleUpdate,
  TaskStatus,
  TaskStatusCreate,
  TaskStatusUpdate,
  TaskUpdate,
} from './types'

const unwrap = <T>(request: Promise<{ data: T }>) => request.then((response) => response.data)

export const api = {
  health: () => unwrap<Record<string, string>>(http.get('/health')),

  meta: {
    list: () => unwrap<MetaMap>(http.get('/meta')),
    put: (key: string, value: string) =>
      unwrap<MetaMap>(http.put(`/meta/${encodeURIComponent(key)}`, { value })),
  },

  statuses: {
    list: (params?: LookupListParams) =>
      unwrap<TaskStatus[]>(http.get('/statuses', { params })),
    get: (id: number) => unwrap<TaskStatus>(http.get(`/statuses/${id}`)),
    create: (payload: TaskStatusCreate) =>
      unwrap<TaskStatus>(http.post('/statuses', payload)),
    update: (id: number, payload: TaskStatusUpdate) =>
      unwrap<TaskStatus>(http.patch(`/statuses/${id}`, payload)),
    remove: (id: number) => unwrap<void>(http.delete(`/statuses/${id}`)),
    restore: (id: number) =>
      unwrap<TaskStatus>(http.post(`/statuses/${id}/restore`)),
  },

  priorities: {
    list: (params?: LookupListParams) =>
      unwrap<PriorityLevel[]>(http.get('/priorities', { params })),
    get: (id: number) => unwrap<PriorityLevel>(http.get(`/priorities/${id}`)),
    create: (payload: PriorityLevelCreate) =>
      unwrap<PriorityLevel>(http.post('/priorities', payload)),
    update: (id: number, payload: PriorityLevelUpdate) =>
      unwrap<PriorityLevel>(http.patch(`/priorities/${id}`, payload)),
    remove: (id: number) => unwrap<void>(http.delete(`/priorities/${id}`)),
    restore: (id: number) =>
      unwrap<PriorityLevel>(http.post(`/priorities/${id}/restore`)),
  },

  tasks: {
    list: (params?: TaskListParams) =>
      unwrap<Task[]>(
        http.get('/tasks', { params, paramsSerializer: { indexes: null } }),
      ),
    unscheduled: (params?: Omit<TaskListParams, 'status_code'>) =>
      unwrap<Task[]>(
        http.get('/tasks/unscheduled', {
          params,
          paramsSerializer: { indexes: null },
        }),
      ),
    get: (id: number) => unwrap<Task>(http.get(`/tasks/${id}`)),
    create: (payload: TaskCreate) => unwrap<Task>(http.post('/tasks', payload)),
    update: (id: number, payload: TaskUpdate) =>
      unwrap<Task>(http.patch(`/tasks/${id}`, payload)),
    remove: (id: number) => unwrap<void>(http.delete(`/tasks/${id}`)),
    restore: (id: number) => unwrap<Task>(http.post(`/tasks/${id}/restore`)),
  },

  dayBlocks: {
    list: (params?: LookupListParams) =>
      unwrap<DayBlock[]>(http.get('/day-blocks', { params })),
    replace: (payload: DayBlockBulkReplace) =>
      unwrap<DayBlock[]>(http.put('/day-blocks', payload)),
    create: (payload: DayBlockCreate) =>
      unwrap<DayBlock>(http.post('/day-blocks', payload)),
    update: (id: number, payload: DayBlockUpdate) =>
      unwrap<DayBlock>(http.patch(`/day-blocks/${id}`, payload)),
    remove: (id: number) => unwrap<void>(http.delete(`/day-blocks/${id}`)),
    restore: (id: number) =>
      unwrap<DayBlock>(http.post(`/day-blocks/${id}/restore`)),
  },

  fixedBlocks: {
    list: (params?: FixedBlockListParams) =>
      unwrap<FixedBlock[]>(http.get('/fixed-blocks', { params })),
    get: (id: number) => unwrap<FixedBlock>(http.get(`/fixed-blocks/${id}`)),
    create: (payload: FixedBlockCreate) =>
      unwrap<FixedBlock>(http.post('/fixed-blocks', payload)),
    update: (id: number, payload: FixedBlockUpdate) =>
      unwrap<FixedBlock>(http.patch(`/fixed-blocks/${id}`, payload)),
    remove: (id: number) => unwrap<void>(http.delete(`/fixed-blocks/${id}`)),
    restore: (id: number) =>
      unwrap<FixedBlock>(http.post(`/fixed-blocks/${id}/restore`)),
  },

  exceptions: {
    listAll: (params?: { fixed_block_id?: number; active_only?: boolean; include_deleted?: boolean }) =>
      unwrap<FixedBlockException[]>(http.get('/fixed-block-exceptions', { params })),
    listByBlock: (fixedBlockId: number, params?: LookupListParams) =>
      unwrap<FixedBlockException[]>(
        http.get(`/fixed-blocks/${fixedBlockId}/exceptions`, { params }),
      ),
    get: (id: number) =>
      unwrap<FixedBlockException>(http.get(`/fixed-block-exceptions/${id}`)),
    create: (fixedBlockId: number, payload: FixedBlockExceptionCreate) =>
      unwrap<FixedBlockException>(
        http.post(`/fixed-blocks/${fixedBlockId}/exceptions`, payload),
      ),
    update: (id: number, payload: FixedBlockExceptionUpdate) =>
      unwrap<FixedBlockException>(http.patch(`/fixed-block-exceptions/${id}`, payload)),
    remove: (id: number) =>
      unwrap<void>(http.delete(`/fixed-block-exceptions/${id}`)),
    restore: (id: number) =>
      unwrap<FixedBlockException>(http.post(`/fixed-block-exceptions/${id}/restore`)),
  },

  schedules: {
    list: (params?: ScheduleListParams) =>
      unwrap<TaskSchedule[]>(http.get('/task-schedules', { params })),
    get: (id: number) =>
      unwrap<TaskSchedule>(http.get(`/task-schedules/${id}`)),
    create: (payload: TaskScheduleCreate) =>
      unwrap<TaskSchedule>(http.post('/task-schedules', payload)),
    update: (id: number, payload: TaskScheduleUpdate) =>
      unwrap<TaskSchedule>(http.patch(`/task-schedules/${id}`, payload)),
    remove: (id: number) => unwrap<void>(http.delete(`/task-schedules/${id}`)),
    restore: (id: number) =>
      unwrap<TaskSchedule>(http.post(`/task-schedules/${id}/restore`)),
  },

  memos: {
    list: (params: MemoListParams) =>
      unwrap<DailyMemo[]>(http.get('/memos', { params })),
    getByDate: (date: string) =>
      unwrap<DailyMemo[]>(http.get(`/memos/by-date/${date}`)),
    create: (payload: DailyMemoCreate) =>
      unwrap<DailyMemo>(http.post('/memos', payload)),
  },

  plan: {
    fixedOccurrences: (date: string) =>
      unwrap<FixedOccurrence[]>(
        http.get('/plan/fixed-occurrences', { params: { date } }),
      ),
  },
}
