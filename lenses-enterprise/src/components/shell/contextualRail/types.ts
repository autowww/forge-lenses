/**
 * Right-hand contextual rail — action-oriented sections, not a duplicate sitemap.
 * Built from route + workspace state in `buildContextualRailModel`.
 */

export type ContextualRailLink = {
  label: string
  to?: string
  href?: string
  external?: boolean
  /** Primary CTAs render with stronger emphasis in the rail UI. */
  variant?: 'primary' | 'default'
}

export type ContextualRailStatus = {
  label: string
  value: string
  tone?: 'ok' | 'warn' | 'muted'
}

export type ContextualRailRecovery = {
  title: string
  body: string
  actions: ContextualRailLink[]
  /** When set, EvidenceRail shows a primary control that calls workspace.refresh(). */
  showWorkspaceRetry?: boolean
  /** Collapsible diagnostics (HTTP body, codes) — not shown inline. */
  technicalDetail?: string | null
}

export type ContextualRailModel = {
  title: string
  lead: string
  /** When false, the conversational lead is omitted (dense utility pages). Default: show. */
  showLead?: boolean
  /** Workspace scan, scope, or access snapshot. */
  status?: ContextualRailStatus
  /** When `/api/workspace-state` failed; shown above route recovery. */
  workspaceAlert?: ContextualRailRecovery
  /** Route-specific empty or invalid state (e.g. missing preview path). */
  recovery?: ContextualRailRecovery
  /** Next best actions for this screen. */
  actions: ContextualRailLink[]
  /** Supporting links that fit the current task (not generic nav dumps). */
  related?: ContextualRailLink[]
  /** Optional developer shortcut (e.g. raw workspace JSON). */
  devLink?: { label: string; href: string }
}
