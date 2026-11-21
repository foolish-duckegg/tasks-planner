<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown,
  Calendar,
  Delete,
  EditPen,
  Plus,
} from '@element-plus/icons-vue'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { Task, TaskSchedule } from '@/api/types'
import CalendarPanel from '@/components/CalendarPanel.vue'
import DailyMemoPanel from '@/components/DailyMemoPanel.vue'
import ScheduleFormDialog from '@/components/ScheduleFormDialog.vue'
import UnscheduledTasksPanel from '@/components/UnscheduledTasksPanel.vue'
import { useCalendar, type CalendarViewMode } from '@/composables/useCalendar'
import { usePageRefresh } from '@/composables/usePageRefresh'
import { useAppStore } from '@/stores/app'
import { useUiStore } from '@/stores/ui'
import { durationLabel, minutesToTime, todayInTimezone } from '@/utils/time'

const { t } = useI18n()
const app = useAppStore()
const ui = useUiStore()

const date = ref(todayInTimezone(app.timezone))
const view = ref<CalendarViewMode>('day')
const dialogOpen = ref(false)
const editingSchedule = ref<TaskSchedule | null>(null)
const presetTaskId = ref<number | null>(null)
const unscheduledTasks = ref<Task[]>([])

const {
  dayBlocks,
  days: calendarDays,
  summary,
  loading,
  reload,
} = useCalendar({
  view,
  date,
  timezone: computed(() => app.timezone),
  weekStart: computed(() => app.weekStart),
  onError: (error) => {
    ElMessage.error(`${t('planner.loadFailed')}: ${apiErrorMessage(error)}`)
  },
})

const selectedDay = computed(
  () =>
    calendarDays.value.find((day) => day.date === date.value) ?? {
      date: date.value,
      occurrences: [],
      schedules: [],
    },
)

const occurrences = computed(() => selectedDay.value.occurrences)
const schedules = computed(() => selectedDay.value.schedules)

const summaryTitle = computed(() => {
  if (view.value === 'week') {
    return t('planner.weekSummary')
  }
  if (view.value === 'month') {
    return t('planner.monthSummary')
  }
  return t('planner.daySummary')
})

async function bootstrap() {
  try {
    await app.loadLookups()
  } catch (error) {
    ElMessage.error(`${t('planner.loadFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function loadUnscheduled() {
  try {
    unscheduledTasks.value = await api.tasks.unscheduled()
  } catch (error) {
    ElMessage.error(`${t('planner.loadFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function refreshAll() {
  await bootstrap()
  await Promise.all([reload(), loadUnscheduled()])
}

function openSchedule(schedule: TaskSchedule | null = null) {
  presetTaskId.value = null
  editingSchedule.value = schedule
  dialogOpen.value = true
}

function openScheduleForTask(task: Task) {
  presetTaskId.value = task.id
  editingSchedule.value = null
  dialogOpen.value = true
}

async function onScheduleSaved() {
  await Promise.all([reload(), loadUnscheduled()])
}

async function removeSchedule(schedule: TaskSchedule) {
  try {
    await ElMessageBox.confirm(
      t('planner.deleteScheduleConfirm'),
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
    await api.schedules.remove(schedule.id)
    ElMessage.success(t('planner.scheduleDeleted'))
    await Promise.all([reload(), loadUnscheduled()])
  } catch (error) {
    ElMessage.error(`${t('errors.deleteFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function setScheduleStatus(schedule: TaskSchedule, status: string) {
  try {
    await api.schedules.update(schedule.id, {
      status: status as TaskSchedule['status'],
    })
    ElMessage.success(t('planner.statusUpdated'))
    await reload()
  } catch (error) {
    ElMessage.error(`${t('errors.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

usePageRefresh(refreshAll)
onMounted(async () => {
  await bootstrap()
  await loadUnscheduled()
})
</script>

<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('planner.title') }}</h2>
        <p class="page-subtitle">{{ t('planner.subtitle') }}</p>
      </div>

      <div class="page-actions">
        <el-button type="primary" @click="openSchedule()">
          <el-icon><Plus /></el-icon>
          {{ t('planner.addSchedule') }}
        </el-button>
      </div>
    </div>

    <section class="summary-row">
      <article class="mini-stat">
        <span class="tiny-label">{{ t('planner.totalFixed') }}</span>
        <strong>{{ durationLabel(summary.fixedMinutes) }}</strong>
        <small>{{ t('planner.fixedOccurrences') }} · {{ summary.fixedCount }}</small>
      </article>
      <article class="mini-stat cyan">
        <span class="tiny-label">{{ t('planner.totalScheduled') }}</span>
        <strong>{{ durationLabel(summary.scheduledMinutes) }}</strong>
        <small>{{ t('planner.schedules') }} · {{ summary.scheduleCount }}</small>
      </article>
      <article class="mini-stat green">
        <span class="tiny-label">{{ t('planner.freeTime') }}</span>
        <strong>{{ durationLabel(summary.freeMinutes) }}</strong>
        <small>{{ summaryTitle }}</small>
      </article>
    </section>

    <div class="grid-2" :class="{ 'single-column': view !== 'day' }">
      <CalendarPanel
        v-model:view="view"
        v-model:date="date"
        :days="calendarDays"
        :day-blocks="dayBlocks"
        :locale="ui.locale"
        :timezone="app.timezone"
        @select-schedule="openSchedule"
      />

      <div v-if="view === 'day'" class="stack">
        <section class="surface-card">
          <div class="section-title">
            <h3>{{ t('planner.fixedOccurrences') }}</h3>
            <span class="pill">{{ occurrences.length }}</span>
          </div>

          <div v-if="occurrences.length" class="event-list">
            <div
              v-for="(occurrence, index) in occurrences"
              :key="`${occurrence.fixed_block_id}-${index}`"
              class="event-row fixed-row"
            >
              <span class="event-time mono">
                {{ minutesToTime(occurrence.start_minute) }}
                <small>{{ minutesToTime(occurrence.end_minute) }}</small>
              </span>
              <span class="event-body">
                <strong>{{ occurrence.title }}</strong>
                <small>{{ occurrence.remark || t('recurrence.daily') }}</small>
              </span>
              <span class="pill">P{{ occurrence.overlap_priority }}</span>
            </div>
          </div>
          <div v-else class="empty-state">
            <el-icon :size="24"><Calendar /></el-icon>
            <strong>{{ t('planner.noOccurrences') }}</strong>
          </div>
        </section>

        <section class="surface-card">
          <div class="section-title">
            <h3>{{ t('planner.schedules') }}</h3>
            <el-button text type="primary" @click="openSchedule()">
              <el-icon><Plus /></el-icon>
              {{ t('planner.addSchedule') }}
            </el-button>
          </div>

          <div v-if="schedules.length" class="event-list">
            <div
              v-for="schedule in schedules"
              :key="schedule.id"
              class="event-row schedule-row"
              :class="schedule.status"
            >
              <span class="event-time mono">
                {{ minutesToTime(schedule.start_minute) }}
                <small>{{ minutesToTime(schedule.end_minute) }}</small>
              </span>
              <span class="event-body">
                <strong>{{ schedule.task_title }}</strong>
                <small>{{ schedule.note || t(`scheduleStatus.${schedule.status}`) }}</small>
              </span>
              <div class="event-actions">
                <el-dropdown trigger="click" @command="(command: string) => setScheduleStatus(schedule, command)">
                  <el-button text size="small" class="status-button">
                    {{ t(`scheduleStatus.${schedule.status}`) }}
                    <el-icon><ArrowDown /></el-icon>
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="planned">
                        {{ t('scheduleStatus.planned') }}
                      </el-dropdown-item>
                      <el-dropdown-item command="done">
                        {{ t('scheduleStatus.done') }}
                      </el-dropdown-item>
                      <el-dropdown-item command="skipped">
                        {{ t('scheduleStatus.skipped') }}
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-button text size="small" type="primary" @click="openSchedule(schedule)">
                  <el-icon><EditPen /></el-icon>
                </el-button>
                <el-button text size="small" type="danger" @click="removeSchedule(schedule)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <el-icon :size="24"><Calendar /></el-icon>
            <strong>{{ t('planner.noSchedules') }}</strong>
          </div>
        </section>

        <UnscheduledTasksPanel
          :tasks="unscheduledTasks"
          @schedule="openScheduleForTask"
        />
      </div>
    </div>

    <DailyMemoPanel :view="view" :date="date" />

    <ScheduleFormDialog
      v-model="dialogOpen"
      :date="date"
      :schedule="editingSchedule"
      :task-id="presetTaskId"
      @saved="onScheduleSaved"
    />
  </div>
</template>

<style scoped>
.grid-2.single-column {
  grid-template-columns: minmax(0, 1fr);
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.mini-stat {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 16px 18px;
  border-radius: var(--tp-radius-lg);
  border: 1px solid var(--tp-border);
  background: linear-gradient(140deg, rgba(109, 93, 252, 0.12), var(--tp-surface) 62%);
  box-shadow: var(--tp-shadow-sm);
}

.mini-stat.cyan {
  background: linear-gradient(140deg, rgba(0, 184, 217, 0.12), var(--tp-surface) 62%);
}

.mini-stat.green {
  background: linear-gradient(140deg, rgba(22, 163, 74, 0.12), var(--tp-surface) 62%);
}

.mini-stat strong {
  font-size: 24px;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.mini-stat small {
  font-size: 11px;
  color: var(--tp-muted);
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.event-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 10px;
  border-radius: 13px;
  background: var(--tp-surface-soft);
}

.event-row.fixed-row {
  border-left: 3px solid #6d5dfc;
}

.event-row.schedule-row {
  border-left: 3px solid #00b8d9;
}

.event-row.schedule-row.done {
  border-left-color: #16a34a;
}

.event-row.schedule-row.skipped {
  border-left-color: #9a9eb5;
  opacity: 0.65;
}

.event-time {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 48px;
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
}

.event-time small {
  font-size: 10px;
  font-weight: 500;
  color: var(--tp-muted);
}

.event-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.event-body strong {
  font-size: 13px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-body small {
  font-size: 11px;
  color: var(--tp-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-actions {
  display: flex;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
}

.status-button {
  font-size: 11px;
}

@media (max-width: 900px) {
  .summary-row {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 560px) {
  .event-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
}
</style>
