<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'

import type { DayBlock, TaskSchedule } from '@/api/types'
import type { CalendarDay, CalendarViewMode } from '@/composables/useCalendar'
import DayTimeline from '@/components/DayTimeline.vue'
import MonthCalendar from '@/components/MonthCalendar.vue'
import WeekCalendar from '@/components/WeekCalendar.vue'
import { addDays, addMonths, todayInTimezone } from '@/utils/time'

const props = withDefaults(
  defineProps<{
    view: CalendarViewMode
    date: string
    days: CalendarDay[]
    dayBlocks: DayBlock[]
    locale?: string
    timezone?: string
    showNav?: boolean
  }>(),
  {
    locale: 'zh-CN',
    timezone: 'Asia/Shanghai',
    showNav: true,
  },
)

const emit = defineEmits<{
  (event: 'update:view', value: CalendarViewMode): void
  (event: 'update:date', value: string): void
  (event: 'select-schedule', value: TaskSchedule): void
}>()

const { t } = useI18n()

const viewOptions = computed<Array<{ label: string; value: CalendarViewMode }>>(() => [
  { label: t('calendar.day'), value: 'day' },
  { label: t('calendar.week'), value: 'week' },
  { label: t('calendar.month'), value: 'month' },
])

const selectedDay = computed<CalendarDay>(() => {
  return (
    props.days.find((day) => day.date === props.date) ?? {
      date: props.date,
      occurrences: [],
      schedules: [],
    }
  )
})

function onViewChange(value: string | number | boolean | undefined) {
  if (value === 'day' || value === 'week' || value === 'month') {
    emit('update:view', value)
  }
}

function onDateChange(value: string | null) {
  if (value) {
    emit('update:date', value)
  }
}

function shift(amount: number) {
  let next = props.date
  if (props.view === 'month') {
    next = addMonths(props.date, amount)
  } else if (props.view === 'week') {
    next = addDays(props.date, amount * 7)
  } else {
    next = addDays(props.date, amount)
  }
  emit('update:date', next)
}

function goToday() {
  emit('update:date', todayInTimezone(props.timezone))
}

function selectDay(value: string) {
  emit('update:date', value)
  emit('update:view', 'day')
}
</script>

<template>
  <div class="calendar-panel">
    <div class="calendar-toolbar">
      <el-radio-group
        :model-value="view"
        size="small"
        class="view-switch"
        @update:model-value="onViewChange"
      >
        <el-radio-button
          v-for="option in viewOptions"
          :key="option.value"
          :value="option.value"
        >
          {{ option.label }}
        </el-radio-button>
      </el-radio-group>

      <div v-if="showNav" class="calendar-nav">
        <el-button circle size="small" @click="shift(-1)">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <el-date-picker
          :model-value="date"
          type="date"
          value-format="YYYY-MM-DD"
          :clearable="false"
          size="small"
          class="calendar-date-picker"
          @update:model-value="onDateChange"
        />
        <el-button size="small" @click="goToday">{{ t('common.today') }}</el-button>
        <el-button circle size="small" @click="shift(1)">
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>
    </div>

    <DayTimeline
      v-if="view === 'day'"
      :date="selectedDay.date"
      :day-blocks="dayBlocks"
      :occurrences="selectedDay.occurrences"
      :schedules="selectedDay.schedules"
      :locale="locale"
      :timezone="timezone"
      @select-schedule="emit('select-schedule', $event)"
    />

    <WeekCalendar
      v-else-if="view === 'week'"
      :days="days"
      :day-blocks="dayBlocks"
      :date="date"
      :locale="locale"
      :timezone="timezone"
      @select-schedule="emit('select-schedule', $event)"
      @select-day="selectDay"
    />

    <MonthCalendar
      v-else
      :days="days"
      :date="date"
      :locale="locale"
      :timezone="timezone"
      @select-schedule="emit('select-schedule', $event)"
      @select-day="selectDay"
    />
  </div>
</template>

<style scoped>
.calendar-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.view-switch {
  flex-shrink: 0;
}

.calendar-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.calendar-date-picker {
  width: 150px;
}

@media (max-width: 560px) {
  .calendar-nav {
    width: 100%;
  }

  .calendar-date-picker {
    flex: 1;
  }
}
</style>
