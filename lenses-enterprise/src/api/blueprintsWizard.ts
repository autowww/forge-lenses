import type { ArtifactReviewApiAction } from '../blueprints-wizard/wizardDomainTypes'
import { apiGetJson, apiPostJson, apiPutJson } from './http'

export type BlueprintsWizardEnabledResponse = {
  ok?: boolean
  enabled?: boolean
}

export type WizardScopePayload = {
  wbs_rel?: string | null
  roadmap_rel?: string | null
  roadmap_section_id?: string | null
}

export type WizardNewProductDraft = {
  repo_name?: string
  visibility?: string
  account_type?: string
  owner?: string
  license?: string
  description?: string
}

export type WizardSessionDocumentJson = {
  version: number
  updated_at: string
  step_index: number
  payload: Record<string, unknown>
}

export type WizardSessionSummary = {
  session_id: string
  updated_at: string
  step_index: number
  title: string
  purpose: string
  state: string
  mode: string
}

export async function getBlueprintsWizardEnabled(): Promise<boolean> {
  const r = await apiGetJson<BlueprintsWizardEnabledResponse>('/api/blueprints/wizard/enabled')
  return r.ok === true && r.enabled === true
}

export async function listWizardSessions(): Promise<WizardSessionSummary[]> {
  const r = await apiGetJson<{ ok?: boolean; sessions?: WizardSessionSummary[] }>(
    '/api/blueprints/wizard/sessions',
  )
  if (!r.ok || !Array.isArray(r.sessions)) {
    throw new Error('listWizardSessions failed')
  }
  return r.sessions
}

export async function createWizardSession(): Promise<{ session_id: string }> {
  const r = await apiPostJson<{ ok?: boolean; session_id?: string }>('/api/blueprints/wizard/session', {})
  if (!r.ok || !r.session_id) {
    throw new Error('createWizardSession failed')
  }
  return { session_id: r.session_id }
}

export async function getWizardSession(sessionId: string): Promise<WizardSessionDocumentJson> {
  const enc = encodeURIComponent(sessionId)
  const r = await apiGetJson<{
    ok?: boolean
    session?: WizardSessionDocumentJson
    error?: string
  }>(`/api/blueprints/wizard/session/${enc}`)
  if (!r.ok || !r.session) {
    throw new Error(r.error || 'getWizardSession failed')
  }
  return r.session
}

export async function putWizardSession(
  sessionId: string,
  session: WizardSessionDocumentJson,
): Promise<void> {
  const enc = encodeURIComponent(sessionId)
  const r = await apiPutJson<{ ok?: boolean; error?: string }>(
    `/api/blueprints/wizard/session/${enc}`,
    session,
  )
  if (!r.ok) {
    throw new Error(r.error || 'putWizardSession failed')
  }
}

export type WizardRefineResponse = {
  ok?: boolean
  text?: string
  session?: WizardSessionDocumentJson
  error?: string
  detail?: string
  model?: string
  usage?: Record<string, unknown>
  routing?: Record<string, unknown>
}

export async function postWizardRefine(
  sessionId: string,
  body: { provider: string; model?: string; refine?: boolean },
): Promise<WizardRefineResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardRefineResponse>(`/api/blueprints/wizard/session/${enc}/refine`, body)
}

export type WizardInterpretResponse = {
  ok?: boolean
  interpretation?: Record<string, unknown>
  session?: WizardSessionDocumentJson
  error?: string
  detail?: string
  model?: string
  usage?: Record<string, unknown>
  routing?: Record<string, unknown>
}

export async function postWizardInterpret(
  sessionId: string,
  body: { provider: string; model?: string; refine?: boolean },
): Promise<WizardInterpretResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardInterpretResponse>(`/api/blueprints/wizard/session/${enc}/interpret`, body)
}

export type WizardClarifySuggestResponse = {
  ok?: boolean
  questions?: unknown[]
  error?: string
  detail?: string
  model?: string
  usage?: Record<string, unknown>
  routing?: Record<string, unknown>
}

export async function postWizardClarifySuggest(
  sessionId: string,
  body: {
    deterministic_questions: unknown[]
    use_llm: boolean
    provider?: string
    model?: string
    refine?: boolean
  },
): Promise<WizardClarifySuggestResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardClarifySuggestResponse>(
    `/api/blueprints/wizard/session/${enc}/clarify-suggest`,
    body,
  )
}

export type WizardCreateRepoResponse = {
  ok?: boolean
  html_url?: string
  session?: WizardSessionDocumentJson
  error?: string
  detail?: string
  status?: number
  save_error?: string
}

export async function postWizardCreateRepo(
  sessionId: string,
  body: { confirm: boolean },
): Promise<WizardCreateRepoResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardCreateRepoResponse>(
    `/api/blueprints/wizard/session/${enc}/create-repo`,
    body,
  )
}

export type WizardGenerateArtifactsResponse = {
  ok?: boolean
  session?: WizardSessionDocumentJson
  error?: string
  detail?: string
  /** Reserved for partial-failure / warning surfaces (server may omit). */
  warnings?: string[]
  failed_artifact_keys?: string[]
  model?: string
  usage?: Record<string, unknown>
  routing?: Record<string, unknown>
}

export async function postWizardGenerateArtifacts(
  sessionId: string,
  body: {
    provider: string
    model?: string
    refine?: boolean
    artifact?: string | null
    artifact_bundle?:
      | 'planning'
      | 'engineering'
      | 'all'
      | 'execution'
      | 'complete'
      | 'full_stack'
    artifact_keys?: string[]
  },
): Promise<WizardGenerateArtifactsResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardGenerateArtifactsResponse>(
    `/api/blueprints/wizard/session/${enc}/generate-artifacts`,
    body,
  )
}

export type WizardArtifactReviewResponse = {
  ok?: boolean
  session?: WizardSessionDocumentJson
  error?: string
  detail?: string
}

export async function postWizardArtifactReview(
  sessionId: string,
  body: {
    action: ArtifactReviewApiAction
    artifact_key?: string
    artifact_keys?: string[]
    feedback?: string
  },
): Promise<WizardArtifactReviewResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardArtifactReviewResponse>(
    `/api/blueprints/wizard/session/${enc}/artifact-review`,
    body,
  )
}

export type WizardArtifactRecheckResponse = {
  ok?: boolean
  session?: WizardSessionDocumentJson
  recheck_summary?: Record<string, unknown>
  /** When true, recheck was computed but not persisted (no `session` in response). */
  dry_run?: boolean
  error?: string
}

export async function postWizardArtifactRecheck(
  sessionId: string,
  body: { dry_run?: boolean } & Record<string, unknown> = {},
): Promise<WizardArtifactRecheckResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardArtifactRecheckResponse>(
    `/api/blueprints/wizard/session/${enc}/artifact-recheck`,
    body,
  )
}

export type WizardArtifactExportResponse = {
  ok?: boolean
  markdown?: string
  error?: string
  detail?: string
}

export async function postWizardArtifactExport(
  sessionId: string,
  body: { artifact_keys: string[] },
): Promise<WizardArtifactExportResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardArtifactExportResponse>(
    `/api/blueprints/wizard/session/${enc}/artifact-export`,
    body,
  )
}

export type WizardCursorLaunchPackPreviewResponse = {
  ok?: boolean
  manifest?: Record<string, unknown>
  files?: { path: string; kind: string; size: number }[]
  warnings?: string[]
  error?: string
  artifact_keys?: string[]
}

export async function postWizardCursorLaunchPackPreview(
  sessionId: string,
  body: { artifact_keys: string[]; closure_options?: string[]; strict_approval?: boolean },
): Promise<WizardCursorLaunchPackPreviewResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardCursorLaunchPackPreviewResponse>(
    `/api/blueprints/wizard/session/${enc}/cursor-launch-pack/preview`,
    body,
  )
}

export type WizardCursorLaunchPackExportResponse = {
  ok?: boolean
  export_path_relative?: string
  file_count?: number
  filename?: string
  content_base64?: string
  byte_length?: number
  /** `inline` — base64 in JSON; `stream` — use ``download_path`` with GET (large zips). */
  download_mode?: 'inline' | 'stream'
  download_token?: string
  download_path?: string
  warnings?: string[]
  error?: string
  detail?: string
  artifact_keys?: string[]
}

export async function postWizardCursorLaunchPackExport(
  sessionId: string,
  body: {
    artifact_keys: string[]
    closure_options?: string[]
    destination: 'workspace' | 'download'
    relative_path?: string
    /** When true with ``destination: download``, always use staged file + GET (not base64). */
    stream?: boolean
    /** Block export/preview if any expanded slice is not approved or locked. */
    strict_approval?: boolean
  },
): Promise<WizardCursorLaunchPackExportResponse> {
  const enc = encodeURIComponent(sessionId)
  return apiPostJson<WizardCursorLaunchPackExportResponse>(
    `/api/blueprints/wizard/session/${enc}/cursor-launch-pack/export`,
    body,
  )
}

export type WizardTelemetryBody = {
  event: string
  session_id?: string
  step_index?: number
  mission_mode?: string
}

/** Opt-in: server must enable ``LENSES_BLUEPRINTS_WIZARD_TELEMETRY``; client uses ``VITE_BLUEPRINTS_WIZARD_TELEMETRY``. */
export async function postWizardTelemetry(
  body: WizardTelemetryBody,
): Promise<{ ok?: boolean; error?: string }> {
  return apiPostJson<{ ok?: boolean; error?: string }>('/api/blueprints/wizard/telemetry', body)
}
