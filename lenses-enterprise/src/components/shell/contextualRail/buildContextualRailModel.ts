import type { NavMode } from '../../../nav/workspaceLensCookie'
import { getStudioNavMeta } from '../../../nav/studioRouteRegistry'
import { FULL_WORKSPACE_UI as FW, REGISTRY as R, STUDIO_VOCAB as V } from '../../../nav/studioVisibleCopy'
import type { WorkspaceState } from '../../../api/workspace'
import { blueprintsWizardFeatureEnabled } from '../../../util/experimentalFlags'
import { STUDIO_DOCS_HOME } from '../../../util/staticPreviewUrl'
import { mergePlanningScopeIntoTo, parsePlanningScopeFromSearch } from '../../../lib/planningClusterScope'
import type { ContextualRailLink, ContextualRailModel, ContextualRailRecovery, ContextualRailStatus } from './types'

const DOCS = STUDIO_DOCS_HOME

export type WorkspaceRailSlice = {
  loading: boolean
  error: string | null
  errorDescription?: string | null
  errorDetail?: string | null
  state: WorkspaceState | null
}

/** Optional live slice for `/settings/llm` (from ``GET /api/llm/diagnostics``). */
export type LlmSetupDiagnosticsSlice = {
  loading: boolean
  error?: boolean
  data: {
    connected_providers: number
    connected_provider_ids: string[]
    routing_mode: string
    next_recommended_step: string
    cost_note?: string
  } | null
}

export type BuildContextualRailInput = {
  pathname: string
  search: string
  mode: NavMode
  workspace: WorkspaceRailSlice
  llmSetup?: LlmSetupDiagnosticsSlice
}

function formatResolvedAt(iso?: string): string {
  if (!iso) return 'Not recorded'
  try {
    return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function planTab(search: string): string {
  const qs = search.startsWith('?') ? search.slice(1) : search
  return new URLSearchParams(qs).get('tab') || 'plan'
}

/** Encoded project segment in pathname (e.g. `my-repo`). */
function projectEncodedSegment(pathname: string): string | null {
  const m = pathname.match(/^\/projects\/([^/]+)/)
  return m?.[1] ?? null
}

function scopeStatusLine(search: string): ContextualRailStatus | undefined {
  const scope = parsePlanningScopeFromSearch(search)
  const parts: string[] = []
  if (scope.repo) parts.push(`Repo · ${scope.repo}`)
  if (scope.wbs_p) {
    const short = scope.wbs_p.length > 42 ? `${scope.wbs_p.slice(0, 40)}…` : scope.wbs_p
    parts.push(`WBS · ${short}`)
  }
  if (scope.roadmap_p) parts.push(`Roadmap file`)
  if (scope.id) parts.push(`Item · ${scope.id}`)
  if (parts.length === 0) return undefined
  return { label: 'Planning scope', value: parts.join(' · '), tone: 'muted' }
}

function workspaceScanStatus(ws: WorkspaceRailSlice): ContextualRailStatus {
  if (ws.loading && !ws.state) {
    return { label: 'Workspace scan', value: 'Loading…', tone: 'muted' }
  }
  if (ws.error) {
    return { label: 'Workspace scan', value: 'Unavailable', tone: 'warn' }
  }
  return { label: 'Last scan', value: formatResolvedAt(ws.state?.resolved_at), tone: 'ok' }
}

function llmSetupSourceLine(setup: LlmSetupDiagnosticsSlice | undefined): ContextualRailStatus | undefined {
  if (!setup) return undefined
  if (setup.loading) {
    return { label: 'Model sources', value: 'Loading diagnostics…', tone: 'muted' }
  }
  if (setup.error || !setup.data) {
    return { label: 'Model sources', value: 'Diagnostics unavailable', tone: 'warn' }
  }
  const n = setup.data.connected_providers
  const ids = setup.data.connected_provider_ids || []
  const tail = ids.length ? ` (${ids.join(', ')})` : ''
  return {
    label: 'Model sources',
    value: `${n} connected${tail}`,
    tone: n === 0 ? 'warn' : 'ok',
  }
}

function workspaceRecovery(ws: WorkspaceRailSlice): ContextualRailRecovery {
  const headline = ws.error?.trim() || 'Workspace unavailable'
  const bodyRaw =
    (ws.errorDescription && ws.errorDescription.trim()) ||
    'Lenses could not finish loading the workspace scan. Confirm the local server is running, then retry.'
  const body = bodyRaw.length > 220 ? `${bodyRaw.slice(0, 217)}…` : bodyRaw
  return {
    title: headline,
    body,
    actions: [{ label: 'Tutorials & troubleshooting', to: '/tutorials' }],
    showWorkspaceRetry: true,
    technicalDetail: ws.errorDetail ?? null,
  }
}

function mergeStatus(
  a: ContextualRailStatus | undefined,
  b: ContextualRailStatus | undefined,
): ContextualRailStatus | undefined {
  if (!a) return b
  if (!b) return a
  return { label: a.label, value: `${a.value} · ${b.value}`, tone: a.tone === 'warn' || b.tone === 'warn' ? 'warn' : a.tone }
}

function m(path: string, search: string): string {
  return mergePlanningScopeIntoTo(path, search)
}

/** First path segment under /view/local-site/ for deep links to Websites browse. */
function localSiteFolderFromPathname(pathname: string): string | null {
  const raw = pathname.replace(/^\/view\/local-site\/?/, '')
  if (!raw) return null
  const seg = raw.split('/').filter(Boolean)[0]
  return seg ? decodeURIComponent(seg) : null
}

function websitesBrowseSiteFromPathname(pathname: string): string | null {
  const m = pathname.match(/^\/websites\/browse\/([^/]+)/)
  return m?.[1] ? decodeURIComponent(m[1]) : null
}

function unknownBrowseSiteRecovery(
  site: string,
  state: WorkspaceState | null,
): ContextualRailRecovery | undefined {
  if (!state?.websites?.length) return undefined
  const known = new Set(state.websites.map((w) => w.name))
  if (known.size === 0 || known.has(site)) return undefined
  return {
    title: 'Site not in this scan',
    body: `No published folder named “${site}” appeared in the latest workspace scan. Rescan after adding hosting output, or pick a listed site.`,
    actions: [
      { label: 'View scanned sites', to: '/websites', variant: 'primary' },
      { label: 'Workspace overview', to: '/' },
    ],
  }
}

function gitChildCount(state: WorkspaceState | null): number {
  return (state?.children ?? []).filter((c) => c.is_git).length
}

function wbsCount(state: WorkspaceState | null): number {
  return state?.wbs?.length ?? 0
}

export function buildContextualRailModel(input: BuildContextualRailInput): ContextualRailModel {
  const { pathname, search, mode, workspace: ws } = input
  const { groupId } = getStudioNavMeta(pathname, search, mode)
  const scan = workspaceScanStatus(ws)

  let model: ContextualRailModel

  if (pathname === '/' || pathname === '') {
    model = {
      title: 'Command center',
      lead: 'Today for urgency, Boards for execution, Projects for per-repo signals.',
      status: scan,
      actions: [
        { label: R.whatNeedsAttentionToday, to: '/plan?tab=today', variant: 'primary' },
        { label: V.boards, to: '/board' },
        { label: R.allProjectsFlow, to: '/projects' },
      ],
      related: [
        { label: V.advancedReporting, to: '/overview/charts' },
        { label: V.lensesReference, to: DOCS },
      ],
      devLink: { label: 'Raw workspace JSON', href: '/api/workspace-state?git_extended=1' },
    }
  } else if (pathname === '/plan' && planTab(search) === 'today') {
    model = {
      title: 'Today',
      lead: 'Commitments and blockers for this backlog scope — Work strip links Plan, Boards, and Timeline.',
      status: mergeStatus(scan, scopeStatusLine(search)),
      actions: [
        { label: V.planSummary, to: m('/plan', search), variant: 'primary' },
        { label: V.boards, to: m('/board', search) },
      ],
      related: [
        { label: V.timeline, to: m('/timeline', search) },
        { label: V.methodologyReadiness, to: m('/knowledge/methodology/readiness', search) },
        { label: V.roadmapMatrix, to: m('/plan/matrix', search) },
      ],
    }
  } else if (pathname === '/plan/matrix') {
    model = {
      title: V.roadmapMatrix,
      lead: 'Dense roadmap grid — pair with Today for blockers or Boards for execution in the same scope.',
      status: mergeStatus(scan, scopeStatusLine(search)),
      actions: [
        { label: V.today, to: m('/plan?tab=today', search), variant: 'primary' },
        { label: V.plan, to: m('/plan', search) },
        { label: V.timeline, to: m('/timeline', search) },
      ],
      related: [
        { label: V.boards, to: m('/board', search) },
        { label: V.workBreakdown, to: m('/wbs', search) },
      ],
    }
  } else if (pathname === '/plan' || pathname.startsWith('/plan/')) {
    const tab = planTab(search)
    const tabLead =
      tab === 'story'
        ? 'Narrative view—open matrix or WBS when you need structure or files.'
        : tab === 'source'
          ? 'Source-backed plan—trace files in WBS view without losing repo scope.'
          : tab === 'map'
            ? 'Map view—pair with matrix and timeline for coverage.'
            : 'Depth tools keep repo, WBS path, and roadmap selections aligned.'
    model = {
      title: `${V.plan} · cluster`,
      lead: tabLead,
      status: mergeStatus(scan, scopeStatusLine(search)),
      actions: [
        { label: V.today, to: m('/plan?tab=today', search), variant: 'primary' },
        { label: V.boards, to: m('/board', search) },
        { label: V.timeline, to: m('/timeline', search) },
      ],
      related: [
        { label: V.roadmapMatrix, to: m('/plan/matrix', search) },
        { label: V.workBreakdown, to: m('/wbs', search) },
        { label: V.methodologyReadiness, to: m('/knowledge/methodology/readiness', search) },
        { label: FW.openRoadmapsSummary, href: '/roadmaps/summary' },
      ],
    }
  } else if (pathname === '/timeline' || pathname === '/roadmap-section') {
    model = {
      title: 'Roadmaps',
      lead: 'Sequence and milestones — same backlog scope as Plan summary and Boards.',
      status: mergeStatus(scan, scopeStatusLine(search)),
      actions: [
        { label: V.plan, to: m('/plan', search), variant: 'primary' },
        { label: V.today, to: m('/plan?tab=today', search) },
        { label: V.boards, to: m('/board', search) },
      ],
      related: [
        { label: V.roadmapMatrix, to: m('/plan/matrix', search) },
        { label: V.methodologyReadiness, to: m('/knowledge/methodology/readiness', search) },
        { label: FW.openRoadmapsSummary, href: '/roadmaps/summary' },
      ],
    }
  } else if (pathname.match(/^\/projects\/[^/]+\/charts\/?$/)) {
    const enc = projectEncodedSegment(pathname)!
    const name = decodeURIComponent(enc)
    model = {
      title: 'Repository charts',
      lead: 'Signals for this repo—return to the dashboard or strategy narrative when interpretation needs context.',
      status: mergeStatus(scan, {
        label: 'Repository',
        value: name,
        tone: 'muted',
      }),
      actions: [
        { label: V.projectDashboard, to: `/projects/${enc}`, variant: 'primary' },
        { label: V.architectureStrategy, to: `/projects/${enc}/strategy` },
      ],
      related: [{ label: R.allProjectsFlow, to: '/projects' }, { label: V.advancedReporting, to: '/overview/charts' }],
    }
  } else if (pathname.match(/^\/projects\/[^/]+\/strategy\/?$/)) {
    const enc = projectEncodedSegment(pathname)!
    const name = decodeURIComponent(enc)
    model = {
      title: 'Architecture strategy',
      lead: 'Narrative and hints for this repo—pair with charts for quantitative checks.',
      status: mergeStatus(scan, { label: 'Repository', value: name, tone: 'muted' }),
      actions: [
        { label: V.projectDashboard, to: `/projects/${enc}`, variant: 'primary' },
        { label: V.repositoryCharts, to: `/projects/${enc}/charts` },
      ],
      related: [
        { label: V.workspaceNotes, to: '/workspace-md' },
        { label: 'Tools & automation', to: '/toolset' },
      ],
    }
  } else if (pathname.match(/^\/projects\/[^/]+\/?$/)) {
    const enc = projectEncodedSegment(pathname)!
    const name = decodeURIComponent(enc)
    model = {
      title: 'Project dashboard',
      lead: 'This repo’s hub—charts and strategy stay scoped to the same encoded path.',
      status: mergeStatus(scan, {
        label: 'Repository',
        value: name,
        tone: 'muted',
      }),
      actions: [
        { label: V.repositoryCharts, to: `/projects/${enc}/charts`, variant: 'primary' },
        { label: V.architectureStrategy, to: `/projects/${enc}/strategy` },
      ],
      related: [
        { label: R.allProjectsFlow, to: '/projects' },
        { label: V.workspaceNotes, to: `/workspace-md?contextProject=${enc}` },
      ],
    }
  } else if (pathname === '/projects') {
    const n = gitChildCount(ws.state)
    model = {
      title: 'Projects portfolio',
      lead: 'Pick a repository for charts and strategy, or run cross-repo automation.',
      status: mergeStatus(scan, {
        label: 'Git repositories',
        value: ws.state ? String(n) : '—',
        tone: 'muted',
      }),
      actions: [{ label: R.allProjectsFlow, to: '/projects', variant: 'primary' }],
      related: [
        { label: V.advancedReporting, to: '/overview/charts' },
        { label: V.workspaceNotes, to: '/workspace-md' },
      ],
    }
  } else if (pathname === '/overview/charts') {
    const n = gitChildCount(ws.state)
    model = {
      title: V.advancedReporting,
      lead: 'Cross-repository reporting for leads and admins—per-repository signals stay under Projects.',
      status: mergeStatus(scan, {
        label: 'Repositories in scan',
        value: ws.state ? String(n) : '—',
        tone: 'muted',
      }),
      actions: [
        { label: R.allProjectsFlow, to: '/projects', variant: 'primary' },
        { label: V.today, to: '/plan?tab=today' },
        { label: V.boards, to: '/board' },
      ],
      related: [],
    }
  } else if (pathname.match(/^\/view\/local-site\/?$/)) {
    model = {
      title: 'Site preview',
      lead: 'Legacy /view/local-site URLs redirect to Websites browse. Pick a site from the list.',
      status: scan,
      recovery: {
        title: 'No path in the URL',
        body: 'Open Websites and choose a published site—the preview opens under /websites/browse/:site.',
        actions: [
          { label: 'Open Websites', to: '/websites', variant: 'primary' },
          { label: 'Tutorials', to: '/tutorials' },
        ],
      },
      actions: [],
      related: [{ label: 'Lenses reference', to: DOCS }],
    }
  } else if (pathname.startsWith('/view/local-site/')) {
    const folder = localSiteFolderFromPathname(pathname)
    const browseTo = folder ? `/websites/browse/${encodeURIComponent(folder)}` : '/websites'
    model = {
      title: 'Static preview',
      lead: 'Redirecting to the unified Sites browse preview.',
      status: scan,
      actions: [
        { label: 'Open preview', to: browseTo, variant: 'primary' },
        { label: 'All sites', to: '/websites' },
        { label: 'Tutorials', to: '/tutorials' },
      ],
      related: [{ label: 'Lenses reference', to: DOCS }],
    }
  } else if (pathname === '/workspace-md') {
    model = {
      title: V.workspaceNotes,
      lead: 'Indexed evidence markdown from the latest workspace scan.',
      status: scan,
      actions: [{ label: 'Search workspace', to: '/search', variant: 'primary' }],
      related: [
        { label: V.tutorials, to: '/tutorials' },
        { label: V.lensesReference, to: DOCS },
      ],
    }
  } else if (pathname.startsWith('/view/docs') || pathname.startsWith('/tutorials')) {
    const wizard: ContextualRailLink[] = blueprintsWizardFeatureEnabled()
      ? [{ label: 'Blueprints Wizard', to: '/blueprints/wizard' }]
      : []
    model = {
      title: 'Knowledge & reference',
      lead: 'Tutorials and embedded docs — workspace notes have their own hub.',
      status: scan,
      actions: [
        ...wizard,
        { label: 'Search workspace', to: '/search', variant: 'primary' },
        { label: 'Tutorials hub', to: '/tutorials' },
      ],
      related: [{ label: V.workspaceNotes, to: '/workspace-md' }, { label: 'Overview', to: '/' }],
    }
  } else if (pathname.startsWith('/websites/browse/')) {
    const site = websitesBrowseSiteFromPathname(pathname)
    const unknown = site && ws.state ? unknownBrowseSiteRecovery(site, ws.state) : undefined
    model = {
      title: 'Sites browse',
      lead: site
        ? `Static preview for “${site}” via /local-site/.`
        : 'Pick a site from the list so the URL includes its folder name.',
      status: scan,
      recovery: unknown,
      actions: site
        ? [
            { label: 'Scanned sites list', to: '/websites', variant: 'primary' },
            { label: V.today, to: '/plan?tab=today' },
          ]
        : [{ label: 'Websites', to: '/websites', variant: 'primary' }],
      related: [{ label: V.tutorials, to: '/tutorials' }],
    }
  } else if (pathname.startsWith('/websites')) {
    model = {
      title: 'Websites',
      lead: 'Handbooks and Firebase/static outputs from the latest scan—preview paths stay tied to folder names.',
      status: mergeStatus(scan, {
        label: 'Sites in scan',
        value: ws.state ? String(ws.state.websites?.length ?? 0) : '—',
        tone: 'muted',
      }),
      actions: [
        { label: 'Browse a site', to: '/websites', variant: 'primary' },
        { label: 'Lenses reference', to: DOCS },
      ],
      related: [{ label: 'Tutorials', to: '/tutorials' }],
    }
  } else if (pathname === '/board' || pathname.startsWith('/board/')) {
    model = {
      title: V.boards,
      lead: 'Active execution — scope from the URL stays aligned with Plan and Today when present.',
      status: scan,
      actions: [
        { label: V.today, to: m('/plan?tab=today', search), variant: 'primary' },
        { label: V.plan, to: m('/plan', search) },
        { label: V.timeline, to: m('/timeline', search) },
      ],
      related: [
        { label: V.methodologyReadiness, to: m('/knowledge/methodology/readiness', search) },
        { label: V.advancedReporting, to: '/overview/charts' },
        { label: R.allBoards, to: '/board' },
      ],
    }
  } else if (pathname === '/wbs' || pathname.startsWith('/wbs/')) {
    model = {
      title: V.workBreakdown,
      lead: 'File-backed backlog—keep matrix and timeline open in the same scope.',
      status: mergeStatus(scan, scopeStatusLine(search)),
      actions: [
        { label: V.plan, to: m('/plan', search), variant: 'primary' },
        { label: V.roadmapMatrix, to: m('/plan/matrix', search) },
        { label: V.today, to: m('/plan?tab=today', search) },
      ],
      related:
        ws.state && wbsCount(ws.state) > 0
          ? [
              { label: V.timeline, to: m('/timeline', search) },
              { label: `WBS files (${wbsCount(ws.state)})`, to: m('/wbs', search) },
            ]
          : [{ label: V.timeline, to: m('/timeline', search) }],
    }
  } else if (pathname === '/search') {
    model = {
      title: 'Search',
      lead: 'Filters are on the page; use links below when you need reference or evidence.',
      showLead: false,
      status: scan,
      actions: [{ label: 'Tutorials & handbooks', to: '/tutorials', variant: 'primary' }],
      related: [{ label: 'Lenses reference', to: DOCS }, { label: V.workspaceNotes, to: '/workspace-md' }],
    }
  } else if (pathname === '/chat') {
    model = {
      title: 'LLM chat',
      lead: 'Routing follows workspace AI Setup (saved on the Lenses host).',
      showLead: false,
      status: scan,
      actions: [{ label: 'AI Setup', to: '/settings/llm', variant: 'primary' }],
      related: [{ label: 'Lenses reference', to: DOCS }, { label: 'Tutorials', to: '/tutorials' }],
    }
  } else if (pathname.startsWith('/blueprints/wizard')) {
    model = {
      title: 'Blueprints Wizard',
      lead: 'Guided session—keep references one click away.',
      status: scan,
      actions: [{ label: 'Tutorials', to: '/tutorials', variant: 'primary' }],
      related: [{ label: 'Lenses reference', to: DOCS }, { label: 'AI Setup', to: '/settings/llm' }],
    }
  } else if (pathname.startsWith('/blog')) {
    model = {
      title: 'Blog',
      lead: 'Posts in Studio mirror the live Forge SDLC site.',
      status: scan,
      actions: [{ label: 'All posts', to: '/blog', variant: 'primary' }],
      related: [
        { label: 'Blog home (live)', href: 'https://forgesdlc.com/blog/index.html', external: true },
        { label: 'Product overview', to: '/' },
      ],
    }
  } else if (pathname === '/settings/llm') {
    const setupLine = llmSetupSourceLine(input.llmSetup)
    const next = input.llmSetup?.data?.next_recommended_step?.trim()
    model = {
      title: 'AI Setup',
      lead: next
        ? `Next recommended step: ${next}`
        : 'Connect sources and routing on this host. Use Health / Discover on each card, then confirm with Try Chat.',
      status: mergeStatus(scan, setupLine),
      actions: [
        { label: 'Try Chat', to: '/chat', variant: 'primary' },
        { label: 'Diagnostics on this page', to: '/settings/llm#ai-setup-diagnostics' },
      ],
      related: [
        { label: 'Tutorials & local setup', to: '/tutorials' },
        { label: 'Forge knowledge (models & methods)', href: 'https://forgesdlc.com/knowledge/', external: true },
        { label: 'Raw diagnostics JSON', href: '/api/llm/diagnostics' },
        { label: 'Raw usage JSON', href: '/api/llm/usage' },
      ],
      devLink: { label: 'Masked settings JSON', href: '/api/llm/settings' },
    }
  } else if (pathname === '/settings/fleet') {
    model = {
      title: 'Forge Fleet',
      lead: 'Optional orchestrator for Docs Health Docker steps — same bearer pattern as cloud LLM keys; paths must exist where Fleet runs.',
      status: scan,
      actions: [
        { label: 'AI Setup', to: '/settings/llm', variant: 'primary' },
        { label: 'Docs health maintainer notes', to: '/view/docs/maintainer/docs-health-mvp.html' },
      ],
      related: [{ label: 'Lenses reference', to: DOCS }],
      devLink: { label: 'Masked fleet settings JSON', href: '/api/fleet/settings' },
    }
  } else if (pathname.startsWith('/toolset')) {
    model = {
      title: 'Automation',
      lead: 'Toolset runs across repositories—open a project dashboard when you need per-repo charts.',
      status: scan,
      actions: [
        { label: R.allProjectsFlow, to: '/projects', variant: 'primary' },
        { label: V.workBreakdown, to: '/wbs' },
      ],
      related: [{ label: 'Lenses reference', to: DOCS }],
    }
  } else if (pathname === '/labs/virtual-camera') {
    model = {
      title: 'Virtual Camera Studio',
      lead: 'Map physical webcams to v4l2loopback virtual devices for VDI and conferencing apps.',
      status: scan,
      actions: [
        { label: 'Refresh cameras', to: '/labs/virtual-camera', variant: 'primary' },
      ],
      related: [],
    }
  } else if (pathname === '/feature-showcase') {
    model = {
      title: 'Showcase',
      lead: 'Lab route (not in primary nav)—visual experiments only; bookmark OK. Return to Overview or open Admin & inspect from the gear menu for diagnostics.',
      status: scan,
      actions: [{ label: 'Overview', to: '/', variant: 'primary' }],
      related: [{ label: 'Tutorials', to: '/tutorials' }],
    }
  } else if (pathname === '/knowledge/methodology/readiness') {
    model = {
      title: V.methodologyReadiness,
      lead: 'Quality and release readiness for this scope — return to Today or Boards in one hop.',
      status: mergeStatus(scan, scopeStatusLine(search)),
      actions: [
        { label: V.today, to: m('/plan?tab=today', search), variant: 'primary' },
        { label: V.planSummary, to: m('/plan', search) },
        { label: V.boards, to: m('/board', search) },
      ],
      related: [{ label: V.timeline, to: m('/timeline', search) }, { label: V.tutorials, to: '/tutorials' }],
    }
  } else {
    model = {
      title: 'This area',
      lead: `Context for ${groupId} — use the left nav for the full map.`,
      status: scan,
      actions: [{ label: 'Overview', to: '/', variant: 'primary' }],
      related: [{ label: V.lensesReference, to: DOCS }],
    }
  }

  if (ws.error) {
    model = { ...model, workspaceAlert: workspaceRecovery(ws) }
  }

  return model
}
