import { computed, ref, watch, type Ref } from 'vue'
import dayjs from 'dayjs'

import { api } from '@/api'
import type { DayBlock, FixedOccurrence, TaskSchedule } from '@/api/types'
import { addDays } from '@/utils/time'

export type CalendarViewMode = 'day' | 'week' | 'month'

export interface CalendarDay {
  date: string
  occurrences: FixedOccurrence[]
  schedules: TaskSchedule[]
}

export interface CalendarSummary {
  fixedMinutes: number
  scheduledMinutes: number
  freeMinutes: number
  fixedCount: number
  scheduleCount: number
}

interface UseCalendarOptions {
  view: Ref<CalendarViewMode>
  date: Ref<string>
  timezone: Ref<string>
  weekStart: Ref<number>
  onError?: (error: unknown) => void
}

function isoWeekday(date: string): number {
  const value = dayjs(date).day()
  return value === 0 ? 7 : value
}

function startOfWeek(date: string, weekStart: number): string {
  const target = weekStart >= 1 && weekStart <= 7 ? weekStart : 1
  const current = isoWeekday(date)
  const diff = (current - target + 7) % 7
  return dayjs(date).subtract(diff, 'day').format('YYYY-MM-DD')
}

function duration(start: number, end: number): number {
  return Math.max(0, end - start)
}

export function useCalendar(options: UseCalendarOptions) {
  const dayBlocks = ref<DayBlock[]>([])
  const occurrencesByDate = ref<Record<string, FixedOccurrence[]>>({})
  const schedulesByDate = ref<Record<string, TaskSchedule[]>>({})
  const loading = ref(false)
  const loadedBlocks = ref(false)
  const loadedSchedules = ref(false)
  let requestId = 0

  const visibleDates = computed(() => {
    if (options.view.value === 'day') {
      return [options.date.value]
    }
    if (options.view.value === 'week') {
      const start = startOfWeek(options.date.value, options.weekStart.value)
      return Array.from({ length: 7 }, (_, index) => addDays(start, index))
    }
    const first = dayjs(options.date.value).startOf('month').format('YYYY-MM-DD')
    const gridStart = startOfWeek(first, options.weekStart.value)
    return Array.from({ length: 42 }, (_, index) => addDays(gridStart, index))
  })

  const rangeStart = computed(() => visibleDates.value[0])
  const rangeEnd = computed(() => visibleDates.value[visibleDates.value.length - 1])

  const statsDates = computed(() => {
    if (options.view.value !== 'month') {
      return visibleDates.value
    }
    const month = dayjs(options.date.value).format('YYYY-MM')
    return visibleDates.value.filter((date) => date.startsWith(month))
  })

  const days = computed<CalendarDay[]>(() =>
    visibleDates.value.map((date) => ({
      date,
      occurrences: occurrencesByDate.value[date] ?? [],
      schedules: schedulesByDate.value[date] ?? [],
    })),
  )

  const summary = computed<CalendarSummary>(() => {
    let fixedMinutes = 0
    let scheduledMinutes = 0
    let freeMinutes = 0
    let fixedCount = 0
    let scheduleCount = 0

    for (const date of statsDates.value) {
      const occurrences = occurrencesByDate.value[date] ?? []
      const schedules = schedulesByDate.value[date] ?? []
      const dayFixed = occurrences.reduce(
        (total, occurrence) =>
          total + duration(occurrence.start_minute, occurrence.end_minute),
        0,
      )
      const dayScheduled = schedules.reduce(
        (total, schedule) =>
          total + duration(schedule.start_minute, schedule.end_minute),
        0,
      )
      fixedMinutes += dayFixed
      scheduledMinutes += dayScheduled
      freeMinutes += Math.max(0, 1440 - dayFixed - dayScheduled)
      fixedCount += occurrences.length
      scheduleCount += schedules.length
    }

    return { fixedMinutes, scheduledMinutes, freeMinutes, fixedCount, scheduleCount }
  })

  async function load(force = false) {
    const current = ++requestId
    loading.value = true
    try {
      const dates = visibleDates.value
      const missing = force
        ? dates
        : dates.filter((date) => !(date in occurrencesByDate.value))
      const shouldLoadBlocks = force || !loadedBlocks.value
      const shouldLoadSchedules = force || !loadedSchedules.value

      const [blocks, scheduleList, occurrenceLists] = await Promise.all([
        shouldLoadBlocks
          ? api.dayBlocks.list({ active_only: true })
          : Promise.resolve(null),
        shouldLoadSchedules ? api.schedules.list() : Promise.resolve(null),
        Promise.all(missing.map((date) => api.plan.fixedOccurrences(date))),
      ])

      if (current !== requestId) {
        return
      }

      if (blocks) {
        dayBlocks.value = blocks
        loadedBlocks.value = true
      }

      missing.forEach((date, index) => {
        occurrencesByDate.value[date] = occurrenceLists[index]
      })

      if (scheduleList) {
        const grouped: Record<string, TaskSchedule[]> = {}
        for (const schedule of scheduleList) {
          const bucket = grouped[schedule.plan_date]
          if (bucket) {
            bucket.push(schedule)
          } else {
            grouped[schedule.plan_date] = [schedule]
          }
        }
        schedulesByDate.value = grouped
        loadedSchedules.value = true
      }
    } catch (error) {
      if (current === requestId) {
        options.onError?.(error)
      }
    } finally {
      if (current === requestId) {
        loading.value = false
      }
    }
  }

  function reload() {
    return load(true)
  }

  watch(
    [rangeStart, rangeEnd],
    () => {
      void load()
    },
    { immediate: true },
  )

  return {
    dayBlocks,
    visibleDates,
    days,
    rangeStart,
    rangeEnd,
    summary,
    loading,
    load,
    reload,
  }
}
