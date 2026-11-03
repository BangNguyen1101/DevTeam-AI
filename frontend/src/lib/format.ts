const dateFormat = new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' })

/** Backend returns naive UTC timestamps (SQL Server DATETIME2). */
export function formatDate(value: string) {
  return dateFormat.format(new Date(value.endsWith('Z') ? value : `${value}Z`))
}
