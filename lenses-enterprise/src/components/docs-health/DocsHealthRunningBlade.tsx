import { useEffect, useState } from 'react'
import type { DocsHealthSessionHeaderStats } from '../../api/docsHealth'
import { formatFleetSandboxHeadline, type FleetSandboxSlice } from '../../lib/docsHealthFleetLive'
import { DOCS_HEALTH_STAGE_DEFS } from '../../lib/docsHealthStageFlow'
import './docs-health-session-layout.css'

const LIVE = new Set(['running', 'awaiting_approval', 'awaiting_input', 'paused'])

function useElapsedSeconds(startedAt: string | undefined) {
  const [sec, setSec] = useState(0)
  useEffect(() => {
    if (!startedAt) {
      setSec(0)
      return
    }
    const start = Date.parse(startedAt)
    if (Number.isNaN(start)) {
      setSec(0)
      return
    }
    const tick = () => setSec(Math.max(0, Math.floor((Date.now() - start) / 1000)))
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [startedAt])
  return sec
}

function fmtElapsed(totalSec: number) {
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  if (m >= 60) {
    const h = Math.floor(m / 60)
    const mm = m % 60
    return `${h}h ${mm}m ${s}s`
  }
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function stepLabel(step: string | null | undefined): string {
  const id = String(step || '').trim()
  if (!id) return ''
  const d = DOCS_HEALTH_STAGE_DEFS.find((x) => x.id === id)
  return d?.label || id
}

type Props = {
  status?: string
  busyStep?: string | null
  startedAt?: string
  header?: DocsHealthSessionHeaderStats
  runStateLine?: string | null
  streamMode?: 'sse' | 'poll' | 'idle'
  /** Tasklet sandbox blob (Fleet writes ``phase``, ``fleet_job_id``, … during ``session_step``). */
  taskletSandbox?: Record<string, unknown> | null
}

/**
 * High-visibility “what is running now” strip — elapsed clock, step, tokens; does not steal page scroll.
 */
export function DocsHealthRunningBlade({
  status,
  busyStep,
  startedAt,
  header,
  runStateLine,
  streamMode = 'idle',
  taskletSandbox,
}: Props) {
  const st = String(status || '').toLowerCase()
  const elapsedSec = useElapsedSeconds(startedAt)
  const sb = (taskletSandbox || null) as FleetSandboxSlice | null
  const fleetLine = formatFleetSandboxHeadline(sb)

  if (!LIVE.has(st) && !busyStep) return null
  const busy = String(busyStep || '').trim()

  let headline = 'Run active'
  let sub: string | null = null
  if (busy) {
    headline = `Running: ${stepLabel(busy)}`
    if (fleetLine) {
      sub = `${fleetLine}. The Lenses server is holding this request open until Fleet finishes the Docker-backed worker; this strip refreshes from session polls or SSE while that happens.`
    } else {
      sub =
        'Studio is waiting on this server request until the step finishes (DevTools Network shows the docs-health POST as pending). Run activity still updates below while the server works.'
    }
  } else if (st === 'running') {
    headline = 'Run in progress'
    sub =
      runStateLine?.trim() ||
      'Orchestration may still be working. Watch Run activity for new events.'
  } else if (st === 'awaiting_approval') {
    headline = 'Waiting for your approval'
    sub = 'Review the proposal in Run activity, then confirm or decline.'
  } else if (st === 'awaiting_input') {
    headline = 'Waiting for your input'
    sub = 'Reply in the panel below when you are ready.'
  } else if (st === 'paused') {
    headline = 'Paused'
    sub = runStateLine?.trim() || null
  }

  const tt = typeof header?.total_tokens === 'number' ? header.total_tokens : null
  const lm = header?.active_model || header?.last_model_id

  return (
    <div
      className="le-dh-running-blade"
      role="status"
      aria-live="polite"
      aria-label="Current session activity"
    >
      <div className="le-dh-running-blade__glow" aria-hidden />
      <div className="le-dh-running-blade__inner">
        <div className="le-dh-running-blade__primary">
          <span className="le-dh-running-blade__pulse" aria-hidden />
          <span className="le-dh-running-blade__headline">{headline}</span>
        </div>
        <div className="le-dh-running-blade__metrics">
          {fleetLine && busy ? (
            <span className="le-dh-running-blade__metric le-dh-running-blade__metric--wide">
              <span className="le-dh-running-blade__metric-label">Fleet</span>
              <span className="le-dh-running-blade__metric-value le-dh-running-blade__mono" title={fleetLine}>
                {sb?.fleet_job_status || sb?.phase || '—'}
                {typeof sb?.fleet_host_cpu_pct === 'number' ? ` · CPU ${sb.fleet_host_cpu_pct}%` : ''}
                {typeof sb?.fleet_host_mem_pct === 'number' ? ` · RAM ${sb.fleet_host_mem_pct}%` : ''}
              </span>
            </span>
          ) : null}
          <span className="le-dh-running-blade__metric">
            <span className="le-dh-running-blade__metric-label">Elapsed</span>
            <span className="le-dh-running-blade__metric-value">{fmtElapsed(elapsedSec)}</span>
          </span>
          {tt != null && tt > 0 ? (
            <span className="le-dh-running-blade__metric">
              <span className="le-dh-running-blade__metric-label">Tokens</span>
              <span className="le-dh-running-blade__metric-value">{tt.toLocaleString()}</span>
            </span>
          ) : (
            <span className="le-dh-running-blade__metric">
              <span className="le-dh-running-blade__metric-label">Tokens</span>
              <span className="le-dh-running-blade__metric-value le-dh-running-blade__muted">0</span>
            </span>
          )}
          {lm ? (
            <span className="le-dh-running-blade__metric le-dh-running-blade__metric--wide">
              <span className="le-dh-running-blade__metric-label">Model</span>
              <span className="le-dh-running-blade__metric-value le-dh-running-blade__mono">{lm}</span>
            </span>
          ) : null}
          <span className="le-dh-running-blade__metric">
            <span className="le-dh-running-blade__metric-label">Feed</span>
            <span className="le-dh-running-blade__metric-value">
              {streamMode === 'sse' ? 'Live (SSE)' : streamMode === 'poll' ? 'Polling' : '—'}
            </span>
          </span>
        </div>
        {sub ? <p className="le-dh-running-blade__sub">{sub}</p> : null}
      </div>
    </div>
  )
}
