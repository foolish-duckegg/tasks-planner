import { createRouter, createWebHistory } from 'vue-router'

import MainLayout from '@/layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
          meta: { title: 'nav.dashboard' },
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: () => import('@/views/TasksView.vue'),
          meta: { title: 'nav.tasks' },
        },
        {
          path: 'planner',
          name: 'planner',
          component: () => import('@/views/PlannerView.vue'),
          meta: { title: 'nav.planner' },
        },
        {
          path: 'day-blocks',
          name: 'day-blocks',
          component: () => import('@/views/DayBlocksView.vue'),
          meta: { title: 'nav.dayBlocks' },
        },
        {
          path: 'fixed-blocks',
          name: 'fixed-blocks',
          component: () => import('@/views/FixedBlocksView.vue'),
          meta: { title: 'nav.fixedBlocks' },
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
          meta: { title: 'nav.settings' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior: () => ({ top: 0 }),
})

export default router
