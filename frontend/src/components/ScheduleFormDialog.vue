<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { Task, TaskSchedule, TaskScheduleCreate } from '@/api/types'
import TimeInput from '@/components/TimeInput.vue'
import { useAppStore } from '@/stores/app'

const props = defineProps<{
  modelValue: boolean
  date: string
  schedule: TaskSchedule | null
  taskId?: number | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved'): void
}>()

const { t } = useI18n()
const app = useAppStore()
const tasks = ref<Task[]>([])
const loadingTasks = ref(false)
const saving = ref(false)

const visibleTasks = computed(() => {
  const allowedCodes = new Set(
    app.statuses
      .filter((status) => status.is_active && status.is_initial_filter)
      .map((status) => status.code),
  )
  return tasks.value.filter(
    (task) =>
      allowedCodes.has(task.status_code) ||
      task.id === props.schedule?.task_id ||
      task.id === props.taskId,
  )
})

const form = reactive({
  task_id: null as number | null,
  plan_date: props.date,
  start_minute: 9 * 60 as number | null,
  end_minute: 10 * 60 as number | null,
  status: 'planned' as 'planned' | 'done' | 'skipped',
  allow_override: true,
  note: '',
})

watch(
  () => [props.modelValue, props.schedule, props.date, props.taskId] as const,
  ([open]) => {
    if (open) {
      resetForm()
      void loadTasks()
    }
  },
  { immediate: true },
)

function resetForm() {
  const schedule = props.schedule
  form.task_id = schedule?.task_id ?? props.taskId ?? null
  form.plan_date = schedule?.plan_date ?? props.date
  form.start_minute = schedule?.start_minute ?? 9 * 60
  form.end_minute = schedule?.end_minute ?? 10 * 60
  form.status = schedule?.status ?? 'planned'
  form.allow_override = schedule?.allow_override ?? true
  form.note = schedule?.note ?? ''
}

async function loadTasks() {
  loadingTasks.value = true
  try {
    tasks.value = await api.tasks.list({ limit: 500 })
  } catch (error) {
    ElMessage.error(`${t('tasks.loadFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    loadingTasks.value = false
  }
}

async function submit() {
  if (!form.task_id) {
    ElMessage.warning(t('planner.selectTaskRequired'))
    return
  }
  if (form.start_minute === null || form.end_minute === null) {
    ElMessage.warning(t('planner.timeInvalid'))
    return
  }
  if (form.end_minute <= form.start_minute) {
    ElMessage.warning(t('planner.timeInvalid'))
    return
  }

  const payload: TaskScheduleCreate = {
    task_id: form.task_id,
    plan_date: form.plan_date,
    start_minute: form.start_minute,
    end_minute: form.end_minute,
    status: form.status,
    allow_override: form.allow_override,
    note: form.note.trim() || null,
  }

  saving.value = true
  try {
    if (props.schedule) {
      await api.schedules.update(props.schedule.id, payload)
    } else {
      await api.schedules.create(payload)
    }
    ElMessage.success(t('planner.scheduleSaved'))
    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    ElMessage.error(`${t('errors.saveFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="schedule ? t('planner.editSchedule') : t('planner.addSchedule')"
    width="min(600px, 92vw)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-position="top">
      <el-form-item :label="t('planner.task')" required>
        <el-select
          v-model="form.task_id"
          filterable
          :loading="loadingTasks"
          :placeholder="t('planner.selectTask')"
        >
          <el-option
            v-for="task in visibleTasks"
            :key="task.id"
            :label="task.title"
            :value="task.id"
          >
            <div class="task-option">
              <span>{{ task.title }}</span>
              <small>{{ task.status_name }}</small>
            </div>
          </el-option>
        </el-select>
        <div v-if="!loadingTasks && !visibleTasks.length" class="hint">{{ t('planner.noTasksHint') }}</div>
      </el-form-item>

      <el-form-item :label="t('planner.date')">
        <el-date-picker
          v-model="form.plan_date"
          type="date"
          value-format="YYYY-MM-DD"
          :clearable="false"
        />
      </el-form-item>

      <div class="form-grid">
        <el-form-item :label="t('planner.start')">
          <TimeInput v-model="form.start_minute" :allow24="false" />
        </el-form-item>
        <el-form-item :label="t('planner.end')">
          <TimeInput v-model="form.end_minute" />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item :label="t('planner.status')">
          <el-select v-model="form.status">
            <el-option :label="t('scheduleStatus.planned')" value="planned" />
            <el-option :label="t('scheduleStatus.done')" value="done" />
            <el-option :label="t('scheduleStatus.skipped')" value="skipped" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('planner.allowOverride')">
          <el-switch v-model="form.allow_override" />
        </el-form-item>
      </div>

      <el-form-item :label="t('planner.note')">
        <el-input v-model="form.note" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving" @click="submit">
          {{ t('common.save') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.task-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-option small {
  color: var(--tp-muted);
}

.hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--tp-muted);
}
</style>
