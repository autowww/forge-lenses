import { apiGetJson, apiPostJson } from './http'

export type AgentRuntimeOverview = {
  ok?: boolean
  capabilities?: Record<string, unknown>[]
  providers?: Record<string, unknown>[]
  slots?: Record<string, unknown>[]
  policy?: Record<string, unknown>
  legacy_slot_aliases?: Record<string, string>
  last_ledger_records?: Record<string, unknown>[]
}

export function getAgentRuntimeOverview() {
  return apiGetJson<AgentRuntimeOverview>('/api/agent-runtime/overview')
}

export function getAgentRuntimeTokenUsage(params?: { session_id?: string; project?: string; scan_run_id?: string }) {
  const q = new URLSearchParams()
  if (params?.session_id) q.set('session_id', params.session_id)
  if (params?.project) q.set('project', params.project)
  if (params?.scan_run_id) q.set('scan_run_id', params.scan_run_id)
  const qs = q.toString()
  return apiGetJson<Record<string, unknown>>(`/api/agent-runtime/token-usage${qs ? `?${qs}` : ''}`)
}

export function createAgentRuntimeSession(body: Record<string, unknown>) {
  return apiPostJson<{ ok?: boolean; session?: Record<string, unknown> }>('/api/agent-runtime/sessions', body)
}

export function getAgentRuntimeSession(sessionId: string) {
  const enc = encodeURIComponent(sessionId)
  return apiGetJson<{ ok?: boolean; session?: Record<string, unknown> }>(`/api/agent-runtime/sessions/${enc}`)
}

export function getAgentRuntimeSessionEvents(sessionId: string, sinceSeq = -1) {
  const enc = encodeURIComponent(sessionId)
  return apiGetJson<{ ok?: boolean; events?: unknown[] }>(
    `/api/agent-runtime/sessions/${enc}/events?since_seq=${sinceSeq}`,
  )
}
