<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type {
  FixedBlockException,
  FixedBlockExceptionCreate,
} from '@/api/types'
import TimeInput from '@/components/TimeInput.vue'

const props = defineProps<{
  modelValue: boolean
  fixedBlockId: number
  exception: FixedBlockException | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved'): void
}>()

const { t } = useI18n()
const form = reactive({
  skip_date: null as string | null,
  effective_from: null as string | null,
  effective_to: null as string | null,
  weekday: null as number | null,
  day_of_month: null as number | null,
  partial_skip: false,
  start_minute: 10 * 60 as number | null,
  end_minute: 11 * 60 as number | null,
  remark: '',
  is_active: true,
})
const saving = reactive({ value: false })

watch(
  () => [props.modelValue, props.exception] as const,
  ([open]) => {
    if (open) {
      resetForm()
    }
  },
  { immediate: true },
)

function resetForm() {
  const exception = props.exception
  form.skip_date = exception?.skip_date ?? null
  form.effective_from = exception?.effective_from ?? null
  form.effective_to = exception?.effective_to ?? null
  form.weekday = exception?.weekday ?? null
  form.day_of_month = exception?.day_of_month ?? null
  form.partial_skip = exception?.start_minute != null && exception?.end_minute != null
  form.start_minute = exception?.start_minute ?? 10 * 60
  form.end_minute = exception?.end_minute ?? 11 * 60
  form.remark = exception?.remark ?? ''
  form.is_active = exception?.is_active ?? true
}

async function submit() {
  if (form.partial_skip) {
    if (
      form.start_minute === null ||
      form.end_minute === null ||
      form.end_minute <= form.start_minute
    ) {
      ElMessage.warning(t('fixedBlocks.timeInvalid'))
      return
    }
  }

  const payload: FixedBlockExceptionCreate = {
    skip_date: form.skip_date || null,
    effective_from: form.effective_from || null,
    effective_to: form.effective_to || null,
    weekday: form.weekday,
    day_of_month: form.day_of_month,
    start_minute: form.partial_skip ? form.start_minute : null,
    end_minute: form.partial_skip ? form.end_minute : null,
    remark: form.remark.trim() || null,
    is_active: form.is_active,
  }

  saving.value = true
  try {
    if (props.exception) {
      await api.exceptions.update(props.exception.id, payload)
    } else {
      await api.exceptions.create(props.fixedBlockId, payload)
    }
    ElMessage.success(t('fixedBlocks.exceptionSaved'))
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
    :title="exception ? t('fixedBlocks.editException') : t('fixedBlocks.addException')"
    width="min(620px, 92vw)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-alert
      :title="t('fixedBlocks.conditionHint')"
      type="info"
      :closable="false"
      show-icon
      class="hint-alert"
    />

    <el-form label-position="top">
      <el-form-item :label="t('fixedBlocks.skipDate')">
        <el-date-picker
          v-model="form.skip_date"
          type="date"
          value-format="YYYY-MM-DD"
          clearable
        />
      </el-form-item>

      <div class="form-grid">
        <el-form-item :label="t('fixedBlocks.effectiveFromEx')">
          <el-date-picker
            v-model="form.effective_from"
            type="date"
            value-format="YYYY-MM-DD"
            clearable
          />
        </el-form-item>
        <el-form-item :label="t('fixedBlocks.effectiveToEx')">
          <el-date-picker
            v-model="form.effective_to"
            type="date"
            value-format="YYYY-MM-DD"
            clearable
          />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item :label="t('fixedBlocks.weekdayFilter')">
          <el-select v-model="form.weekday" clearable>
            <el-option
              v-for="day in 7"
              :key="day"
              :label="t(`weekday.${day}`)"
              :value="day"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('fixedBlocks.dayOfMonthFilter')">
          <el-input-number
            v-model="form.day_of_month"
            :min="1"
            :max="31"
            :value-on-clear="null"
            controls-position="right"
          />
        </el-form-item>
      </div>

      <el-form-item :label="t('fixedBlocks.partialSkip')">
        <el-switch v-model="form.partial_skip" />
      </el-form-item>

      <div v-if="form.partial_skip" class="form-grid">
        <el-form-item :label="t('fixedBlocks.start')">
          <TimeInput v-model="form.start_minute" :allow24="false" />
        </el-form-item>
        <el-form-item :label="t('fixedBlocks.end')">
          <TimeInput v-model="form.end_minute" />
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

<style scoped>
.hint-alert {
  margin-bottom: 16px;
}
</style>
