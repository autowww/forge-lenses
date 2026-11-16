import { apiGetJson, apiPostJson } from './http'

export type AuthStatus = {
  expected_login: string
  expected_configured: boolean
  session_login: string | null
  session_ok: boolean
  access_policy_enforced: boolean
  workspace_super_admin: boolean
  sites_with_allowlisted_actions: string[]
  action_keys_by_site: Record<string, string[]>
}

export function getAuthStatus(): Promise<AuthStatus> {
  return apiGetJson<AuthStatus>('/api/auth/status')
}

export function postGithubToken(token: string): Promise<{ ok?: boolean; error?: string }> {
  return apiPostJson('/api/auth/github', { token })
}

export function postLogout(): Promise<{ ok?: boolean }> {
  return apiPostJson('/api/auth/logout', {})
}
