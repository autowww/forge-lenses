/**
 * Central user-visible copy for Lenses Studio. Import from here (and from
 * `studioRouteRegistry` for route-derived sidebar labels) instead of scattering literals.
 *
 * - `STUDIO_VOCAB` — canonical nouns for consistent naming.
 * - `STUDIO_GLOSSARY` — short/long text for tooltips and screen readers.
 * - `FULL_WORKSPACE_UI` — links to the non-Studio Lenses web UI (URLs unchanged).
 */
import type { TopSectionId } from './navPlacementTypes'

export const STUDIO_PRODUCT_NAME = 'Forge Studio'

/** Canonical nouns — use these as the primary name for the same object everywhere. */
export const STUDIO_VOCAB = {
  /** Primary tab label — matches top navigation “Home”. */
  home: 'Home',
  /** Header / chrome: short label for the grounded assistant entry. */
  copilot: 'Copilot',
  plan: 'Plan',
  /** Default `/plan` surface (backlog + readiness); distinct from Delivery “Today” and from matrix/timeline. */
  planSummary: 'Plan summary',
  today: 'Today',
  story: 'Story',
  sources: 'Sources',
  roadmap: 'Roadmap',
  timeline: 'Timeline',
  board: 'Board',
  boards: 'Boards',
  project: 'Project',
  projects: 'Projects',
  projectDashboard: 'Project dashboard',
  workspace: 'Workspace',
  workspaceCharts: 'Workspace charts',
  /** Cross-repo charts surface (`/overview/charts`) — prefer in product copy over internal “workspace charts”. */
  advancedReporting: 'Advanced reporting',
  /** Markdown in the repo (route remains `/workspace-md`). */
  workspaceNotes: 'Workspace notes',
  /** Project subnav — distinct from generic “workspace notes”. */
  projectEvidenceBrowse: 'Evidence (browse)',
  knowledge: 'Knowledge',
  tutorials: 'Tutorials',
  workBreakdown: 'Work breakdown',
  delivery: 'Delivery',
  automation: 'Automation',
  automationRun: 'Automation run',
  roadmapMatrix: 'Roadmap matrix',
  architectureStrategy: 'Architecture & repo strategy',
  projectBranching: 'Branching',
  repositoryCharts: 'Repository charts',
  /** Grounded orchestration assistant (search index + graph + delivery payloads). */
  llmChat: 'Lenses Copilot',
  /** AI Setup (route `/settings/llm`; legacy internal id `llmPreferences`). */
  llmPreferences: 'AI Setup',
  /** Forge Fleet orchestrator (route `/settings/fleet`). */
  fleetPreferences: 'Forge Fleet',
  search: 'Search',
  websites: 'Websites',
  siteBrowse: 'Site browse',
  sitePreview: 'Site preview',
  blog: 'Blog',
  overview: 'Overview',
  /** Sprint UX1 — primary “Work” area (plan, boards, timeline, readiness). */
  work: 'Work',
  /** Markdown documentation scan, score, and guided fixes for one repository. */
  docsHealth: 'Docs health',
  /** Breadcrumb / route label for the governed remediation console (same scope as documentationRemediationRun). */
  docsHealthSession: 'Documentation remediation run',
  /** H1 for the remediation session console — governed run, not a raw log. */
  documentationRemediationRun: 'Documentation remediation run',
  /** One-cluster-at-a-time guided remediation (Master). */
  docsHealthMaster: 'Docs Master',
  /** Sprint UX1 — sites, blog, and shipped outputs. */
  publish: 'Publish',
  boardEditor: 'Board editor',
  /** Workspace-root shell scripts index (`/toolset`). */
  toolset: 'Toolset',
  blogPost: 'Blog post',
  lensesReference: 'Lenses reference',
  blueprintsWizard: 'Blueprints Wizard',
  featureShowcase: 'Feature showcase',
  /** Forge Platform Self-Host — `.forge/runs/` file store surfaced in Studio. */
  forgePlatformRun: 'Forge Platform run',
  /** Local browser UX diagnostics (route/sidebar/state counts). */
  uxInsights: 'UX insights',
  /** Provider dispatch, token ledger, and agent sessions (Admin & inspect). */
  agentRuntimeInspect: 'Agent runtime',
  /**
   * Breadcrumb parent for global header utilities (Search, Chat, AI Setup).
   * Not a routable page—only IA framing.
   */
  studioTools: 'Tools',
  /** Breadcrumb parent for workspace admin, diagnostics, automation, and cross-repo charts (Sprint UX7). */
  adminInspect: 'Admin & inspect',
  /** Orchestration graph — methodology artifacts and ingested evidence (Sprint B2). */
  methodologyEvidenceRegistry: 'Evidence registry',
  methodologyDecisionsRegistry: 'Decision registry',
  methodologyGraphRecord: 'Graph record',
  methodologyReadiness: 'Release readiness',
  /** Sprint B3 — agent registry, drift, runs (orchestration graph). */
  agenticBridge: 'Agentic bridge',
} as const

/** Sprint UX7 — standard framing for advanced / admin routes (who / blast radius / when / safety / return). */
export type AdvancedSurfaceFrame = {
  audience: string
  affects: string
  whenToUse: string
  safety: string
  returnTo: string
  returnLabel: string
}

export const ADVANCED_SURFACE_FRAMES = {
  advancedReporting: {
    audience: 'Operators, program leads, and workspace admins reviewing portfolio signals.',
    affects: 'Nothing on disk or in integrations—read-only charts from the workspace scan bundle.',
    whenToUse: 'Weekly health reviews, compliance snapshots, or before broad stakeholder readouts.',
    safety: 'Read-only in this Studio view.',
    returnTo: '/',
    returnLabel: STUDIO_VOCAB.overview,
  },
  connectorHealth: {
    audience: 'Integration owners, platform engineers, and admins checking delivery adapters.',
    affects: 'Read-only health checks against configured connectors; does not change credentials from this page.',
    whenToUse: 'After configuration changes, during incident triage, or when CI or release signals look wrong.',
    safety: 'Read-only here unless you follow outbound links to external consoles.',
    returnTo: '/projects',
    returnLabel: STUDIO_VOCAB.projects,
  },
  auditLog: {
    audience: 'Workspace super-admins and security reviewers.',
    affects: 'Sensitive operational history (access, connectors, and AI-related actions) for this workspace.',
    whenToUse: 'After policy changes, suspected misuse, or when proving who did what for compliance.',
    safety: 'Read-only append-only log in Studio; retention depends on the Lenses host.',
    returnTo: '/governance/connectors',
    returnLabel: 'Connector health',
  },
  toolset: {
    audience: 'Automation-minded engineers running approved workspace scripts.',
    affects: 'Scripts may modify files, call the network, or run host commands depending on their contents.',
    whenToUse: 'When you have an explicit runbook and need script output in-repo.',
    safety: 'Potentially destructive—review each script and prefer a safe branch or environment first.',
    returnTo: '/projects',
    returnLabel: STUDIO_VOCAB.projects,
  },
  uxDiagnostics: {
    audience: 'Developers, QA, and support capturing this browser session behavior.',
    affects: 'Session-only counters in this tab; clearing affects only local telemetry.',
    whenToUse: 'Dogfood weeks, regressions after navigation changes, or attaching a bundle to a bug.',
    safety: 'Read-only unless you explicitly clear the buffer.',
    returnTo: '/',
    returnLabel: STUDIO_VOCAB.overview,
  },
  llmPreferences: {
    audience: 'Anyone making Chat, Ask, or copilot work in this workspace.',
    affects: 'Which models answer you on this Lenses host—credentials stay local, not in the browser.',
    whenToUse: 'First-time setup, after switching laptops, or when a provider stops responding.',
    safety: 'Wrong settings usually mean “no AI answer” until fixed; they do not change your repos from this page alone.',
    returnTo: '/chat',
    returnLabel: STUDIO_VOCAB.llmChat,
  },
  featureShowcaseLab: {
    audience: 'Design QA and stakeholders reviewing experimental layout demos.',
    affects: 'Visual-only demo content; no workspace repository data.',
    whenToUse: 'Layout polish reviews or demos of Studio chrome experiments.',
    safety: 'Read-only demo.',
    returnTo: '/',
    returnLabel: STUDIO_VOCAB.overview,
  },
} as const satisfies Record<string, AdvancedSurfaceFrame>

/** Labels only used inside `studioRouteRegistry` (breadcrumbs, sidebars, secondary titles). */
export const REGISTRY = {
  workspaceActivityCharts: 'Workspace activity charts',
  perProjectActivity: 'Per-project activity',
  browseAndPreview: 'Browse and preview',
  allSites: 'All sites',
  workBreakdownDetailTitle: 'Work breakdown (detail)',
  /** Breadcrumb leaf — must match {@link workBreakdownDetailTitle} for H1 alignment. */
  workBreakdownDetailBc: 'Work breakdown (detail)',
  /** Breadcrumb leaf for `/wbs` — matches {@link STUDIO_VOCAB.workBreakdown}. */
  workBreakdownBc: 'Work breakdown',
  roadmapsTimeline: 'Roadmaps timeline',
  roadmapSectionPreview: 'Roadmap section preview',
  sectionPreview: 'Section preview',
  boardsEditor: 'Editor',
  executionBoards: 'Execution boards',
  allBoards: 'All boards',
  allPosts: 'All posts',
  lensesReferenceDocs: 'Lenses reference docs',
  knowledgeReferenceBc: 'Reference',
  sitesPreviewBc: 'Preview',
  workspaceNotesDeepLink: 'Deep link (same as Workspace notes)',
  blueprintsWizardSession: 'Blueprints Wizard session',
  wizardExperimentalSidebar: 'Blueprints Wizard (experimental)',
  llmChatDemo: 'Lenses Copilot',
  showcase: 'Showcase',
  portfolioOverview: 'Portfolio overview',
  whatNeedsAttentionToday: 'What needs attention today',
  planOverviewSidebar: 'Plan summary',
  allPlansSidebar: 'All plans',
  allProjectsFlow: 'All projects',
  /** Sidebar: open workspace markdown with optional project context query. */
  /** Project nav + header: markdown evidence in workspace (not tutorials / not decision graph). */
  /** Linked from project nav — browse-first framing. */
  projectLinkedNotes: 'Evidence (browse)',
  /** Knowledge sidebar: distinguish allowlisted markdown from tutorial/reference docs. */
  workspaceNotesEvidenceSidebar: 'Workspace notes (evidence)',
  methodologyEvidenceSidebar: 'Evidence registry (graph)',
  methodologyDecisionsSidebar: 'Decisions (graph)',
  methodologyReadinessSidebar: 'Release readiness (gaps)',
  agenticBridgeSidebar: 'Agentic bridge',
} as const

/**
 * Information architecture copy: Knowledge reference vs evidence vs experimental AI.
 * Search/Chat/LLM prefs use `groupId: home` for the sidebar but breadcrumbs use {@link STUDIO_VOCAB.studioTools}
 * as parent (see `studioRouteRegistry`) so they read as global tools, not handbook content.
 */
export const STUDIO_IA = {
  searchPageSubtitle:
    'Advanced mode: full result lists, paging, and repository filters. Use header Find for quick lookup and navigation.',
  llmChatPageSubtitle:
    'Long-form Copilot: threads, history, and optional legacy chat. Quick grounded questions: use header Ask. Provider and model defaults live under AI Setup.',
  llmPreferencesPageSubtitle:
    'Wire model sources on this machine, then try Chat. Optional for Plan and Boards unless you rely on AI answers.',
  fleetPreferencesPageSubtitle:
    'One or more Fleet base URLs with bearer auth, priority, and optional CPU/memory ceilings — Lenses skips busy or unhealthy nodes. Env vars still override with a single node.',
  tutorialsPageSubtitle:
    'Handbooks and guides served as reference. Different from workspace notes, which are allowlisted markdown logs and evidence in your repository tree.',
  tutorialsPagePurposeLearn:
    'Onboarding and long-form guides discovered in your workspace scan—pair with Lenses reference for product docs, and with Workspace notes for repo evidence.',
  lensesReferenceReadingSubtitle:
    'Embedded Lenses documentation (reference). For markdown work logs, charge notes, or ADRs in your workspace, open Workspace notes.',
  lensesReferencePurposeLearn:
    'In-product Lenses documentation—use for how Studio and lenses behave; use Tutorials for methodology handbooks and Workspace notes for repo evidence.',
  workspaceMdEvidenceVersusRef:
    'Evidence hub: browse indexed markdown from your tree. Docs = Tutorials + Lenses reference. Decisions = methodology graph registry.',
  wizardExperimentalLead:
    'Experimental, AI-assisted flow; drafts stay on the machine running Lenses (not in git). Use alongside—not instead of—normal planning, delivery, and reference material.',
} as const

/** Sprint UX6 — Knowledge sidebar grouping and landing hints (Learn / Evidence / Govern / Build). */
export const KNOWLEDGE_SECTION_NAV = {
  sidebarHint:
    'Knowledge is grouped by job: learn from handbooks and reference, browse evidence, review governance, or run the optional Blueprints Wizard—Plan and Today stay the system of record for delivery.',
  learnHeading: 'Learn',
  learnHint: 'Onboarding and product reference—curated or embedded read-only.',
  evidenceHeading: 'Evidence',
  evidenceHint: 'Markdown in your repo plus methodology-linked proof when the workspace exposes it.',
  governHeading: 'Govern',
  governHint: 'Signed decisions and how agents attach to your workspace—review before high-risk automation.',
  buildHeading: 'Build & bootstrap',
  buildHint: 'Guided Blueprints sessions for early framing; export outcomes into normal Plan and project work.',
} as const

/** Sprint UX6 — Publish sidebar grouping (shipped sites vs stories). */
export const PUBLISH_SECTION_NAV = {
  sidebarHint:
    'Publish is where shipped output lives: static or Firebase sites from your scan, and the blog mirror for release-style stories—tie them back to Today and evidence when you announce work.',
  shippedHeading: 'Sites & previews',
  shippedHint: 'Built HTML your workspace already knows about—preview before sharing links.',
  storiesHeading: 'Stories & updates',
  storiesHint: 'Release notes and narrative posts; draft in Copilot from Plan or evidence, then refresh the feed.',
} as const

/** Embedded Copilot defaults for Knowledge / Publish surfaces (Sprint UX6). */
export const KNOWLEDGE_PUBLISH_COPILOT = {
  tutorialsHub:
    'Classify these handbook rows as tutorial vs reference vs evidence, and suggest which Knowledge link a new teammate should open first.',
  lensesReference:
    'Summarize how Lenses reference docs differ from Workspace notes (evidence) and from the decision registry.',
  methodologyEvidence:
    'Explain what belongs in this registry versus repo markdown in Workspace notes, in plain language for a tech lead.',
  methodologyDecisions:
    'List the top decisions implied by this registry view and what sign-off or review is still missing.',
  releaseReadiness:
    'Explain this readiness view for a release manager: what the gaps mean, what evidence to pull, and what to verify in Plan before sign-off.',
  agenticBridge:
    'Explain what the Agentic bridge is for in one paragraph, when to use Plan vs this page, and one safe first action.',
  publishWebsites:
    'Explain how these sites relate to workspace work and suggest one sentence for stakeholders about what each site is for.',
  publishBlog:
    'Draft short release notes or a blog intro from themes in Today and evidence—say what is assumed unknown.',
  wizardHub:
    'Explain when Blueprints Wizard is appropriate versus Plan summary, boards, or project dashboards, and what a user should expect to leave the session with.',
} as const

/**
 * Copy for Blueprints Wizard **session probe** URLs (`/blueprints/wizard/session/:id`).
 * Routes stay registered for developers and automation; UI must not degrade to raw full-page spinners.
 */
/** Blueprints Wizard hub — confident entry while keeping experimental status visible (Sprint UX6). */
export const BLUEPRINTS_WIZARD_HUB_COPY = {
  valueLead:
    'Walk a structured Blueprints mission (idea → contribution) with AI nudges and checkpoints. You leave with a session document you can copy into Plan, boards, or tickets—not a replacement for those systems.',
  whenToUse:
    'Use this for early discovery, workshop facilitation, or teaching the Blueprints flow. Use Plan summary, Today, and project dashboards for ongoing delivery and status.',
  emptySessionsDetail:
    'No saved drafts on this server yet. Start a session to capture a guided run; drafts stay under local server storage until you export or discard them.',
} as const

export const WIZARD_PROBE_COPY = {
  layoutCheckingServer: 'Checking whether the Blueprints Wizard API is enabled on this Lenses server…',
  sessionLoading: 'Fetching the session document from the wizard API…',
  sessionLoadTimeout:
    'Loading took too long. The server may be unreachable, blocked, or the session id invalid. Retry or return to the wizard hub.',
  sessionNotFound:
    'No wizard session exists for this id. Use a link from the Blueprints Wizard hub, create a new session, or verify the server still has this draft.',
  devAccessibilityNote:
    'Session URLs are intentionally registered for developers and automated probes (E2E, API checks). They are not primary navigation—expect framed errors instead of endless loading when an id is wrong or expired.',
} as const

/**
 * Canonical utility taxonomy: Search, Chat, and AI Setup are **global header tools** (always visible).
 * Section sidebars list them once under **Tools** as secondary entry points; Knowledge holds tutorials/reference.
 */
export const STUDIO_UTILITIES = {
  sidebarGroupLabel: STUDIO_VOCAB.studioTools,
  searchEmptyTitle: 'Search your workspace',
  searchEmptyBody:
    'Use the search field in the header or below, then press Enter. Results come from the workspace index—distinct from Tutorials or Lenses reference in Knowledge.',
  searchShortcutHint: 'Focus header search: Ctrl+K or ⌘K (when not typing in a field).',
  chatLandingBody:
    'Same chat entry as the header on every screen—use this page for longer threads, provider checks, and model overrides.',
  llmPrefsFraming:
    'Preferences are stored locally (see paths in the form). Use the gear menu for a quick modal, or this page when you want the full layout.',
} as const

export type StudioGlossaryId =
  | 'story'
  | 'sources'
  | 'timelineVsRoadmap'
  | 'workspaceNotes'
  | 'fullWorkspaceUi'
  | 'roadmapMatrix'
  | 'planningCluster'
  | 'workspaceLens'

export const STUDIO_GLOSSARY: Record<
  StudioGlossaryId,
  { title: string; short: string; long: string }
> = {
  story: {
    title: 'Story',
    short: 'One prioritized work item from your plan backlog.',
    long: 'A story is a single WBS-backed work item. Use the Story tab to inspect its tasks, status, and details.',
  },
  sources: {
    title: 'Sources',
    short: 'Files and markdown the plan view reads (roadmaps, outlines).',
    long: 'Sources are roadmap outlines and related documents Lenses loads when building this plan scope.',
  },
  timelineVsRoadmap: {
    title: 'Timeline vs roadmap',
    short: 'Timeline shows dates and dependencies; roadmaps show themes and matrix rollups.',
    long: 'Open Timeline for a schedule-oriented view. Use Roadmap matrix and roadmap summaries for narrative and cross-repository coverage.',
  },
  workspaceNotes: {
    title: 'Workspace notes',
    short: 'Workspace evidence: allowlisted markdown (logs, charge, journals) — not tutorials.',
    long: 'Workspace notes are evidence-grade markdown served when paths are allowlisted (charge, journal, ember-logs, forge-logs). Tutorials and Lenses reference live under Knowledge as docs, not here.',
  },
  fullWorkspaceUi: {
    title: 'Full workspace UI',
    short: 'Original multi-pane Lenses pages outside the Studio shell.',
    long: 'Some workflows still use the full Lenses layout. Links preserve your query string so scope stays aligned.',
  },
  roadmapMatrix: {
    title: 'Roadmap matrix',
    short: 'Stories mapped across repositories.',
    long: 'The matrix summarizes which stories touch which repositories at a glance.',
  },
  planningCluster: {
    title: 'Work journey',
    short: 'Today, Plan, Boards, Timeline, and Readiness share one scope — move without changing tools.',
    long: 'Use the Work strip to move between execution and planning surfaces. Repository, backlog, roadmap, and work item ids stay in the URL until you change them.',
  },
  workspaceLens: {
    title: 'Flow vs Artifacts',
    short:
      'Flow orders the top nav by delivery journey; Artifacts groups the same URLs by object type (plans, boards, sites, blog, knowledge).',
    long:
      'The workspace lens toggle does not change your data—only how primary navigation and breadcrumbs are labeled. Flow follows planning → delivery → projects; Artifacts clusters plans, roadmaps, boards, and sites separately. Pick whichever matches how you are thinking about the work.',
  },
}

/** Delivery lens vs Planning; board hub framing; shortcut labeling. */
export const DELIVERY_LENS = {
  todayVersusPlanning:
    'Today is the execution pulse; Plan holds roadmap and backlog structure — both are one Work journey with the same scope.',
  boardHubLeadFlow:
    'Sticker boards for active execution—freshness and ownership here. Plan summary, timeline, and readiness stay in the same Work scope via the strip above.',
  boardHubLeadArtifacts:
    'Board portfolio: templates, registry hygiene, project links, and Studio or full-workspace editors.',
  shortcutsSectionTitle: 'More Work and workspace links',
  shortcutsSectionLead:
    'Jump to Today, Plan, or timeline with the same scope when your URL includes backlog picks.',
  executionSectionTitle: 'Execution and planning shortcuts',
  executionSectionLead:
    'Boards are execution home; other cards jump across the Work journey with the same scope when possible.',
  todayBandShortcutTitle: 'Planning or workspace shortcut',
  boardManagementSectionTitle: 'Board management',
  boardManagementSectionLead:
    'Sort, filter, and expand rows to inspect template, ACL counts, and editors. Registry paths are optional detail—use Inspect or Technical details on the Boards hub when you need the file location.',
  activeBoardsFilterLabel: 'Active',
  staleBoardsFilterLabel: 'Stale',
  createBoardSectionTitle: 'Create a new board',
  createBoardSectionLead: 'Adds an entry to the registry; open the Studio or full editor to set columns and stickers.',
  boardEditorExecutionLead:
    'Studio execution editor—edit columns and stickers here; portfolio hygiene stays on the boards hub.',
} as const

/** Evidence vs reference vs governance — used on hub, project, and rails. */
export const EVIDENCE_IA = {
  evidenceDefinition:
    'Evidence is material in your workspace that supports status: charge logs, journals, Ember logs, forge-logs, and similar allowlisted markdown.',
  docsDefinition:
    'Docs are reference and onboarding: Tutorials (handbooks) and Lenses reference — curated or embedded read-only, not arbitrary repo files.',
  decisionsDefinition:
    'Decisions are intentional governance records in the methodology graph (stored with this workspace) — distinct from markdown evidence files.',
  hubCompareHeading: 'Evidence, docs, and decisions',
  hubBrowseHeading: 'Browse indexed evidence',
  hubBrowseLead:
    'Open files from the scan below — pinned and recent lists stay above the full index. Path entry is an advanced option at the bottom of this page.',
  hubSuggestedHeading: 'Suggested opens',
  hubSuggestedLead: 'Quick links into typical evidence files for this workspace (no typing required).',
  methodologyEvidenceCta: 'Methodology evidence (graph)',
  methodologyDecisionsCta: 'Decision registry (graph)',
  portfolioFilterEvidenceLink: 'Evidence signal',
  copilotProjectHealth:
    'Summarize this repository’s health for a stakeholder in plain language: top risks, what changed recently, and the next 2–3 actions. Then suggest which linked work or evidence paths (charge, journal, logs) would best support those actions, and name any decisions or release links that should be checked in the methodology graph.',
  copilotEvidenceExtract:
    'From the evidence context implied by this page: extract risks, decisions, and follow-ups in short bullets. If the path is unknown, say what is missing.',
} as const

/**
 * Project object-home: list vs dashboard, evidence naming, and in-page nav copy.
 * Evidence = allowlisted markdown served by Lenses (`/workspace-md`)—charge logs, ADRs, handbooks—not a separate repo object.
 */
export const PROJECT_OBJECT_HOME = {
  listVersusDashboardLead:
    'Pick a repository for an action-first dashboard: health, risks, PR signals, and workspace evidence — then open charts or strategy when you need depth.',
  projectDashboardSubtitle:
    'Health, risks, PR signals, and workspace evidence for this repository — session and adapter detail stay under Inspect.',
  atAGlanceTitle: 'At a glance',
  atAGlanceRisksTitle: 'Risks & attention',
  atAGlanceRisksEmpty: 'No automated risk flags in the current snapshot — still review charts and evidence periodically.',
  atAGlanceNextTitle: 'Suggested next step',
  atAGlanceMetricsTitle: 'Snapshot',
  atAGlanceLinkedWorkTitle: 'Linked work',
  atAGlanceLinkedWorkEmpty: 'No story ↔ branch ↔ PR links in the workflow payload yet.',
  atAGlanceEvidenceTitle: 'Workspace evidence',
  atAGlanceEvidenceLead:
    'Proof and supporting markdown (charge, journals, logs) indexed for this repository — browse without typing paths.',
  atAGlanceRecentTitle: 'Recent activity',
  atAGlanceRecentLead:
    'Snapshot counts come from the latest scan. Use charts for PR, gate, and security trends over time.',
  atAGlanceMethodologyTitle: 'Decisions & methodology',
  atAGlanceMethodologyLead:
    'Governance records and graph-backed registries are separate from markdown evidence files.',
  atAGlanceQuickLinks: 'Delivery links',
  healthSectionTitle: 'Repository health & signals',
  healthSectionLead:
    'Commits, files, PR health, quality gates, and security summaries — expand Inspect for fixtures, JSON endpoints, and raw payloads.',
  accessRiskTitle: 'Access & risks',
  accessRiskReadonly: 'Effective read-only—plan changes elsewhere or use a session with write access.',
  nextStepsTitle: 'Other useful moves',
  evidenceSectionTitle: 'Workspace evidence (markdown)',
  evidenceSectionLead:
    'Browse indexed charge logs, journals, and logs from the evidence hub — pick a file from the list instead of typing paths.',
  evidenceLinkLabel: 'Browse workspace evidence',
  workspaceScopePill: 'Workspace',
  contextFromProject: (projectName: string) =>
    `Browsing evidence in the context of project “${projectName}” — Plan and Today links stay scoped when you return.`,
  chartsPageLead:
    'Per-repository charts use the same JSON bundle as the full workspace UI. If a block fails, use recovery actions or open the classic charts page.',
  strategyPageLead:
    'Submodule layout from the project chart payload. Extended strategy (registry, LENSES-REPO-STRATEGY.md) remains on the full workspace page.',
  forgeRunPageLead:
    'File-backed ForgeRun under `.forge/runs/` — approval, evidence packet, and local runner output. Hermes and Fleet placeholders stay explicit until later milestones.',
} as const

/** Embedded copilot default on project dashboard (plain-language health). */
export const PROJECT_COPILOT_DEFAULT = EVIDENCE_IA.copilotProjectHealth

/** Projects portfolio view — batched map-reduce friendly prompt. */
export const PROJECT_PORTFOLIO_COPILOT_DEFAULT =
  'Describe each git repository in this workspace in one sentence, using grounded sources. Note gaps where context is missing.'

/** Sprint UX7 — admin / inspect / automation surfaces (gear menu, page framing, copilot defaults). */
export const ADMIN_INSPECT_COPY = {
  settingsSectionPreferences: 'Preferences',
  settingsSectionAdmin: 'Workspace admin',
  settingsSectionInspect: 'Inspect & advanced',
  settingsSectionLabs: 'Labs & probes',
  gearMenuPreferencesIntro:
    'LLM routing is an advanced workspace control. Day-to-day delivery stays on Home, Work, and Projects.',
  llmPreferencesModalTitle: 'AI Setup (advanced workspace)',
  connectorHealthPurpose:
    'For operators and admins: integration health for delivery, CI/CD, quality, DevSecOps, and ops adapters. Does not replace normal Work or Projects workflows.',
  connectorHealthSubtitle: 'Live integration status for delivery, CI/CD, quality, DevSecOps, and ops fixtures.',
  auditLogPurpose:
    'For workspace super-admins: append-only access, connector, and AI audit events. Contains sensitive operational history.',
  auditLogSubtitle: 'Super-admin audit trail: access, connectors, and AI-related actions.',
  toolsetPurpose:
    'Advanced automation: workspace-root shell scripts from the scan. Scripts may modify files or use the network — review before running.',
  uxDiagnosticsPurpose:
    'Local UX telemetry for this browser only (developers and support). Copy or clear JSON when attaching a diagnostics bundle.',
  workspaceChartsAdvancedPurpose:
    'Cross-repository activity and compliance charts (advanced reporting). Same bundle as the classic charts API; optional for routine repository work.',
  copilotConnectorHealth:
    'Summarize connector health in plain language: what is degraded, likely causes, and the next three checks an admin should run. If sign-in, SSO, or permission messages appear, translate them for a workspace operator and list concrete host or IdP checks.',
  copilotAuditDigest:
    'Summarize recent audit events for a non-technical reader: actors, actions, risk, and recommended follow-ups.',
  copilotAutomationExplain:
    'Explain what the workspace toolset can and cannot do here and how to run scripts safely.',
  copilotAdvancedReporting:
    'Summarize what these cross-repository charts show for a non-technical reader and call out any compliance or activity anomalies worth investigating.',
  copilotUxDiagnostics:
    'Explain this UX diagnostics snapshot: top routes, friction signals, and what to try next for support or QA follow-up.',
  copilotLlmPreferencesPlain:
    'Explain this AI Setup page in plain language: sources (cloud, custom, local), routing modes, per-task routes when multiple providers exist, how keys stay on the Lenses host, and safe rollback if something breaks.',
} as const

/** Optional H1 / page subtitles (see `StudioRouteDefinition.subtitle`). Placed after `STUDIO_GLOSSARY`. */
export const ROUTE_SUBTITLE = {
  boardHub: DELIVERY_LENS.boardHubLeadFlow,
  projectDashboard: PROJECT_OBJECT_HOME.projectDashboardSubtitle,
  repositoryCharts: REGISTRY.perProjectActivity,
  timeline:
    'Schedule and dependencies—uses the same repository and backlog scope as Plan summary and the roadmap matrix.',
  planStory: STUDIO_GLOSSARY.story.short,
  planSource: STUDIO_GLOSSARY.sources.short,
  workspaceNotes: STUDIO_GLOSSARY.workspaceNotes.short,
  searchUtility: STUDIO_IA.searchPageSubtitle,
  llmChatUtility: STUDIO_IA.llmChatPageSubtitle,
  tutorialsReference: STUDIO_IA.tutorialsPageSubtitle,
  lensesReferenceEmbed: STUDIO_IA.lensesReferenceReadingSubtitle,
  wizardExperimental: STUDIO_IA.wizardExperimentalLead,
  uxInsights:
    'Session-only diagnostics for this browser: route counts, lens usage, sidebar intent, state panels, and page failures — not uploaded to a server.',
  agentRuntimeInspect:
    'Local-first model routing (Ollama and OpenAI-compatible URLs), live token ledger, and resumable agent sessions — same trust boundary as AI Setup.',
  llmPreferencesUtility: STUDIO_IA.llmPreferencesPageSubtitle,
  fleetPreferencesUtility: STUDIO_IA.fleetPreferencesPageSubtitle,
  methodologyBridge:
    'What your workspace already recorded about evidence, decisions, and readiness—open a row for detail; technical payloads stay under Inspect.',
  agenticBridge:
    'See how agents, recipes, and approvals are configured here—read-only catalog tied to your workspace; execution stays in Work and Plan.',
  connectorHealth: ADMIN_INSPECT_COPY.connectorHealthSubtitle,
  governanceAudit: ADMIN_INSPECT_COPY.auditLogSubtitle,
  toolsetAdvanced: ADMIN_INSPECT_COPY.toolsetPurpose,
  workspaceChartsAdvanced: ADMIN_INSPECT_COPY.workspaceChartsAdvancedPurpose,
  docsHealth:
    'Deterministic scan first, then local models for explanations and safe markdown drafts—approve before anything is written.',
  docsHealthSession:
    'Structured run with approvals, proposed edits, verification, and resumable checkpoints—same session until you close it.',
  docsHealthRemediationConsole:
    'See what is wrong, where the run stands, and the next safe actions—approve before anything is written to the repo.',
  docsHealthMaster:
    'One cluster at a time: explain impact, draft or ticket, suppress with reason — local-first agents with preview before apply.',
} as const

/** First-run copy; keep short to avoid chrome noise. */
export const STUDIO_ONBOARDING = {
  flowArtifactsTitle: 'Two ways to navigate the same Studio',
  flowArtifactsChipLabel: 'Layout: journey vs by type',
  flowArtifactsChipHint:
    'Same pages; the workspace lens only changes how the sidebar and breadcrumbs are grouped. Open for details or use Settings → Studio view.',
  /** Canonical rule: breadcrumbs come from studioRouteRegistry per active lens. */
  breadcrumbLensRule:
    'Breadcrumbs follow the active lens (Flow vs Artifacts) from the route registry—URLs and data stay the same; only labels and grouping change.',
  flowArtifactsGotIt: 'Got it',
  flowArtifactsHideOverviewChip: "Don't show overview hint",
  flowArtifactsCollapse: 'Collapse',
  uxInsightsHelpLead:
    'Same URLs for every page; Flow vs Artifacts only changes how the sidebar and breadcrumbs are grouped. Read inline below or reopen the chip on Home.',
} as const

/**
 * Sprint UX1 — short section rail line (sidebar). Replaces repeated “scoped links…” boilerplate.
 * Detailed Knowledge/Publish grouping stays in section subheads.
 */
export const SHELL_RAIL_HINT: Record<TopSectionId, string> = {
  home: 'Workspace overview and shortcuts. Find, Ask, and Do live in the header.',
  work: 'Plan and run delivery for the scope in your URL—deeper tools are in the list below.',
  projects: 'Repositories in this scan—open one for health, charts, and evidence.',
  knowledge: 'Learn, evidence, governance, and optional Blueprints Wizard—links stay in this area.',
  publish: 'Sites and blog from your workspace—preview what ships, then share links.',
}

/** Hint under the in-page Work strip (Sprint UX4 — one dominant journey; advanced in overflow). */
export const PLANNING_CLUSTER_NAV_HINT =
  'Main path: Today → Plan → Boards → Timeline → Story → Sources → Readiness — one shared scope in the URL. Matrix, WBS, roadmap previews, and classic roadmaps sit under Advanced & more.'

/** Non-Studio Lenses UI — avoid the internal name “Classic” in primary labels. */
export const FULL_WORKSPACE_UI = {
  pill: 'Full UI',
  navHint: 'Full Lenses workspace',
  openPlanSameScope: 'Open full Plan workspace',
  openPlanSameQuery: 'Open full Plan with this scope',
  openRoadmapsSummary: 'Open roadmaps summary (full workspace)',
  chartsApiNote: 'full workspace charts',
  openFullProjectPage: 'Open full workspace project page',
  openFullBoardEditor: 'Open full workspace board editor',
  openFullWebsitesList: 'Open full workspace Sites list',
  sitesBrowseFullUi: 'Full workspace Sites browse',
} as const

/**
 * Sites, blog, and embed viewers: disclose native vs embedded vs legacy so pages feel intentional.
 * Pair with `EmbeddedPreviewFrame` `disclosureKind` for iframe surfaces.
 */
export const VIEWER_EMBED_DISCLOSURE = {
  'reference-docs': {
    pill: 'Embedded docs',
    lead:
      'Lenses reference HTML from /docs inside an iframe—not native Studio panels. Toolbar actions move history or reload only inside the embedded document.',
  },
  'local-site-static': {
    pill: 'Static preview',
    lead:
      'Built output from your workspace under /local-site/… Distinct from /websites/browse/…, which embeds the legacy full-workspace Sites UI (sidebar + preview).',
  },
  'workspace-legacy-sites': {
    pill: 'Legacy workspace UI',
    lead:
      'Classic Lenses Sites experience (sidebar + preview iframe) from the root app, same-origin. Forge Studio shell, lens switcher, and primary nav stay outside this frame.',
  },
  'blog-cached-html': {
    pill: 'Cached HTML mirror',
    lead:
      'Post HTML from your workspace cache when the slug is available—mirrors forgesdlc.com content shapes; it is not a live third-party embed.',
  },
} as const

/** Sprint UX0 — methodology registry pages (user-first leads; APIs live under Technical details on each page). */
export const METHODOLOGY_UX = {
  evidenceRegistryPurpose:
    'One place to review proof the methodology graph knows about—reviews, packs, and linked rows—after work has been captured elsewhere.',
  evidenceLead:
    'Scan recent proof packs and methodology-linked items when your workspace exposes them. For day-to-day markdown in the repo, start with Workspace notes.',
  evidenceLoading: 'Gathering the latest registry items from your workspace.',
  evidenceEmpty:
    'Nothing is listed yet—either the graph is empty or this server has the view turned off. Use Workspace notes for repo markdown, Plan for active work, or ask your operator about demo graph data.',
  decisionsRegistryPurpose:
    'Read ADRs and similar records with sign-off context—use this when you need governance history, not when editing backlog.',
  decisionsLead:
    'Scan decision titles and sign-off state before a release or audit. Capture new decisions in your usual Forge workflow; they appear here once ingested.',
  decisionsLoading: 'Loading decision records from your workspace.',
  decisionsEmpty:
    'No decisions are indexed yet. Continue capturing ADRs in your normal process; this list fills when those records reach the workspace graph.',
  readinessPagePurpose:
    'See whether a specific release looks ready against methodology coverage hints—pair with Plan and evidence before you call a train “go”.',
  readinessLead:
    'Compare a release to expected methodology coverage (reviews, assays, directives) using heuristics from your workspace graph.',
  readinessPrereq:
    'Choose the release you want to evaluate, then run the check. You need a release identifier that exists in your graph—use an example below for demos, or paste your own when you have one.',
} as const

/** Agentic bridge page — user-first framing (HTTP names under Technical details on the page). */
export const METHODOLOGY_UX_AGENTIC = {
  bridgePurpose:
    'Understand how AI agents and recipes are wired to your workspace—browse before turning anything on or changing approvals.',
  lead:
    'Browse personas, recipes, tasklets, drift hints, and recent runs in read-only form. Use Plan and Today to execute work; use this page to sanity-check automation posture.',
  empty:
    'No catalog rows yet—your workspace may not expose the agent registry, or nothing is configured. Keep using Plan and project pages for delivery; return here after operators enable agents.',
} as const

/** Methodology graph record detail — user-facing title support. */
export const METHODOLOGY_UX_RECORD = {
  pageTitle: 'Evidence or decision record',
  pagePurpose:
    'Detail for one item from the evidence or decision registries—relationships and payloads; use the registries to browse lists.',
} as const

export type StudioEmbeddedPreviewKind = keyof typeof VIEWER_EMBED_DISCLOSURE

export const STUDIO_VIEWER = {
  websitesIndexPurpose:
    'Outputs readers can open: each card is a site folder the workspace scan already found—preview here, then share the built URL or Firebase target.',
  websitesIndexLead:
    'Sites are built artifacts tied to your repo (handbooks, product sites, internal previews). Open a card to preview HTML; static preview skips legacy Sites chrome when you only need files.',
  ctaEmbeddedSitesPreview: 'Embedded Sites preview',
  ctaStaticPreviewInStudio: 'Static preview in Studio',
  metaPublishedSiteFolder: 'Published site folder',
  siteBrowsePageSubtitle:
    'Preview below embeds the legacy full-workspace Sites UI for this folder. Use Reset preview or Open without shell if navigation inside the frame misbehaves.',
  siteBrowsePreviewPurpose:
    'Live HTML from a built site folder in your workspace—pair what you see here with Today and evidence before you call a release “done”.',
  unknownSitePageTitle: (name: string) => `Unknown site — ${name}`,
  unknownSitePageSubtitle:
    'Not listed under published sites in the latest workspace scan—the name may be stale, from another root, or need a rescan.',
  blogFeedTitle: 'Forge SDLC blog',
  blogFeedPurpose:
    'Public-facing stories and release-style updates—mirror of forgesdlc.com; use it to announce what shipped after you close work in Plan.',
  blogFeedLead:
    'Native list in Studio; post bodies use cached HTML when available. Refresh pulls the latest from the live site.',
  blogSyncNoteTitle: 'Blog sync note',
  blogLoadingTitle: 'Loading blog feed',
  blogLoadingDescription: 'Reading cached posts and index from the workspace.',
  blogEmptyTitle: 'No posts in Studio yet',
  blogEmptyDescription:
    'Sync may be offline or the cache is empty. When you are drafting announcements, pull themes from Today and evidence first, then refresh here or open the live blog.',
  blogPostInvalidTitle: 'Post cannot be shown in Studio',
  blogPostInvalidDescription:
    'Studio only mirrors HTML posts with a slug like my-post.html from the synced feed. Deep links and odd paths may need the live site.',
  blogPostSubtitleWithMirror:
    'Embedded cached HTML mirror—use the live site link if the frame is empty or shows an error page inside.',
  embedRecoveryHint:
    'If the preview stays blank or shows an error inside the frame: Reload, Reset preview, Open without shell, or follow the live / full workspace links above.',
  /** PageHeader subtitle when /view/local-site/… has a path (not the empty-path error state). */
  localSitePathPageSubtitle:
    'Static HTML from your workspace via /local-site/…—an embedded preview without legacy Sites chrome. Distinct from /websites/browse/… which wraps the full-workspace Sites UI.',
} as const

/** Work sidebar — collapsed block for matrix / WBS / classic roadmaps (Sprint UX4). */
export const WORK_SECTION_ADVANCED_NAV = {
  summary: 'Advanced & legacy (Work)',
  hint: 'Roadmap matrix, WBS paths, roadmap HTML preview, and the classic roadmaps summary. Same scope is preserved when the URL allows.',
} as const

export const PLAN_PAGE_COPY = {
  planSubtitle: 'Roadmap, scope, and structure for the selected backlog — same Work journey as Today and Boards.',
  todaySubtitle: 'Immediate focus: commitments, blockers, and signals — still the same scope as Plan and Timeline.',
  planDetailSectionTitle: 'Plan tools',
  planDetailSectionLead:
    'Optional: Today charge, sources, and story hub in one place. Prefer the Work strip above for the same tabs—open this section only when you need these panels together.',
  artifactsLensHint:
    'Use the Flow lens for the overview layout, or open the full workspace Plan view:',
} as const

/** Subtle line when `?from=` marks a cross-link inside Work (legacy param names). */
export const PLANNING_CLUSTER_ENTRY = {
  delivery: 'Linked from another Work view — scope in the URL is unchanged.',
  boards: 'Linked from Boards in Work — scope in the URL is unchanged.',
} as const

/** Short labels for the unified Work strip (local nav). */
export const WORK_JOURNEY = {
  today: STUDIO_VOCAB.today,
  plan: STUDIO_VOCAB.planSummary,
  boards: STUDIO_VOCAB.boards,
  timeline: STUDIO_VOCAB.timeline,
  /** Strip label; page H1 remains {@link STUDIO_VOCAB.methodologyReadiness}. */
  readiness: 'Readiness',
  matrix: STUDIO_VOCAB.roadmapMatrix,
  wbs: STUDIO_VOCAB.workBreakdown,
  wbsFile: 'WBS file',
  story: STUDIO_VOCAB.story,
  sources: STUDIO_VOCAB.sources,
} as const

/** Prefill for embedded copilot on Work / Today — variance, blockers, readiness gaps, slip, business wording. */
export const WORK_COPILOT_DEFAULT_TODAY =
  'For this backlog scope: (1) plan vs execution variance in plain language, (2) blockers needing a decision, (3) anything slipping vs milestones, (4) missing readiness inputs, (5) one work item summarized for a business stakeholder.'

/** Prefill for Plan summary — same Work AI themes without assuming Today tab. */
export const WORK_COPILOT_DEFAULT_PLAN =
  'For this Plan summary scope: (1) summarize plan vs execution variance, (2) list blockers that need a decision, (3) flag missing readiness inputs, (4) explain what is slipping vs milestones, (5) translate the focused work item into business language.'

/** Query tab value → visible label (matches registry titles). */
export const PLAN_TAB_LABEL: Record<'plan' | 'today' | 'source' | 'story', string> = {
  plan: STUDIO_VOCAB.planSummary,
  today: STUDIO_VOCAB.today,
  source: STUDIO_VOCAB.sources,
  story: STUDIO_VOCAB.story,
}

export const PRIMARY_SECTION_LABEL: Record<TopSectionId, string> = {
  home: STUDIO_VOCAB.home,
  work: STUDIO_VOCAB.work,
  projects: STUDIO_VOCAB.projects,
  knowledge: STUDIO_VOCAB.knowledge,
  publish: STUDIO_VOCAB.publish,
}

export function getPrimarySectionLabel(section: TopSectionId): string {
  return PRIMARY_SECTION_LABEL[section] ?? 'Section'
}
