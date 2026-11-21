const KIND_COLORS: Record<string, string> = {
  sleep: '#7c83fd',
  rest: '#3ecf8e',
  work: '#6d5dfc',
  free: '#f5a524',
  study: '#00b8d9',
  exercise: '#ff6b6b',
}

const FALLBACK_COLORS = ['#6d5dfc', '#00b8d9', '#3ecf8e', '#f5a524', '#ff6b6b', '#a855f7']

export function kindColor(kind: string | null | undefined): string {
  if (!kind) {
    return '#8b8fa8'
  }
  const normalized = kind.toLowerCase()
  if (KIND_COLORS[normalized]) {
    return KIND_COLORS[normalized]
  }
  let hash = 0
  for (let index = 0; index < normalized.length; index += 1) {
    hash = (hash * 31 + normalized.charCodeAt(index)) >>> 0
  }
  return FALLBACK_COLORS[hash % FALLBACK_COLORS.length]
}

export function withAlpha(hex: string, alpha: number): string {
  const value = hex.replace('#', '')
  const full = value.length === 3 ? value.split('').map((char) => char + char).join('') : value
  const red = Number.parseInt(full.slice(0, 2), 16)
  const green = Number.parseInt(full.slice(2, 4), 16)
  const blue = Number.parseInt(full.slice(4, 6), 16)
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}
