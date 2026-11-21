<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Clock, Delete, Plus } from '@element-plus/icons-vue'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { FixedBlock, FixedBlockException } from '@/api/types'
import ExceptionFormDialog from '@/components/ExceptionFormDialog.vue'
import FixedBlockFormDialog from '@/components/FixedBlockFormDialog.vue'
import { usePageRefresh } from '@/composables/usePageRefresh'
import { minutesToTime } from '@/utils/time'

type RecurrenceFilter = '' | 'daily' | 'weekly' | 'monthly'

const { t } = useI18n()

const blocks = ref<FixedBlock[]>([])
const loading = ref(false)
const recurrence = ref<RecurrenceFilter>('')
const includeDeleted = ref(false)
const dialogOpen = ref(false)
const editing = ref<FixedBlock | null>(null)

const drawerOpen = ref(false)
const activeBlock = ref<FixedBlock | null>(null)
const exceptions = ref<FixedBlockException[]>([])
const exceptionsLoading = ref(false)
const exceptionIncludeDeleted = ref(false)
const exceptionDialogOpen = ref(false)
const editingException = ref<FixedBlockException | null>(null)

async function loadBlocks() {
  loading.value = true
  try {
    blocks.value = await api.fixedBlocks.list({
      recurrence: recurrence.value || null,
      include_deleted: includeDeleted.value,
    })
  } catch (error) {
    ElMessage.error(`${t('fixedBlocks.loadFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    loading.value = false
  }
}

async function loadExceptions() {
  if (!activeBlock.value) {
    return
  }
  exceptionsLoading.value = true
  try {
    exceptions.value = await api.exceptions.listByBlock(activeBlock.value.id, {
      include_deleted: exceptionIncludeDeleted.value,
    })
  } catch (error) {
    ElMessage.error(`${t('errors.loadFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    exceptionsLoading.value = false
  }
}

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(block: FixedBlock) {
  editing.value = block
  dialogOpen.value = true
}

async function remove(block: FixedBlock) {
  try {
    await ElMessageBox.confirm(
      t('fixedBlocks.deleteConfirm', { title: block.title }),
      t('common.delete'),
      {
        type: 'warning',
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
      },
    )
  } catch {
    return
  }
  try {
    await api.fixedBlocks.remove(block.id)
    ElMessage.success(t('fixedBlocks.deleted'))
    await loadBlocks()
  } catch (error) {
    ElMessage.error(`${t('errors.deleteFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function restore(block: FixedBlock) {
  try {
    await api.fixedBlocks.restore(block.id)
    ElMessage.success(t('fixedBlocks.restored'))
    await loadBlocks()
  } catch (error) {
    ElMessage.error(`${t('errors.restoreFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function toggleActive(block: FixedBlock) {
  try {
    await api.fixedBlocks.update(block.id, { is_active: block.is_active })
  } catch (error) {
    block.is_active = !block.is_active
    ElMessage.error(`${t('fixedBlocks.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function openExceptions(block: FixedBlock) {
  activeBlock.value = block
  exceptionIncludeDeleted.value = false
  drawerOpen.value = true
  await loadExceptions()
}

function openExceptionCreate() {
  editingException.value = null
  exceptionDialogOpen.value = true
}

function openExceptionEdit(exception: FixedBlockException) {
  editingException.value = exception
  exceptionDialogOpen.value = true
}

async function removeException(exception: FixedBlockException) {
  try {
    await ElMessageBox.confirm(
      t('fixedBlocks.deleteExceptionConfirm'),
      t('common.delete'),
      {
        type: 'warning',
        confirmButtonText: t('common.delete'),
        cancelButtonText: t('common.cancel'),
      },
    )
  } catch {
    return
  }
  try {
    await api.exceptions.remove(exception.id)
    ElMessage.success(t('fixedBlocks.exceptionDeleted'))
    await loadExceptions()
  } catch (error) {
    ElMessage.error(`${t('errors.deleteFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function restoreException(exception: FixedBlockException) {
  try {
    await api.exceptions.restore(exception.id)
    ElMessage.success(t('fixedBlocks.exceptionSaved'))
    await loadExceptions()
  } catch (error) {
    ElMessage.error(`${t('errors.restoreFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function toggleExceptionActive(exception: FixedBlockException) {
  try {
    await api.exceptions.update(exception.id, { is_active: exception.is_active })
  } catch (error) {
    exception.is_active = !exception.is_active
    ElMessage.error(`${t('errors.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

function recurrenceLabel(block: FixedBlock) {
  if (block.recurrence === 'daily') {
    return t('fixedBlocks.daily')
  }
  if (block.recurrence === 'weekly') {
    return `${t('fixedBlocks.weekly')} · ${t(`weekday.${block.recurrence_value}`)}`
  }
  return `${t('fixedBlocks.monthly')} · ${block.recurrence_value}`
}

function conditionSummary(exception: FixedBlockException) {
  const parts: string[] = []
  if (exception.skip_date) {
    parts.push(`${t('fixedBlocks.skipDate')}: ${exception.skip_date}`)
  }
  if (exception.effective_from || exception.effective_to) {
    parts.push(
      `${exception.effective_from || '…'} → ${exception.effective_to || '…'}`,
    )
  }
  if (exception.weekday) {
    parts.push(t(`weekday.${exception.weekday}`))
  }
  if (exception.day_of_month) {
    parts.push(`${t('fixedBlocks.dayOfMonth')} ${exception.day_of_month}`)
  }
  return parts.length ? parts.join(' · ') : t('common.all')
}

function exceptionTime(exception: FixedBlockException) {
  if (exception.start_minute === null || exception.end_minute === null) {
    return t('fixedBlocks.wholeBlock')
  }
  return `${minutesToTime(exception.start_minute)}–${minutesToTime(exception.end_minute)}`
}

watch([recurrence, includeDeleted], () => {
  void loadBlocks()
})

watch(exceptionIncludeDeleted, () => {
  void loadExceptions()
})

usePageRefresh(loadBlocks)
onMounted(loadBlocks)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('fixedBlocks.title') }}</h2>
        <p class="page-subtitle">{{ t('fixedBlocks.subtitle') }}</p>
      </div>
      <div class="page-actions">
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          {{ t('fixedBlocks.add') }}
        </el-button>
      </div>
    </div>

    <section class="surface-card filter-card">
      <div class="filter-bar">
        <el-select v-model="recurrence" clearable :placeholder="t('fixedBlocks.recurrence')">
          <el-option :label="t('fixedBlocks.daily')" value="daily" />
          <el-option :label="t('fixedBlocks.weekly')" value="weekly" />
          <el-option :label="t('fixedBlocks.monthly')" value="monthly" />
        </el-select>
        <el-checkbox v-model="includeDeleted">{{ t('fixedBlocks.includeDeleted') }}</el-checkbox>
        <span class="filter-spacer" />
        <span class="pill">{{ t('fixedBlocks.total', { count: blocks.length }) }}</span>
      </div>
    </section>

    <section class="surface-card table-card">
      <el-table v-loading="loading" :data="blocks" style="width: 100%">
        <el-table-column :label="t('fixedBlocks.titleLabel')" min-width="220">
          <template #default="{ row }">
            <div class="block-title">
              <div class="block-name-row">
                <strong :class="{ faded: row.deleted_at }">{{ row.title }}</strong>
                <span v-if="row.deleted_at" class="deleted-pill">{{ t('common.deletedTag') }}</span>
              </div>
              <small v-if="row.remark">{{ row.remark }}</small>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="t('fixedBlocks.recurrence')" width="170">
          <template #default="{ row }">
            <span class="recurrence-tag">{{ recurrenceLabel(row) }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('fixedBlocks.start')" width="130">
          <template #default="{ row }">
            <span class="mono time-value">
              {{ minutesToTime(row.start_minute) }}–{{ minutesToTime(row.end_minute) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column :label="t('fixedBlocks.effectiveFrom')" width="200">
          <template #default="{ row }">
            <span v-if="row.effective_from || row.effective_to" class="muted range">
              {{ row.effective_from || '…' }} → {{ row.effective_to || '…' }}
            </span>
            <span v-else class="faint">{{ t('common.all') }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('fixedBlocks.overlapPriority')" width="130">
          <template #default="{ row }">
            <span class="pill">P{{ row.overlap_priority }}</span>
            <span v-if="row.allow_task_schedule" class="soft-tag">{{ t('common.yes') }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('fixedBlocks.isActive')" width="100">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :disabled="Boolean(row.deleted_at)"
              @change="toggleActive(row)"
            />
          </template>
        </el-table-column>

        <el-table-column :label="t('common.actions')" width="220" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <template v-if="!row.deleted_at">
                <el-button text type="primary" size="small" @click="openExceptions(row)">
                  {{ t('fixedBlocks.exceptions') }}
                </el-button>
                <el-button text type="primary" size="small" @click="openEdit(row)">
                  {{ t('common.edit') }}
                </el-button>
                <el-button text type="danger" size="small" @click="remove(row)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
              <el-button v-else text type="primary" size="small" @click="restore(row)">
                {{ t('common.restore') }}
              </el-button>
            </div>
          </template>
        </el-table-column>

        <template #empty>
          <div class="empty-state">
            <el-icon :size="26"><Clock /></el-icon>
            <strong>{{ t('fixedBlocks.empty') }}</strong>
          </div>
        </template>
      </el-table>
    </section>

    <FixedBlockFormDialog v-model="dialogOpen" :block="editing" @saved="loadBlocks" />

    <el-drawer
      v-model="drawerOpen"
      size="min(680px, 96vw)"
      class="exceptions-drawer"
      append-to-body
    >
      <template #header>
        <div class="drawer-title">
          <span class="tiny-label">{{ t('fixedBlocks.exceptions') }}</span>
          <strong>{{ activeBlock?.title }}</strong>
          <small v-if="activeBlock">{{ recurrenceLabel(activeBlock) }}</small>
        </div>
      </template>

      <div class="drawer-toolbar">
        <el-checkbox v-model="exceptionIncludeDeleted">
          {{ t('common.showDeleted') }}
        </el-checkbox>
        <span class="filter-spacer" />
        <el-button type="primary" size="small" @click="openExceptionCreate">
          <el-icon><Plus /></el-icon>
          {{ t('fixedBlocks.addException') }}
        </el-button>
      </div>

      <div v-loading="exceptionsLoading" class="exception-list">
        <div
          v-for="exception in exceptions"
          :key="exception.id"
          class="exception-card"
          :class="{ deleted: exception.deleted_at }"
        >
          <div class="exception-main">
            <div class="exception-head">
              <strong>{{ exceptionTime(exception) }}</strong>
              <span v-if="exception.deleted_at" class="deleted-pill">
                {{ t('common.deletedTag') }}
              </span>
              <span v-else-if="!exception.is_active" class="pill">{{ t('common.disabled') }}</span>
            </div>
            <small>{{ conditionSummary(exception) }}</small>
            <small v-if="exception.remark" class="exception-remark">{{ exception.remark }}</small>
          </div>

          <div class="exception-actions">
            <el-switch
              v-if="!exception.deleted_at"
              v-model="exception.is_active"
              size="small"
              @change="toggleExceptionActive(exception)"
            />
            <template v-if="!exception.deleted_at">
              <el-button text type="primary" size="small" @click="openExceptionEdit(exception)">
                {{ t('common.edit') }}
              </el-button>
              <el-button text type="danger" size="small" @click="removeException(exception)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
            <el-button v-else text type="primary" size="small" @click="restoreException(exception)">
              {{ t('common.restore') }}
            </el-button>
          </div>
        </div>

        <div v-if="!exceptionsLoading && !exceptions.length" class="empty-state">
          <el-icon :size="24"><Clock /></el-icon>
          <strong>{{ t('fixedBlocks.noExceptions') }}</strong>
        </div>
      </div>
    </el-drawer>

    <ExceptionFormDialog
      v-model="exceptionDialogOpen"
      :fixed-block-id="activeBlock?.id ?? 0"
      :exception="editingException"
      @saved="loadExceptions"
    />
  </div>
</template>

<style scoped>
.filter-card {
  padding: 14px 16px;
}

.table-card {
  padding: 6px 18px 16px;
}

.block-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.block-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.block-title strong {
  font-size: 13.5px;
  font-weight: 650;
}

.block-title strong.faded {
  color: var(--tp-faint);
  text-decoration: line-through;
}

.block-title small {
  font-size: 11px;
  color: var(--tp-muted);
}

.recurrence-tag {
  font-size: 12px;
  font-weight: 600;
  color: var(--tp-primary);
  background: var(--tp-primary-soft);
  padding: 3px 9px;
  border-radius: 999px;
}

.time-value {
  font-size: 12.5px;
  font-weight: 650;
}

.range {
  font-size: 11.5px;
  font-variant-numeric: tabular-nums;
}

.soft-tag {
  margin-left: 6px;
  font-size: 10px;
  color: var(--tp-muted);
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 0;
}

.drawer-title {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.drawer-title strong {
  font-size: 18px;
  letter-spacing: -0.02em;
}

.drawer-title small {
  color: var(--tp-muted);
  font-size: 12px;
}

.drawer-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.exception-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 120px;
}

.exception-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid var(--tp-border);
  background: var(--tp-surface-soft);
}

.exception-card.deleted {
  opacity: 0.6;
}

.exception-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.exception-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.exception-head strong {
  font-size: 13px;
  font-weight: 700;
}

.exception-main small {
  font-size: 11.5px;
  color: var(--tp-muted);
}

.exception-remark {
  font-style: italic;
}

.exception-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

@media (max-width: 560px) {
  .exception-card {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
