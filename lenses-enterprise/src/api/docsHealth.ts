import { apiGetJson, apiPostJson } from './http'

export type DocsHealthScoreSub = {
  weight?: number
  value?: number
  penalty_sum?: number
}

export type DocsHealthScore = {
  value?: number
  scale_max?: number
  finding_count?: number
  sub_scores?: Record<string, DocsHealthScoreSub>
  weights?: Record<string, number>
  formula?: string
  sum_based_score?: number
  potential_value_if_all_findings_cleared?: number
  potential_delta_if_resolved?: number
  total_expected_recovery_points?: number
}

export type DocsHealthRunSummary = {
  id?: string
  started_at?: string
  finished_at?: string
  finding_count?: number
  score?: number
  critical_open_count?: number
}

export type ContractStatus = {
  mode?: string
  contract_path?: string | null
  uses_convention_defaults?: boolean
  legacy_contract?: boolean
}

export type InventorySummary = {
  id?: string
  updated_at?: string
  document_count?: number | null
  by_doc_type?: Record<string, number>
  by_knowledge_category?: Record<string, number>
  link_edge_count?: number
  partial?: boolean
}

export type DocsHealthFinding = {
  id?: string
  title?: string
  summary?: string
  plain_language_summary?: string
  category?: string
  severity?: string
  confidence?: number
  scope?: string
  affected_paths?: string[]
  /** Alias used by some scan payloads (same paths as affected_paths). */
  affected_files?: string[]
  why_it_matters?: string
  score_impact?: number
  expected_score_impact?: number
  /** Which score sub-area this finding touches (scanner). */
  score_area?: string
  fixability?: string
  rule_code?: string
  suppressed?: boolean
  user_suppressed?: boolean
}

export type DocsHealthCluster = {
  id?: string
  label?: string
  finding_ids?: string[]
  primary_category?: string
  primary_severity?: string
  expected_score_gain_if_cleared?: number
  suggested_next?: string
}

export type DocsHealthClusterSuppression = {
  cluster_id?: string
  reason?: string
  suppressed_at?: string
  run_id?: string | null
}

export type DocsHealthFindingSuppression = {
  finding_id?: string
  reason?: string
  mode?: string
  review_at?: string | null
  run_id?: string | null
  suppressed_at?: string
}

export type DocsHealthClosureStatus = {
  complete?: boolean
  open_critical_or_major?: number
  suppressed_findings_in_view?: number
  open_manual_or_ticket_style?: number
  open_docs_work_items?: number
  notes?: string
}

export type DocsHealthRecentSessionRow = {
  session_id?: string
  status?: string
  display_name?: string | null
  cluster_label?: string | null
  verification_run_id?: string
  total_tokens?: number
  started_at?: string
  updated_at?: string
  last_model?: string | null
  closure_complete?: boolean
  verification_pipeline_ok?: boolean | null
  score_delta?: number | null
  href_session?: string
}

export type DocsHealthProjectPayload = {
  ok?: boolean
  project?: string
  project_docs_contract?: Record<string, unknown>
  contract_status?: ContractStatus
  required_doc_type_count?: number
  inventory_summary?: InventorySummary | null
  latest_inventory?: Record<string, unknown> | null
  docs_scan_run?: Record<string, unknown>
  contract?: Record<string, unknown>
  latest_run?: Record<string, unknown> | null
  run_history?: DocsHealthRunSummary[]
  run_compare?: {
    prior_run_id?: string
    score_delta?: number | null
    finding_count_delta?: number
  } | null
  work_items?: {
    id?: string
    title?: string
    status?: string
    project?: string
    finding_id?: string
    severity?: string
    kind?: string
    source?: string
    tasklet_run_id?: string
    tasklet_run_state?: string
    project_docs_health_href?: string
    finding_anchor?: string
    expected_score_impact?: number
    docs_health_session_href?: string
    project_docs_health_master_href?: string
    workspace_md_href?: string
  }[]
  cluster_suppressions?: DocsHealthClusterSuppression[]
  finding_suppressions?: DocsHealthFindingSuppression[]
  closure_status?: DocsHealthClosureStatus | null
  recent_sessions?: DocsHealthRecentSessionRow[]
  /** Recent TaskletRun records for this repo (generic runtime lifecycle). */
  tasklet_runs?: Array<{
    id?: string
    state?: string
    stop_reason?: string | null
    updated_at?: string
    docs_health_session_id?: string
    tasklet_id?: string
    last_error?: string | null
  }>
  /** Count of TaskletRuns needing operator action (awaiting input/approval, stopped, failed, paused). */
  open_tasklet_followups?: number
}

export type DocsHealthBuiltinTasklet = {
  id?: string
  version?: number
  kind?: string
  label?: string
  executor?: string
  schema_version?: number
  description?: string
  sandbox?: string
}

export type DocsHealthWorkspaceSummary = {
  ok?: boolean
  projects?: {
    project: string
    last_score?: number | null
    last_finding_count?: number | null
    critical_open_findings?: number | null
    open_docs_work_items?: number
    /** Actionable TaskletRun follow-ups (runtime), not scan debt rows. */
    open_tasklet_followups?: number
    needs_attention?: boolean
    has_docs_contract_file?: boolean
    markdown_document_count?: number | null
    last_docs_inventory_at?: string | null
    last_score_delta?: number | null
  }[]
  active_sessions_estimate?: number
  live_docs_health_sessions?: DocsHealthLiveSessionRow[]
  projects_with_contract_file?: number
  projects_with_inventory?: number
  builtin_tasklets?: DocsHealthBuiltinTasklet[]
  rollup?: {
    average_last_score?: number | null
    projects_with_critical_open_findings?: number
    open_docs_work_items_total?: number
    open_tasklet_followups_total?: number
    estimated_llm_tokens_in_flight?: number
    projects_with_recent_score_gain?: number
  }
}

export function getDocsHealthWorkspaceSummary() {
  return apiGetJson<DocsHealthWorkspaceSummary>('/api/docs-health/summary')
}

export function getDocsHealthWorkItems() {
  return apiGetJson<{ ok?: boolean; work_items?: DocsHealthProjectPayload['work_items'] }>(
    '/api/docs-health/work-items',
  )
}

export function getProjectDocsHealth(projectSlug: string, opts?: { fullInventory?: boolean }) {
  const enc = encodeURIComponent(projectSlug)
  const q = opts?.fullInventory === true ? '?full_inventory=1' : ''
  return apiGetJson<DocsHealthProjectPayload>(`/api/project/${enc}/docs-health${q}`)
}

export function postProjectDocsHealth(projectSlug: string, body: Record<string, unknown>) {
  const enc = encodeURIComponent(projectSlug)
  return apiPostJson<Record<string, unknown>>(`/api/project/${enc}/docs-health`, body)
}

export type DocsHealthModelRoutingSlotPreview = {
  label?: string
  primary_provider?: string | null
  primary_model?: string
  provider_chain?: string[]
  chain_with_models?: Array<{ provider?: string; model?: string }>
  capability_id?: string
}

export type DocsHealthModelRoutingPreview = {
  slots?: Record<string, DocsHealthModelRoutingSlotPreview>
  default_cloud_provider?: string
  note?: string
}

/** Ranked excerpts from the project repo’s Markdown (deterministic keyword + path search). */
export type DocsHealthRepoMdContext = {
  repository_label?: string | null
  query_terms?: string[]
  hits?: Array<{
    path?: string
    relevance_score?: number
    excerpt?: string
    match_terms?: string[]
    /** Present when the file is a finding’s affected_path. */
    source?: string
  }>
  scanned_file_count?: number
  ranked_file_count?: number
  note?: string
}

/** Session cluster: deterministic scan findings vs proposed markdown patch (API-enriched). */
export type DocsHealthRemediationScope = {
  cluster_label?: string | null
  cluster_id?: string | null
  finding_count?: number
  distinct_affected_paths?: string[]
  distinct_path_count?: number
  rules_breakdown?: Record<string, number>
  rules_breakdown_list?: Array<{ rule_code?: string; count?: number }>
  sample_findings?: Array<{
    id?: string
    title?: string
    summary?: string
    rule_code?: string
    severity?: string
    affected_paths?: string[]
  }>
  agent_intent?: string
  proposed_patch_path?: string | null
  proposed_patch_kind?: string | null
  unified_diff_excerpt?: string | null
  before_after?: {
    path?: string
    before_excerpt?: string
    after_excerpt?: string
  } | null
  /** Markdown files in the project repository relevant to these findings (search, not LLM). */
  repo_md_context?: DocsHealthRepoMdContext
  note?: string
}

export type DocsHealthSessionHeaderStats = {
  elapsed_seconds?: number | null
  status?: string
  active_model?: string | null
  /** Last LLM response model id recorded on the session (when available). */
  last_model_id?: string | null
  active_slot?: string | null
  /** Provider chosen on the last model call (from agent runtime). */
  last_provider?: string | null
  total_tokens?: number
  prompt_tokens?: number
  completion_tokens?: number
  commands_run?: number
  files_changed?: number
  verification?: { ok?: boolean; detail?: string; layer?: string } | null
  verification_pipeline?: { ok?: boolean; detail?: string; layer?: string } | null
  score_delta?: number | null
  baseline_score?: number | null
  updated_at?: string
  /** Planned provider + configured main_models id per capability (no network; local-first dispatch). */
  model_routing_preview?: DocsHealthModelRoutingPreview
}

export type DocsHealthSessionEvent = {
  type?: string
  ts?: string
  title?: string
  body?: string
  path?: string
  unified?: string
  ok?: boolean
  detail?: string
  layer?: string
  pipeline?: unknown
  snapshot?: unknown
  steps?: string[]
  last_model?: string
  choices?: { id?: string; label?: string }[]
  requires_reply?: boolean
  prompt?: string
  paths?: string[]
  hint?: string
  cmd?: string
  why?: string
  status?: string
  duration_ms?: number
  stdout_summary?: string
  raw_output?: string
  summary?: string
  detail_raw?: string
  score?: number
  finding_count?: number
  run_id?: string
  score_delta?: number
  baseline_score?: number
  cluster_id?: string
  operation?: string
  bytes_written?: number
  choice_id?: string | null
  confirm?: boolean
}

export type DocsHealthSessionPayload = {
  id?: string
  display_name?: string
  status?: string
  started_at?: string
  updated_at?: string
  cancelled_at?: string
  events?: DocsHealthSessionEvent[]
  usage_session?: Record<string, unknown>
  proposed_patch?: { path?: string; content?: string }
  proposed_patch_kind?: string
  header_stats?: DocsHealthSessionHeaderStats
  /** Same as header_stats.model_routing_preview when present (convenience). */
  model_routing_preview?: DocsHealthModelRoutingPreview
  /** Finding scope + proposed change summary (server-computed). */
  remediation_scope?: DocsHealthRemediationScope
  baseline_score?: number | null
  cluster?: { label?: string; id?: string }
  run_id?: string
  cluster_id?: string
  suggested_git_branch?: string
  /** How suggested_git_branch was chosen (server: git_branch_policy resolver). */
  git_branch_policy?: { source?: string; trunk?: string; style?: string }
  knowledge_links?: Record<string, string>
  closure_status?: DocsHealthClosureStatus
  efficiency_metrics?: Record<string, unknown>
  verification_run_id?: string
  /** Tasklet / sandbox execution metadata (Docs Health remediation). */
  tasklet_run_id?: string
  /** TaskletRun state machine value (source of truth for lifecycle). */
  run_state?: string
  tasklet_run?: {
    id?: string
    state?: string
    stop_reason?: string | null
    event_seq?: number
    checkpoints?: unknown[]
    /** Docker sandbox lifecycle + last step outcome (from TaskletRun). */
    sandbox?: Record<string, unknown>
    sandbox_backend?: string | null
  }
  tasklet?: { id?: string; version?: number }
  /** Agent runtime session id (workspace `.lenses-local/agent-runtime/sessions/`) when bound to this remediation run. */
  agent_runtime_session_id?: string
  execution?: { step_backend?: string; resumable?: boolean }
  /** Run-scoped git worktree or isolated draft directory (drafts never touch source until apply). */
  scratch_workspace?: {
    ok?: boolean
    worktree_path?: string
    reused?: boolean
    source?: string
  }
  scratch_worktree?: { path?: string; preview_rel_path?: string; source?: string }
  patch_preview?: {
    artifact?: string
    apply_artifact?: string
    apply_ready?: boolean
  }
  apply_gate?: { status?: string; sha256?: string; notes?: string }
  scratch_discarded?: { ok?: boolean; discarded?: boolean; error?: string }
  artifact_manifest?: Array<{ name?: string; bytes?: number; updated_at?: string }>
  /** Per-step invocation metrics (server-recorded token deltas and wall time). */
  step_metrics?: Array<{
    step?: string
    prompt_tokens?: number
    completion_tokens?: number
    total_tokens?: number
    elapsed_ms?: number
    ts?: string
    gate?: 'awaiting_input' | 'awaiting_approval'
  }>
  /** Present when verification step finished; includes finding_diff vs prior scan. */
  completion_summary?: {
    verification_pipeline_ok?: boolean
    verification_run_id?: string
    finding_diff?: {
      resolved_from_prior_scan?: string[]
      new_since_prior_scan?: string[]
      reopened_findings?: string[]
    }
    findings_new_or_reopened?: { new?: string[]; reopened?: string[] }
    artifact_links?: Record<string, string>
  }
}

export type DocsHealthLiveSessionRow = {
  project?: string
  session_id?: string
  status?: string
  started_at?: string
  updated_at?: string
  total_tokens?: number
  prompt_tokens?: number
  completion_tokens?: number
  last_model?: string | null
  cluster_label?: string | null
  tasklet_run_id?: string
  tasklet_state?: string
  tasklet_stop_reason?: string | null
}

export function getDocsHealthLiveSessions() {
  return apiGetJson<{ ok?: boolean; sessions?: DocsHealthLiveSessionRow[] }>('/api/docs-health/live-sessions')
}

export function postDocsHealthSessionReply(
  projectSlug: string,
  body: { session_id: string; reply_text?: string; choice_id?: string; confirm?: boolean },
) {
  const enc = encodeURIComponent(projectSlug)
  return apiPostJson<{ ok?: boolean; session?: DocsHealthSessionPayload }>(`/api/project/${enc}/docs-health`, {
    op: 'session_reply',
    ...body,
  })
}

export function postDocsHealthSessionResume(projectSlug: string, body: { session_id: string }) {
  const enc = encodeURIComponent(projectSlug)
  return apiPostJson<{ ok?: boolean; session?: DocsHealthSessionPayload }>(`/api/project/${enc}/docs-health`, {
    op: 'session_resume',
    ...body,
  })
}

/** GET URL for Server-Sent Events stream (merged session payload, same as ``session_get``). */
export function docsHealthSessionEventsUrl(projectSlug: string, sessionId: string): string {
  const enc = encodeURIComponent(projectSlug)
  const sid = encodeURIComponent(sessionId)
  return `/api/project/${enc}/docs-health-session-events?session_id=${sid}`
}
