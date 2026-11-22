<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { FixedBlock, FixedBlockCreate } from '@/api/types'
import TimeInput from '@/components/TimeInput.vue'

type Recurrence = 'daily' | 'weekly' | 'monthly'

const props = defineProps<{
  modelValue: boolean
  block: FixedBlock | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved'): void
}>()

const { t } = useI18n()

function todayString(): string {
  const now = new Date()
  const offset = now.getTimezoneOffset() * 60000
  return new Date(now.getTime() - offset).toISOString().slice(0, 10)
}

const form = reactive({
  title: '',
  recurrence: 'weekly' as Recurrence,
  recurrence_value: 1 as number | null,
  start_minute: 10 * 60 as number | null,
  end_minute: 11 * 60 as number | null,
  effective_from: todayString(),
  effective_to: null as string | null,
  overlap_priority: 0,
  allow_task_schedule: true,
  remark: '',
  is_active: true,
})
const saving = reactive({ value: false })

watch(
  () => [props.modelValue, props.block] as const,
  ([open]) => {
    if (open) {
      resetForm()
    }
  },
  { immediate: true },
)

function resetForm() {
  const block = props.block
  form.title = block?.title ?? ''
  form.recurrence = block?.recurrence ?? 'weekly'
  form.recurrence_value = block?.recurrence_value ?? (form.recurrence === 'daily' ? null : 1)
  form.start_minute = block?.start_minute ?? 10 * 60
  form.end_minute = block?.end_minute ?? 11 * 60
  form.effective_from = block?.effective_from ?? todayString()
  form.effective_to = block?.effective_to ?? null
  form.overlap_priority = block?.overlap_priority ?? 0
  form.allow_task_schedule = block?.allow_task_schedule ?? true
  form.remark = block?.remark ?? ''
  form.is_active = block?.is_active ?? true
}

function onRecurrenceChange(value: Recurrence) {
  if (value === 'daily') {
    form.recurrence_value = null
  } else if (form.recurrence_value === null) {
    form.recurrence_value = 1
  }
}

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning(t('tasks.titleRequired'))
    return
  }
  if (form.start_minute === null || form.end_minute === null || form.end_minute <= form.start_minute) {
    ElMessage.warning(t('fixedBlocks.timeInvalid'))
    return
  }
  if (form.recurrence !== 'daily' && !form.recurrence_value) {
    ElMessage.warning(t('fixedBlocks.recurrenceValueRequired'))
    return
  }
  if (!form.effective_from) {
    ElMessage.warning(t('fixedBlocks.effectiveFromRequired'))
    return
  }

  const payload: FixedBlockCreate = {
    title: form.title.trim(),
    recurrence: form.recurrence,
    recurrence_value: form.recurrence === 'daily' ? null : form.recurrence_value,
    start_minute: form.start_minute,
    end_minute: form.end_minute,
    effective_from: form.effective_from,
    effective_to: form.effective_to || null,
    overlap_priority: form.overlap_priority,
    allow_task_schedule: form.allow_task_schedule,
    remark: form.remark.trim() || null,
    is_active: form.is_active,
  }

  saving.value = true
  try {
    if (props.block) {
      await api.fixedBlocks.update(props.block.id, payload)
    } else {
      await api.fixedBlocks.create(payload)
    }
    ElMessage.success(t('fixedBlocks.saved'))
    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    ElMessage.error(`${t('fixedBlocks.saveFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="block ? t('fixedBlocks.edit') : t('fixedBlocks.add')"
    width="min(640px, 92vw)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-position="top">
      <el-form-item :label="t('fixedBlocks.titleLabel')" required>
        <el-input v-model="form.title" maxlength="200" :placeholder="t('fixedBlocks.titlePlaceholder')" />
      </el-form-item>

      <div class="form-grid">
        <el-form-item :label="t('fixedBlocks.recurrence')">
          <el-select v-model="form.recurrence" @change="onRecurrenceChange">
            <el-option :label="t('fixedBlocks.daily')" value="daily" />
            <el-option :label="t('fixedBlocks.weekly')" value="weekly" />
            <el-option :label="t('fixedBlocks.monthly')" value="monthly" />
          </el-select>
        </el-form-item>

        <el-form-item
          v-if="form.recurrence === 'weekly'"
          :label="t('fixedBlocks.weekday')"
        >
          <el-select v-model="form.recurrence_value">
            <el-option
              v-for="day in 7"
              :key="day"
              :label="t(`weekday.${day}`)"
              :value="day"
            />
          </el-select>
        </el-form-item>

        <el-form-item
          v-else-if="form.recurrence === 'monthly'"
          :label="t('fixedBlocks.dayOfMonth')"
        >
          <el-input-number
            v-model="form.recurrence_value"
            :min="1"
            :max="31"
            controls-position="right"
          />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item :label="t('fixedBlocks.start')">
          <TimeInput v-model="form.start_minute" :allow24="false" />
        </el-form-item>
        <el-form-item :label="t('fixedBlocks.end')">
          <TimeInput v-model="form.end_minute" />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item :label="t('fixedBlocks.effectiveFrom')" required>
          <el-date-picker
            v-model="form.effective_from"
            type="date"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item :label="t('fixedBlocks.effectiveTo')">
          <el-date-picker
            v-model="form.effective_to"
            type="date"
            value-format="YYYY-MM-DD"
            clearable
          />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item :label="t('fixedBlocks.overlapPriority')">
          <el-input-number v-model="form.overlap_priority" controls-position="right" />
        </el-form-item>
        <el-form-item :label="t('fixedBlocks.allowTaskSchedule')">
          <el-switch v-model="form.allow_task_schedule" />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item :label="t('fixedBlocks.isActive')">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </div>

      <el-form-item :label="t('fixedBlocks.remark')">
        <el-input v-model="form.remark" type="textarea" :rows="2" />
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
