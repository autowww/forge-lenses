import type { DocsHealthSessionEvent } from '../api/docsHealth'
import { docsHealthEventKindLabel } from './docsHealthTimelineLabels'

export type DocsHealthLiveLogLine = {
  id: string
  ts?: string
  text: string
  tone: 'info' | 'ok' | 'err' | 'busy'
}

const STORY_TYPES = new Set([
  'summary',
  'plan',
  'question',
  'user_reply',
  'file_inquiry',
  'diff',
  'file_change',
  'command',
  'command_result',
  'verification',
  'work_item',
  'kpi_update',
])

function clip(s: string, max: number): string {
  const t = s.trim().replace(/\s+/g, ' ')
  if (t.length <= max) return t
  return `${t.slice(0, max - 1)}…`
}

function toneFor(ev: DocsHealthSessionEvent): DocsHealthLiveLogLine['tone'] {
  const t = String(ev.type || '').toLowerCase()
  if (t === 'command_result' && ev.ok === false) return 'err'
  if (t === 'verification' && ev.ok === false) return 'err'
  if (t === 'question') return 'busy'
  if (t === 'plan' || t === 'command' || t === 'file_change') return 'busy'
  if (t === 'command_result' && ev.ok === true) return 'ok'
  if (t === 'verification' && ev.ok === true) return 'ok'
  return 'info'
}

function oneLine(ev: DocsHealthSessionEvent): string {
  const kind = docsHealthEventKindLabel(ev.type)
  const title = ev.title?.trim()
  if (title) return `${kind}: ${clip(title, 140)}`
  const body = ev.body?.trim()
  if (body) return `${kind}: ${clip(body, 140)}`
  const cmd = ev.cmd?.trim()
  if (cmd) return `${kind}: ${clip(cmd, 120)}`
  const path = ev.path?.trim()
  if (path) return `${kind}: ${clip(path, 120)}`
  return kind
}

/**
 * Compact chronological lines for an agent-style live log (newest at bottom).
 */
export function buildDocsHealthLiveLogLines(events: DocsHealthSessionEvent[] | undefined, limit = 120): DocsHealthLiveLogLine[] {
  if (!events?.length) return []
  const rows: DocsHealthLiveLogLine[] = []
  let seq = 0
  for (const ev of events) {
    const t = String(ev.type || '').toLowerCase()
    if (t === 'token_stats') continue
    if (!STORY_TYPES.has(t)) continue
    const id = `${seq++}-${t}-${ev.ts || ''}-${ev.title?.slice(0, 12) || ''}`
    rows.push({
      id,
      ts: ev.ts,
      text: oneLine(ev),
      tone: toneFor(ev),
    })
  }
  if (rows.length <= limit) return rows
  return rows.slice(-limit)
}
