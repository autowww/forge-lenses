import { apiGetJson } from './http'

export type AutonomyMaturityComponents = {
  gate_definition?: number
  demonstrated_evidence?: number
  repeatability?: number
  operational_metrics?: number
}

export type AutonomyMaturitySignals = {
  forge_config_present?: boolean
  forge_config_assay_keys?: boolean
  cursor_rules_present?: boolean
  ci_present?: boolean
  tests_present?: boolean
}

export type AutonomyMaturityRunEvidence = {
  green_runs?: number
  levels?: Record<string, number>
  escalation_rate?: number | null
}

export type AutonomyMaturityProject = {
  ok?: boolean
  project?: string
  observed_level?: string
  observed_sublevel?: string | null
  observed_grade?: string
  claim?: string
  score?: number
  components?: AutonomyMaturityComponents
  weights?: Record<string, number>
  signals?: AutonomyMaturitySignals
  run_evidence?: AutonomyMaturityRunEvidence
  recommendations?: string[]
  note?: string
  error?: string
}

export type AutonomyMaturityOverviewRow = {
  project?: string
  score?: number
  observed_level?: string
  observed_sublevel?: string | null
  observed_grade?: string
  claim?: string
  recommendations?: string[]
}

export type AutonomyMaturityOverview = {
  ok?: boolean
  projects?: AutonomyMaturityOverviewRow[]
  count?: number
  note?: string
  error?: string
}

export function fetchAutonomyMaturityEnabled(): Promise<{ ok?: boolean; enabled?: boolean }> {
  return apiGetJson('/api/autonomy-maturity/enabled')
}

export function fetchAutonomyMaturityOverview(): Promise<AutonomyMaturityOverview> {
  return apiGetJson('/api/autonomy-maturity/overview')
}

export function fetchProjectAutonomyMaturity(name: string): Promise<AutonomyMaturityProject> {
  return apiGetJson(`/api/project/${encodeURIComponent(name)}/autonomy-maturity`)
}
