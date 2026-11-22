<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  ArrowRight,
  Calendar,
  CircleCheck,
  Tickets,
  Timer,
  Warning,
} from '@element-plus/icons-vue'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { Task } from '@/api/types'
import CalendarPanel from '@/components/CalendarPanel.vue'
import DailyMemoPanel from '@/components/DailyMemoPanel.vue'
import UnscheduledTasksPanel from '@/components/UnscheduledTasksPanel.vue'
import { useCalendar, type CalendarViewMode } from '@/composables/useCalendar'
import { usePageRefresh } from '@/composables/usePageRefresh'
import { useAppStore } from '@/stores/app'
import { useUiStore } from '@/stores/ui'
import {
  formatDateLabel,
  formatDateTime,
  formatMonthLabel,
  formatShortDate,
  todayInTimezone,
} from '@/utils/time'

const router = useRouter()
const { t } = useI18n()
const app = useAppStore()
const ui = useUiStore()

const loading = ref(false)
const today = ref(todayInTimezone(app.timezone))
const calendarView = ref<CalendarViewMode>('day')
const calendarDate = ref(today.value)
const tasks = ref<Task[]>([])
const unscheduledTasks = ref<Task[]>([])

const {
  dayBlocks,
  days: calendarDays,
  rangeStart,
  rangeEnd,
  summary,
  loading: calendarLoading,
  reload: reloadCalendar,
} = useCalendar({
  view: calendarView,
  date: calendarDate,
  timezone: computed(() => app.timezone),
  weekStart: computed(() => app.weekStart),
  onError: (error) => {
    ElMessage.error(`${t('errors.loadFailed')}: ${apiErrorMessage(error)}`)
  },
})

const activeTasks = computed(() => tasks.value.filter((task) => !task.deleted_at))
const totalTasks = computed(() => activeTasks.value.length)
const inProgress = computed(
  () => activeTasks.value.filter((task) => task.status_code === 'doing').length,
)
const blocked = computed(
  () => activeTasks.value.filter((task) => task.status_code === 'blocked').length,
)
const completed = computed(
  () => activeTasks.value.filter((task) => task.status_code === 'done').length,
)

const upcoming = computed(() =>
  activeTasks.value
    .filter(
      (task) =>
        task.deadline_at &&
        task.status_code !== 'done' &&
        task.status_code !== 'cancelled',
    )
    .sort(
      (left, right) =>
        new Date(left.deadline_at as string).getTime() -
        new Date(right.deadline_at as string).getTime(),
    )
    .slice(0, 5),
)

const scheduledLabel = computed(() => {
  if (calendarView.value === 'week') {
    return t('dashboard.scheduledWeek')
  }
  if (calendarView.value === 'month') {
    return t('dashboard.scheduledMonth')
  }
  return t('dashboard.scheduledToday')
})

const fixedLabel = computed(() => {
  if (calendarView.value === 'week') {
    return t('dashboard.fixedWeek')
  }
  if (calendarView.value === 'month') {
    return t('dashboard.fixedMonth')
  }
  return t('dashboard.fixedToday')
})

const summaryTitle = computed(() => {
  if (calendarView.value === 'week') {
    return t('planner.weekSummary')
  }
  if (calendarView.value === 'month') {
    return t('planner.monthSummary')
  }
  return t('planner.daySummary')
})

const summaryPeriod = computed(() => {
  if (calendarView.value === 'week') {
    return `${formatShortDate(rangeStart.value, ui.locale)} – ${formatShortDate(rangeEnd.value, ui.locale)}`
  }
  if (calendarView.value === 'month') {
    return formatMonthLabel(calendarDate.value, ui.locale)
  }
  return today.value
})

const greeting = computed(() => {
  const hour = hourInTimezone(app.timezone)
  if (hour < 12) {
    return t('dashboard.greetingMorning')
  }
  if (hour < 18) {
    return t('dashboard.greetingAfternoon')
  }
  return t('dashboard.greetingEvening')
})

const statCards = computed(() => [
  {
    key: 'total',
    label: t('dashboard.totalTasks'),
    value: totalTasks.value,
    icon: Tickets,
    tone: 'violet',
  },
  {
    key: 'doing',
    label: t('dashboard.inProgress'),
    value: inProgress.value,
    icon: Timer,
    tone: 'cyan',
  },
  {
    key: 'blocked',
    label: t('dashboard.blocked'),
    value: blocked.value,
    icon: Warning,
    tone: 'red',
  },
  {
    key: 'done',
    label: t('dashboard.completed'),
    value: completed.value,
    icon: CircleCheck,
    tone: 'green',
  },
])

const todayLabel = computed(() => formatDateLabel(today.value, ui.locale))

function hourInTimezone(timezone: string) {
  try {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone,
      hour: '2-digit',
      hour12: false,
    }).formatToParts(new Date())
    return Number(parts.find((part) => part.type === 'hour')?.value || 0) % 24
  } catch {
    return new Date().getHours()
  }
}

function isOverdue(value: string | null) {
  return value ? new Date(value).getTime() < Date.now() : false
}

async function load() {
  loading.value = true
  try {
    await app.loadLookups()
    const currentDate = todayInTimezone(app.timezone)
    today.value = currentDate
    calendarDate.value = currentDate
    const [taskList, unscheduled] = await Promise.all([
      api.tasks.list({ limit: 500 }),
      api.tasks.unscheduled(),
    ])
    tasks.value = taskList
    unscheduledTasks.value = unscheduled
  } catch (error) {
    ElMessage.error(`${t('errors.loadFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  await load()
  calendarDate.value = today.value
  await reloadCalendar()
}

usePageRefresh(refreshAll)
onMounted(load)
</script>

<template>
  <div class="page" v-loading="loading || calendarLoading">
    <section class="hero">
      <div class="hero-copy">
        <span class="hero-eyebrow">{{ greeting }} · {{ todayLabel }}</span>
        <h2>{{ t('app.tagline') }}</h2>
        <p>{{ t('dashboard.heroDesc') }}</p>
        <div class="hero-actions">
          <el-button
            type="primary"
            size="large"
            @click="router.push({ name: 'tasks', query: { create: '1' } })"
          >
            <el-icon><Tickets /></el-icon>
            {{ t('dashboard.newTask') }}
          </el-button>
          <el-button size="large" class="ghost-button" @click="router.push('/planner')">
            <el-icon><Calendar /></el-icon>
            {{ t('dashboard.openPlanner') }}
          </el-button>
        </div>
      </div>
      <div class="hero-art" aria-hidden="true">
        <div class="hero-orbit orbit-one" />
        <div class="hero-orbit orbit-two" />
        <div class="hero-clock">
          <span class="clock-hand hour" />
          <span class="clock-hand minute" />
          <span class="clock-center" />
        </div>
        <div class="hero-pill">
          <span class="hero-pill-dot" />
          {{ scheduledLabel }}
          <strong>{{ summary.scheduleCount }}</strong>
        </div>
      </div>
    </section>

    <section class="stats-grid">
      <article v-for="card in statCards" :key="card.key" class="stat-card" :class="card.tone">
        <div class="stat-icon">
          <el-icon :size="20"><component :is="card.icon" /></el-icon>
        </div>
        <div>
          <span class="stat-label">{{ card.label }}</span>
          <strong class="stat-value">{{ card.value }}</strong>
        </div>
      </article>
    </section>

    <div class="overview-grid" :class="{ 'calendar-wide': calendarView !== 'day' }">
      <CalendarPanel
        v-model:view="calendarView"
        v-model:date="calendarDate"
        :days="calendarDays"
        :day-blocks="dayBlocks"
        :locale="ui.locale"
        :timezone="app.timezone"
        :show-nav="false"
        @select-schedule="router.push('/planner')"
        @occurrence-updated="reloadCalendar"
      />

      <div class="stack">
        <section class="surface-card">
          <div class="section-title">
            <h3>{{ t('dashboard.upcomingDeadlines') }}</h3>
            <el-button text type="primary" @click="router.push('/tasks')">
              {{ t('common.viewAll') }}
              <el-icon class="el-icon--right"><ArrowRight /></el-icon>
            </el-button>
          </div>

          <div v-if="upcoming.length" class="deadline-list">
            <button
              v-for="task in upcoming"
              :key="task.id"
              class="deadline-item"
              type="button"
              @click="router.push('/tasks')"
            >
              <span
                class="deadline-dot"
                :style="{ background: task.priority_color || '#8b8fa8' }"
              />
              <span class="deadline-main">
                <strong>{{ task.title }}</strong>
                <small>{{ task.priority_name || t('common.none') }} · {{ task.status_name }}</small>
              </span>
              <span class="deadline-time" :class="{ overdue: isOverdue(task.deadline_at) }">
                {{ formatDateTime(task.deadline_at) }}
              </span>
            </button>
          </div>
          <div v-else class="empty-state">
            <el-icon :size="26"><CircleCheck /></el-icon>
            <strong>{{ t('dashboard.noUpcoming') }}</strong>
          </div>
        </section>

        <section class="surface-card summary-card">
          <div class="section-title">
            <h3>{{ summaryTitle }}</h3>
            <span class="pill">{{ summaryPeriod }}</span>
          </div>

          <div class="summary-grid">
            <div class="summary-item">
              <span class="tiny-label">{{ scheduledLabel }}</span>
              <strong>{{ summary.scheduleCount }}</strong>
              <small>{{ summary.scheduledMinutes }} {{ t('common.minutes') }}</small>
            </div>
            <div class="summary-item">
              <span class="tiny-label">{{ fixedLabel }}</span>
              <strong>{{ summary.fixedCount }}</strong>
              <small>{{ summary.fixedMinutes }} {{ t('common.minutes') }}</small>
            </div>
            <div class="summary-item">
              <span class="tiny-label">{{ t('dashboard.openTasks') }}</span>
              <strong>{{ totalTasks - completed }}</strong>
              <small>{{ t('dashboard.activeTasks') }}</small>
            </div>
          </div>

          <el-button class="summary-cta" type="primary" plain @click="router.push('/planner')">
            {{ t('dashboard.openPlanner') }}
          </el-button>
        </section>

        <UnscheduledTasksPanel :tasks="unscheduledTasks" :show-action="false" />
      </div>

      <DailyMemoPanel :view="calendarView" :date="calendarDate" />
    </div>
  </div>
</template>

<style scoped>
.overview-grid {
  display: grid;
  grid-template-columns:
    minmax(0, 1.6fr)
    minmax(280px, 1fr)
    minmax(260px, 0.9fr);
  gap: 20px;
  align-items: start;
}

.overview-grid.calendar-wide {
  grid-template-columns: minmax(0, 1fr);
}

.hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  overflow: hidden;
  border-radius: 28px;
  padding: 30px 34px;
  color: #fff;
  background:
    radial-gradient(circle at 82% 18%, rgba(0, 213, 255, 0.32), transparent 34%),
    radial-gradient(circle at 68% 90%, rgba(255, 255, 255, 0.13), transparent 38%),
    linear-gradient(125deg, #4b39d8 0%, #6d5dfc 46%, #8b5cf6 100%);
  box-shadow: 0 34px 70px -46px rgba(76, 57, 216, 0.95);
}

.hero-copy {
  position: relative;
  z-index: 2;
  max-width: 560px;
}

.hero-eyebrow {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.76;
}

.hero h2 {
  margin: 10px 0 8px;
  font-size: 31px;
  line-height: 1.16;
  letter-spacing: -0.03em;
}

.hero p {
  margin: 0;
  max-width: 460px;
  font-size: 14px;
  line-height: 1.65;
  opacity: 0.82;
}

.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 22px;
}

.hero-actions .el-button--primary {
  --el-button-bg-color: #ffffff;
  --el-button-border-color: #ffffff;
  --el-button-text-color: #5640e8;
  --el-button-hover-bg-color: #f1efff;
  --el-button-hover-border-color: #f1efff;
  --el-button-hover-text-color: #5640e8;
}

.ghost-button {
  --el-button-bg-color: rgba(255, 255, 255, 0.14);
  --el-button-border-color: rgba(255, 255, 255, 0.28);
  --el-button-text-color: #ffffff;
  --el-button-hover-bg-color: rgba(255, 255, 255, 0.22);
  --el-button-hover-border-color: rgba(255, 255, 255, 0.4);
  --el-button-hover-text-color: #ffffff;
  backdrop-filter: blur(8px);
}

.hero-art {
  position: relative;
  width: 230px;
  height: 180px;
  flex-shrink: 0;
}

.hero-orbit {
  position: absolute;
  border: 1px solid rgba(255, 255, 255, 0.25);
  border-radius: 50%;
}

.orbit-one {
  inset: 4px 26px 18px 12px;
}

.orbit-two {
  inset: 28px 0 0 46px;
  border-style: dashed;
  opacity: 0.55;
}

.hero-clock {
  position: absolute;
  top: 36px;
  left: 54px;
  width: 106px;
  height: 106px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.34);
  box-shadow: inset 0 0 24px rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
}

.hero-clock::before {
  content: '';
  position: absolute;
  inset: 12px;
  border-radius: 50%;
  border: 1px dashed rgba(255, 255, 255, 0.28);
}

.clock-hand {
  position: absolute;
  left: 50%;
  bottom: 50%;
  transform-origin: bottom center;
  border-radius: 999px;
  background: #fff;
}

.clock-hand.hour {
  width: 4px;
  height: 27px;
  margin-left: -2px;
  transform: rotate(42deg);
}

.clock-hand.minute {
  width: 3px;
  height: 38px;
  margin-left: -1.5px;
  transform: rotate(148deg);
  opacity: 0.8;
}

.clock-center {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #fff;
  transform: translate(-50%, -50%);
}

.hero-pill {
  position: absolute;
  right: 0;
  bottom: 8px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 14px;
  border-radius: 999px;
  background: rgba(19, 16, 58, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(12px);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.hero-pill strong {
  font-size: 16px;
}

.hero-pill-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 0 3px rgba(74, 222, 128, 0.2);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px;
  background: var(--tp-surface);
  border: 1px solid var(--tp-border);
  border-radius: var(--tp-radius-lg);
  box-shadow: var(--tp-shadow-sm);
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--tp-shadow);
}

.stat-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  flex-shrink: 0;
}

.stat-card.violet .stat-icon {
  background: rgba(109, 93, 252, 0.14);
  color: #6d5dfc;
}

.stat-card.cyan .stat-icon {
  background: rgba(0, 184, 217, 0.14);
  color: #0099b8;
}

.stat-card.red .stat-icon {
  background: rgba(239, 68, 68, 0.12);
  color: #dc2626;
}

.stat-card.green .stat-icon {
  background: rgba(22, 163, 74, 0.12);
  color: #15803d;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--tp-muted);
  font-weight: 600;
}

.stat-value {
  display: block;
  margin-top: 2px;
  font-size: 26px;
  line-height: 1;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.deadline-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.deadline-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 8px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  transition: background 0.16s ease;
}

.deadline-item:hover {
  background: var(--tp-surface-soft);
}

.deadline-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  flex-shrink: 0;
}

.deadline-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.deadline-main strong {
  font-size: 13px;
  font-weight: 650;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.deadline-main small {
  font-size: 11px;
  color: var(--tp-muted);
}

.deadline-time {
  font-size: 11.5px;
  color: var(--tp-muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.deadline-time.overdue {
  color: #dc2626;
  font-weight: 700;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px;
  border-radius: 14px;
  background: var(--tp-surface-soft);
}

.summary-item strong {
  font-size: 22px;
  letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
}

.summary-item small {
  font-size: 11px;
  color: var(--tp-muted);
}

.summary-cta {
  width: 100%;
  margin-top: 14px;
}

@media (max-width: 1400px) {
  .overview-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 1180px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .hero {
    padding: 24px;
  }

  .hero-art {
    display: none;
  }

  .hero h2 {
    font-size: 26px;
  }
}

@media (max-width: 560px) {
  .stats-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .summary-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
