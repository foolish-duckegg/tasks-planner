<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import dayjs from 'dayjs'

import type { DayBlock, FixedOccurrence, TaskSchedule } from '@/api/types'
import type { CalendarDay } from '@/composables/useCalendar'
import { kindColor, withAlpha } from '@/utils/colors'
import {
  formatShortDate,
  isoWeekday,
  minutesToTime,
  todayInTimezone,
} from '@/utils/time'

const props = withDefaults(
  defineProps<{
    days: CalendarDay[]
    dayBlocks: DayBlock[]
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
const HOUR_HEIGHT = 26
const PX_PER_MINUTE = HOUR_HEIGHT / 60
const TOTAL_HEIGHT = 24 * HOUR_HEIGHT
const markers = [0, 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, 1320, 1440]
const nowMinutes = ref(minutesNowInTimezone(props.timezone))
let timer = 0

const today = computed(() => todayInTimezone(props.timezone))
const rangeLabel = computed(() => {
  if (!props.days.length) {
    return ''
  }
  const first = props.days[0].date
  const last = props.days[props.days.length - 1].date
  return `${formatShortDate(first, props.locale)} – ${formatShortDate(last, props.locale)}`
})

function minutesNowInTimezone(timezone: string) {
  try {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone,
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    }).formatToParts(new Date())
    const hour = Number(parts.find((part) => part.type === 'hour')?.value || 0)
    const minute = Number(parts.find((part) => part.type === 'minute')?.value || 0)
    return (hour % 24) * 60 + minute
  } catch {
    const now = new Date()
    return now.getHours() * 60 + now.getMinutes()
  }
}

function updateNow() {
  nowMinutes.value = minutesNowInTimezone(props.timezone)
}

function weekdayLabel(date: string) {
  return t(`weekday.${isoWeekday(date)}`)
}

function dayNumber(date: string) {
  return dayjs(date).format('D')
}

function bandStyle(block: DayBlock) {
  const color = kindColor(block.kind)
  return {
    top: `${block.start_minute * PX_PER_MINUTE}px`,
    height: `${Math.max((block.end_minute - block.start_minute) * PX_PER_MINUTE, 2)}px`,
    background: withAlpha(color, 0.08),
    borderLeft: `3px solid ${withAlpha(color, 0.5)}`,
  }
}

function eventStyle(start: number, end: number, color: string) {
  return {
    top: `${start * PX_PER_MINUTE}px`,
    height: `${Math.max((end - start) * PX_PER_MINUTE - 2, 18)}px`,
    background: withAlpha(color, 0.16),
    borderColor: withAlpha(color, 0.42),
    color,
  }
}

function scheduleColor(schedule: TaskSchedule) {
  if (schedule.status === 'done') {
    return '#16a34a'
  }
  if (schedule.status === 'skipped') {
    return '#9a9eb5'
  }
  return '#00b8d9'
}

function occurrenceKey(occurrence: FixedOccurrence, index: number) {
  return `fixed-${occurrence.fixed_block_id}-${occurrence.start_minute}-${index}`
}

onMounted(() => {
  timer = window.setInterval(updateNow, 60_000)
})

onUnmounted(() => {
  window.clearInterval(timer)
})
</script>

<template>
  <div class="calendar-card">
    <div class="calendar-head">
      <div>
        <span class="tiny-label">{{ t('calendar.week') }}</span>
        <strong>{{ rangeLabel }}</strong>
      </div>
      <div class="legend">
        <span class="legend-item fixed">{{ t('planner.fixedOccurrences') }}</span>
        <span class="legend-item task">{{ t('planner.schedules') }}</span>
      </div>
    </div>

    <div class="week-scroll">
      <div class="week-inner">
        <div class="week-header">
          <div class="time-spacer" />
          <div
            v-for="day in days"
            :key="`head-${day.date}`"
            class="day-head"
            :class="{ today: day.date === today, weekend: isoWeekday(day.date) >= 6 }"
            @click="emit('select-day', day.date)"
          >
            <span>{{ weekdayLabel(day.date) }}</span>
            <strong>{{ dayNumber(day.date) }}</strong>
          </div>
        </div>

        <div class="week-body" :style="{ height: `${TOTAL_HEIGHT}px` }">
          <div class="time-col">
            <span
              v-for="marker in markers"
              :key="`label-${marker}`"
              class="time-label"
              :style="{ top: `${marker * PX_PER_MINUTE}px` }"
            >
              {{ minutesToTime(marker) }}
            </span>
          </div>

          <div
            v-for="day in days"
            :key="`col-${day.date}`"
            class="day-col"
            :class="{ today: day.date === today, weekend: isoWeekday(day.date) >= 6 }"
            @click="emit('select-day', day.date)"
          >
            <div
              v-for="marker in markers"
              :key="`line-${day.date}-${marker}`"
              class="hour-line"
              :style="{ top: `${marker * PX_PER_MINUTE}px` }"
            />

            <div
              v-for="block in dayBlocks"
              :key="`band-${day.date}-${block.id}`"
              class="day-band"
              :style="bandStyle(block)"
            />

            <div
              v-for="(occurrence, index) in day.occurrences"
              :key="occurrenceKey(occurrence, index)"
              class="event fixed"
              :style="eventStyle(occurrence.start_minute, occurrence.end_minute, '#6d5dfc')"
              :title="`${occurrence.title} ${minutesToTime(occurrence.start_minute)}–${minutesToTime(occurrence.end_minute)}`"
            >
              <span class="event-title">{{ occurrence.title }}</span>
              <span class="event-time">
                {{ minutesToTime(occurrence.start_minute) }}–{{ minutesToTime(occurrence.end_minute) }}
              </span>
            </div>

            <div
              v-for="schedule in day.schedules"
              :key="`schedule-${schedule.id}`"
              class="event task"
              :class="schedule.status"
              :style="eventStyle(schedule.start_minute, schedule.end_minute, scheduleColor(schedule))"
              :title="`${schedule.task_title} ${minutesToTime(schedule.start_minute)}–${minutesToTime(schedule.end_minute)}`"
              @click.stop="emit('select-schedule', schedule)"
            >
              <span class="event-title">{{ schedule.task_title }}</span>
              <span class="event-time">
                {{ minutesToTime(schedule.start_minute) }}–{{ minutesToTime(schedule.end_minute) }}
              </span>
            </div>

            <div
              v-if="day.date === today"
              class="now-line"
              :style="{ top: `${nowMinutes * PX_PER_MINUTE}px` }"
            >
              <span class="now-dot" />
            </div>
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
  padding: 18px 18px 12px;
}

.calendar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
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

.legend {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 11px;
  color: var(--tp-muted);
  font-weight: 600;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.legend-item::before {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 3px;
}

.legend-item.fixed::before {
  background: #6d5dfc;
}

.legend-item.task::before {
  background: #00b8d9;
}

.week-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  padding-right: 4px;
}

.week-inner {
  min-width: 760px;
}

.week-header,
.week-body {
  display: grid;
  grid-template-columns: 52px repeat(7, minmax(0, 1fr));
}

.week-header {
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--tp-surface);
  border-bottom: 1px solid var(--tp-border);
  padding-bottom: 6px;
}

.day-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 0;
  color: var(--tp-muted);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 8px;
  transition: background 0.16s ease;
}

.day-head:hover {
  background: var(--tp-surface-soft);
}

.day-head strong {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 14px;
  color: var(--tp-text);
}

.day-head.today strong {
  background: var(--tp-primary);
  color: #fff;
  box-shadow: 0 8px 16px -10px rgba(109, 93, 252, 0.9);
}

.day-head.weekend span {
  color: var(--tp-faint);
}

.week-body {
  position: relative;
  margin-top: 4px;
}

.time-col {
  position: relative;
}

.time-label {
  position: absolute;
  right: 10px;
  transform: translateY(-7px);
  font-size: 10.5px;
  color: var(--tp-faint);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  white-space: nowrap;
}

.day-col {
  position: relative;
  border-left: 1px solid var(--tp-border);
  cursor: pointer;
}

.day-col::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 1;
  transition: background 0.16s ease;
  pointer-events: none;
}

.day-col:hover::after {
  background: var(--tp-surface-soft);
  opacity: 0.55;
}

.day-col.weekend {
  background: var(--tp-surface-soft);
}

.day-col.today {
  background: var(--tp-primary-soft);
}

.hour-line {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px dashed var(--tp-border);
  z-index: 1;
}

.day-band {
  position: absolute;
  left: 4px;
  right: 4px;
  border-radius: 7px;
  z-index: 0;
  opacity: 0.75;
}

.event {
  position: absolute;
  left: 4px;
  right: 4px;
  padding: 3px 6px;
  border: 1px solid;
  border-radius: 8px;
  overflow: hidden;
  cursor: default;
  z-index: 2;
  backdrop-filter: blur(4px);
}

.event.task {
  left: 50%;
  z-index: 3;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease;
}

.event.task:hover {
  transform: translateX(-2px);
  box-shadow: 0 8px 18px -14px rgba(15, 16, 32, 0.7);
  z-index: 4;
}

.event.skipped {
  opacity: 0.55;
  text-decoration: line-through;
}

.event-title {
  display: block;
  font-size: 10.5px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.3;
}

.event-time {
  display: block;
  font-size: 9px;
  opacity: 0.78;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.now-line {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 2px solid #ef4444;
  z-index: 6;
  pointer-events: none;
}

.now-dot {
  position: absolute;
  left: -4px;
  top: -5px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.18);
}

@media (max-width: 640px) {
  .calendar-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
