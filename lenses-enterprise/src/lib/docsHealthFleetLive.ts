/**
 * Live telemetry from Docs Health sandbox when steps run via Forge Fleet
 * (written by ``lenses/docs_health/isolation.py`` while the HTTP step is in flight).
 */

export type FleetSandboxSlice = {
  phase?: string
  fleet_endpoint?: string
  fleet_job_id?: string
  fleet_job_status?: string
  fleet_job_http?: number
  fleet_submit_at?: string
  fleet_poll_at?: string
  fleet_finished_at?: string
  fleet_host_cpu_pct?: number | null
  fleet_host_mem_pct?: number | null
  fleet_job_terminal_status?: string
  container_id?: string | null
  fleet_argv_len?: number
}

/** Human-readable one-liner for the run hero / live strip. */
export function formatFleetSandboxHeadline(sb: FleetSandboxSlice | null | undefined): string | null {
  if (!sb?.phase?.startsWith('fleet')) return null
  const ep = String(sb.fleet_endpoint || '').trim()
  const jid = String(sb.fleet_job_id || '').trim()
  const st = String(sb.fleet_job_status || sb.phase || '').trim()
  const cid = String(sb.container_id || '').trim()
  const parts: string[] = ['Forge Fleet']
  if (ep) parts.push(ep)
  if (jid) parts.push(`job ${jid.length > 14 ? `${jid.slice(0, 10)}…` : jid}`)
  if (st) parts.push(st)
  if (cid) parts.push(`container ${cid.length > 16 ? `${cid.slice(0, 12)}…` : cid}`)
  return parts.join(' · ')
}

/** Optional sub-progress (10–95) so the main workflow bar is not the only motion during long Fleet waits. */
export function fleetActivityPercent(sb: FleetSandboxSlice | null | undefined): number | null {
  const ph = String(sb?.phase || '')
  if (!ph.startsWith('fleet')) return null
  const order: Record<string, number> = {
    fleet_connecting: 12,
    fleet_argv_ready: 22,
    fleet_job_submitted: 34,
    fleet_job_poll: 58,
    fleet_job_finished: 92,
  }
  const base = order[ph]
  if (base == null) return 18
  if (ph === 'fleet_job_poll') {
    const jst = String(sb?.fleet_job_status || '').toLowerCase()
    if (jst === 'running') return 72
    if (jst === 'queued') return 48
    return base
  }
  return base
}
