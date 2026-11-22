<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type {
  FixedBlockOccurrence,
  FixedOccurrenceStatus,
} from '@/api/types'
import { minutesToTime } from '@/utils/time'

const props = defineProps<{
  modelValue: boolean
  occurrence: FixedBlockOccurrence | null
  date: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'updated'): void
}>()

const { t } = useI18n()
const saving = ref(false)

const timeLabel = computed(() => {
  if (!props.occurrence) {
    return ''
  }
  return `${minutesToTime(props.occurrence.start_minute)}–${minutesToTime(props.occurrence.end_minute)}`
})

function statusTagType(status: FixedOccurrenceStatus) {
  if (status === 'done') {
    return 'success'
  }
  if (status === 'missed') {
    return 'danger'
  }
  return 'info'
}

async function setStatus(status: FixedOccurrenceStatus) {
  if (!props.occurrence) {
    return
  }
  saving.value = true
  try {
    await api.fixedBlockOccurrences.setStatus({
      fixed_block_id: props.occurrence.fixed_block_id,
      date: props.date,
      status,
    })
    ElMessage.success(t('occurrenceStatus.updated'))
    emit('update:modelValue', false)
    emit('updated')
  } catch (error) {
    ElMessage.error(`${t('errors.saveFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    saving.value = false
  }
}

async function clearStatus() {
  if (!props.occurrence) {
    return
  }
  saving.value = true
  try {
    await api.fixedBlockOccurrences.clearStatus({
      fixed_block_id: props.occurrence.fixed_block_id,
      date: props.date,
    })
    ElMessage.success(t('occurrenceStatus.cleared'))
    emit('update:modelValue', false)
    emit('updated')
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
    :title="t('occurrenceStatus.title')"
    width="min(460px, 92vw)"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div v-if="occurrence" class="occurrence-summary">
      <div class="occurrence-main">
        <strong>{{ occurrence.title }}</strong>
        <small>{{ date }} · {{ timeLabel }}</small>
      </div>
      <el-tag
        v-if="occurrence.status"
        :type="statusTagType(occurrence.status)"
        size="small"
      >
        {{ t(`occurrenceStatus.${occurrence.status}`) }}
      </el-tag>
    </div>

    <div class="status-grid">
      <el-button
        type="success"
        :loading="saving"
        @click="setStatus('done')"
      >
        {{ t('occurrenceStatus.done') }}
      </el-button>
      <el-button :loading="saving" @click="setStatus('skipped')">
        {{ t('occurrenceStatus.skipped') }}
      </el-button>
      <el-button
        type="danger"
        plain
        :loading="saving"
        @click="setStatus('missed')"
      >
        {{ t('occurrenceStatus.missed') }}
      </el-button>
      <el-button
        :disabled="!occurrence?.status || saving"
        @click="clearStatus"
      >
        {{ t('occurrenceStatus.clear') }}
      </el-button>
    </div>

    <template #footer>
      <el-button @click="emit('update:modelValue', false)">
        {{ t('common.cancel') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.occurrence-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--tp-surface-soft);
}

.occurrence-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.occurrence-main strong {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.occurrence-main small {
  font-size: 11px;
  color: var(--tp-muted);
  font-variant-numeric: tabular-nums;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
  margin-top: 14px;
}

.status-grid .el-button {
  margin-left: 0;
}
</style>
