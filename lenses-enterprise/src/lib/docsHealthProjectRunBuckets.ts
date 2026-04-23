/**
 * Buckets TaskletRun rows and docs-health session summaries for the project
 * Docs health lifecycle tabs (queue / running / completed / failed).
 */

export type TaskletRunRow = {
  id?: string
  state?: string
  stop_reason?: string | null
  updated_at?: string
  docs_health_session_id?: string
  tasklet_id?: string
  last_error?: string | null
}

export type RecentSessionRow = {
  session_id?: string
  status?: string
  display_name?: string | null
  cluster_label?: string | null
  total_tokens?: number
  href_session?: string
  updated_at?: string
  last_model?: string | null
}

const QUEUE = new Set(['created', 'preparing'])
const RUNNING = new Set([
  'running',
  'awaiting_input',
  'awaiting_approval',
  'verifying',
  'paused',
  'stopping',
])
const COMPLETED = new Set(['completed'])
const FAILED_TASKLET = new Set(['failed', 'stopped'])

function norm(s: string | undefined | null): string {
  return String(s ?? '')
    .trim()
    .toLowerCase()
}

/** Single coarse bucket for a tasklet run `state` string. */
export function bucketTaskletState(state: string | undefined | null): 'queue' | 'running' | 'completed' | 'failed' {
  const s = norm(state)
  if (!s) return 'running'
  if (QUEUE.has(s)) return 'queue'
  if (COMPLETED.has(s)) return 'completed'
  if (FAILED_TASKLET.has(s)) return 'failed'
  if (RUNNING.has(s)) return 'running'
  return 'running'
}

/** Session `status` from store / projection (run_state_to_docs_session_status). */
export function bucketSessionStatus(status: string | undefined | null): 'running' | 'completed' | 'failed' {
  const s = norm(status)
  if (s === 'completed') return 'completed'
  if (s === 'failed' || s === 'cancelled') return 'failed'
  return 'running'
}

export type TaskletBuckets = {
  queue: TaskletRunRow[]
  running: TaskletRunRow[]
  completed: TaskletRunRow[]
  failed: TaskletRunRow[]
}

export function bucketTaskletRuns(runs: TaskletRunRow[] | undefined | null): TaskletBuckets {
  const out: TaskletBuckets = { queue: [], running: [], completed: [], failed: [] }
  if (!runs?.length) return out
  for (const r of runs) {
    const b = bucketTaskletState(r.state)
    out[b === 'queue' ? 'queue' : b === 'completed' ? 'completed' : b === 'failed' ? 'failed' : 'running'].push(r)
  }
  return out
}

export type SessionBuckets = {
  running: RecentSessionRow[]
  completed: RecentSessionRow[]
  failed: RecentSessionRow[]
}

export function bucketRecentSessions(sessions: RecentSessionRow[] | undefined | null): SessionBuckets {
  const out: SessionBuckets = { running: [], completed: [], failed: [] }
  if (!sessions?.length) return out
  for (const s of sessions) {
    const b = bucketSessionStatus(s.status)
    if (b === 'completed') out.completed.push(s)
    else if (b === 'failed') out.failed.push(s)
    else out.running.push(s)
  }
  return out
}

/** Sum remediation LLM tokens across recent session rows (best-effort). */
export function sumSessionTokens(sessions: RecentSessionRow[] | undefined | null): number {
  if (!sessions?.length) return 0
  let t = 0
  for (const s of sessions) {
    const n = Number(s.total_tokens)
    if (Number.isFinite(n) && n > 0) t += n
  }
  return t
}

/** Latest session row by `updated_at` (ISO) or first with tokens — for a one-line model hint. */
export function pickLatestSessionModel(sessions: RecentSessionRow[] | undefined | null): string | null {
  if (!sessions?.length) return null
  const sorted = [...sessions].sort((a, b) => {
    const ta = Date.parse(String(a.updated_at || '')) || 0
    const tb = Date.parse(String(b.updated_at || '')) || 0
    return tb - ta
  })
  for (const s of sorted) {
    const m = s.last_model?.trim()
    if (m) return m
  }
  return null
}
