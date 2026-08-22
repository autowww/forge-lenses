import type { FleetTestAttention, WorkspaceChild, WorkspaceState } from '../../api/workspace'

export type AttentionCategory =
  | 'risk'
  | 'evidence_gap'
  | 'decision'
  | 'win'
  | 'dependency'
  | 'slip'
  /** New model ids from a URL-backed LLM catalog (Ollama / custom gateway) */
  | 'catalog'
  /** Forge Fleet admin ``Test Fleet`` host CPU probe summary */
  | 'fleet'

export type AttentionItem = {
  id: string
  category: AttentionCategory
  headline: string
  scopeLabel: string
  actionHint: string
  to?: string
  href?: string
}

function dirtyRepos(children: WorkspaceChild[]): WorkspaceChild[] {
  return children.filter(
    (c) =>
      c.is_git &&
      c.git &&
      typeof (c.git as { dirty?: boolean }).dirty !== 'undefined' &&
      (c.git as { dirty?: boolean }).dirty === true,
  )
}

function weakStandards(children: WorkspaceChild[]): WorkspaceChild[] {
  return children.filter((c) => {
    const sc = c.standards_compliance
    if (!sc || typeof sc.score !== 'number') return false
    return sc.score < 70 || sc.tier === 'minimal'
  })
}

/** Exception-style items derived from workspace scan (no separate news API yet). */
export function buildAttentionItems(state: WorkspaceState | null): AttentionItem[] {
  if (!state) return []
  const children = Array.isArray(state.children) ? state.children : []
  const gitChildren = children.filter((c) => c.is_git)
  const roadmaps = state.roadmaps ?? []
  const wbs = state.wbs ?? []
  const sites = state.websites ?? []

  const fta = state.fleet_test_attention as FleetTestAttention | undefined
  const fleetItems: AttentionItem[] = []
  if (fta?.ok === true && typeof fta.headline === 'string' && fta.headline.trim()) {
    const to =
      typeof fta.to === 'string' && fta.to.startsWith('/') && !fta.to.startsWith('//') ? fta.to : '/settings/fleet'
    fleetItems.push({
      id: `fleet-test-${String(fta.batch_id || 'cpu').slice(0, 24)}`,
      category: 'fleet',
      headline: fta.headline.trim(),
      scopeLabel: 'Forge Fleet',
      actionHint:
        'Short Docker jobs on the Fleet host sampled host CPU via mounted /proc. Refresh workspace scan if this looks stale.',
      to,
    })
  }

  const items: AttentionItem[] = []

  const dr = dirtyRepos(children)
  if (dr.length > 0) {
    items.push({
      id: 'dirty-working-trees',
      category: 'risk',
      headline: `${dr.length} repo${dr.length === 1 ? '' : 's'} with uncommitted changes`,
      scopeLabel: 'Workspace',
      actionHint: 'Review before you rely on scans or release tags.',
      to: '/projects',
    })
  }

  const weak = weakStandards(children)
  if (weak.length > 0) {
    const first = weak[0]
    items.push({
      id: `weak-standards-${first.name}`,
      category: 'risk',
      headline: `Standards gap on ${weak.length} repo${weak.length === 1 ? '' : 's'} (score or tier)`,
      scopeLabel: first.name ?? 'Project',
      actionHint: 'Align repo layout with Forge standards or document exceptions.',
      to: `/projects/${encodeURIComponent(first.name)}`,
    })
  }

  if (gitChildren.length > 0 && roadmaps.length === 0) {
    items.push({
      id: 'no-roadmaps',
      category: 'evidence_gap',
      headline: 'No roadmap files detected in the workspace scan',
      scopeLabel: 'Plans',
      actionHint: 'Add ROADMAP.md where leadership expects commitments.',
      to: '/plan',
    })
  }

  if (gitChildren.length > 0 && wbs.length === 0) {
    items.push({
      id: 'no-wbs',
      category: 'evidence_gap',
      headline: 'No WBS files indexed yet',
      scopeLabel: 'Plans',
      actionHint: 'Add docs/requirements/WBS.md under a project.',
      to: '/wbs',
    })
  }

  if (gitChildren.length > 2 && sites.length === 0) {
    items.push({
      id: 'no-sites',
      category: 'evidence_gap',
      headline: 'No Firebase or static sites linked in this workspace',
      scopeLabel: 'Sites',
      actionHint: 'Connect published sites when customer-facing delivery matters.',
      to: '/websites',
    })
  }

  if (items.length === 0 && gitChildren.length > 0) {
    items.push({
      id: 'all-clear',
      category: 'win',
      headline: 'No blocking exceptions surfaced from the latest workspace scan',
      scopeLabel: 'Workspace',
      actionHint: 'Drill into Plans or Delivery for execution detail.',
      to: '/plan?tab=today',
    })
  }

  return [...fleetItems, ...items].slice(0, 8)
}
