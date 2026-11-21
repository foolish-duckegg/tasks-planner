<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { DayBlock, DayBlockCreate } from '@/api/types'
import TimeInput from '@/components/TimeInput.vue'

const props = defineProps<{
  modelValue: boolean
  block: DayBlock | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved'): void
}>()

const { t } = useI18n()
const form = reactive({
  start_minute: 9 * 60 as number | null,
  end_minute: 10 * 60 as number | null,
  label: '',
  kind: '',
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
  form.start_minute = block?.start_minute ?? 9 * 60
  form.end_minute = block?.end_minute ?? 10 * 60
  form.label = block?.label ?? ''
  form.kind = block?.kind ?? ''
  form.remark = block?.remark ?? ''
  form.is_active = block?.is_active ?? true
}

async function submit() {
  if (form.start_minute === null || form.end_minute === null) {
    ElMessage.warning(t('dayBlocks.timeInvalid'))
    return
  }
  if (form.end_minute <= form.start_minute) {
    ElMessage.warning(t('dayBlocks.timeInvalid'))
    return
  }

  const payload: DayBlockCreate = {
    start_minute: form.start_minute,
    end_minute: form.end_minute,
    label: form.label.trim() || null,
    kind: form.kind.trim() || null,
    remark: form.remark.trim() || null,
    is_active: form.is_active,
  }

  saving.value = true
  try {
    if (props.block) {
      await api.dayBlocks.update(props.block.id, payload)
    } else {
      await api.dayBlocks.create(payload)
    }
    ElMessage.success(t('dayBlocks.blockSaved'))
    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    ElMessage.error(`${t('dayBlocks.saveFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="block ? t('dayBlocks.edit') : t('dayBlocks.add')"
    width="min(560px, 92vw)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-position="top">
      <div class="form-grid">
        <el-form-item :label="t('dayBlocks.start')">
          <TimeInput v-model="form.start_minute" :allow24="false" />
        </el-form-item>
        <el-form-item :label="t('dayBlocks.end')">
          <TimeInput v-model="form.end_minute" />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item :label="t('dayBlocks.label')">
          <el-input v-model="form.label" maxlength="100" :placeholder="t('dayBlocks.labelPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('dayBlocks.kind')">
          <el-input v-model="form.kind" maxlength="50" :placeholder="t('dayBlocks.kindPlaceholder')" />
        </el-form-item>
      </div>

      <el-form-item :label="t('dayBlocks.isActive')">
        <el-switch v-model="form.is_active" />
      </el-form-item>

      <el-form-item :label="t('tasks.remark')">
        <el-input
          v-model="form.remark"
          type="textarea"
          :rows="2"
          :placeholder="t('dayBlocks.remarkPlaceholder')"
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
