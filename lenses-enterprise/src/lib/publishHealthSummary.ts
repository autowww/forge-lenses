import type { WorkspaceWebsite } from '../api/workspace'

export type PublishHealthSummary = {
  siteCount: number
  needsAttention: number
  label: string
  tone: 'ok' | 'warn' | 'muted'
}

/** Human label for top-nav Publish badge — sites count + readiness attention, not blog unread alone. */
export function publishHealthSummary(websites: WorkspaceWebsite[] | undefined): PublishHealthSummary {
  const sites = websites ?? []
  let needsAttention = 0
  for (const w of sites) {
    const html = w.html_total ?? 0
    if (html <= 0 || html < 5) needsAttention++
  }
  const siteCount = sites.length
  if (siteCount === 0) {
    return { siteCount: 0, needsAttention: 0, label: 'No sites in scan', tone: 'muted' }
  }
  if (needsAttention > 0) {
    return {
      siteCount,
      needsAttention,
      label: `${siteCount} site${siteCount === 1 ? '' : 's'} · ${needsAttention} need attention`,
      tone: 'warn',
    }
  }
  return {
    siteCount,
    needsAttention: 0,
    label: `${siteCount} site${siteCount === 1 ? '' : 's'} · healthy`,
    tone: 'ok',
  }
}
