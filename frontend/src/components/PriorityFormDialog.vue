<script setup lang="ts">
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { PriorityLevel, PriorityLevelCreate } from '@/api/types'

const props = defineProps<{
  modelValue: boolean
  priority: PriorityLevel | null
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'saved'): void
}>()

const { t } = useI18n()
const form = reactive({
  level: 1,
  name: '',
  usage: '',
  remark: '',
  color: '#6d5dfc' as string | null,
  is_active: true,
})
const saving = reactive({ value: false })

watch(
  () => [props.modelValue, props.priority] as const,
  ([open]) => {
    if (open) {
      resetForm()
    }
  },
  { immediate: true },
)

function resetForm() {
  form.level = props.priority?.level ?? 1
  form.name = props.priority?.name ?? ''
  form.usage = props.priority?.usage ?? ''
  form.remark = props.priority?.remark ?? ''
  form.color = props.priority?.color ?? '#6d5dfc'
  form.is_active = props.priority?.is_active ?? true
}

async function submit() {
  if (!form.name.trim()) {
    ElMessage.warning(t('settings.priorityName'))
    return
  }

  saving.value = true
  try {
    if (props.priority) {
      await api.priorities.update(props.priority.id, {
        level: form.level,
        name: form.name.trim(),
        usage: form.usage.trim() || null,
        remark: form.remark.trim() || null,
        color: form.color,
        is_active: form.is_active,
      })
    } else {
      const payload: PriorityLevelCreate = {
        level: form.level,
        name: form.name.trim(),
        usage: form.usage.trim() || null,
        remark: form.remark.trim() || null,
        color: form.color,
        is_active: form.is_active,
      }
      await api.priorities.create(payload)
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
    :title="priority ? t('settings.editPriority') : t('settings.addPriority')"
    width="min(540px, 92vw)"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-position="top">
      <div class="form-grid">
        <el-form-item :label="t('settings.priorityLevel')">
          <el-input-number v-model="form.level" :min="1" controls-position="right" />
        </el-form-item>
        <el-form-item :label="t('settings.priorityName')" required>
          <el-input v-model="form.name" maxlength="50" placeholder="P0" />
        </el-form-item>
      </div>

      <div class="form-grid">
        <el-form-item :label="t('settings.priorityColor')">
          <el-color-picker v-model="form.color" />
        </el-form-item>
        <el-form-item :label="t('dayBlocks.isActive')">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </div>

      <el-form-item :label="t('settings.priorityUsage')">
        <el-input
          v-model="form.usage"
          type="textarea"
          :rows="2"
          :placeholder="t('settings.usagePlaceholder')"
        />
      </el-form-item>

      <el-form-item :label="t('tasks.remark')">
        <el-input
          v-model="form.remark"
          type="textarea"
          :rows="2"
          :placeholder="t('settings.remarkPlaceholder')"
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
