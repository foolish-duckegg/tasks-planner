import { defineStore } from 'pinia'

import { setI18nLocale, type AppLocale } from '@/i18n'

export type AppTheme = 'light' | 'dark'

const storedTheme = localStorage.getItem('tp-theme')
const storedLocale = localStorage.getItem('tp-locale')

const initialTheme: AppTheme = storedTheme === 'dark' ? 'dark' : 'light'
const initialLocale: AppLocale = storedLocale === 'en-US' ? 'en-US' : 'zh-CN'

function applyTheme(theme: AppTheme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  document.documentElement.style.colorScheme = theme
}

applyTheme(initialTheme)
setI18nLocale(initialLocale)

export const useUiStore = defineStore('ui', {
  state: () => ({
    theme: initialTheme as AppTheme,
    locale: initialLocale as AppLocale,
    sidebarCollapsed: false,
    mobileMenuOpen: false,
  }),

  actions: {
    setTheme(theme: AppTheme) {
      this.theme = theme
      localStorage.setItem('tp-theme', theme)
      applyTheme(theme)
    },

    toggleTheme() {
      this.setTheme(this.theme === 'dark' ? 'light' : 'dark')
    },

    setLocale(locale: AppLocale) {
      this.locale = locale
      localStorage.setItem('tp-locale', locale)
      setI18nLocale(locale)
    },

    toggleLocale() {
      this.setLocale(this.locale === 'zh-CN' ? 'en-US' : 'zh-CN')
    },

    toggleSidebar() {
      this.sidebarCollapsed = !this.sidebarCollapsed
    },
  },
})
