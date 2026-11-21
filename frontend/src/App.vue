<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import enUs from 'element-plus/es/locale/lang/en'

import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const { locale } = useI18n({ useScope: 'global' })

watch(
  () => ui.locale,
  (value) => {
    locale.value = value
  },
  { immediate: true },
)

watch(
  () => ui.theme,
  (value) => {
    document.documentElement.classList.toggle('dark', value === 'dark')
    document.documentElement.style.colorScheme = value
  },
  { immediate: true },
)

const elementLocale = computed(() => (ui.locale === 'zh-CN' ? zhCn : enUs))
</script>

<template>
  <el-config-provider :locale="elementLocale">
    <router-view />
  </el-config-provider>
</template>
