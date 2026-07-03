import type { ForgeWorkflowStageStatus } from '../forgesdlc-kitchensink/forgeRunTypes'

export type FoundryPhase = {
  id: string
  label: string
  status: ForgeWorkflowStageStatus
  detail?: string
}

export type FoundryRun = {
  ok?: boolean
  id?: string
  status?: string
  goal?: string
  target?: string
  level?: string
  execution_mode?: string
  project?: string
  phases?: FoundryPhase[]
  plan?: Record<string, unknown>
  final_status?: string
  assay_ok?: boolean | null
  assay?: Record<string, unknown>
  proof?: Record<string, unknown>
  promoted?: boolean
  approved?: boolean
  created_at?: string
  updated_at?: string
  error?: string
}

export type FoundryRunsList = {
  ok?: boolean
  runs?: FoundryRun[]
}

export type FoundryPlan = {
  ok?: boolean
  goal?: string
  level?: string
  units?: {
    id?: string
    summary?: string
    allowed_files?: string[]
    verification?: string
  }[]
  error?: string
  reason?: string
}

export type FoundryCapabilities = {
  ok?: boolean
  ladder?: Record<string, { status?: string; label?: string }>
}

export type FoundryIntake = {
  ok?: boolean
  goal?: string
  level?: string
  target?: string
  project?: string
  source?: string
}
