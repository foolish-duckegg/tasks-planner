import axios from 'axios'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 20000,
})

export function apiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    if (
      detail &&
      typeof detail === 'object' &&
      'message' in detail &&
      typeof detail.message === 'string'
    ) {
      return detail.message
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => {
          if (item && typeof item === 'object' && 'msg' in item) {
            const loc = Array.isArray(item.loc) ? item.loc.join('.') : ''
            return loc ? `${loc}: ${item.msg}` : String(item.msg)
          }
          return JSON.stringify(item)
        })
        .join('; ')
    }
    if (error.code === 'ECONNABORTED') {
      return 'Request timed out.'
    }
    if (!error.response) {
      return 'Cannot reach the API service.'
    }
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return String(error)
}
