<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Grid, Plus } from '@element-plus/icons-vue'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { DayBlock, DayBlockCreate } from '@/api/types'
import DayBlockFormDialog from '@/components/DayBlockFormDialog.vue'
import { usePageRefresh } from '@/composables/usePageRefresh'
import { kindColor, withAlpha } from '@/utils/colors'
import { durationLabel, minutesBetween, minutesToTime } from '@/utils/time'

const { t } = useI18n()

const blocks = ref<DayBlock[]>([])
const loading = ref(false)
const includeDeleted = ref(false)
const dialogOpen = ref(false)
const editing = ref<DayBlock | null>(null)

async function load() {
  loading.value = true
  try {
    blocks.value = await api.dayBlocks.list({ include_deleted: includeDeleted.value })
  } catch (error) {
    ElMessage.error(`${t('dayBlocks.loadFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  dialogOpen.value = true
}

function openEdit(block: DayBlock) {
  editing.value = block
  dialogOpen.value = true
}

async function remove(block: DayBlock) {
  try {
    await ElMessageBox.confirm(t('dayBlocks.deleteConfirm'), t('common.delete'), {
      type: 'warning',
      confirmButtonText: t('common.delete'),
      cancelButtonText: t('common.cancel'),
    })
  } catch {
    return
  }
  try {
    await api.dayBlocks.remove(block.id)
    ElMessage.success(t('dayBlocks.deleted'))
    await load()
  } catch (error) {
    ElMessage.error(`${t('errors.deleteFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function restore(block: DayBlock) {
  try {
    await api.dayBlocks.restore(block.id)
    ElMessage.success(t('dayBlocks.restored'))
    await load()
  } catch (error) {
    ElMessage.error(`${t('errors.restoreFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function toggleActive(block: DayBlock) {
  try {
    await api.dayBlocks.update(block.id, { is_active: block.is_active })
  } catch (error) {
    block.is_active = !block.is_active
    ElMessage.error(`${t('dayBlocks.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

function toPayload(block: DayBlock): DayBlockCreate {
  return {
    start_minute: block.start_minute,
    end_minute: block.end_minute,
    label: block.label,
    kind: block.kind,
    remark: block.remark,
    is_active: block.is_active,
  }
}

async function saveAsTemplate() {
  try {
    await ElMessageBox.confirm(
      t('dayBlocks.saveAsTemplateConfirm'),
      t('dayBlocks.saveAsTemplate'),
      {
        type: 'info',
        confirmButtonText: t('common.save'),
        cancelButtonText: t('common.cancel'),
      },
    )
  } catch {
    return
  }
  try {
    const payload = blocks.value
      .filter((block) => !block.deleted_at)
      .map((block) => toPayload(block))
    blocks.value = await api.dayBlocks.replace({ blocks: payload })
    ElMessage.success(t('dayBlocks.templateSaved'))
  } catch (error) {
    ElMessage.error(`${t('dayBlocks.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function clearTemplate() {
  try {
    await ElMessageBox.confirm(t('dayBlocks.clearTemplateConfirm'), t('dayBlocks.clearTemplate'), {
      type: 'warning',
      confirmButtonText: t('common.confirm'),
      cancelButtonText: t('common.cancel'),
    })
  } catch {
    return
  }
  try {
    blocks.value = await api.dayBlocks.replace({ blocks: [] })
    ElMessage.success(t('dayBlocks.templateCleared'))
  } catch (error) {
    ElMessage.error(`${t('dayBlocks.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

watch(includeDeleted, () => {
  void load()
})

usePageRefresh(load)
onMounted(load)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('dayBlocks.title') }}</h2>
        <p class="page-subtitle">{{ t('dayBlocks.subtitle') }}</p>
      </div>
      <div class="page-actions">
        <el-button @click="clearTemplate">{{ t('dayBlocks.clearTemplate') }}</el-button>
        <el-button @click="saveAsTemplate">{{ t('dayBlocks.saveAsTemplate') }}</el-button>
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          {{ t('dayBlocks.add') }}
        </el-button>
      </div>
    </div>

    <el-alert
      :title="t('dayBlocks.overlapHint')"
      type="info"
      :closable="false"
      show-icon
    />

    <section class="surface-card table-card">
      <div class="table-toolbar">
        <span class="pill">{{ t('common.totalBlocks', { count: blocks.length }) }}</span>
        <span class="filter-spacer" />
        <el-checkbox v-model="includeDeleted">{{ t('dayBlocks.includeDeleted') }}</el-checkbox>
      </div>

      <el-table v-loading="loading" :data="blocks" style="width: 100%">
        <el-table-column :label="t('dayBlocks.start')" width="170">
          <template #default="{ row }">
            <span class="time-range mono">
              {{ minutesToTime(row.start_minute) }}
              <span class="muted">–</span>
              {{ minutesToTime(row.end_minute) }}
            </span>
            <span class="duration">{{ durationLabel(minutesBetween(row.start_minute, row.end_minute)) }}</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('dayBlocks.label')" min-width="200">
          <template #default="{ row }">
            <div class="block-label">
              <span
                class="kind-swatch"
                :style="{ background: withAlpha(kindColor(row.kind), 0.16), borderColor: kindColor(row.kind) }"
              />
              <div>
                <strong :class="{ faded: row.deleted_at }">{{ row.label || '—' }}</strong>
                <small v-if="row.remark">{{ row.remark }}</small>
              </div>
              <span v-if="row.deleted_at" class="deleted-pill">{{ t('common.deletedTag') }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column :label="t('dayBlocks.kind')" width="140">
          <template #default="{ row }">
            <span v-if="row.kind" class="kind-tag" :style="{ color: kindColor(row.kind) }">
              {{ row.kind }}
            </span>
            <span v-else class="faint">—</span>
          </template>
        </el-table-column>

        <el-table-column :label="t('dayBlocks.isActive')" width="110">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :disabled="Boolean(row.deleted_at)"
              @change="toggleActive(row)"
            />
          </template>
        </el-table-column>

        <el-table-column :label="t('common.actions')" width="140" fixed="right">
          <template #default="{ row }">
            <template v-if="!row.deleted_at">
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
          </template>
        </el-table-column>

        <template #empty>
          <div class="empty-state">
            <el-icon :size="26"><Grid /></el-icon>
            <strong>{{ t('dayBlocks.empty') }}</strong>
          </div>
        </template>
      </el-table>
    </section>

    <DayBlockFormDialog v-model="dialogOpen" :block="editing" @saved="load" />
  </div>
</template>

<style scoped>
.table-card {
  padding: 12px 18px 16px;
}

.table-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0 12px;
}

.time-range {
  font-size: 13px;
  font-weight: 650;
}

.duration {
  display: block;
  font-size: 10.5px;
  color: var(--tp-faint);
}

.block-label {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.block-label > div {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.block-label strong {
  font-size: 13px;
  font-weight: 650;
}

.block-label strong.faded {
  color: var(--tp-faint);
  text-decoration: line-through;
}

.block-label small {
  font-size: 11px;
  color: var(--tp-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kind-swatch {
  width: 10px;
  height: 26px;
  border-radius: 5px;
  border-left: 2px solid;
  flex-shrink: 0;
}

.kind-tag {
  font-size: 12px;
  font-weight: 700;
}
</style>
