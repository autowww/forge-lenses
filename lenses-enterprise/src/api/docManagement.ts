import { apiGetJson, apiPostJson } from './http'

export type DocManagementSurface = {
  surface_id: string
  label: string
  kind: string
  repo?: string
  relative_path?: string
}

export type DocManagementPersona = {
  persona_id: string
  label: string
  main_question?: string
}

export type DocManagementSessionSummary = {
  session_id: string
  display_name: string
  status: string
  updated_at?: string
  created_at?: string
  forge_run_id?: string
  workflow_stage?: string
  intake_source?: string | null
  target_surfaces?: string[]
}

export type DocManagementSeed = {
  path: string
  name: string
  status: string
  source_url?: string
  blog_slug?: string
}

export type DocManagementPackArtifact = {
  slug: string
  artifacts: string[]
  hydration_brief_markdown?: string | null
}

export type DocManagementSession = {
  id: string
  display_name: string
  status: string
  forge_run_id?: string
  wizard?: {
    step_index?: number
    intake_source?: string | null
    persona?: string
    target_surfaces?: string[]
    use_llm?: boolean
    source_url?: string | null
    blog_slug?: string | null
  }
  intake?: { seeds?: DocManagementSeed[]; warnings?: string[] }
  workflow?: { stage?: string; stages_completed?: string[] }
  events?: Array<Record<string, unknown>>
  pack_artifacts?: DocManagementPackArtifact[]
  reviewer_decision_manifest?: Record<string, unknown> | null
  session_href?: string
}

export async function getDocManagementCatalog(): Promise<{
  ok: boolean
  personas: DocManagementPersona[]
  surfaces: DocManagementSurface[]
}> {
  return apiGetJson('/api/doc-management/catalog')
}

export async function listDocManagementSessions(): Promise<{
  ok: boolean
  sessions: DocManagementSessionSummary[]
}> {
  return apiGetJson('/api/doc-management/sessions')
}

export async function getDocManagementSession(sessionId: string): Promise<{
  ok: boolean
  session: DocManagementSession
}> {
  return apiGetJson(`/api/doc-management/session/${encodeURIComponent(sessionId)}`)
}

export async function postDocManagement(body: Record<string, unknown>): Promise<Record<string, unknown>> {
  return apiPostJson('/api/doc-management', body)
}

export function docManagementSessionEventsUrl(sessionId: string): string {
  const q = new URLSearchParams({ session_id: sessionId })
  return `/api/doc-management/session-events?${q.toString()}`
}

export async function createDocManagementSession(displayName?: string, wizard?: Record<string, unknown>) {
  return postDocManagement({
    op: 'create_session',
    display_name: displayName,
    wizard,
  })
}

export async function submitDocManagementIntake(
  sessionId: string,
  payload: {
    intake_source: string
    text?: string
    zip_base64?: string
    url?: string
    blog_slug?: string
    display_name?: string
  },
) {
  return postDocManagement({ op: 'session_intake', session_id: sessionId, ...payload })
}

export async function saveDocManagementWizard(sessionId: string, wizard: Record<string, unknown>) {
  return postDocManagement({ op: 'session_wizard', session_id: sessionId, wizard })
}

export async function runDocManagementSession(sessionId: string) {
  return postDocManagement({ op: 'session_run', session_id: sessionId })
}

export async function saveDocManagementDecisions(
  sessionId: string,
  reviewer: string,
  decisions: Array<Record<string, unknown>>,
) {
  return postDocManagement({
    op: 'session_decisions',
    session_id: sessionId,
    reviewer,
    decisions,
  })
}

export async function promoteDocManagementSession(sessionId: string, dryRun: boolean) {
  return postDocManagement({ op: 'session_promote', session_id: sessionId, dry_run: dryRun })
}

export async function rollbackDocManagementSession(sessionId: string) {
  return postDocManagement({ op: 'session_rollback', session_id: sessionId })
}

export async function cancelDocManagementSession(sessionId: string) {
  return postDocManagement({ op: 'session_cancel', session_id: sessionId })
}
