import { apiGetJson } from './http'

export type WorkspaceMdIndexEntry = {
  rel_path: string
  category: string
}

export type WorkspaceMdIndexPayload = {
  ok?: boolean
  files?: WorkspaceMdIndexEntry[]
  truncated?: boolean
}

export async function getWorkspaceMdIndex(): Promise<WorkspaceMdIndexPayload> {
  return apiGetJson<WorkspaceMdIndexPayload>('/api/workspace-md-index')
}
