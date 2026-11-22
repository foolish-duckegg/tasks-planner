<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import type {
  DayBlock,
  FixedBlockOccurrence,
  TaskSchedule,
} from '@/api/types'
import { formatDateLabel, minutesToTime, todayInTimezone } from '@/utils/time'
import { kindColor, withAlpha } from '@/utils/colors'

const props = withDefaults(
  defineProps<{
    date: string
    dayBlocks: DayBlock[]
    occurrences: FixedBlockOccurrence[]
    schedules: TaskSchedule[]
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
  (
    event: 'select-occurrence',
    value: { occurrence: FixedBlockOccurrence; date: string },
  ): void
}>()

const { t } = useI18n()
const PX_PER_MINUTE = 0.5
const markers = [0, 120, 240, 360, 480, 600, 720, 840, 960, 1080, 1200, 1320, 1440]
const nowMinutes = ref(minutesNowInTimezone(props.timezone))
let timer = 0

const showNow = computed(() => props.date === todayInTimezone(props.timezone))
const isEmpty = computed(
  () =>
    props.dayBlocks.length === 0 &&
    props.occurrences.length === 0 &&
    props.schedules.length === 0,
)
const fixedOccurrences = computed(() =>
  props.occurrences.filter((occurrence) => occurrence.allow_task_schedule),
)
const wideOccurrences = computed(() =>
  props.occurrences.filter((occurrence) => !occurrence.allow_task_schedule),
)

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

onMounted(() => {
  timer = window.setInterval(updateNow, 60_000)
})

onUnmounted(() => {
  window.clearInterval(timer)
})

function bandStyle(block: DayBlock) {
  const color = kindColor(block.kind)
  return {
    top: `${block.start_minute * PX_PER_MINUTE}px`,
    height: `${Math.max((block.end_minute - block.start_minute) * PX_PER_MINUTE, 2)}px`,
    background: withAlpha(color, 0.1),
    borderLeft: `3px solid ${withAlpha(color, 0.62)}`,
  }
}

function eventStyle(start: number, end: number, color: string) {
  return {
    top: `${start * PX_PER_MINUTE}px`,
    height: `${Math.max((end - start) * PX_PER_MINUTE - 3, 20)}px`,
    background: withAlpha(color, 0.16),
    borderColor: withAlpha(color, 0.4),
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

function occurrenceColor(occurrence: FixedBlockOccurrence) {
  if (occurrence.status === 'done') {
    return '#16a34a'
  }
  if (occurrence.status === 'skipped') {
    return '#9a9eb5'
  }
  if (occurrence.status === 'missed') {
    return '#ef4444'
  }
  return '#6d5dfc'
}

function occurrenceTitle(occurrence: FixedBlockOccurrence) {
  const base = `${occurrence.title} ${minutesToTime(occurrence.start_minute)}–${minutesToTime(occurrence.end_minute)}`
  return occurrence.status
    ? `${base} · ${t(`occurrenceStatus.${occurrence.status}`)}`
    : base
}

function selectOccurrence(occurrence: FixedBlockOccurrence) {
  emit('select-occurrence', { occurrence, date: props.date })
}
</script>

<template>
  <div class="timeline-card">
    <div class="timeline-head">
      <div>
        <span class="tiny-label">{{ t('planner.timeline') }}</span>
        <strong>{{ formatDateLabel(date, locale) }}</strong>
      </div>
      <div class="legend">
        <span class="legend-item fixed">{{ t('planner.fixedOccurrences') }}</span>
        <span class="legend-item task">{{ t('planner.schedules') }}</span>
      </div>
    </div>

    <div class="timeline-scroll">
      <div class="timeline" :style="{ height: `${1440 * PX_PER_MINUTE}px` }">
        <div
          v-for="marker in markers"
          :key="marker"
          class="hour-line"
          :style="{ top: `${marker * PX_PER_MINUTE}px` }"
        >
          <span class="hour-label">{{ minutesToTime(marker) }}</span>
        </div>

        <div
          v-for="block in dayBlocks"
          :key="`block-${block.id}`"
          class="day-band"
          :class="{ inactive: !block.is_active }"
          :style="bandStyle(block)"
        >
          <span class="band-label">{{ block.label || block.kind || '—' }}</span>
          <span class="band-time">
            {{ minutesToTime(block.start_minute) }}–{{ minutesToTime(block.end_minute) }}
          </span>
        </div>

        <div class="lane lane-fixed">
          <div
            v-for="(occurrence, index) in fixedOccurrences"
            :key="`fixed-${occurrence.fixed_block_id}-${index}`"
            class="event fixed"
            :class="occurrence.status"
            :style="eventStyle(occurrence.start_minute, occurrence.end_minute, occurrenceColor(occurrence))"
            :title="occurrenceTitle(occurrence)"
            @click.stop="selectOccurrence(occurrence)"
          >
            <span
              v-if="occurrence.status"
              class="event-status-dot"
              :class="occurrence.status"
            />
            <span class="event-title">{{ occurrence.title }}</span>
            <span class="event-time">
              {{ minutesToTime(occurrence.start_minute) }}–{{ minutesToTime(occurrence.end_minute) }}
            </span>
          </div>
        </div>

        <div class="lane lane-wide">
          <div
            v-for="(occurrence, index) in wideOccurrences"
            :key="`wide-${occurrence.fixed_block_id}-${index}`"
            class="event fixed wide"
            :class="occurrence.status"
            :style="eventStyle(occurrence.start_minute, occurrence.end_minute, occurrenceColor(occurrence))"
            :title="occurrenceTitle(occurrence)"
            @click.stop="selectOccurrence(occurrence)"
          >
            <span
              v-if="occurrence.status"
              class="event-status-dot"
              :class="occurrence.status"
            />
            <span class="event-title">{{ occurrence.title }}</span>
            <span class="event-time">
              {{ minutesToTime(occurrence.start_minute) }}–{{ minutesToTime(occurrence.end_minute) }}
            </span>
          </div>
        </div>

        <div class="lane lane-task">
          <div
            v-for="schedule in schedules"
            :key="`schedule-${schedule.id}`"
            class="event task"
            :class="schedule.status"
            :style="eventStyle(schedule.start_minute, schedule.end_minute, scheduleColor(schedule))"
            :title="`${schedule.task_title} ${minutesToTime(schedule.start_minute)}–${minutesToTime(schedule.end_minute)}`"
            @click="emit('select-schedule', schedule)"
          >
            <span class="event-title">{{ schedule.task_title }}</span>
            <span class="event-time">
              {{ minutesToTime(schedule.start_minute) }}–{{ minutesToTime(schedule.end_minute) }}
            </span>
          </div>
        </div>

        <div
          v-if="showNow"
          class="now-line"
          :style="{ top: `${nowMinutes * PX_PER_MINUTE}px` }"
        >
          <span class="now-dot" />
          <span class="now-label">{{ minutesToTime(nowMinutes) }}</span>
        </div>

        <div v-if="isEmpty" class="timeline-empty">{{ t('dashboard.emptyTimeline') }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-card {
  background: var(--tp-surface);
  border: 1px solid var(--tp-border);
  border-radius: var(--tp-radius-lg);
  box-shadow: var(--tp-shadow-sm);
  padding: 18px 18px 10px;
}

.timeline-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.timeline-head > div:first-child {
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.timeline-head strong {
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

.timeline-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  padding-right: 4px;
}

.timeline {
  position: relative;
  margin-top: 12px;
  min-width: 420px;
}

.hour-line {
  position: absolute;
  left: 52px;
  right: 4px;
  border-top: 1px dashed var(--tp-border);
  z-index: 1;
}

.hour-label {
  position: absolute;
  left: -52px;
  top: -8px;
  width: 46px;
  text-align: right;
  font-size: 10.5px;
  color: var(--tp-faint);
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.day-band {
  position: absolute;
  left: 52px;
  right: 4px;
  border-radius: 8px;
  z-index: 0;
  padding: 3px 10px;
  overflow: hidden;
}

.day-band.inactive {
  opacity: 0.4;
}

.band-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: var(--tp-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.band-time {
  display: block;
  font-size: 10px;
  color: var(--tp-faint);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.lane {
  position: absolute;
  top: 0;
  bottom: 0;
  z-index: 2;
  pointer-events: none;
}

.lane-fixed {
  left: 38%;
  width: 27%;
}

.lane-wide {
  left: 38%;
  right: 4px;
}

.lane-task {
  left: 67%;
  width: 30%;
}

.event {
  position: absolute;
  left: 0;
  right: 0;
  padding: 3px 7px;
  border: 1px solid;
  border-radius: 8px;
  overflow: hidden;
  cursor: default;
  backdrop-filter: blur(4px);
  pointer-events: auto;
}

.event.task {
  cursor: pointer;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease;
}

.event.fixed {
  cursor: pointer;
  transition:
    transform 0.16s ease,
    box-shadow 0.16s ease;
}

.event.fixed:hover,
.event.task:hover {
  transform: translateX(-2px);
  box-shadow: 0 8px 18px -14px rgba(15, 16, 32, 0.7);
  z-index: 4;
}

.event-status-dot {
  position: absolute;
  top: 4px;
  right: 5px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.event-status-dot.done {
  background: #16a34a;
}

.event-status-dot.skipped {
  background: #9a9eb5;
}

.event-status-dot.missed {
  background: #ef4444;
}

.event.skipped {
  opacity: 0.55;
  text-decoration: line-through;
}

.event-title {
  display: block;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.35;
}

.event-time {
  display: block;
  font-size: 9.5px;
  opacity: 0.78;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.now-line {
  position: absolute;
  left: 48px;
  right: 4px;
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

.now-label {
  position: absolute;
  right: 0;
  top: -17px;
  font-size: 10px;
  font-weight: 700;
  color: #ef4444;
  background: var(--tp-surface);
  padding: 0 4px;
  border-radius: 4px;
}

.timeline-empty {
  position: absolute;
  left: 52px;
  right: 8px;
  top: 300px;
  text-align: center;
  color: var(--tp-faint);
  font-size: 13px;
}

@media (max-width: 640px) {
  .timeline-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .lane-fixed {
    left: 32%;
    width: 30%;
  }

  .lane-wide {
    left: 32%;
  }

  .lane-task {
    left: 64%;
    width: 32%;
  }
}
</style>
