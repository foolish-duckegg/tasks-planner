import { defineStore } from 'pinia'

import { api } from '@/api'
import type { MetaMap, PriorityLevel, TaskStatus } from '@/api/types'

export const useAppStore = defineStore('app', {
  state: () => ({
    meta: {} as MetaMap,
    statuses: [] as TaskStatus[],
    priorities: [] as PriorityLevel[],
    lookupsLoaded: false,
    loading: false,
  }),

  getters: {
    timezone: (state) => state.meta.timezone || 'Asia/Shanghai',
    weekStart: (state) => {
      const value = Number(state.meta.week_start || 1)
      return value >= 1 && value <= 7 ? value : 1
    },
    activeStatuses: (state) => state.statuses.filter((item) => item.is_active),
    activePriorities: (state) => state.priorities.filter((item) => item.is_active),
    statusById: (state) => (id: number) => state.statuses.find((item) => item.id === id),
    priorityById: (state) => (id: number | null) =>
      id === null ? undefined : state.priorities.find((item) => item.id === id),
  },

  actions: {
    async loadMeta() {
      this.meta = await api.meta.list()
      return this.meta
    },

    async loadLookups(force = false) {
      if (this.lookupsLoaded && !force) {
        return
      }
      this.loading = true
      try {
        const [meta, statuses, priorities] = await Promise.all([
          api.meta.list(),
          api.statuses.list(),
          api.priorities.list(),
        ])
        this.meta = meta
        this.statuses = statuses
        this.priorities = priorities
        this.lookupsLoaded = true
      } finally {
        this.loading = false
      }
    },

    async saveMeta(key: string, value: string) {
      this.meta = await api.meta.put(key, value)
    },
  },
})
