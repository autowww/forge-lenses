/**
 * Single source of truth for Studio routes: paths, IA placement, breadcrumbs, titles, and sidebar labels.
 * Flow vs Artifacts lenses share URLs but may differ in nav chrome; both are encoded here.
 *
 * User-facing strings are imported from `studioVisibleCopy.ts` so titles and nav stay aligned.
 */
import { matchPath } from 'react-router-dom'
import type { NavMode } from './workspaceLensCookie'
import type { TopSectionId } from './navPlacementTypes'
import {
  PLAN_PAGE_COPY,
  REGISTRY as R,
  ROUTE_SUBTITLE as SUB,
  STUDIO_GLOSSARY,
  STUDIO_PRODUCT_NAME,
  STUDIO_VOCAB as V,
} from './studioVisibleCopy'

export { getPrimarySectionLabel, PRIMARY_SECTION_LABEL, STUDIO_PRODUCT_NAME } from './studioVisibleCopy'

export type StudioRouteKind = 'canonical' | 'alias' | 'legacy' | 'utility'

export type StudioObjectType =
  | 'workspace'
  | 'chart'
  | 'project'
  | 'plan'
  | 'roadmap'
  | 'timeline'
  | 'board'
  | 'search'
  | 'chat'
  | 'settings'
  | 'automation'
  | 'site'
  | 'knowledge'
  | 'blog'
  | 'wizard'
  | 'demo'
  | 'unknown'

export type StudioNavBundle = {
  groupId: TopSectionId
  breadcrumbs: string[]
  hrefs: (string | null)[]
}

export type StudioLensVisibility = { flow: boolean; artifacts: boolean }

/**
 * Optional / probe surfaces: deep-linked or session-scoped URLs that must stay registered for
 * debugging and E2E, but are not primary product navigation. UIs should use framed loading and
 * explicit invalid-session states (see `WizardSessionProbeChrome`).
 */
export type StudioRouteProbeKind = 'wizard_session' | 'docs_health_session'

export type StudioRouteDefinition = {
  id: string
  /** React Router path pattern (omit for plan-tab-only rows). */
  pattern?: string
  /** Default true. Use false for `/foo/*` style patterns. */
  end?: boolean
  /** When set, only matches `pathname === '/plan'` with this `tab` query (or default tab). */
  planTab?: 'plan' | 'today' | 'story' | 'source'
  kind: StudioRouteKind
  /** For alias/legacy rows: canonical route id this resolves as. */
  canonicalRouteId?: string
  /** Human hint when kind is alias/legacy (e.g. “Saved view”). */
  aliasLabel?: string
  /** Short primary name for tabs, history, and H1 alignment (unique per static surface). */
  canonicalTitle: string
  subtitle?: string
  objectType: StudioObjectType
  lensVisibility: StudioLensVisibility
  flow: StudioNavBundle
  artifacts: StudioNavBundle
  /** Optional sidebar copy that differs from `canonicalTitle` for a given lens + section. */
  sidebar?: Partial<Record<NavMode, Partial<Record<TopSectionId, string>>>>
  /** When no `sidebar[mode][section]` override exists, use this in sidebars instead of `canonicalTitle`. */
  defaultSidebarLabel?: string
  /** Deep-link / probe route — omit from product “happy path” smoke lists; keep reachable in App routes. */
  probeKind?: StudioRouteProbeKind
}

/** Stable ids for sidebar + tests (registry keys). */
export const SR = {
  homeOverview: 'sr.home.overview',
  planToday: 'sr.plan.today',
  planStory: 'sr.plan.story',
  planSource: 'sr.plan.source',
  planDefault: 'sr.plan.default',
  overviewCharts: 'sr.workspace.charts',
  projectsIndex: 'sr.projects.index',
  projectDashboard: 'sr.projects.dashboard',
  projectCharts: 'sr.projects.charts',
  projectStrategy: 'sr.projects.strategy',
  projectBranching: 'sr.projects.branching',
  projectDocsHealthSession: 'sr.projects.docsHealthSession',
  projectDocsHealthMaster: 'sr.projects.docsHealthMaster',
  projectDocsHealth: 'sr.projects.docsHealth',
  projectForgeRun: 'sr.projects.forgeRun',
  search: 'sr.utilities.search',
  chat: 'sr.utilities.chat',
  llmSettings: 'sr.workspace.llmSettings',
  fleetSettings: 'sr.workspace.fleetSettings',
  uxInsights: 'sr.workspace.uxInsights',
  agentRuntimeInspect: 'sr.workspace.agentRuntimeInspect',
  governanceConnectors: 'sr.governance.connectors',
  governanceAudit: 'sr.governance.audit',
  toolsetIndex: 'sr.automation.toolset',
  toolsetRun: 'sr.automation.run',
  websitesIndex: 'sr.sites.index',
  websitesBrowse: 'sr.sites.browse',
  wbsIndex: 'sr.plans.wbs',
  wbsView: 'sr.plans.wbsView',
  planMatrix: 'sr.plans.matrix',
  timeline: 'sr.plans.timeline',
  roadmapSection: 'sr.roadmaps.sectionPreview',
  boardHub: 'sr.delivery.boardsHub',
  boardEditor: 'sr.delivery.boardEditor',
  tutorials: 'sr.knowledge.tutorials',
  docsEmbed: 'sr.knowledge.docsEmbed',
  localSiteEmbed: 'sr.sites.localPreview',
  workspaceMd: 'sr.knowledge.workspaceMd',
  workspaceMdView: 'sr.knowledge.workspaceMdView',
  blogIndex: 'sr.blog.index',
  blogPost: 'sr.blog.post',
  blueprintsWizard: 'sr.knowledge.blueprintsWizard',
  blueprintsWizardSession: 'sr.knowledge.blueprintsWizardSession',
  featureShowcase: 'sr.demo.featureShowcase',
  methodologyEvidence: 'sr.knowledge.methodologyEvidence',
  methodologyDecisions: 'sr.knowledge.methodologyDecisions',
  methodologyRecord: 'sr.knowledge.methodologyRecord',
  methodologyReadiness: 'sr.delivery.methodologyReadiness',
  agenticBridge: 'sr.knowledge.agenticBridge',
  fallback: 'sr.fallback',
} as const

export type StudioRouteId = (typeof SR)[keyof typeof SR]

const PRIMARY: StudioLensVisibility = { flow: true, artifacts: true }

function bundle(
  groupId: TopSectionId,
  breadcrumbs: string[],
  hrefs: (string | null)[],
): StudioNavBundle {
  return { groupId, breadcrumbs, hrefs }
}

/** Ordered patterns: first match wins (most specific first). Excludes `/plan` tabs (handled separately). */
const ORDERED_PATTERNS: StudioRouteDefinition[] = [
  {
    id: SR.overviewCharts,
    pattern: '/overview/charts',
    kind: 'canonical',
    canonicalTitle: V.advancedReporting,
    subtitle: SUB.workspaceChartsAdvanced,
    objectType: 'chart',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.adminInspect, V.advancedReporting], [null, null]),
    artifacts: bundle('home', [V.adminInspect, V.advancedReporting], [null, null]),
    sidebar: {
      flow: { home: R.workspaceActivityCharts },
      artifacts: { home: V.workspaceCharts },
    },
    defaultSidebarLabel: V.advancedReporting,
  },
  {
    id: SR.projectCharts,
    pattern: '/projects/:name/charts',
    kind: 'canonical',
    canonicalTitle: V.repositoryCharts,
    subtitle: SUB.repositoryCharts,
    objectType: 'chart',
    lensVisibility: PRIMARY,
    flow: bundle('projects', [V.projects, V.repositoryCharts], ['/projects', null]),
    artifacts: bundle('projects', [V.projects, V.repositoryCharts], ['/projects', null]),
    sidebar: {
      flow: { projects: V.repositoryCharts },
      artifacts: { projects: V.repositoryCharts },
    },
  },
  {
    id: SR.projectStrategy,
    pattern: '/projects/:name/strategy',
    kind: 'canonical',
    canonicalTitle: V.architectureStrategy,
    objectType: 'project',
    lensVisibility: PRIMARY,
    flow: bundle('projects', [V.projects, V.architectureStrategy], ['/projects', null]),
    artifacts: bundle('projects', [V.projects, V.architectureStrategy], ['/projects', null]),
    sidebar: {
      flow: { projects: V.architectureStrategy },
      artifacts: { projects: V.architectureStrategy },
    },
  },
  {
    id: SR.projectBranching,
    pattern: '/projects/:name/branching',
    kind: 'canonical',
    canonicalTitle: V.projectBranching,
    subtitle: SUB.repositoryCharts,
    objectType: 'project',
    lensVisibility: PRIMARY,
    flow: bundle('projects', [V.projects, V.projectBranching], ['/projects', null]),
    artifacts: bundle('projects', [V.projects, V.projectBranching], ['/projects', null]),
    sidebar: {
      flow: { projects: V.projectBranching },
      artifacts: { projects: V.projectBranching },
    },
  },
  {
    id: SR.projectForgeRun,
    pattern: '/projects/:name/forge-run',
    kind: 'canonical',
    canonicalTitle: V.forgePlatformRun,
    objectType: 'project',
    lensVisibility: PRIMARY,
    flow: bundle('projects', [V.projects, V.forgePlatformRun], ['/projects', null]),
    artifacts: bundle('projects', [V.projects, V.forgePlatformRun], ['/projects', null]),
    sidebar: {
      flow: { projects: V.forgePlatformRun },
      artifacts: { projects: V.forgePlatformRun },
    },
  },
  {
    id: SR.projectDocsHealthSession,
    pattern: '/projects/:name/docs-health/session/:sessionId',
    kind: 'canonical',
    canonicalTitle: V.docsHealthSession,
    subtitle: SUB.docsHealthSession,
    objectType: 'project',
    lensVisibility: PRIMARY,
    probeKind: 'docs_health_session',
    flow: bundle('projects', [V.projects, V.docsHealth, V.docsHealthSession], ['/projects', null, null]),
    artifacts: bundle('projects', [V.projects, V.docsHealth, V.docsHealthSession], ['/projects', null, null]),
    sidebar: {
      flow: { projects: V.docsHealthSession },
      artifacts: { projects: V.docsHealthSession },
    },
    defaultSidebarLabel: V.docsHealthSession,
  },
  {
    id: SR.projectDocsHealthMaster,
    pattern: '/projects/:name/docs-health/master',
    kind: 'canonical',
    canonicalTitle: V.docsHealthMaster,
    subtitle: SUB.docsHealthMaster,
    objectType: 'project',
    lensVisibility: PRIMARY,
    flow: bundle('projects', [V.projects, V.docsHealth, V.docsHealthMaster], ['/projects', null, null]),
    artifacts: bundle('projects', [V.projects, V.docsHealth, V.docsHealthMaster], ['/projects', null, null]),
    sidebar: {
      flow: { projects: V.docsHealthMaster },
      artifacts: { projects: V.docsHealthMaster },
    },
    defaultSidebarLabel: V.docsHealthMaster,
  },
  {
    id: SR.projectDocsHealth,
    pattern: '/projects/:name/docs-health',
    kind: 'canonical',
    canonicalTitle: V.docsHealth,
    subtitle: SUB.docsHealth,
    objectType: 'project',
    lensVisibility: PRIMARY,
    flow: bundle('projects', [V.projects, V.docsHealth], ['/projects', null]),
    artifacts: bundle('projects', [V.projects, V.docsHealth], ['/projects', null]),
    sidebar: {
      flow: { projects: V.docsHealth },
      artifacts: { projects: V.docsHealth },
    },
    defaultSidebarLabel: V.docsHealth,
  },
  {
    id: SR.projectDashboard,
    pattern: '/projects/:name',
    kind: 'canonical',
    canonicalTitle: V.projectDashboard,
    subtitle: SUB.projectDashboard,
    objectType: 'project',
    lensVisibility: PRIMARY,
    flow: bundle('projects', [V.projects, V.projectDashboard], ['/projects', null]),
    artifacts: bundle('projects', [V.projects, V.projectDashboard], ['/projects', null]),
    sidebar: {
      flow: { projects: V.projectDashboard },
      artifacts: { projects: V.projectDashboard },
    },
  },
  {
    id: SR.projectsIndex,
    pattern: '/projects',
    kind: 'canonical',
    canonicalTitle: V.projects,
    objectType: 'project',
    lensVisibility: PRIMARY,
    flow: bundle('projects', [V.projects], [null]),
    artifacts: bundle('projects', [V.projects], [null]),
    sidebar: {
      flow: { home: R.allProjectsFlow, projects: R.allProjectsFlow },
      artifacts: { home: R.allProjectsFlow, projects: R.allProjectsFlow },
    },
    defaultSidebarLabel: R.allProjectsFlow,
  },
  {
    id: SR.websitesBrowse,
    pattern: '/websites/browse/:site',
    kind: 'canonical',
    canonicalTitle: V.siteBrowse,
    objectType: 'site',
    lensVisibility: PRIMARY,
    flow: bundle('publish', ['Sites', V.siteBrowse], ['/websites', null]),
    artifacts: bundle('publish', ['Sites', V.siteBrowse], ['/websites', null]),
    sidebar: {
      flow: { publish: R.browseAndPreview },
      artifacts: { publish: R.browseAndPreview },
    },
  },
  {
    id: SR.websitesIndex,
    pattern: '/websites',
    kind: 'canonical',
    canonicalTitle: V.websites,
    objectType: 'site',
    lensVisibility: PRIMARY,
    flow: bundle('publish', ['Sites'], [null]),
    artifacts: bundle('publish', ['Sites'], [null]),
    sidebar: {
      flow: { publish: R.allSites },
      artifacts: { publish: R.allSites },
    },
    defaultSidebarLabel: R.allSites,
  },
  {
    id: SR.toolsetRun,
    pattern: '/toolset/:name',
    kind: 'canonical',
    canonicalTitle: V.automationRun,
    subtitle: SUB.toolsetAdvanced,
    objectType: 'automation',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.adminInspect, V.automationRun], [null, '/toolset']),
    artifacts: bundle('home', [V.adminInspect, V.automationRun], [null, '/toolset']),
  },
  {
    id: SR.toolsetIndex,
    pattern: '/toolset',
    kind: 'canonical',
    canonicalTitle: V.automation,
    subtitle: SUB.toolsetAdvanced,
    objectType: 'automation',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.adminInspect, V.automation], [null, null]),
    artifacts: bundle('home', [V.adminInspect, V.automation], [null, null]),
  },
  {
    id: SR.planMatrix,
    pattern: '/plan/matrix',
    kind: 'canonical',
    canonicalTitle: V.roadmapMatrix,
    subtitle: STUDIO_GLOSSARY.roadmapMatrix.short,
    objectType: 'roadmap',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.roadmapMatrix], ['/plan', null]),
    artifacts: bundle('work', [V.work, V.roadmapMatrix], ['/plan', null]),
  },
  {
    id: SR.wbsView,
    pattern: '/wbs/view',
    kind: 'canonical',
    canonicalTitle: R.workBreakdownDetailTitle,
    subtitle:
      'Markdown for one backlog file—aligned with Plan scope when you use the planning bar (`p` or `wbs_p`).',
    objectType: 'plan',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, R.workBreakdownDetailBc], ['/wbs', null]),
    artifacts: bundle('work', [V.work, R.workBreakdownDetailBc], ['/wbs', null]),
  },
  {
    id: SR.wbsIndex,
    pattern: '/wbs',
    kind: 'canonical',
    canonicalTitle: V.workBreakdown,
    subtitle:
      'Workspace backlog files—open one to view markdown; repository, WBS, and roadmap scope stay in the URL via the bar above.',
    objectType: 'plan',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, R.workBreakdownBc], ['/plan', null]),
    artifacts: bundle('work', [V.work, R.workBreakdownBc], ['/plan', null]),
  },
  {
    id: SR.timeline,
    pattern: '/timeline',
    kind: 'canonical',
    canonicalTitle: V.timeline,
    subtitle: SUB.timeline,
    objectType: 'timeline',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.timeline], ['/plan', null]),
    artifacts: bundle('work', ['Roadmaps', V.timeline], ['/', null]),
    sidebar: {
      flow: { work: V.timeline },
      artifacts: { home: R.roadmapsTimeline, work: V.timeline },
    },
    defaultSidebarLabel: V.timeline,
  },
  {
    id: SR.roadmapSection,
    pattern: '/roadmap-section',
    kind: 'canonical',
    canonicalTitle: R.roadmapSectionPreview,
    objectType: 'roadmap',
    lensVisibility: { flow: true, artifacts: true },
    flow: bundle('work', [V.work, R.sectionPreview], ['/plan', null]),
    artifacts: bundle('work', ['Roadmaps', R.sectionPreview], ['/timeline', null]),
    sidebar: {
      artifacts: { work: R.sectionPreview },
    },
  },
  {
    id: SR.boardEditor,
    pattern: '/board/:id',
    kind: 'canonical',
    canonicalTitle: V.boardEditor,
    objectType: 'board',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.board], ['/board', null]),
    artifacts: bundle('work', [V.boards, R.boardsEditor], ['/board', null]),
  },
  {
    id: SR.boardHub,
    pattern: '/board',
    kind: 'canonical',
    canonicalTitle: V.boards,
    subtitle: SUB.boardHub,
    objectType: 'board',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.boards], ['/plan?tab=today', null]),
    artifacts: bundle('work', [V.boards], [null]),
    sidebar: {
      flow: { home: R.executionBoards, work: V.boards },
      artifacts: { work: R.allBoards },
    },
    defaultSidebarLabel: V.boards,
  },
  {
    id: SR.blogPost,
    pattern: '/blog/post/:slug',
    kind: 'canonical',
    canonicalTitle: V.blogPost,
    objectType: 'blog',
    lensVisibility: PRIMARY,
    flow: bundle('publish', [V.blog, 'Post'], ['/blog', null]),
    artifacts: bundle('publish', [V.blog, 'Post'], ['/blog', null]),
  },
  {
    id: SR.blogIndex,
    pattern: '/blog',
    kind: 'canonical',
    canonicalTitle: V.blog,
    objectType: 'blog',
    lensVisibility: PRIMARY,
    flow: bundle('publish', [V.blog], [null]),
    artifacts: bundle('publish', [V.blog], [null]),
    sidebar: {
      flow: { publish: R.allPosts },
      artifacts: { publish: R.allPosts },
    },
    defaultSidebarLabel: R.allPosts,
  },
  {
    id: SR.tutorials,
    pattern: '/tutorials',
    kind: 'canonical',
    canonicalTitle: V.tutorials,
    subtitle: SUB.tutorialsReference,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.tutorials], ['/', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.tutorials], ['/', null]),
    sidebar: {
      flow: { knowledge: V.tutorials },
      artifacts: { knowledge: V.tutorials },
    },
    defaultSidebarLabel: V.tutorials,
  },
  {
    id: SR.docsEmbed,
    pattern: '/view/docs/*',
    end: false,
    kind: 'canonical',
    canonicalTitle: V.lensesReference,
    subtitle: SUB.lensesReferenceEmbed,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, R.knowledgeReferenceBc], ['/tutorials', null]),
    artifacts: bundle('knowledge', [V.knowledge, R.knowledgeReferenceBc], ['/tutorials', null]),
    sidebar: {
      flow: { knowledge: R.lensesReferenceDocs },
      artifacts: { knowledge: R.lensesReferenceDocs },
    },
    defaultSidebarLabel: R.lensesReferenceDocs,
  },
  {
    id: SR.localSiteEmbed,
    pattern: '/view/local-site/*',
    end: false,
    kind: 'canonical',
    canonicalTitle: V.sitePreview,
    objectType: 'site',
    lensVisibility: PRIMARY,
    flow: bundle('publish', ['Sites', R.sitesPreviewBc], ['/websites', null]),
    artifacts: bundle('publish', ['Sites', R.sitesPreviewBc], ['/websites', null]),
  },
  {
    id: SR.workspaceMdView,
    pattern: '/workspace-md/view',
    kind: 'alias',
    canonicalRouteId: SR.workspaceMd,
    aliasLabel: R.workspaceNotesDeepLink,
    canonicalTitle: V.workspaceNotes,
    subtitle: SUB.workspaceNotes,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.workspaceNotes], ['/tutorials', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.workspaceNotes], ['/tutorials', null]),
    sidebar: {
      flow: {
        projects: R.projectLinkedNotes,
        knowledge: R.workspaceNotesEvidenceSidebar,
        home: R.workspaceNotesEvidenceSidebar,
      },
      artifacts: {
        projects: R.projectLinkedNotes,
        knowledge: R.workspaceNotesEvidenceSidebar,
        home: R.workspaceNotesEvidenceSidebar,
      },
    },
    defaultSidebarLabel: R.workspaceNotesEvidenceSidebar,
  },
  {
    id: SR.workspaceMd,
    pattern: '/workspace-md',
    kind: 'canonical',
    canonicalTitle: V.workspaceNotes,
    subtitle: SUB.workspaceNotes,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.workspaceNotes], ['/tutorials', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.workspaceNotes], ['/tutorials', null]),
    sidebar: {
      flow: {
        projects: R.projectLinkedNotes,
        knowledge: R.workspaceNotesEvidenceSidebar,
        home: R.workspaceNotesEvidenceSidebar,
      },
      artifacts: {
        projects: R.projectLinkedNotes,
        knowledge: R.workspaceNotesEvidenceSidebar,
        home: R.workspaceNotesEvidenceSidebar,
      },
    },
    defaultSidebarLabel: R.workspaceNotesEvidenceSidebar,
  },
  {
    id: SR.methodologyRecord,
    pattern: '/knowledge/methodology/record/:entityId',
    kind: 'canonical',
    canonicalTitle: V.methodologyGraphRecord,
    subtitle: SUB.methodologyBridge,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.methodologyGraphRecord], ['/tutorials', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.methodologyGraphRecord], ['/tutorials', null]),
    sidebar: {
      flow: { knowledge: R.methodologyEvidenceSidebar },
      artifacts: { knowledge: R.methodologyEvidenceSidebar },
    },
    defaultSidebarLabel: R.methodologyEvidenceSidebar,
  },
  {
    id: SR.methodologyReadiness,
    pattern: '/knowledge/methodology/readiness',
    kind: 'canonical',
    canonicalTitle: V.methodologyReadiness,
    subtitle: SUB.methodologyBridge,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.methodologyReadiness], ['/plan', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.methodologyReadiness], ['/tutorials', null]),
    sidebar: {
      flow: { work: R.methodologyReadinessSidebar },
      artifacts: { knowledge: R.methodologyReadinessSidebar },
    },
    defaultSidebarLabel: R.methodologyReadinessSidebar,
  },
  {
    id: SR.methodologyDecisions,
    pattern: '/knowledge/methodology/decisions',
    kind: 'canonical',
    canonicalTitle: V.methodologyDecisionsRegistry,
    subtitle: SUB.methodologyBridge,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.methodologyDecisionsRegistry], ['/tutorials', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.methodologyDecisionsRegistry], ['/tutorials', null]),
    sidebar: {
      flow: { knowledge: R.methodologyDecisionsSidebar },
      artifacts: { knowledge: R.methodologyDecisionsSidebar },
    },
    defaultSidebarLabel: R.methodologyDecisionsSidebar,
  },
  {
    id: SR.methodologyEvidence,
    pattern: '/knowledge/methodology/evidence',
    kind: 'canonical',
    canonicalTitle: V.methodologyEvidenceRegistry,
    subtitle: SUB.methodologyBridge,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.methodologyEvidenceRegistry], ['/tutorials', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.methodologyEvidenceRegistry], ['/tutorials', null]),
    sidebar: {
      flow: { knowledge: R.methodologyEvidenceSidebar },
      artifacts: { knowledge: R.methodologyEvidenceSidebar },
    },
    defaultSidebarLabel: R.methodologyEvidenceSidebar,
  },
  {
    id: SR.agenticBridge,
    pattern: '/knowledge/agentic-bridge',
    kind: 'canonical',
    canonicalTitle: V.agenticBridge,
    subtitle: SUB.agenticBridge,
    objectType: 'knowledge',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.agenticBridge], ['/tutorials', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.agenticBridge], ['/tutorials', null]),
    sidebar: {
      flow: { knowledge: R.agenticBridgeSidebar },
      artifacts: { knowledge: R.agenticBridgeSidebar },
    },
    defaultSidebarLabel: R.agenticBridgeSidebar,
  },
  {
    id: SR.search,
    pattern: '/search',
    kind: 'utility',
    canonicalTitle: V.search,
    subtitle: SUB.searchUtility,
    objectType: 'search',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.studioTools, V.search], [null, null]),
    artifacts: bundle('home', [V.studioTools, V.search], [null, null]),
    defaultSidebarLabel: 'Search workspace',
  },
  {
    id: SR.blueprintsWizardSession,
    pattern: '/blueprints/wizard/session/:sessionId',
    kind: 'canonical',
    canonicalTitle: R.blueprintsWizardSession,
    subtitle: SUB.wizardExperimental,
    objectType: 'wizard',
    probeKind: 'wizard_session',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.blueprintsWizard, 'Session'], [
      '/tutorials',
      '/blueprints/wizard',
      null,
    ]),
    artifacts: bundle('knowledge', [V.knowledge, V.blueprintsWizard, 'Session'], [
      '/tutorials',
      '/blueprints/wizard',
      null,
    ]),
    sidebar: {
      flow: { knowledge: R.wizardExperimentalSidebar },
      artifacts: { knowledge: R.wizardExperimentalSidebar },
    },
  },
  {
    id: SR.blueprintsWizard,
    pattern: '/blueprints/wizard',
    kind: 'canonical',
    canonicalTitle: V.blueprintsWizard,
    subtitle: SUB.wizardExperimental,
    objectType: 'wizard',
    lensVisibility: PRIMARY,
    flow: bundle('knowledge', [V.knowledge, V.blueprintsWizard], ['/tutorials', null]),
    artifacts: bundle('knowledge', [V.knowledge, V.blueprintsWizard], ['/tutorials', null]),
    sidebar: {
      flow: { knowledge: R.wizardExperimentalSidebar },
      artifacts: { knowledge: R.wizardExperimentalSidebar },
    },
    defaultSidebarLabel: R.wizardExperimentalSidebar,
  },
  {
    id: SR.chat,
    pattern: '/chat',
    kind: 'utility',
    canonicalTitle: V.llmChat,
    subtitle: SUB.llmChatUtility,
    objectType: 'chat',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.studioTools, V.llmChat], [null, null]),
    artifacts: bundle('home', [V.studioTools, V.llmChat], [null, null]),
    sidebar: {
      flow: { home: R.llmChatDemo },
      artifacts: { home: R.llmChatDemo },
    },
    defaultSidebarLabel: R.llmChatDemo,
  },
  {
    id: SR.llmSettings,
    pattern: '/settings/llm',
    kind: 'canonical',
    canonicalTitle: V.llmPreferences,
    subtitle: SUB.llmPreferencesUtility,
    objectType: 'settings',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.studioTools, V.llmPreferences], [null, null]),
    artifacts: bundle('home', [V.studioTools, V.llmPreferences], [null, null]),
    sidebar: {
      flow: { home: V.llmPreferences },
      artifacts: { home: V.llmPreferences },
    },
  },
  {
    id: SR.fleetSettings,
    pattern: '/settings/fleet',
    kind: 'utility',
    canonicalTitle: V.fleetPreferences,
    subtitle: SUB.fleetPreferencesUtility,
    objectType: 'settings',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.studioTools, V.fleetPreferences], [null, null]),
    artifacts: bundle('home', [V.studioTools, V.fleetPreferences], [null, null]),
    defaultSidebarLabel: V.fleetPreferences,
  },
  {
    id: SR.uxInsights,
    pattern: '/settings/ux-insights',
    kind: 'utility',
    canonicalTitle: V.uxInsights,
    subtitle: SUB.uxInsights,
    objectType: 'settings',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.adminInspect, V.uxInsights], [null, null]),
    artifacts: bundle('home', [V.adminInspect, V.uxInsights], [null, null]),
    defaultSidebarLabel: V.uxInsights,
  },
  {
    id: SR.agentRuntimeInspect,
    pattern: '/settings/agent-runtime',
    kind: 'utility',
    canonicalTitle: V.agentRuntimeInspect,
    subtitle: SUB.agentRuntimeInspect,
    objectType: 'settings',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.adminInspect, V.agentRuntimeInspect], [null, null]),
    artifacts: bundle('home', [V.adminInspect, V.agentRuntimeInspect], [null, null]),
    defaultSidebarLabel: V.agentRuntimeInspect,
  },
  {
    id: SR.governanceConnectors,
    pattern: '/governance/connectors',
    kind: 'canonical',
    canonicalTitle: 'Connector health',
    subtitle: SUB.connectorHealth,
    objectType: 'settings',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.adminInspect, 'Connector health'], [null, null]),
    artifacts: bundle('home', [V.adminInspect, 'Connector health'], [null, null]),
    defaultSidebarLabel: 'Connector health',
  },
  {
    id: SR.governanceAudit,
    pattern: '/governance/audit',
    kind: 'canonical',
    canonicalTitle: 'Audit log',
    subtitle: SUB.governanceAudit,
    objectType: 'settings',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.adminInspect, 'Audit log'], [null, null]),
    artifacts: bundle('home', [V.adminInspect, 'Audit log'], [null, null]),
    defaultSidebarLabel: 'Audit log',
  },
  {
    id: SR.featureShowcase,
    pattern: '/feature-showcase',
    kind: 'utility',
    canonicalTitle: V.featureShowcase,
    objectType: 'demo',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.adminInspect, V.featureShowcase], [null, null]),
    artifacts: bundle('home', [V.adminInspect, V.featureShowcase], [null, null]),
  },
  {
    id: SR.homeOverview,
    pattern: '/',
    kind: 'canonical',
    canonicalTitle: V.overview,
    objectType: 'workspace',
    lensVisibility: PRIMARY,
    flow: bundle('home', [V.home, V.overview], [null, null]),
    artifacts: bundle('home', [V.home, V.overview], [null, null]),
    defaultSidebarLabel: R.portfolioOverview,
    sidebar: {
      flow: { home: R.portfolioOverview },
      artifacts: { home: R.portfolioOverview },
    },
  },
]

const PLAN_TAB_RULES: StudioRouteDefinition[] = [
  {
    id: SR.planToday,
    planTab: 'today',
    kind: 'canonical',
    canonicalTitle: V.today,
    subtitle: PLAN_PAGE_COPY.todaySubtitle,
    objectType: 'plan',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.today], ['/', null]),
    artifacts: bundle('work', [V.work, V.today], ['/plan', null]),
    sidebar: {
      flow: { home: R.whatNeedsAttentionToday, work: V.today },
      artifacts: { work: V.today },
    },
  },
  {
    id: SR.planStory,
    planTab: 'story',
    kind: 'canonical',
    canonicalTitle: V.story,
    subtitle: SUB.planStory,
    objectType: 'plan',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.story], ['/plan', null]),
    artifacts: bundle('work', [V.work, V.story], ['/plan', null]),
    sidebar: {
      flow: { work: V.story },
      artifacts: { work: V.story },
    },
  },
  {
    id: SR.planSource,
    planTab: 'source',
    kind: 'canonical',
    canonicalTitle: V.sources,
    subtitle: SUB.planSource,
    objectType: 'plan',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.sources], ['/plan', null]),
    artifacts: bundle('work', [V.work, V.sources], ['/plan', null]),
    sidebar: {
      flow: { work: V.sources },
      artifacts: { work: V.sources },
    },
  },
  {
    id: SR.planDefault,
    planTab: 'plan',
    kind: 'canonical',
    canonicalTitle: V.planSummary,
    subtitle: PLAN_PAGE_COPY.planSubtitle,
    objectType: 'plan',
    lensVisibility: PRIMARY,
    flow: bundle('work', [V.work, V.planSummary], ['/', null]),
    artifacts: bundle('work', [V.work, V.planSummary], ['/', null]),
    sidebar: {
      flow: { work: R.planOverviewSidebar },
      artifacts: { work: R.allPlansSidebar },
    },
    defaultSidebarLabel: V.planSummary,
  },
]

const FALLBACK_DEF: StudioRouteDefinition = {
  id: SR.fallback,
  kind: 'canonical',
  canonicalTitle: V.workspace,
  objectType: 'workspace',
  lensVisibility: PRIMARY,
  flow: bundle('home', [V.workspace], [null]),
  artifacts: bundle('home', [V.workspace], [null]),
}

const PLAN_BY_TAB: Record<string, StudioRouteDefinition> = Object.fromEntries(
  PLAN_TAB_RULES.map((d) => [d.planTab!, d]),
) as Record<string, StudioRouteDefinition>

const ROUTE_BY_ID: Map<string, StudioRouteDefinition> = new Map()
for (const d of [...ORDERED_PATTERNS, ...PLAN_TAB_RULES, FALLBACK_DEF]) {
  ROUTE_BY_ID.set(d.id, d)
}

export type MatchedStudioRoute = {
  definition: StudioRouteDefinition
  params: Record<string, string | undefined>
}

export function matchStudioRoute(pathname: string, search: string): MatchedStudioRoute {
  if (pathname === '/plan') {
    const q = search.startsWith('?') ? search.slice(1) : search
    const tab = new URLSearchParams(q).get('tab') || 'plan'
    const def = PLAN_BY_TAB[tab] ?? PLAN_BY_TAB.plan
    return { definition: def, params: {} }
  }

  for (const def of ORDERED_PATTERNS) {
    if (!def.pattern) continue
    const m = matchPath({ path: def.pattern, end: def.end ?? true }, pathname)
    if (m) {
      return { definition: def, params: m.params as Record<string, string | undefined> }
    }
  }

  return { definition: FALLBACK_DEF, params: {} }
}

export function getStudioNavMeta(pathname: string, search: string, mode: NavMode): StudioNavBundle {
  const { definition } = matchStudioRoute(pathname, search)
  return mode === 'flow' ? definition.flow : definition.artifacts
}

export function getStudioRouteDefinition(pathname: string, search: string): StudioRouteDefinition {
  return matchStudioRoute(pathname, search).definition
}

/** Probe/debug route classification for the current URL (see `StudioRouteDefinition.probeKind`). */
export function routeProbeKindForPath(pathname: string, search: string): StudioRouteProbeKind | null {
  return matchStudioRoute(pathname, search).definition.probeKind ?? null
}

/** Registry rows marked as probe surfaces — keep in `App.tsx` routes; omit from core product smoke lists. */
export function listProbeRouteDefinitions(): StudioRouteDefinition[] {
  return ORDERED_PATTERNS.filter((d) => d.probeKind != null)
}

/**
 * Breadcrumb trail for the current route (no product suffix). Matches the body of `document.title` before ` · Studio`.
 * Story tab appends ` · {id}` when `id` is set.
 */
export function getStudioTitleTrail(pathname: string, search: string, mode: NavMode): string {
  const nav = getStudioNavMeta(pathname, search, mode)
  let trail = nav.breadcrumbs.join(' › ')
  if (pathname === '/plan') {
    const q = search.startsWith('?') ? search.slice(1) : search
    const sp = new URLSearchParams(q)
    if (sp.get('tab') === 'story') {
      const sid = sp.get('id')?.trim()
      if (sid) trail += ` · ${sid}`
    }
  }
  return trail
}

/** Browser tab / `document.title` (breadcrumb trail + product). */
export function getStudioDocumentTitle(pathname: string, search: string, mode: NavMode): string {
  return `${getStudioTitleTrail(pathname, search, mode)} · ${STUDIO_PRODUCT_NAME}`
}

export function studioRouteSidebarLabel(
  routeId: StudioRouteId,
  mode: NavMode,
  section: TopSectionId,
): string {
  const def = ROUTE_BY_ID.get(routeId)
  if (!def) {
    return routeId
  }
  const byPlacement = def.sidebar?.[mode]?.[section]
  if (byPlacement) return byPlacement
  if (def.defaultSidebarLabel) return def.defaultSidebarLabel
  return def.canonicalTitle
}

/** Section heading in the left rail (aligned with top-nav primary tabs). */
// --- Registry validation (tests + CI guard) ---

export function isParameterizedPattern(pattern: string): boolean {
  return pattern.includes(':') || pattern.includes('*')
}

export type StudioRouteRegistryIssue = { code: string; detail: string }

export function validateStudioRouteRegistry(): StudioRouteRegistryIssue[] {
  const issues: StudioRouteRegistryIssue[] = []
  const seenIds = new Set<string>()

  const allDefs = [...ORDERED_PATTERNS, ...PLAN_TAB_RULES, FALLBACK_DEF]
  for (const d of allDefs) {
    if (seenIds.has(d.id)) {
      issues.push({ code: 'dup_id', detail: `duplicate route id: ${d.id}` })
    }
    seenIds.add(d.id)
  }

  for (const d of allDefs) {
    if (d.kind === 'alias' || d.kind === 'legacy') {
      if (!d.canonicalRouteId) {
        issues.push({ code: 'alias_target', detail: `${d.id} missing canonicalRouteId` })
      } else if (!ROUTE_BY_ID.has(d.canonicalRouteId)) {
        issues.push({
          code: 'alias_target',
          detail: `${d.id} canonicalRouteId ${d.canonicalRouteId} not found`,
        })
      }
    }
  }

  const staticCanonicalTitles: string[] = []
  for (const d of allDefs) {
    if (d.kind !== 'canonical' && d.kind !== 'utility') continue
    if (d.planTab) {
      staticCanonicalTitles.push(d.canonicalTitle)
      continue
    }
    if (!d.pattern) continue
    if (isParameterizedPattern(d.pattern)) continue
    staticCanonicalTitles.push(d.canonicalTitle)
  }
  const titleCounts = new Map<string, number>()
  for (const t of staticCanonicalTitles) {
    titleCounts.set(t, (titleCounts.get(t) ?? 0) + 1)
  }
  for (const [t, n] of titleCounts) {
    if (n > 1) {
      issues.push({
        code: 'dup_canonical_title',
        detail: `canonicalTitle "${t}" used ${n} times (static routes)`,
      })
    }
  }

  return issues
}

/** All registered route ids (for drift checks). */
export function listStudioRouteIds(): string[] {
  return [...ROUTE_BY_ID.keys()]
}
