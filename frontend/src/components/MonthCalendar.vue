<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'

import type { TaskSchedule } from '@/api/types'
import type { CalendarDay } from '@/composables/useCalendar'
import {
  formatMonthLabel,
  isoWeekday,
  minutesToTime,
  todayInTimezone,
} from '@/utils/time'

type CellEvent = {
  key: string
  kind: 'fixed' | 'schedule'
  start: number
  end: number
  title: string
  status?: string
  schedule?: TaskSchedule
}

const props = withDefaults(
  defineProps<{
    days: CalendarDay[]
    date: string
    locale?: string
    timezone?: string
  }>(),
  {
    locale: 'zh-CN',
    timezone: 'Asia/Shanghai',
  },
)

const emit = defineEmits<{
  (event: 'select-schedule', value: TaskSchedule): void
  (event: 'select-day', value: string): void
}>()

const { t } = useI18n()
const maxVisible = 3

const today = computed(() => todayInTimezone(props.timezone))
const monthLabel = computed(() => formatMonthLabel(props.date, props.locale))
const currentMonth = computed(() => dayjs(props.date).format('YYYY-MM'))
const monthDays = computed(() => props.days.filter((day) => day.date.startsWith(currentMonth.value)))

const weekdays = computed(() => {
  if (!props.days.length) {
    return []
  }
  return props.days.slice(0, 7).map((day) => t(`weekday.${isoWeekday(day.date)}`))
})

const cells = computed(() =>
  props.days.map((day) => ({
    ...day,
    outside: !day.date.startsWith(currentMonth.value),
    events: buildEvents(day),
  })),
)

function buildEvents(day: CalendarDay): CellEvent[] {
  const fixed: CellEvent[] = day.occurrences.map((occurrence, index) => ({
    key: `fixed-${occurrence.fixed_block_id}-${occurrence.start_minute}-${index}`,
    kind: 'fixed',
    start: occurrence.start_minute,
    end: occurrence.end_minute,
    title: occurrence.title,
  }))
  const schedules: CellEvent[] = day.schedules.map((schedule) => ({
    key: `schedule-${schedule.id}`,
    kind: 'schedule',
    start: schedule.start_minute,
    end: schedule.end_minute,
    title: schedule.task_title,
    status: schedule.status,
    schedule,
  }))
  return [...fixed, ...schedules].sort(
    (left, right) => left.start - right.start || left.end - right.end,
  )
}

function dayNumber(date: string) {
  return dayjs(date).format('D')
}
</script>

<template>
  <div class="calendar-card">
    <div class="calendar-head">
      <div>
        <span class="tiny-label">{{ t('calendar.month') }}</span>
        <strong>{{ monthLabel }}</strong>
      </div>
      <div class="month-meta">
        <span>{{ monthDays.length }} {{ t('common.days') }}</span>
      </div>
    </div>

    <div class="month-scroll">
      <div class="month-grid">
        <div
          v-for="weekday in weekdays"
          :key="`weekday-${weekday}`"
          class="month-weekday"
        >
          {{ weekday }}
        </div>

        <div
          v-for="cell in cells"
          :key="`cell-${cell.date}`"
          class="month-cell"
          :class="{ outside: cell.outside, today: cell.date === today }"
          @click="emit('select-day', cell.date)"
        >
          <div class="month-day-head">
            <span>{{ dayNumber(cell.date) }}</span>
            <small v-if="cell.events.length">{{ cell.events.length }}</small>
          </div>

          <div class="month-events">
            <button
              v-for="event in cell.events.slice(0, maxVisible)"
              :key="event.key"
              class="month-event"
              :class="[event.kind, event.status]"
              type="button"
              :title="`${event.title} ${minutesToTime(event.start)}–${minutesToTime(event.end)}`"
              @click.stop="event.schedule && emit('select-schedule', event.schedule)"
            >
              <span class="event-dot" />
              <span class="event-time">{{ minutesToTime(event.start) }}</span>
              <span class="event-title">{{ event.title }}</span>
            </button>

            <span v-if="cell.events.length > maxVisible" class="month-more">
              +{{ cell.events.length - maxVisible }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.calendar-card {
  background: var(--tp-surface);
  border: 1px solid var(--tp-border);
  border-radius: var(--tp-radius-lg);
  box-shadow: var(--tp-shadow-sm);
  padding: 18px;
}

.calendar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.calendar-head > div:first-child {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.calendar-head strong {
  font-size: 15px;
  letter-spacing: -0.01em;
}

.month-meta {
  font-size: 11px;
  color: var(--tp-muted);
  font-weight: 600;
}

.month-scroll {
  overflow-x: auto;
}

.month-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
  min-width: 720px;
}

.month-weekday {
  padding: 4px 8px;
  text-align: center;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--tp-muted);
  text-transform: uppercase;
}

.month-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-height: 112px;
  padding: 8px;
  border: 1px solid var(--tp-border);
  border-radius: 14px;
  background: var(--tp-surface-soft);
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease;
}

.month-cell:hover {
  border-color: var(--tp-border-strong);
  box-shadow: var(--tp-shadow-sm);
}

.month-cell.outside {
  opacity: 0.45;
}

.month-cell.today {
  border-color: rgba(109, 93, 252, 0.45);
  background: linear-gradient(145deg, rgba(109, 93, 252, 0.12), var(--tp-surface) 55%);
}

.month-day-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--tp-muted);
}

.month-cell.today .month-day-head span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  margin-left: -3px;
  padding: 0 5px;
  border-radius: 999px;
  background: var(--tp-primary);
  color: #fff;
}

.month-day-head small {
  font-size: 10px;
  font-weight: 600;
  color: var(--tp-faint);
}

.month-events {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.month-event {
  display: flex;
  align-items: center;
  gap: 5px;
  width: 100%;
  padding: 3px 6px;
  border: none;
  border-radius: 7px;
  background: var(--tp-surface);
  color: inherit;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  font-size: 10px;
  min-width: 0;
}

.month-event:hover {
  background: var(--tp-surface-strong);
}

.event-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.month-event.fixed .event-dot {
  background: #6d5dfc;
}

.month-event.schedule .event-dot {
  background: #00b8d9;
}

.month-event.done .event-dot {
  background: #16a34a;
}

.month-event.skipped .event-dot {
  background: #9a9eb5;
}

.month-event.skipped {
  opacity: 0.6;
  text-decoration: line-through;
}

.event-time {
  flex-shrink: 0;
  font-size: 9px;
  font-weight: 700;
  color: var(--tp-faint);
  font-variant-numeric: tabular-nums;
}

.event-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.month-more {
  padding-left: 6px;
  font-size: 10px;
  font-weight: 600;
  color: var(--tp-muted);
}

@media (max-width: 640px) {
  .calendar-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
