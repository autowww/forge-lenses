import { apiGetJson } from './http'

export type WorkspaceChild = {
  name: string
  path?: string
  is_git?: boolean
  git?: Record<string, unknown>
  standards_compliance?: { score: number; tier: string }
}

export type ForgeHint = {
  repo_hint: string
  has_charge: boolean
  has_ember_logs: boolean
  has_versona: boolean
  has_journal: boolean
}

/** Per-site entry from workspace scan (`lenses/scan.py` / workspace-scan-contract). */
export type WorkspaceWebsite = {
  name: string
  path?: string
  firebase_json?: string
  hosting_public?: string
  firebase_site_id?: string
  preview_base?: string
  pages?: { path?: string; title?: string; h1?: string; label?: string }[]
  html_total?: number
  html_indexed?: number
  index_html_mtime?: number | null
  suggested_commands?: Record<string, string>
}

/** Written by Forge Fleet admin ``Test Fleet`` when ``FLEET_LENSES_WORKSPACE_ROOT`` points at this workspace. */
export type FleetTestAttention = {
  ok?: boolean
  headline?: string
  to?: string
  updated_at?: string
  samples?: unknown[]
  batch_id?: string
}

export type WorkspaceState = {
  workspace_root: string
  resolved_at?: string
  children: WorkspaceChild[]
  forge_hints?: ForgeHint[]
  websites?: WorkspaceWebsite[]
  wbs?: { rel_path: string; repo_hint?: string }[]
  roadmaps?: { rel_path: string; repo_hint?: string }[]
  toolset?: {
    root_scripts?: string[]
    script_cards?: { name: string; blurb: string }[]
    cursor_dir?: string
  }
  fleet_test_attention?: FleetTestAttention
}

export function getWorkspaceState(gitExtended = false): Promise<WorkspaceState> {
  const q = gitExtended ? '?git_extended=1' : ''
  return apiGetJson<WorkspaceState>(`/api/workspace-state${q}`)
}
