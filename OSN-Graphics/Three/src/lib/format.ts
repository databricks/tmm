/**
 * Format a date as relative time (e.g., "2 minutes ago")
 */
export function formatDistanceToNow(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 60) {
    return 'just now'
  }

  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) {
    return `${diffMin} min ago`
  }

  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) {
    return `${diffHour} hour${diffHour > 1 ? 's' : ''} ago`
  }

  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`
}
