<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Connection, Delete, Plus, Setting as SettingIcon } from '@element-plus/icons-vue'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { PriorityLevel, TaskStatus } from '@/api/types'
import PriorityFormDialog from '@/components/PriorityFormDialog.vue'
import StatusFormDialog from '@/components/StatusFormDialog.vue'
import { usePageRefresh } from '@/composables/usePageRefresh'
import { useAppStore } from '@/stores/app'

const { t } = useI18n()
const app = useAppStore()

const activeTab = ref('general')
const loading = ref(false)
const savingGeneral = ref(false)
const health = ref<'unknown' | 'ok' | 'error'>('unknown')

const metaForm = reactive({
  timezone: 'Asia/Shanghai',
  week_start: 1,
})

const statuses = ref<TaskStatus[]>([])
const priorities = ref<PriorityLevel[]>([])

const statusDialog = ref(false)
const editingStatus = ref<TaskStatus | null>(null)
const priorityDialog = ref(false)
const editingPriority = ref<PriorityLevel | null>(null)

const timezones = [
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Asia/Singapore',
  'Asia/Hong_Kong',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'America/New_York',
  'America/Los_Angeles',
  'Australia/Sydney',
  'UTC',
]

const endpoint = import.meta.env.VITE_API_BASE || '/api'
const schemaVersion = computed(() => app.meta.schema_version || '1')
const healthText = computed(() => {
  if (health.value === 'ok') {
    return t('settings.healthy')
  }
  if (health.value === 'error') {
    return t('settings.unhealthy')
  }
  return t('common.loading')
})

async function checkHealth() {
  try {
    await api.health()
    health.value = 'ok'
  } catch {
    health.value = 'error'
  }
}

async function load() {
  loading.value = true
  try {
    await app.loadLookups(true)
    const [meta, statusData, priorityData] = await Promise.all([
      api.meta.list(),
      api.statuses.list({ include_deleted: true }),
      api.priorities.list({ include_deleted: true }),
    ])
    metaForm.timezone = meta.timezone || 'Asia/Shanghai'
    metaForm.week_start = Number(meta.week_start || 1)
    statuses.value = statusData
    priorities.value = priorityData
    await checkHealth()
  } catch (error) {
    ElMessage.error(`${t('settings.loadFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    loading.value = false
  }
}

async function refreshLookups() {
  await app.loadLookups(true)
  statuses.value = await api.statuses.list({ include_deleted: true })
  priorities.value = await api.priorities.list({ include_deleted: true })
}

async function saveGeneral() {
  savingGeneral.value = true
  try {
    await app.saveMeta('timezone', metaForm.timezone)
    await app.saveMeta('week_start', String(metaForm.week_start))
    ElMessage.success(t('settings.generalSaved'))
  } catch (error) {
    ElMessage.error(`${t('settings.saveFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    savingGeneral.value = false
  }
}

function isBuiltIn(status: TaskStatus) {
  return status.id >= 1 && status.id <= 5
}

function openStatusCreate() {
  editingStatus.value = null
  statusDialog.value = true
}

function openStatusEdit(status: TaskStatus) {
  editingStatus.value = status
  statusDialog.value = true
}

async function removeStatus(status: TaskStatus) {
  if (isBuiltIn(status)) {
    ElMessage.warning(t('settings.cannotDeleteBuiltIn'))
    return
  }
  try {
    await ElMessageBox.confirm(
      t('settings.deleteStatusConfirm', { name: status.name }),
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
    await api.statuses.remove(status.id)
    await refreshLookups()
    ElMessage.success(t('tasks.deleted'))
  } catch (error) {
    ElMessage.error(`${t('errors.deleteFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function restoreStatus(status: TaskStatus) {
  try {
    await api.statuses.restore(status.id)
    await refreshLookups()
    ElMessage.success(t('tasks.restored'))
  } catch (error) {
    ElMessage.error(`${t('errors.restoreFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function toggleStatus(status: TaskStatus) {
  try {
    await api.statuses.update(status.id, { is_active: status.is_active })
    await app.loadLookups(true)
  } catch (error) {
    status.is_active = !status.is_active
    ElMessage.error(`${t('errors.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function toggleStatusInitialFilter(status: TaskStatus) {
  try {
    await api.statuses.update(status.id, {
      is_initial_filter: status.is_initial_filter,
    })
    await app.loadLookups(true)
  } catch (error) {
    status.is_initial_filter = !status.is_initial_filter
    ElMessage.error(`${t('errors.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

function openPriorityCreate() {
  editingPriority.value = null
  priorityDialog.value = true
}

function openPriorityEdit(priority: PriorityLevel) {
  editingPriority.value = priority
  priorityDialog.value = true
}

async function removePriority(priority: PriorityLevel) {
  try {
    await ElMessageBox.confirm(
      t('settings.deletePriorityConfirm', { name: priority.name }),
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
    await api.priorities.remove(priority.id)
    await refreshLookups()
    ElMessage.success(t('tasks.deleted'))
  } catch (error) {
    ElMessage.error(`${t('errors.deleteFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function restorePriority(priority: PriorityLevel) {
  try {
    await api.priorities.restore(priority.id)
    await refreshLookups()
    ElMessage.success(t('tasks.restored'))
  } catch (error) {
    ElMessage.error(`${t('errors.restoreFailed')}: ${apiErrorMessage(error)}`)
  }
}

async function togglePriority(priority: PriorityLevel) {
  try {
    await api.priorities.update(priority.id, { is_active: priority.is_active })
    await app.loadLookups(true)
  } catch (error) {
    priority.is_active = !priority.is_active
    ElMessage.error(`${t('errors.saveFailed')}: ${apiErrorMessage(error)}`)
  }
}

usePageRefresh(load)
onMounted(load)
</script>

<template>
  <div class="page settings-page" v-loading="loading">
    <div class="page-header">
      <div>
        <h2 class="page-title">{{ t('settings.title') }}</h2>
        <p class="page-subtitle">{{ t('settings.subtitle') }}</p>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="settings-tabs">
      <el-tab-pane :label="t('settings.general')" name="general">
        <section class="surface-card">
          <div class="section-title">
            <h3>{{ t('settings.general') }}</h3>
            <span class="pill">{{ t('app.version') }} 0.1.0</span>
          </div>

          <el-form label-position="top" class="settings-form">
            <div class="form-grid">
              <el-form-item :label="t('settings.timezone')">
                <el-select
                  v-model="metaForm.timezone"
                  filterable
                  allow-create
                  default-first-option
                >
                  <el-option v-for="zone in timezones" :key="zone" :label="zone" :value="zone" />
                </el-select>
                <div class="hint">{{ t('settings.timezoneHint') }}</div>
              </el-form-item>

              <el-form-item :label="t('settings.weekStart')">
                <el-select v-model="metaForm.week_start">
                  <el-option
                    v-for="day in 7"
                    :key="day"
                    :label="t(`weekday.${day}`)"
                    :value="day"
                  />
                </el-select>
              </el-form-item>
            </div>

            <el-button type="primary" :loading="savingGeneral" @click="saveGeneral">
              {{ t('settings.saveGeneral') }}
            </el-button>
          </el-form>
        </section>
      </el-tab-pane>

      <el-tab-pane :label="t('settings.statuses')" name="statuses">
        <section class="surface-card">
          <div class="section-title">
            <h3>{{ t('settings.statuses') }}</h3>
            <el-button type="primary" size="small" @click="openStatusCreate">
              <el-icon><Plus /></el-icon>
              {{ t('settings.addStatus') }}
            </el-button>
          </div>

          <el-table :data="statuses" style="width: 100%">
            <el-table-column :label="t('settings.statusCode')" width="150">
              <template #default="{ row }">
                <span class="code-chip">{{ row.code }}</span>
              </template>
            </el-table-column>

            <el-table-column :label="t('settings.statusName')" min-width="160">
              <template #default="{ row }">
                <div class="name-cell">
                  <span class="status-dot" :class="row.code" />
                  <strong :class="{ faded: row.deleted_at }">{{ row.name }}</strong>
                  <span v-if="isBuiltIn(row)" class="soft-tag">{{ t('settings.builtIn') }}</span>
                  <span v-if="row.deleted_at" class="deleted-pill">{{ t('common.deletedTag') }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column :label="t('settings.sortOrder')" width="100">
              <template #default="{ row }">
                <span class="mono">{{ row.sort_order }}</span>
              </template>
            </el-table-column>

            <el-table-column :label="t('settings.initialFilter')" width="110">
              <template #default="{ row }">
                <el-switch
                  v-model="row.is_initial_filter"
                  :disabled="Boolean(row.deleted_at)"
                  @change="toggleStatusInitialFilter(row)"
                />
              </template>
            </el-table-column>

            <el-table-column :label="t('tasks.remark')" min-width="160">
              <template #default="{ row }">
                <span class="muted remark">{{ row.remark || '—' }}</span>
              </template>
            </el-table-column>

            <el-table-column :label="t('dayBlocks.isActive')" width="100">
              <template #default="{ row }">
                <el-switch
                  v-model="row.is_active"
                  :disabled="Boolean(row.deleted_at)"
                  @change="toggleStatus(row)"
                />
              </template>
            </el-table-column>

            <el-table-column :label="t('common.actions')" width="150" fixed="right">
              <template #default="{ row }">
                <template v-if="!row.deleted_at">
                  <el-button text type="primary" size="small" @click="openStatusEdit(row)">
                    {{ t('common.edit') }}
                  </el-button>
                  <el-tooltip
                    :content="t('settings.cannotDeleteBuiltIn')"
                    :disabled="!isBuiltIn(row)"
                  >
                    <span>
                      <el-button
                        text
                        type="danger"
                        size="small"
                        :disabled="isBuiltIn(row)"
                        @click="removeStatus(row)"
                      >
                        <el-icon><Delete /></el-icon>
                      </el-button>
                    </span>
                  </el-tooltip>
                </template>
                <el-button v-else text type="primary" size="small" @click="restoreStatus(row)">
                  {{ t('common.restore') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane :label="t('settings.priorities')" name="priorities">
        <section class="surface-card">
          <div class="section-title">
            <h3>{{ t('settings.priorities') }}</h3>
            <el-button type="primary" size="small" @click="openPriorityCreate">
              <el-icon><Plus /></el-icon>
              {{ t('settings.addPriority') }}
            </el-button>
          </div>

          <el-table :data="priorities" style="width: 100%">
            <el-table-column :label="t('settings.priorityLevel')" width="100">
              <template #default="{ row }">
                <span class="level-pill">L{{ row.level }}</span>
              </template>
            </el-table-column>

            <el-table-column :label="t('settings.priorityName')" width="160">
              <template #default="{ row }">
                <div class="name-cell">
                  <span
                    class="color-dot"
                    :style="{ background: row.color || '#8b8fa8' }"
                  />
                  <strong :class="{ faded: row.deleted_at }">{{ row.name }}</strong>
                  <span v-if="row.deleted_at" class="deleted-pill">{{ t('common.deletedTag') }}</span>
                </div>
              </template>
            </el-table-column>

            <el-table-column :label="t('settings.priorityUsage')" min-width="220">
              <template #default="{ row }">
                <span class="muted">{{ row.usage || '—' }}</span>
              </template>
            </el-table-column>

            <el-table-column :label="t('tasks.remark')" min-width="150">
              <template #default="{ row }">
                <span class="muted">{{ row.remark || '—' }}</span>
              </template>
            </el-table-column>

            <el-table-column :label="t('dayBlocks.isActive')" width="100">
              <template #default="{ row }">
                <el-switch
                  v-model="row.is_active"
                  :disabled="Boolean(row.deleted_at)"
                  @change="togglePriority(row)"
                />
              </template>
            </el-table-column>

            <el-table-column :label="t('common.actions')" width="150" fixed="right">
              <template #default="{ row }">
                <template v-if="!row.deleted_at">
                  <el-button text type="primary" size="small" @click="openPriorityEdit(row)">
                    {{ t('common.edit') }}
                  </el-button>
                  <el-button text type="danger" size="small" @click="removePriority(row)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </template>
                <el-button v-else text type="primary" size="small" @click="restorePriority(row)">
                  {{ t('common.restore') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </el-tab-pane>

      <el-tab-pane :label="t('settings.about')" name="about">
        <div class="about-grid">
          <section class="surface-card about-card about-hero">
            <span class="about-mark"><el-icon :size="22"><SettingIcon /></el-icon></span>
            <div>
              <h3>{{ t('app.name') }}</h3>
              <p>{{ t('settings.aboutText') }}</p>
            </div>
          </section>

          <section class="surface-card about-card">
            <span class="tiny-label">{{ t('settings.apiStatus') }}</span>
            <div class="health-line" :class="health">
              <span class="health-dot" />
              <strong>{{ healthText }}</strong>
            </div>
            <small>{{ t('settings.endpoint') }}: <code>{{ endpoint }}</code></small>
          </section>

          <section class="surface-card about-card">
            <span class="tiny-label">{{ t('settings.schemaVersion') }}</span>
            <strong class="about-number">{{ schemaVersion }}</strong>
            <small>{{ t('app.version') }} 0.1.0</small>
          </section>

          <section class="surface-card about-card about-note">
            <el-icon :size="20"><Connection /></el-icon>
            <p>{{ t('settings.softDeleteNote') }}</p>
          </section>
        </div>
      </el-tab-pane>
    </el-tabs>

    <StatusFormDialog v-model="statusDialog" :status="editingStatus" @saved="refreshLookups" />
    <PriorityFormDialog
      v-model="priorityDialog"
      :priority="editingPriority"
      @saved="refreshLookups"
    />
  </div>
</template>

<style scoped>
.settings-page {
  gap: 18px;
}

.settings-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

.settings-tabs :deep(.el-tabs__nav-wrap::after) {
  background: var(--tp-border);
}

.settings-tabs :deep(.el-tabs__item) {
  font-weight: 650;
  color: var(--tp-muted);
}

.settings-tabs :deep(.el-tabs__item.is-active) {
  color: var(--tp-primary);
}

.settings-tabs :deep(.el-tabs__active-bar) {
  border-radius: 999px;
  height: 3px;
}

.settings-form {
  max-width: 620px;
}

.hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--tp-muted);
}

.name-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.name-cell strong {
  font-size: 13px;
  font-weight: 650;
}

.name-cell strong.faded {
  color: var(--tp-faint);
  text-decoration: line-through;
}

.soft-tag {
  font-size: 10px;
  color: var(--tp-muted);
  background: var(--tp-surface-strong);
  padding: 2px 7px;
  border-radius: 999px;
}

.level-pill {
  display: inline-flex;
  padding: 3px 9px;
  border-radius: 999px;
  background: var(--tp-primary-soft);
  color: var(--tp-primary);
  font-size: 12px;
  font-weight: 700;
}

.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.remark {
  font-size: 12.5px;
}

.about-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.about-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 140px;
  justify-content: center;
}

.about-hero {
  flex-direction: row;
  align-items: center;
  gap: 16px;
  background: linear-gradient(130deg, rgba(109, 93, 252, 0.14), var(--tp-surface) 62%);
}

.about-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, #6d5dfc, #9b6dff);
  flex-shrink: 0;
}

.about-hero h3 {
  margin: 0 0 4px;
  font-size: 18px;
}

.about-hero p,
.about-note p {
  margin: 0;
  font-size: 13px;
  color: var(--tp-muted);
  line-height: 1.6;
}

.health-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.health-line.ok .health-dot {
  background: #16a34a;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.16);
}

.health-line.error .health-dot {
  background: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.16);
}

.health-line strong {
  font-size: 16px;
}

.about-card small {
  font-size: 11.5px;
  color: var(--tp-muted);
  word-break: break-all;
}

.about-card code {
  font-family: 'SFMono-Regular', Consolas, monospace;
  background: var(--tp-surface-strong);
  padding: 1px 6px;
  border-radius: 6px;
}

.about-number {
  font-size: 34px;
  line-height: 1;
  letter-spacing: -0.04em;
}

.about-note {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

@media (max-width: 760px) {
  .about-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
