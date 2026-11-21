<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Notebook, Plus } from '@element-plus/icons-vue'

import { api } from '@/api'
import { apiErrorMessage } from '@/api/client'
import type { DailyMemo } from '@/api/types'
import type { CalendarViewMode } from '@/composables/useCalendar'
import { usePageRefresh } from '@/composables/usePageRefresh'
import { useUiStore } from '@/stores/ui'
import { formatDateLabel } from '@/utils/time'

const props = defineProps<{
  view: CalendarViewMode
  date: string
}>()

const { t } = useI18n()
const ui = useUiStore()

const memos = ref<DailyMemo[]>([])
const loading = ref(false)
const saving = ref(false)
const dialogOpen = ref(false)
const form = reactive({
  memo_date: props.date,
  content: '',
})
let requestId = 0

const periodLabel = computed(() => t(`memo.period.${props.view}`))

async function load() {
  const current = ++requestId
  loading.value = true
  try {
    const rows = await api.memos.list({ period: props.view, date: props.date })
    if (current === requestId) {
      memos.value = rows
    }
  } catch (error) {
    if (current === requestId) {
      ElMessage.error(`${t('memo.loadFailed')}: ${apiErrorMessage(error)}`)
    }
  } finally {
    if (current === requestId) {
      loading.value = false
    }
  }
}

function openCreate() {
  form.memo_date = props.date
  form.content = ''
  dialogOpen.value = true
}

async function submit() {
  const content = form.content.trim()
  if (!form.memo_date) {
    ElMessage.warning(t('memo.dateRequired'))
    return
  }
  if (!content) {
    ElMessage.warning(t('memo.contentRequired'))
    return
  }

  saving.value = true
  try {
    await api.memos.create({ memo_date: form.memo_date, content })
    ElMessage.success(t('memo.saved'))
    dialogOpen.value = false
    await load()
  } catch (error) {
    ElMessage.error(`${t('errors.saveFailed')}: ${apiErrorMessage(error)}`)
  } finally {
    saving.value = false
  }
}

watch(
  () => [props.view, props.date],
  () => {
    void load()
  },
  { immediate: true },
)

usePageRefresh(load)
</script>

<template>
  <section class="surface-card memo-card" v-loading="loading">
    <div class="section-title">
      <div class="memo-heading">
        <h3>{{ t('memo.title') }}</h3>
        <span class="pill">{{ periodLabel }}</span>
      </div>
      <el-button text type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        {{ t('memo.add') }}
      </el-button>
    </div>

    <div v-if="memos.length" class="memo-list">
      <article v-for="memo in memos" :key="memo.id" class="memo-row">
        <div class="memo-date">
          <strong>{{ formatDateLabel(memo.memo_date, ui.locale) }}</strong>
          <small>{{ memo.memo_date }}</small>
        </div>
        <p class="memo-content">{{ memo.content }}</p>
      </article>
    </div>

    <div v-else class="empty-state">
      <el-icon :size="24"><Notebook /></el-icon>
      <strong>{{ t('memo.empty') }}</strong>
      <span>{{ t('memo.emptyHint') }}</span>
    </div>

    <el-dialog
      v-model="dialogOpen"
      :title="t('memo.add')"
      width="min(560px, 92vw)"
      destroy-on-close
    >
      <el-form label-position="top">
        <el-form-item :label="t('memo.date')">
          <el-date-picker
            v-model="form.memo_date"
            type="date"
            value-format="YYYY-MM-DD"
            :clearable="false"
          />
        </el-form-item>
        <el-form-item :label="t('memo.content')">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            maxlength="20000"
            show-word-limit
            :placeholder="t('memo.contentPlaceholder')"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogOpen = false">{{ t('common.cancel') }}</el-button>
          <el-button type="primary" :loading="saving" @click="submit">
            {{ t('common.save') }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.memo-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.memo-heading {
  display: flex;
  align-items: center;
  gap: 10px;
}

.memo-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memo-row {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--tp-surface-soft);
  border-left: 3px solid #6d5dfc;
}

.memo-date {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 92px;
  flex-shrink: 0;
}

.memo-date strong {
  font-size: 12px;
  font-weight: 700;
}

.memo-date small {
  font-size: 10px;
  color: var(--tp-faint);
  font-variant-numeric: tabular-nums;
}

.memo-content {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.empty-state span {
  font-size: 11px;
  color: var(--tp-muted);
}

@media (max-width: 560px) {
  .memo-row {
    flex-direction: column;
    gap: 6px;
  }

  .memo-date {
    width: auto;
  }
}
</style>
