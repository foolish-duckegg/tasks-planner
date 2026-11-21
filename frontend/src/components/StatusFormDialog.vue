<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { TaskStatus, TaskStatusCreate } from '@/api/types'

const props = defineProps<{
  modelValue: boolean
  status: TaskStatus | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved'): void
}>()

const { t } = useI18n()
const form = reactive({
  code: '',
  name: '',
  sort_order: 0,
  remark: '',
  is_active: true,
  is_initial_filter: true,
})
const saving = reactive({ value: false })

watch(
  () => [props.modelValue, props.status] as const,
  ([open]) => {
    if (open) {
      resetForm()
    }
  },
  { immediate: true },
)

function resetForm() {
  form.code = props.status?.code ?? ''
  form.name = props.status?.name ?? ''
  form.sort_order = props.status?.sort_order ?? 0
  form.remark = props.status?.remark ?? ''
  form.is_active = props.status?.is_active ?? true
  form.is_initial_filter = props.status?.is_initial_filter ?? true
}

async function submit() {
  if (!form.code.trim() || !form.name.trim()) {
    ElMessage.warning(t('settings.statusCodeHint'))
    return
  }

  saving.value = true
  try {
    if (props.status) {
      await api.statuses.update(props.status.id, {
        name: form.name.trim(),
        sort_order: form.sort_order,
        remark: form.remark.trim() || null,
        is_active: form.is_active,
        is_initial_filter: form.is_initial_filter,
      })
    } else {
      const payload: TaskStatusCreate = {
        code: form.code.trim(),
        name: form.name.trim(),
        sort_order: form.sort_order,
        remark: form.remark.trim() || null,
        is_active: form.is_active,
        is_initial_filter: form.is_initial_filter,
      }
      await api.statuses.create(payload)
    }
    ElMessage.success(t('settings.saved'))
    emit('update:modelValue', false)
    emit('saved')
  } catch (error) {
    ElMessage.error(`${t('settings.saveFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="status ? t('settings.editStatus') : t('settings.addStatus')"
    width="min(520px, 92vw)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-position="top">
      <el-form-item :label="t('settings.statusCode')" required>
        <el-input
          v-model="form.code"
          :disabled="Boolean(status)"
          maxlength="50"
          placeholder="todo"
        />
        <div class="hint">
          {{ status ? t('settings.statusCodeImmutable') : t('settings.statusCodeHint') }}
        </div>
      </el-form-item>

      <el-form-item :label="t('settings.statusName')" required>
        <el-input v-model="form.name" maxlength="100" />
      </el-form-item>

      <div class="form-grid">
        <el-form-item :label="t('settings.sortOrder')">
          <el-input-number v-model="form.sort_order" controls-position="right" />
        </el-form-item>
        <el-form-item :label="t('dayBlocks.isActive')">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </div>

      <el-form-item :label="t('settings.initialFilter')">
        <el-switch v-model="form.is_initial_filter" />
        <div class="hint">{{ t('settings.initialFilterHint') }}</div>
      </el-form-item>

      <el-form-item :label="t('tasks.remark')">
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
.hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--tp-muted);
}
</style>
