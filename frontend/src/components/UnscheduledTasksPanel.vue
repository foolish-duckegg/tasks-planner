<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { Calendar, Plus } from '@element-plus/icons-vue'

import type { Task } from '@/api/types'
import { formatDateTime } from '@/utils/time'

withDefaults(
  defineProps<{
    tasks: Task[]
    showAction?: boolean
  }>(),
  {
    showAction: true,
  },
)

const emit = defineEmits<{
  (event: 'schedule', value: Task): void
}>()

const { t } = useI18n()
</script>

<template>
  <section class="surface-card">
    <div class="section-title">
      <h3>{{ t('planner.unscheduledTasks') }}</h3>
      <span class="pill">{{ tasks.length }}</span>
    </div>

    <div v-if="tasks.length" class="event-list">
      <div
        v-for="task in tasks"
        :key="`unscheduled-${task.id}`"
        class="event-row unscheduled-row"
      >
        <span class="event-body">
          <strong>{{ task.title }}</strong>
          <small>
            {{ task.status_name }}
            <template v-if="task.priority_name"> · {{ task.priority_name }}</template>
            <template v-if="task.deadline_at">
              · {{ formatDateTime(task.deadline_at) }}
            </template>
          </small>
        </span>
        <el-button
          v-if="showAction"
          text
          size="small"
          type="primary"
          @click="emit('schedule', task)"
        >
          <el-icon><Plus /></el-icon>
          {{ t('planner.addSchedule') }}
        </el-button>
      </div>
    </div>
    <div v-else class="empty-state">
      <el-icon :size="24"><Calendar /></el-icon>
      <strong>{{ t('planner.noUnscheduledTasks') }}</strong>
    </div>
  </section>
</template>

<style scoped>
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

.event-row.unscheduled-row {
  border-left: 3px solid #f59e0b;
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
</style>
