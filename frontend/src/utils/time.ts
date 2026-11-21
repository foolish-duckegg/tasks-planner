import dayjs from 'dayjs'
import isoWeek from 'dayjs/plugin/isoWeek'

dayjs.extend(isoWeek)

export const MINUTES_PER_DAY = 1440

export function minutesToTime(value: number | null | undefined, show24 = true): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return ''
  }
  if (value >= MINUTES_PER_DAY) {
    return show24 ? '24:00' : '00:00'
  }
  const safe = Math.max(0, Math.floor(value))
  const hours = Math.floor(safe / 60)
  const minutes = safe % 60
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
}

export function parseTime(text: string): number | null {
  const value = text.trim()
  if (!value) {
    return null
  }
  if (value === '24:00') {
    return MINUTES_PER_DAY
  }
  const match = /^(\d{1,2}):(\d{2})$/.exec(value)
  if (!match) {
    return null
  }
  const hours = Number(match[1])
  const minutes = Number(match[2])
  if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59) {
    return null
  }
  return hours * 60 + minutes
}

export function todayInTimezone(timeZone = 'Asia/Shanghai'): string {
  try {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(new Date())
    const get = (type: string) => parts.find((part) => part.type === type)?.value
    const year = get('year')
    const month = get('month')
    const day = get('day')
    if (year && month && day) {
      return `${year}-${month}-${day}`
    }
  } catch {
    // Fall through to the local date.
  }
  return dayjs().format('YYYY-MM-DD')
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return ''
  }
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

export function formatDate(value: string | null | undefined, template = 'YYYY-MM-DD'): string {
  if (!value) {
    return ''
  }
  return dayjs(value).format(template)
}

export function formatDateLabel(date: string, locale: string): string {
  if (!date) {
    return ''
  }
  const parsed = dayjs(date)
  if (!parsed.isValid()) {
    return date
  }
  return new Intl.DateTimeFormat(locale === 'zh-CN' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
    weekday: 'short',
  }).format(parsed.toDate())
}

export function addDays(date: string, amount: number): string {
  return dayjs(date).add(amount, 'day').format('YYYY-MM-DD')
}

export function addMonths(date: string, amount: number): string {
  return dayjs(date).add(amount, 'month').format('YYYY-MM-DD')
}

export function formatShortDate(date: string, locale: string): string {
  const parsed = dayjs(date)
  if (!parsed.isValid()) {
    return date
  }
  return new Intl.DateTimeFormat(locale === 'zh-CN' ? 'zh-CN' : 'en-US', {
    month: 'short',
    day: 'numeric',
  }).format(parsed.toDate())
}

export function formatMonthLabel(date: string, locale: string): string {
  const parsed = dayjs(date)
  if (!parsed.isValid()) {
    return date
  }
  return new Intl.DateTimeFormat(locale === 'zh-CN' ? 'zh-CN' : 'en-US', {
    year: 'numeric',
    month: 'long',
  }).format(parsed.toDate())
}

export function isoWeekday(date: string): number {
  return dayjs(date).isoWeekday()
}

export function minutesBetween(start: number, end: number): number {
  return Math.max(0, end - start)
}

export function durationLabel(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  if (hours && mins) {
    return `${hours}h ${mins}m`
  }
  if (hours) {
    return `${hours}h`
  }
  return `${mins}m`
}
