export type RecentUsageEvent = {
  provider?: string
  ok?: boolean
  error?: string | null
  detail?: string | null
}

/** ``recent_events`` is chronological (oldest-first). Attention should follow the latest row per provider. */
export function attentionLineFromRecentUsage(
  events: RecentUsageEvent[] | undefined,
  providerId: string,
): string {
  if (!events?.length) return ''
  for (let i = events.length - 1; i >= 0; i--) {
    const e = events[i]
    if (!e || e.provider !== providerId) continue
    if (e.ok === false) {
      return (e.error || e.detail || '').trim()
    }
    return ''
  }
  return ''
}
