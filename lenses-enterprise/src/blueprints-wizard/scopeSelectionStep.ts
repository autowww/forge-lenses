/**
 * Step 7 — Scope selection. `payload.scopeSelection` ↔ extended `wizard_domain.scope_spec`.
 */

import type { ClosureOption, ScopeBoundary, ScopeSpecJson } from './wizardDomainTypes'
import { CLOSURE_OPTIONS, SCOPE_BOUNDARIES } from './wizardDomainTypes'
import { normalizeClosureOptionsList } from './wizardDomainNormalize'

export type ScopeSelectionPayloadV1 = {
  scopeBoundary: ScopeBoundary
  milestoneRef: string
  wbePath: string
  capabilityLabel: string
  teamLabel: string
  /** Newline or semicolon separated in UI; normalized to `scope_spec.repo_paths`. */
  repoPathsText: string
  recheckIssueRefs: string
  closureOptions: ClosureOption[]
  /** UI: advanced section expanded (persisted for continuity). */
  advancedScopeExpanded: boolean
}

function isScopeBoundary(v: unknown): v is ScopeBoundary {
  return typeof v === 'string' && (SCOPE_BOUNDARIES as readonly string[]).includes(v)
}

function parseRepoPathsText(text: string): string[] {
  const parts = text
    .split(/[\n,;]+/)
    .map((s) => s.trim())
    .filter(Boolean)
  return parts.slice(0, 64).map((p) => p.slice(0, 2000))
}

export const SCOPE_BOUNDARY_UI: Record<ScopeBoundary, { title: string; plain: string }> = {
  full_plan: { title: 'Full plan', plain: 'Entire initiative scope.' },
  milestone: { title: 'Milestone', plain: 'One milestone or checkpoint.' },
  wbe_subtree: { title: 'WBE subtree', plain: 'A branch of the work breakdown.' },
  capability: { title: 'Capability / feature', plain: 'A named capability or feature slice.' },
  team_slice: { title: 'Team-owned slice', plain: 'Owned by a specific team.' },
  repo_path: { title: 'Repo path slice', plain: 'Specific paths in the repository.' },
  recheck_subset: {
    title: 'Stale / conflicting subset (recheck)',
    plain: 'Issues called out by a recheck pass (described here).',
  },
}

export const CLOSURE_OPTION_UI: Record<ClosureOption, string> = {
  exact_only: 'Exact only',
  include_required_upstream: 'Include required upstream',
  include_shared_contracts: 'Include shared contracts',
  include_downstream_impacted: 'Include downstream impacted',
  include_verification_artifacts: 'Include verification artifacts',
}

export function emptyScopeSelectionPayload(): ScopeSelectionPayloadV1 {
  return {
    scopeBoundary: 'full_plan',
    milestoneRef: '',
    wbePath: '',
    capabilityLabel: '',
    teamLabel: '',
    repoPathsText: '',
    recheckIssueRefs: '',
    closureOptions: [],
    advancedScopeExpanded: false,
  }
}

export function scopeSelectionFromScopeSpec(spec: ScopeSpecJson): ScopeSelectionPayloadV1 {
  const boundary = isScopeBoundary(spec.scope_boundary) ? spec.scope_boundary : 'full_plan'
  const repoText = (spec.repo_paths ?? []).join('\n')
  const closure = normalizeClosureOptionsList(spec.closure_options)
  return {
    scopeBoundary: boundary,
    milestoneRef: spec.milestone_ref ?? '',
    wbePath: spec.wbe_path ?? '',
    capabilityLabel: spec.capability_label ?? '',
    teamLabel: spec.team_label ?? '',
    repoPathsText: repoText,
    recheckIssueRefs: spec.recheck_issue_refs ?? '',
    closureOptions: closure,
    advancedScopeExpanded: false,
  }
}

export function parseScopeSelectionFromPayload(
  payload: Record<string, unknown>,
  spec: ScopeSpecJson,
): ScopeSelectionPayloadV1 {
  const base = scopeSelectionFromScopeSpec(spec)
  const raw = payload.scopeSelection
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return base
  }
  const o = raw as Record<string, unknown>
  const boundary = isScopeBoundary(o.scopeBoundary) ? o.scopeBoundary : base.scopeBoundary
  return {
    scopeBoundary: boundary,
    milestoneRef: typeof o.milestoneRef === 'string' ? o.milestoneRef : base.milestoneRef,
    wbePath: typeof o.wbePath === 'string' ? o.wbePath : base.wbePath,
    capabilityLabel: typeof o.capabilityLabel === 'string' ? o.capabilityLabel : base.capabilityLabel,
    teamLabel: typeof o.teamLabel === 'string' ? o.teamLabel : base.teamLabel,
    repoPathsText: typeof o.repoPathsText === 'string' ? o.repoPathsText : base.repoPathsText,
    recheckIssueRefs: typeof o.recheckIssueRefs === 'string' ? o.recheckIssueRefs : base.recheckIssueRefs,
    closureOptions: Array.isArray(o.closureOptions)
      ? normalizeClosureOptionsList(o.closureOptions)
      : base.closureOptions,
    advancedScopeExpanded: o.advancedScopeExpanded === true,
  }
}

export function clampScopeSelectionPayload(s: ScopeSelectionPayloadV1 | undefined): ScopeSelectionPayloadV1 {
  if (!s) return emptyScopeSelectionPayload()
  return {
    scopeBoundary: isScopeBoundary(s.scopeBoundary) ? s.scopeBoundary : 'full_plan',
    milestoneRef: s.milestoneRef.slice(0, 2000),
    wbePath: s.wbePath.slice(0, 4000),
    capabilityLabel: s.capabilityLabel.slice(0, 2000),
    teamLabel: s.teamLabel.slice(0, 2000),
    repoPathsText: s.repoPathsText.slice(0, 12000),
    recheckIssueRefs: s.recheckIssueRefs.slice(0, 8000),
    closureOptions: normalizeClosureOptionsList(s.closureOptions),
    advancedScopeExpanded: s.advancedScopeExpanded === true,
  }
}

/** Merge scope step fields into normalized scope_spec (summary/constraints from understanding stay in caller). */
export function scopeSpecFromSelection(
  base: ScopeSpecJson,
  sel: ScopeSelectionPayloadV1,
): ScopeSpecJson {
  const c = clampScopeSelectionPayload(sel)
  return {
    ...base,
    scope_boundary: c.scopeBoundary,
    milestone_ref: c.milestoneRef,
    wbe_path: c.wbePath,
    capability_label: c.capabilityLabel,
    team_label: c.teamLabel,
    repo_paths: parseRepoPathsText(c.repoPathsText),
    recheck_issue_refs: c.recheckIssueRefs,
    closure_options: c.closureOptions.filter((x) =>
      (CLOSURE_OPTIONS as readonly string[]).includes(x),
    ) as ClosureOption[],
  }
}

export type ScopeSelectionFieldErrors = {
  scopeBoundary?: string
  detail?: string
}

/** Require detail hints when boundary implies them (soft: one combined message). */
export function validateScopeSelectionForNext(s: ScopeSelectionPayloadV1): {
  ok: boolean
  errors: ScopeSelectionFieldErrors
} {
  const errors: ScopeSelectionFieldErrors = {}
  if (!isScopeBoundary(s.scopeBoundary)) {
    errors.scopeBoundary = 'Pick a scope boundary.'
  }
  const c = clampScopeSelectionPayload(s)
  if (c.scopeBoundary === 'milestone' && !c.milestoneRef.trim()) {
    errors.detail = 'Name or reference the milestone, or switch boundary.'
  }
  if (c.scopeBoundary === 'wbe_subtree' && !c.wbePath.trim()) {
    errors.detail = 'Describe the WBE path, or switch boundary.'
  }
  if (c.scopeBoundary === 'capability' && !c.capabilityLabel.trim()) {
    errors.detail = 'Name the capability or feature, or switch boundary.'
  }
  if (c.scopeBoundary === 'team_slice' && !c.teamLabel.trim()) {
    errors.detail = 'Name the owning team, or switch boundary.'
  }
  if (c.scopeBoundary === 'repo_path' && !parseRepoPathsText(c.repoPathsText).length) {
    errors.detail = 'Add at least one repo path, or switch boundary.'
  }
  if (c.scopeBoundary === 'recheck_subset' && !c.recheckIssueRefs.trim()) {
    errors.detail = 'Describe the recheck issues or stale subset, or switch boundary.'
  }
  return { ok: Object.keys(errors).length === 0, errors }
}

export function formatScopeSelectionForStepNote(s: ScopeSelectionPayloadV1): string {
  const c = clampScopeSelectionPayload(s)
  const lines: string[] = []
  lines.push(`Scope boundary: ${SCOPE_BOUNDARY_UI[c.scopeBoundary]?.title ?? c.scopeBoundary}`)
  if (c.milestoneRef.trim()) lines.push(`Milestone: ${c.milestoneRef.trim()}`)
  if (c.wbePath.trim()) lines.push(`WBE path: ${c.wbePath.trim()}`)
  if (c.capabilityLabel.trim()) lines.push(`Capability: ${c.capabilityLabel.trim()}`)
  if (c.teamLabel.trim()) lines.push(`Team: ${c.teamLabel.trim()}`)
  if (c.repoPathsText.trim()) lines.push(`Repo paths:\n${c.repoPathsText.trim()}`)
  if (c.recheckIssueRefs.trim()) lines.push(`Recheck / stale subset:\n${c.recheckIssueRefs.trim()}`)
  if (c.closureOptions.length) {
    lines.push(
      `Closure: ${c.closureOptions.map((x) => CLOSURE_OPTION_UI[x] ?? x).join('; ')}`,
    )
  }
  return lines.join('\n\n')
}
