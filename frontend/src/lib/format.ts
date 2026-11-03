const dateFormat = new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' })
const timeFormat = new Intl.DateTimeFormat('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 })
const integer = new Intl.NumberFormat('en-US')

/** Backend returns naive UTC timestamps (SQL Server DATETIME2). */
export function parseUtc(value: string): Date {
  return new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
}

export function formatDate(value: string) {
  return dateFormat.format(parseUtc(value))
}

export function formatTime(value: string) {
  return timeFormat.format(parseUtc(value))
}

export function formatRelative(value: string | null): string {
  if (!value) return '—'
  const seconds = Math.round((Date.now() - parseUtc(value).getTime()) / 1000)
  if (seconds < 45) return 'vừa xong'
  if (seconds < 3600) return `${Math.round(seconds / 60)} phút trước`
  if (seconds < 86_400) return `${Math.round(seconds / 3600)} giờ trước`
  if (seconds < 7 * 86_400) return `${Math.round(seconds / 86_400)} ngày trước`
  return formatDate(value)
}

export const formatInt = (n: number) => integer.format(n)
export const formatCompact = (n: number) => compact.format(n)

export function formatUsd(n: number, digits = 2) {
  return `$${n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: Math.max(digits, 4) })}`
}

export function formatDuration(start: string | null, end: string | null): string {
  if (!start) return '—'
  const ms = (end ? parseUtc(end) : new Date()).getTime() - parseUtc(start).getTime()
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  return m < 60 ? `${m}m ${s % 60}s` : `${Math.floor(m / 60)}h ${m % 60}m`
}

export function formatBytes(n: number | null) {
  if (n === null) return ''
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

export const percent = (part: number, total: number) => (total > 0 ? Math.round((part / total) * 100) : 0)
