<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Tickets } from '@element-plus/icons-vue'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { Task, TaskListParams } from '@/api/types'
import TaskFormDialog from '@/components/TaskFormDialog.vue'
import { usePageRefresh } from '@/composables/usePageRefresh'
import { useAppStore } from '@/stores/app'
import { formatDateTime } from '@/utils/time'
import { withAlpha } from '@/utils/colors'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const app = useAppStore()

const tasks = ref<Task[]>([])
const loading = ref(false)
const dialogOpen = ref(false)
const editing = ref<Task | null>(null)
const filtersInitialized = ref(false)

const filters = reactive({
  status_code: [] as string[],
  priority_level_id: [] as number[],
  q: '',
  include_deleted: false,
})

function applyInitialStatusFilters() {
  if (filtersInitialized.value) {
    return
  }
  filters.status_code = app.statuses
    .filter(
      (status) =>
        status.is_active && status.is_initial_filter && !status.deleted_at,
    )
    .map((status) => status.code)
  filtersInitialized.value = true
}

async function load() {
  loading.value = true
  try {
    const params: TaskListParams = {
      limit: 500,
      status_code: filters.status_code.length ? filters.status_code : null,
      priority_level_id: filters.priority_level_id.length
        ? filters.priority_level_id
        : null,
      q: filters.q.trim() || null,
      include_deleted: filters.include_deleted,
    }
    tasks.value = await api.tasks.list(params)
  } catch (error) {
    ElMessage.error(`${t('tasks.loadFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.status_code = []
  filters.priority_level_id = []
  filters.q = ''
  filters.include_deleted = false
  void load()
}

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(task: Task) {
  editing.value = task
  dialogOpen.value = true
}

async function remove(task: Task) {
  try {
    await ElMessageBox.confirm(
      t('tasks.deleteConfirm', { title: task.title }),
      t('common.delete'),
      {
        type: 'warning',
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
      },
    )
  } catch {
    return
  }
  try {
    await api.tasks.remove(task.id)
    ElMessage.success(t('tasks.deleted'))
    await load()
  } catch (error) {
    ElMessage.error(`${t('errors.deleteFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function restore(task: Task) {
  try {
    await api.tasks.restore(task.id)
    ElMessage.success(t('tasks.restored'))
    await load()
  } catch (error) {
    ElMessage.error(`${t('errors.restoreFailed')}: ${apiErrorMessage(error)}`)
  }
}

function rowClassName({ row }: { row: Task }) {
  return row.deleted_at ? 'deleted-row' : ''
}

function isOverdue(value: string | null) {
  return value ? new Date(value).getTime() < Date.now() : false
}

usePageRefresh(load)

onMounted(async () => {
  await app.loadLookups()
  applyInitialStatusFilters()
  await load()
  if (route.query.create === '1') {
    openCreate()
    const query = { ...route.query }
    delete query.create
    void router.replace({ query })
  }
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('tasks.title') }}</h2>
        <p class="page-subtitle">{{ t('tasks.subtitle') }}</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          {{ t('tasks.new') }}
        </el-button>
      </div>
    </div>

    <section class="surface-card filter-card">
      <div class="filter-bar">
        <el-input
          v-model="filters.q"
          clearable
          :placeholder="t('tasks.searchPlaceholder')"
          @keyup.enter="load"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <el-select
          v-model="filters.status_code"
          multiple
          collapse-tags
          collapse-tags-tooltip
          clearable
          :placeholder="t('tasks.allStatuses')"
        >
          <el-option
            v-for="status in app.statuses"
            :key="status.id"
            :label="status.name"
            :value="status.code"
          />
        </el-select>

        <el-select
          v-model="filters.priority_level_id"
          multiple
          collapse-tags
          collapse-tags-tooltip
          clearable
          :placeholder="t('tasks.allPriorities')"
        >
          <el-option
            v-for="priority in app.priorities"
            :key="priority.id"
            :label="`${priority.name} · L${priority.level}`"
            :value="priority.id"
          />
        </el-select>

        <el-checkbox v-model="filters.include_deleted">
          {{ t('tasks.includeDeleted') }}
        </el-checkbox>

        <el-button type="primary" @click="load">{{ t('common.search') }}</el-button>
        <el-button @click="resetFilters">{{ t('common.reset') }}</el-button>
        <span class="filter-spacer" />
        <span class="pill">{{ t('common.total', { count: tasks.length }) }}</span>
      </div>
    </section>

    <section class="surface-card table-card">
      <el-table
        v-loading="loading"
        :data="tasks"
        :row-class-name="rowClassName"
        style="width: 100%"
      >
        <el-table-column :label="t('tasks.titleLabel')" min-width="260">
          <template #default="{ row }">
            <div class="task-title-cell">
              <div class="task-title-row">
                <span class="task-title" :class="{ faded: row.deleted_at }">{{ row.title }}</span>
                <span v-if="row.deleted_at" class="deleted-pill">{{ t('common.deletedTag') }}</span>
              </div>
              <span v-if="row.progress" class="task-progress">{{ row.progress }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="t('tasks.status')" width="140">
          <template #default="{ row }">
            <span class="status-cell">
              <span class="status-dot" :class="row.status_code" />
              {{ row.status_name }}
            </span>
          </template>
        </el-table-column>

        <el-table-column :label="t('tasks.priority')" width="120">
          <template #default="{ row }">
            <span
              v-if="row.priority_name"
              class="priority-pill"
              :style="{
                background: withAlpha(row.priority_color || '#8b8fa8', 0.14),
                color: row.priority_color || '#6f7490',
              }"
            >
              {{ row.priority_name }}
            </span>
            <span v-else class="faint">—</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('tasks.deadline')" width="190">
          <template #default="{ row }">
            <span
              v-if="row.deadline_at"
              class="deadline-value"
              :class="{ overdue: isOverdue(row.deadline_at) }"
            >
              {{ formatDateTime(row.deadline_at) }}
            </span>
            <span v-else class="faint">{{ t('common.noDeadline') }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('tasks.remark')" min-width="180">
          <template #default="{ row }">
            <span class="remark-text">{{ row.remark || '—' }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('common.actions')" width="150" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <template v-if="!row.deleted_at">
                <el-button text type="primary" size="small" @click="openEdit(row)">
                  {{ t('common.edit') }}
                </el-button>
                <el-button text type="danger" size="small" @click="remove(row)">
                  {{ t('common.delete') }}
                </el-button>
              </template>
              <el-button v-else text type="primary" size="small" @click="restore(row)">
                {{ t('common.restore') }}
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <div class="empty-state">
            <el-icon :size="26"><Tickets /></el-icon>
            <strong>{{ t('tasks.empty') }}</strong>
            <span>{{ t('tasks.filterHint') }}</span>
          </div>
        </template>
      </el-table>
    </section>

    <TaskFormDialog v-model="dialogOpen" :task="editing" @saved="load" />
  </div>
</template>

<style scoped>
.filter-card {
  padding: 14px 16px;
}

.table-card {
  padding: 6px 18px 14px;
}

.task-title-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.task-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-title {
  font-size: 13.5px;
  font-weight: 650;
}

.task-title.faded {
  color: var(--tp-faint);
  text-decoration: line-through;
}

.task-progress {
  font-size: 11.5px;
  color: var(--tp-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-cell {
  display: inline-flex;
  align-items: center;
  font-size: 12.5px;
  font-weight: 600;
}

.deadline-value {
  font-size: 12.5px;
  color: var(--tp-muted);
  font-variant-numeric: tabular-nums;
}

.deadline-value.overdue {
  color: #dc2626;
  font-weight: 700;
}

.remark-text {
  font-size: 12.5px;
  color: var(--tp-muted);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

:deep(.deleted-row) {
  opacity: 0.62;
}
</style>
