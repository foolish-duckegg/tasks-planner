import { onMounted, onUnmounted } from 'vue'

export function usePageRefresh(handler: () => void | Promise<void>) {
  const listener = () => {
    void handler()
  }

  onMounted(() => window.addEventListener('tp:refresh', listener))
  onUnmounted(() => window.removeEventListener('tp:refresh', listener))
}
