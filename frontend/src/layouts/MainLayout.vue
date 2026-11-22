<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Calendar,
  Clock,
  Compass,
  Expand,
  Fold,
  Grid,
  Moon,
  Odometer,
  Refresh,
  Setting,
  Sunny,
  Tickets,
} from '@element-plus/icons-vue'

import { api } from '@/api'
import { useAppStore } from '@/stores/app'
import { useUiStore } from '@/stores/ui'
import { formatDateLabel, todayInTimezone } from '@/utils/time'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const ui = useUiStore()
const app = useAppStore()

const health = ref<'unknown' | 'ok' | 'error'>('unknown')
const refreshing = ref(false)

const navItems = [
  { path: '/', key: 'nav.dashboard', icon: Odometer },
  { path: '/tasks', key: 'nav.tasks', icon: Tickets },
  { path: '/planner', key: 'nav.planner', icon: Calendar },
  { path: '/day-blocks', key: 'nav.dayBlocks', icon: Grid },
  { path: '/fixed-blocks', key: 'nav.fixedBlocks', icon: Clock },
  { path: '/settings', key: 'nav.settings', icon: Setting },
]

const pageTitle = computed(() =>
  route.meta.title ? t(String(route.meta.title)) : t('app.name'),
)

const dateLabel = computed(() =>
  formatDateLabel(todayInTimezone(app.timezone), ui.locale),
)

const healthText = computed(() => {
  if (health.value === 'ok') {
    return t('app.online')
  }
  if (health.value === 'error') {
    return t('app.offline')
  }
  return t('common.loading')
})

const isCollapsed = computed(() => ui.sidebarCollapsed)

function isActive(path: string) {
  return path === '/' ? route.path === '/' : route.path.startsWith(path)
}

function onMenuClick() {
  if (window.innerWidth <= 900) {
    ui.mobileMenuOpen = true
    return
  }
  ui.toggleSidebar()
}

function go(path: string) {
  ui.mobileMenuOpen = false
  void router.push(path)
}

async function checkHealth() {
  try {
    await api.health()
    health.value = 'ok'
  } catch {
    health.value = 'error'
  }
}

async function refresh() {
  if (refreshing.value) {
    return
  }
  refreshing.value = true
  try {
    await app.loadLookups(true)
    await checkHealth()
    window.dispatchEvent(new Event('tp:refresh'))
  } finally {
    window.setTimeout(() => {
      refreshing.value = false
    }, 450)
  }
}

onMounted(async () => {
  await checkHealth()
  try {
    await app.loadLookups()
  } catch {
    health.value = 'error'
  }
})
</script>

<template>
  <div class="app-shell" :class="{ collapsed: isCollapsed }">
    <aside class="sidebar">
      <button class="brand" type="button" @click="go('/')">
        <span class="brand-mark"><el-icon :size="20"><Compass /></el-icon></span>
        <span class="brand-text">
          <strong>{{ t('app.name') }}</strong>
          <small>{{ t('app.tagline') }}</small>
        </span>
      </button>

      <nav class="nav-list">
        <a
          v-for="item in navItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          :href="item.path"
          @click.prevent="go(item.path)"
        >
          <el-icon class="nav-icon" :size="19"><component :is="item.icon" /></el-icon>
          <span class="nav-label">{{ t(item.key) }}</span>
        </a>
      </nav>

      <div class="sidebar-footer">
        <div class="health-pill" :class="health">
          <span class="health-dot" />
          <span class="nav-label">{{ healthText }}</span>
        </div>
        <div class="version nav-label">{{ t('app.version') }} 0.2.0</div>
      </div>
    </aside>

    <div class="main-area">
      <header class="topbar">
        <div class="topbar-left">
          <button class="icon-button" type="button" @click="onMenuClick">
            <el-icon :size="18">
              <Expand v-if="isCollapsed" />
              <Fold v-else />
            </el-icon>
          </button>
          <div class="heading">
            <span class="date-chip">{{ dateLabel }}</span>
            <h1>{{ pageTitle }}</h1>
          </div>
        </div>

        <div class="topbar-right">
          <button
            class="icon-button"
            :class="{ spinning: refreshing }"
            type="button"
            :title="t('app.refresh')"
            @click="refresh"
          >
            <el-icon :size="18"><Refresh /></el-icon>
          </button>

          <button class="lang-switch" type="button" :title="t('app.language')" @click="ui.toggleLocale()">
            <span :class="{ active: ui.locale === 'zh-CN' }">中</span>
            <span :class="{ active: ui.locale === 'en-US' }">EN</span>
          </button>

          <button class="icon-button" type="button" :title="t('app.theme')" @click="ui.toggleTheme()">
            <el-icon :size="18">
              <Sunny v-if="ui.theme === 'dark'" />
              <Moon v-else />
            </el-icon>
          </button>
        </div>
      </header>

      <main class="content">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <el-drawer
      v-model="ui.mobileMenuOpen"
      direction="ltr"
      size="280px"
      :with-header="false"
      class="mobile-drawer"
    >
      <div class="mobile-nav">
        <div class="brand">
          <span class="brand-mark"><el-icon :size="20"><Compass /></el-icon></span>
          <span class="brand-text">
            <strong>{{ t('app.name') }}</strong>
            <small>{{ t('app.tagline') }}</small>
          </span>
        </div>
        <nav class="nav-list">
          <a
            v-for="item in navItems"
            :key="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
            :href="item.path"
            @click.prevent="go(item.path)"
          >
            <el-icon class="nav-icon" :size="19"><component :is="item.icon" /></el-icon>
            <span class="nav-label">{{ t(item.key) }}</span>
          </a>
        </nav>
        <div class="health-pill" :class="health">
          <span class="health-dot" />
          <span>{{ healthText }}</span>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  gap: 18px;
  min-height: 100vh;
  padding: 18px;
}

.sidebar {
  position: sticky;
  top: 18px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  width: 248px;
  flex-shrink: 0;
  height: calc(100vh - 36px);
  padding: 20px 14px;
  background: var(--tp-surface);
  border: 1px solid var(--tp-border);
  border-radius: 28px;
  box-shadow: var(--tp-shadow);
  transition: width 0.22s ease;
  overflow: hidden;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 8px;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
  white-space: nowrap;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  border-radius: 15px;
  color: #fff;
  background: linear-gradient(135deg, #6d5dfc, #9b6dff 55%, #00b8d9);
  box-shadow: 0 12px 24px -14px rgba(109, 93, 252, 0.9);
}

.brand-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.brand-text strong {
  font-size: 15px;
  font-weight: 760;
  letter-spacing: -0.02em;
}

.brand-text small {
  font-size: 11px;
  color: var(--tp-muted);
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 13px;
  border-radius: 14px;
  color: var(--tp-muted);
  font-size: 13.5px;
  font-weight: 600;
  white-space: nowrap;
  transition:
    background 0.18s ease,
    color 0.18s ease,
    transform 0.18s ease;
}

.nav-item:hover {
  background: var(--tp-surface-soft);
  color: var(--tp-text);
}

.nav-item.active {
  color: var(--tp-primary);
  background: linear-gradient(120deg, rgba(109, 93, 252, 0.16), rgba(109, 93, 252, 0.06));
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 3px;
  height: 20px;
  border-radius: 999px;
  background: var(--tp-primary);
  transform: translateY(-50%);
}

.nav-icon {
  flex-shrink: 0;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 6px;
}

.health-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 11px;
  border-radius: 12px;
  background: var(--tp-surface-soft);
  color: var(--tp-muted);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}

.health-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--tp-faint);
  flex-shrink: 0;
}

.health-pill.ok .health-dot {
  background: #16a34a;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.16);
}

.health-pill.error .health-dot {
  background: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.16);
}

.version {
  font-size: 11px;
  color: var(--tp-faint);
  padding-left: 4px;
}

.main-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
  flex: 1;
  min-width: 0;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 4px 0;
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.heading {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.heading h1 {
  margin: 0;
  font-size: 21px;
  font-weight: 760;
  letter-spacing: -0.02em;
  line-height: 1.2;
}

.date-chip {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--tp-muted);
}

.lang-switch {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border: 1px solid var(--tp-border);
  border-radius: 999px;
  background: var(--tp-surface);
  cursor: pointer;
}

.lang-switch span {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: var(--tp-muted);
  transition:
    background 0.18s ease,
    color 0.18s ease;
}

.lang-switch span.active {
  color: #fff;
  background: var(--tp-primary);
  box-shadow: 0 8px 16px -10px rgba(109, 93, 252, 0.9);
}

.content {
  min-width: 0;
  padding-bottom: 24px;
}

.spinning :deep(.el-icon) {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition:
    opacity 0.18s ease,
    transform 0.18s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.mobile-nav {
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 8px 2px;
}

.app-shell.collapsed .sidebar {
  width: 88px;
}

.app-shell.collapsed .brand {
  justify-content: center;
  padding: 4px 0;
}

.app-shell.collapsed .brand-text,
.app-shell.collapsed .nav-label {
  display: none;
}

.app-shell.collapsed .nav-item {
  justify-content: center;
  padding: 12px;
}

.app-shell.collapsed .health-pill {
  justify-content: center;
  padding: 10px;
}

.app-shell.collapsed .version {
  display: none;
}

@media (max-width: 900px) {
  .app-shell {
    display: block;
    padding: 12px;
  }

  .sidebar {
    display: none;
  }

  .topbar {
    padding: 0;
  }

  .heading h1 {
    font-size: 18px;
  }

  .content {
    padding-top: 14px;
  }
}

@media (max-width: 560px) {
  .date-chip {
    display: none;
  }

  .topbar-right {
    gap: 6px;
  }

  .icon-button {
    width: 36px;
    height: 36px;
  }
}
</style>
