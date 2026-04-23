import type { NavMode } from './workspaceLensCookie'
import type { SideNavEntry, TopSectionId } from './navPlacementTypes'
import { mergePlanningScopeIntoTo } from '../lib/planningClusterScope'
import {
  ADMIN_INSPECT_COPY,
  REGISTRY,
  STUDIO_ONBOARDING,
  STUDIO_VOCAB as V,
} from './studioVisibleCopy'
import { SR, studioRouteSidebarLabel as lbl } from './studioRouteRegistry'
import { STUDIO_DOCS_HOME } from '../util/staticPreviewUrl'
import { blueprintsWizardFeatureEnabled } from '../util/experimentalFlags'
import { flowArtifactsHelpHomeTo } from './studioHelpQuery'

const HOME_LABEL = V.home

export type { SideNavEntry, TopSectionId } from './navPlacementTypes'

/** @deprecated Lens is no longer switched from primary tabs; kept for TopNavItem typing. */
export type TopNavLens = NavMode

export type TopNavItem = {
  id: TopSectionId
  label: string
  /** Default entry when clicking the top tab */
  to: string
  /** Legacy field — primary tabs no longer drive lens changes (see Settings → Studio view). */
  lens: TopNavLens
}

const DOCS = STUDIO_DOCS_HOME

/** Browse URL: first workspace site when known, else all-sites list. */
export function browsePathForSite(siteName?: string | null): string {
  const n = siteName?.trim()
  if (!n) return '/websites'
  return `/websites/browse/${encodeURIComponent(n)}`
}

/** Sprint UX1 — single primary strip (task-based). */
export const topNavPrimary: TopNavItem[] = [
  { id: 'home', label: HOME_LABEL, to: '/', lens: 'flow' },
  { id: 'work', label: V.work, to: '/plan', lens: 'flow' },
  { id: 'projects', label: V.projects, to: '/projects', lens: 'flow' },
  { id: 'knowledge', label: V.knowledge, to: '/tutorials', lens: 'flow' },
  { id: 'publish', label: V.publish, to: '/websites', lens: 'flow' },
]

export function getTopNav(_mode: NavMode): TopNavItem[] {
  return topNavPrimary
}

/** @deprecated Use {@link getTopNav} — returns the unified primary nav. */
export const topNavFlow = topNavPrimary
/** @deprecated Use {@link getTopNav}. */
export const topNavArtifacts = topNavPrimary

function sideNavForSection(
  section: TopSectionId,
  mode: NavMode,
  projectName?: string,
  browseSiteName?: string | null,
): SideNavEntry[] {
  const pn = projectName?.trim()
  switch (section) {
    case 'home':
      return [
        { label: lbl(SR.homeOverview, mode, 'home'), to: '/' },
        { label: lbl(SR.planToday, mode, 'home'), to: '/plan?tab=today' },
        { label: lbl(SR.boardHub, mode, 'home'), to: '/board' },
        { label: lbl(SR.projectsIndex, mode, 'home'), to: '/projects' },
      ]
    case 'work':
      return [
        { label: lbl(SR.planToday, mode, 'work'), to: '/plan?tab=today' },
        { label: lbl(SR.planDefault, mode, 'work'), to: '/plan' },
        { label: lbl(SR.boardHub, mode, 'work'), to: '/board' },
        { label: lbl(SR.timeline, mode, 'work'), to: '/timeline' },
        { label: lbl(SR.planStory, mode, 'work'), to: '/plan?tab=story' },
        { label: lbl(SR.planSource, mode, 'work'), to: '/plan?tab=source' },
        { label: lbl(SR.methodologyReadiness, mode, 'work'), to: '/knowledge/methodology/readiness' },
        { label: lbl(SR.planMatrix, mode, 'work'), to: '/plan/matrix', sidebarGroup: 'work_advanced' },
        { label: lbl(SR.wbsIndex, mode, 'work'), to: '/wbs', sidebarGroup: 'work_advanced' },
        { label: lbl(SR.wbsView, mode, 'work'), to: '/wbs/view', sidebarGroup: 'work_advanced' },
        { label: lbl(SR.roadmapSection, mode, 'work'), to: '/roadmap-section', sidebarGroup: 'work_advanced' },
        {
          label: 'Roadmaps summary (full workspace)',
          href: '/roadmaps/summary',
          sidebarGroup: 'work_advanced',
        },
      ]
    case 'projects':
      return [
        { label: lbl(SR.projectsIndex, mode, 'projects'), to: '/projects' },
        {
          label: lbl(SR.projectDashboard, mode, 'projects'),
          to: pn ? `/projects/${pn}` : '/projects',
          disabled: !pn,
        },
        {
          label: lbl(SR.projectCharts, mode, 'projects'),
          to: pn ? `/projects/${pn}/charts` : '/projects',
          disabled: !pn,
        },
        {
          label: lbl(SR.projectStrategy, mode, 'projects'),
          to: pn ? `/projects/${pn}/strategy` : '/projects',
          disabled: !pn,
        },
        {
          label: REGISTRY.projectLinkedNotes,
          to: pn ? `/workspace-md?contextProject=${encodeURIComponent(pn)}` : '/workspace-md',
        },
      ]
    case 'knowledge':
      return [
        { label: lbl(SR.tutorials, mode, 'knowledge'), to: '/tutorials', sidebarGroup: 'knowledge_learn' as const },
        { label: lbl(SR.docsEmbed, mode, 'knowledge'), to: DOCS, sidebarGroup: 'knowledge_learn' as const },
        { label: lbl(SR.workspaceMd, mode, 'knowledge'), to: '/workspace-md', sidebarGroup: 'knowledge_evidence' as const },
        {
          label: lbl(SR.methodologyEvidence, mode, 'knowledge'),
          to: '/knowledge/methodology/evidence',
          sidebarGroup: 'knowledge_evidence' as const,
        },
        {
          label: lbl(SR.methodologyDecisions, mode, 'knowledge'),
          to: '/knowledge/methodology/decisions',
          sidebarGroup: 'knowledge_govern' as const,
        },
        {
          label: lbl(SR.agenticBridge, mode, 'knowledge'),
          to: '/knowledge/agentic-bridge',
          sidebarGroup: 'knowledge_govern' as const,
        },
        ...(blueprintsWizardFeatureEnabled()
          ? [
              {
                label: lbl(SR.blueprintsWizard, mode, 'knowledge'),
                to: '/blueprints/wizard',
                sidebarGroup: 'knowledge_build' as const,
              },
            ]
          : []),
      ]
    case 'publish':
      return [
        { label: lbl(SR.websitesIndex, mode, 'publish'), to: '/websites', sidebarGroup: 'publish_sites' as const },
        {
          label: lbl(SR.websitesBrowse, mode, 'publish'),
          to: browsePathForSite(browseSiteName),
          sidebarGroup: 'publish_sites' as const,
        },
        { label: lbl(SR.blogIndex, mode, 'publish'), to: '/blog', sidebarGroup: 'publish_stories' as const },
        {
          label: 'Blog home (live)',
          href: 'https://forgesdlc.com/blog/index.html',
          external: true,
          sidebarGroup: 'publish_stories' as const,
        },
      ]
    default:
      return []
  }
}

export function getSideNavEntries(
  section: TopSectionId,
  mode: NavMode,
  projectName?: string,
  browseSiteName?: string | null,
): SideNavEntry[] {
  return sideNavForSection(section, mode, projectName, browseSiteName)
}

/** Preserve planning scope (`repo`, `wbs_p`, `roadmap_p`, `id`) on in-app sidebar targets. */
export function withPlanningScopeOnSideNavEntries(
  entries: SideNavEntry[],
  currentSearch: string,
): SideNavEntry[] {
  if (!currentSearch || currentSearch === '?') return entries
  return entries.map((e) => {
    if (!e.to || e.href) return e
    return { ...e, to: mergePlanningScopeIntoTo(e.to, currentSearch) }
  })
}

/** Settings (gear) — grouped for Sprint UX7 (preferences vs admin vs inspect). */
export type SettingsGearSection = { heading: string; entries: SideNavEntry[] }

const gearWorkspaceAdmin: SideNavEntry[] = [
  { label: 'Workspace settings', href: DOCS, external: true },
  { label: 'Access & roles', href: DOCS, external: true },
]

const gearInspectAdvanced: SideNavEntry[] = [
  { label: 'Connector health', to: '/governance/connectors' },
  { label: 'Audit log', to: '/governance/audit' },
  { label: V.advancedReporting, to: '/overview/charts' },
  { label: 'Tools & automation', to: '/toolset' },
  { label: 'UX diagnostics', to: '/settings/ux-insights' },
  { label: V.agentRuntimeInspect, to: '/settings/agent-runtime' },
]

const gearLabsProbes: SideNavEntry[] = [
  { label: `${V.featureShowcase} (lab)`, to: '/feature-showcase' },
  { label: 'Site preview (empty lab)', to: '/view/local-site/' },
  {
    label: `${STUDIO_ONBOARDING.flowArtifactsChipLabel} (overview deep link)`,
    to: flowArtifactsHelpHomeTo(),
  },
  ...(blueprintsWizardFeatureEnabled()
    ? ([
        {
          label: 'Blueprints Wizard session (probe)',
          to: '/blueprints/wizard/session/probe',
        },
      ] satisfies SideNavEntry[])
    : []),
]

/** @deprecated Prefer {@link getSettingsGearMenuSections}. */
export const adminSideNavEntries: SideNavEntry[] = [
  ...gearWorkspaceAdmin,
  ...gearInspectAdvanced,
  ...gearLabsProbes,
]

export const adminSideNavArtifacts: SideNavEntry[] = adminSideNavEntries

export function getAdminSideNav(_mode: NavMode): SideNavEntry[] {
  return adminSideNavEntries
}

export function getSettingsGearMenuSections(_mode: NavMode): SettingsGearSection[] {
  void _mode
  return [
    { heading: ADMIN_INSPECT_COPY.settingsSectionAdmin, entries: gearWorkspaceAdmin },
    { heading: ADMIN_INSPECT_COPY.settingsSectionInspect, entries: gearInspectAdvanced },
    { heading: ADMIN_INSPECT_COPY.settingsSectionLabs, entries: gearLabsProbes },
  ]
}
