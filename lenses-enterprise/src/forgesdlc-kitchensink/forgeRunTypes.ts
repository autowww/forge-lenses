/**
 * Shared types for Forge enterprise run surfaces (Lenses Studio + synced consumers).
 * Canonical source: this file; sync via `npm run sync-kitchensink-react` in lenses-enterprise.
 */

export type ForgeWorkflowStageStatus =
  | 'not_started'
  | 'in_progress'
  | 'waiting'
  | 'blocked'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'cancelled'

export type ForgeStatusBannerVariant =
  | 'cancelled'
  | 'failed'
  | 'awaiting_approval'
  | 'awaiting_input'
  | 'verified'
  | 'info'
  | 'success'
  | 'warning'

export type ForgeBadgeTone = 'neutral' | 'success' | 'warning' | 'danger' | 'info'
