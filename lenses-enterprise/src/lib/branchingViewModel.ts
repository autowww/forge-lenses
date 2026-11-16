/**
 * Pure view helpers for GET /api/project/<name>/branching (schema_version 1).
 */

export type BranchingPolicy = {
  source?: string
  trunk?: string
  model?: string
  team_scale?: string
  topology?: string
  cicd_maturity?: string
  feature_prefix?: string
  fix_prefix?: string
  product_prefix?: string
  iter_prefix?: string
  spark_prefix?: string
  spike_prefix?: string
  release_prefix?: string
  hotfix_prefix?: string
  require_pr?: boolean
  required_approvals?: number
  require_green_checks?: boolean
  docs_health_style?: string
  lanes_enabled?: boolean
}

export type BranchingPayload = {
  ok?: boolean
  schema_version?: number
  project?: string
  policy?: BranchingPolicy
  current?: {
    branch?: string
    head_short?: string
    origin_url?: string
    is_git?: boolean
  }
  structure?: {
    branches?: { name?: string; category?: string; protected?: boolean; head_sha?: string; url?: string }[]
    branches_by_lane?: Record<string, { name?: string }[]>
    pull_requests?: {
      number?: number
      title?: string
      head_ref?: string
      base_ref?: string
      state?: string
      mergeable?: string
    }[]
    branch_protection?: { pattern?: string; required_reviews?: number }[]
    work_item_links?: unknown[]
  }
  recommendations?: Record<string, string>
  hints?: string[]
}

const TEAM_SCALE: Record<string, string> = {
  solo: 'Solo maintainer — minimal ceremony.',
  small: 'Small team — lightweight review habits.',
  team: 'Team tier — shared trunk with review and checks scaled to the profile.',
  'multi-team': 'Multi-team — stronger coordination and gatekeeping on the trunk.',
}

const TOPOLOGY: Record<string, string> = {
  single: 'Single repo (one integration surface).',
  polyrepo: 'Polyrepo or multi-repo workspace — align branch names with the owning repo.',
}

const CICD: Record<string, string> = {
  none: 'CI maturity not modeled as blocking in this profile.',
  standard: 'Standard CI — automated checks are part of the delivery habit.',
  advanced: 'Advanced CI — richer automation and enforcement expected.',
}

const RECOMMENDATION_TITLES: Record<string, string> = {
  charge_work: 'Charge and change work',
  backlog_lane_work: 'Backlog-driven work',
  ad_hoc_user_task: 'Ad-hoc tasks',
  exploration_spike: 'Exploration and spikes',
  hotfix: 'Hotfixes',
  release_hardening: 'Release hardening',
}

export function formatBranchingModel(model?: string): { title: string; code: string } {
  const code = (model || 'team_tier').trim() || 'team_tier'
  if (code === 'forge_lanes') {
    return {
      title: 'Forge lanes (product, iteration, spark, and related lane prefixes)',
      code,
    }
  }
  return {
    title: 'Team tier (protected trunk, short-lived branches, promotion through review)',
    code,
  }
}

export function glossTeamScale(scale?: string): string {
  const k = (scale || '').trim().toLowerCase()
  return TEAM_SCALE[k] || (k ? `Scale: ${k}.` : 'Scale not recorded.')
}

export function glossTopology(topology?: string): string {
  const k = (topology || '').trim().toLowerCase()
  return TOPOLOGY[k] || (k ? `Topology: ${k}.` : 'Topology not recorded.')
}

export function glossCicdMaturity(maturity?: string): string {
  const k = (maturity || '').trim().toLowerCase()
  return CICD[k] || (k ? `CI/CD posture: ${k}.` : 'CI/CD posture not recorded.')
}

export function formatTeamProfileSentence(policy: BranchingPolicy | undefined): string {
  if (!policy) return 'Team profile not loaded.'
  const parts = [
    glossTeamScale(policy.team_scale),
    glossTopology(policy.topology),
    glossCicdMaturity(policy.cicd_maturity),
  ]
  return parts.join(' ')
}

export function formatDocsHealthStyle(style?: string): string {
  const k = (style || '').trim().toLowerCase()
  if (k === 'legacy_docs_health' || k === 'legacy') {
    return 'Docs Health branches may use legacy naming; confirm before automation rewrites branch names.'
  }
  return 'Docs Health branches follow feature-prefixed topic branches (preferred).'
}

export type MergeGuardrailsView = {
  summary: string
  bullets: string[]
}

export function formatMergeGuardrails(policy: BranchingPolicy | undefined): MergeGuardrailsView {
  if (!policy) {
    return {
      summary: 'Merge guardrails were not loaded for this repository.',
      bullets: [],
    }
  }
  const pr = Boolean(policy.require_pr)
  const n = Math.max(0, Number(policy.required_approvals ?? 0))
  const green = Boolean(policy.require_green_checks)

  const bullets: string[] = []
  if (pr) {
    bullets.push('Integrations to the trunk go through a pull request (or equivalent merge review).')
  } else {
    bullets.push('Direct pushes to the trunk may be allowed in this profile; confirm on your host before bypassing review.')
  }
  if (n > 0) {
    bullets.push(`Human review: at least ${n} approval${n === 1 ? '' : 's'} expected before merge.`)
  } else {
    bullets.push('Approvals: none required by this resolved policy (host rules may still apply).')
  }
  if (green) {
    bullets.push('Quality gates: automated status checks must pass before merge.')
  } else {
    bullets.push('Quality gates: green checks are not modeled as blocking in this profile (CI may still run on the host).')
  }

  const summary = pr
    ? 'This profile expects governed promotion to the trunk with review and explicit quality signals.'
    : 'This profile is permissive about direct integration; pair it with host-level protections if you need hard gates.'

  return { summary, bullets }
}

export type RecommendationRow = {
  key: string
  title: string
  body: string
}

export function recommendationRows(recommendations: Record<string, string> | undefined): RecommendationRow[] {
  if (!recommendations) return []
  const keys = Object.keys(recommendations).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }))
  return keys.map((key) => ({
    key,
    title: RECOMMENDATION_TITLES[key] || humanizeKey(key),
    body: recommendations[key] || '',
  }))
}

function humanizeKey(key: string): string {
  return key
    .split('_')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export type BranchNamingRow = {
  lane: string
  prefix: string
  usage: string
}

const LANE_USAGE: Record<string, string> = {
  Feature: 'User-visible capability or structured product change.',
  Fix: 'Defect repair and small corrective work.',
  Product: 'Longer-lived product line or initiative branch (Forge lanes).',
  Iteration: 'Time-boxed iteration or charge lane parent (Forge lanes).',
  Spark: 'Risky or experimental execution within an iteration (Forge lanes).',
  Spike: 'Time-boxed discovery; prefer read-only exploration when possible.',
  Release: 'Release candidate or version-stabilization line when policy calls for it.',
  Hotfix: 'Production-urgent correction path.',
}

export function branchNamingRows(policy: BranchingPolicy | undefined): BranchNamingRow[] {
  if (!policy) return []
  const pairs: [string, keyof BranchingPolicy][] = [
    ['Feature', 'feature_prefix'],
    ['Fix', 'fix_prefix'],
    ['Product', 'product_prefix'],
    ['Iteration', 'iter_prefix'],
    ['Spark', 'spark_prefix'],
    ['Spike', 'spike_prefix'],
    ['Release', 'release_prefix'],
    ['Hotfix', 'hotfix_prefix'],
  ]
  return pairs.map(([lane, field]) => ({
    lane,
    prefix: String(policy[field] ?? ''),
    usage: LANE_USAGE[lane] || '',
  }))
}

export function isForgeLanesModel(policy: BranchingPolicy | undefined): boolean {
  const m = (policy?.model || '').trim().toLowerCase()
  return m === 'forge_lanes' || Boolean(policy?.lanes_enabled)
}

/** Matches backend `project_branching._lane_bucket_template` ordering for stable charts. */
export const LANE_CHART_ORDER: readonly string[] = [
  'main',
  'product',
  'iter',
  'spark',
  'spike',
  'release',
  'hotfix',
  'feature',
  'fix',
  'topic',
  'other',
]

export type LaneVolumeRow = { lane: string; count: number }

export function laneVolumesForChart(
  branches_by_lane: Record<string, { name?: string }[] | unknown[]> | undefined,
): LaneVolumeRow[] {
  const raw = branches_by_lane && typeof branches_by_lane === 'object' ? branches_by_lane : {}
  const keys = new Set<string>([...LANE_CHART_ORDER, ...Object.keys(raw)])
  const ordered = [...LANE_CHART_ORDER.filter((k) => keys.has(k)), ...[...keys].filter((k) => !LANE_CHART_ORDER.includes(k)).sort()]
  return ordered.map((lane) => {
    const rows = raw[lane]
    const count = Array.isArray(rows) ? rows.length : 0
    return { lane, count }
  })
}

export type CategoryCountRow = { category: string; count: number }

export function categoryMixFromBranches(
  branches: { name?: string; category?: string }[] | undefined,
): CategoryCountRow[] {
  if (!Array.isArray(branches) || !branches.length) return []
  const tally: Record<string, number> = {}
  for (const b of branches) {
    if (!b || typeof b !== 'object') continue
    const c = String(b.category || 'other').trim() || 'other'
    tally[c] = (tally[c] || 0) + 1
  }
  return Object.entries(tally)
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count || a.category.localeCompare(b.category))
}

export type PolicyResolutionStep = {
  id: string
  label: string
  detail: string
}

export const POLICY_RESOLUTION_STEPS: readonly PolicyResolutionStep[] = [
  {
    id: 'branching_yml',
    label: 'forge/branching.yml',
    detail: 'Explicit lanes, prefixes, and promotion rules when present.',
  },
  {
    id: 'branching_profile',
    label: 'docs/process/branching-profile.md',
    detail: 'Heuristic lane detection from prose when no branching.yml.',
  },
  {
    id: 'forge_config',
    label: 'forge/forge.config.yaml',
    detail: 'Team scale and ceremony mapped to a team-tier profile.',
  },
  {
    id: 'blueprints_repo',
    label: 'blueprints/…/BRANCHING-STRATEGY.md',
    detail: 'Methodology defaults shipped inside this repository.',
  },
  {
    id: 'blueprints_workspace',
    label: 'workspace/blueprints/…/BRANCHING-STRATEGY.md',
    detail: 'Shared blueprints at the workspace root (meta-repo).',
  },
  {
    id: 'fallback',
    label: 'Built-in fallback',
    detail: 'Conservative team-tier defaults when nothing else matches.',
  },
]

export function matchPolicyResolutionStepIndex(source: string | undefined): number {
  const s = (source || '').trim().toLowerCase()
  if (!s) return POLICY_RESOLUTION_STEPS.length - 1
  if (s.includes('forge/branching.yml') || s.endsWith('branching.yml')) return 0
  if (s.includes('branching-profile.md')) return 1
  if (s.includes('forge.config.yaml') || s.includes('forge/forge.config')) return 2
  if (s.includes('workspace/') && s.includes('branching-strategy')) return 4
  if (s.includes('branching-strategy') || s.includes('blueprints')) return 3
  return POLICY_RESOLUTION_STEPS.length - 1
}

export type PayloadSchemaCard = {
  key: string
  title: string
  body: string
}

export const PAYLOAD_SCHEMA_CARDS: readonly PayloadSchemaCard[] = [
  {
    key: 'policy',
    title: 'policy',
    body: 'Resolved trunk, model, team profile, prefix map, merge guardrails, Docs Health branch style.',
  },
  {
    key: 'current',
    title: 'current',
    body: 'Local scan: checked-out branch, short HEAD, origin remote, whether git metadata was present.',
  },
  {
    key: 'structure',
    title: 'structure',
    body: 'Branches, lane buckets, pull requests, branch protection — richer when repo-workflow fixtures exist.',
  },
  {
    key: 'recommendations',
    title: 'recommendations',
    body: 'Short operator and agent branch-choice hints keyed by intent.',
  },
  {
    key: 'hints',
    title: 'hints',
    body: 'Workspace-level notes such as missing repo-workflow overlay files.',
  },
]
