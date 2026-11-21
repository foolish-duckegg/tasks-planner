<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { Task, TaskCreate } from '@/api/types'
import { useAppStore } from '@/stores/app'

const props = defineProps<{
  modelValue: boolean
  task: Task | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved'): void
}>()

const { t } = useI18n()
const appStore = useAppStore()

const form = reactive({
  title: '',
  status_id: 1,
  priority_level_id: null as number | null,
  deadline: null as Date | null,
  progress: '',
  remark: '',
})
const saving = reactive({ value: false })

watch(
  () => [props.modelValue, props.task] as const,
  ([open]) => {
    if (open) {
      resetForm()
    }
  },
  { immediate: true },
)

function resetForm() {
  const task = props.task
  form.title = task?.title ?? ''
  form.status_id =
    task?.status_id ??
    appStore.activeStatuses.find((status) => status.code === 'todo')?.id ??
    appStore.statuses[0]?.id ??
    1
  form.priority_level_id = task?.priority_level_id ?? null
  form.deadline = task?.deadline_at ? new Date(task.deadline_at) : null
  form.progress = task?.progress ?? ''
  form.remark = task?.remark ?? ''
}

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning(t('tasks.titleRequired'))
    return
  }

  const payload: TaskCreate = {
    title: form.title.trim(),
    status_id: form.status_id,
    priority_level_id: form.priority_level_id,
    deadline_at: form.deadline ? form.deadline.toISOString() : null,
    progress: form.progress.trim() || null,
    remark: form.remark.trim() || null,
  }

  saving.value = true
  try {
    if (props.task) {
      await api.tasks.update(props.task.id, payload)
      ElMessage.success(t('tasks.updated'))
    } else {
      await api.tasks.create(payload)
      ElMessage.success(t('tasks.created'))
    }
    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    ElMessage.error(`${t('tasks.saveFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="task ? t('tasks.edit') : t('tasks.new')"
    width="min(620px, 92vw)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-position="top">
      <el-form-item :label="t('tasks.titleLabel')" required>
        <el-input v-model="form.title" maxlength="500" show-word-limit />
      </el-form-item>

      <div class="form-grid">
        <el-form-item :label="t('tasks.status')">
          <el-select v-model="form.status_id" :placeholder="t('tasks.selectStatus')">
            <el-option
              v-for="status in appStore.statuses"
              :key="status.id"
              :label="status.name"
              :value="status.id"
            >
              <span class="status-dot" :class="status.code" />
              {{ status.name }}
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item :label="t('tasks.priority')">
          <el-select
            v-model="form.priority_level_id"
            clearable
            :placeholder="t('tasks.selectPriority')"
          >
            <el-option
              v-for="priority in appStore.priorities"
              :key="priority.id"
              :label="`${priority.name} · L${priority.level}`"
              :value="priority.id"
            >
              <span
                class="priority-dot"
                :style="{ background: priority.color || '#8b8fa8' }"
              />
              {{ priority.name }}
              <span class="muted">· L{{ priority.level }}</span>
            </el-option>
          </el-select>
        </el-form-item>
      </div>

      <el-form-item :label="t('tasks.deadline')">
        <el-date-picker
          v-model="form.deadline"
          type="datetime"
          clearable
          :placeholder="t('tasks.deadlinePlaceholder')"
        />
      </el-form-item>

      <el-form-item :label="t('tasks.progress')">
        <el-input
          v-model="form.progress"
          type="textarea"
          :rows="2"
          :placeholder="t('tasks.progressPlaceholder')"
        />
      </el-form-item>

      <el-form-item :label="t('tasks.remark')">
        <el-input
          v-model="form.remark"
          type="textarea"
          :rows="3"
          :placeholder="t('tasks.remarkPlaceholder')"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="emit('update:modelValue', false)">{{ t('common.cancel') }}</el-button>
        <el-button type="primary" :loading="saving.value" @click="submit">
          {{ t('common.save') }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.priority-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 7px;
  vertical-align: middle;
}
</style>
