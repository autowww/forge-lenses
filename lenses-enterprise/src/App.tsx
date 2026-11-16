import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { StatePanel } from './components/page'
import { WorkspaceProvider } from './context/WorkspaceContext'
import { DocsHealthLiveProvider } from './context/DocsHealthLiveContext'
import { DocsHealthSummaryProvider } from './context/DocsHealthSummaryContext'
import { OverviewTelemetryProvider } from './context/OverviewTelemetryContext'
import { ShellChromeProvider } from './context/ShellChromeContext'
import { NavModeProvider } from './context/NavModeProvider'
import { ForgesdlcBlogProvider } from './context/ForgesdlcBlogContext'
import { MainContentInertProvider } from './context/MainContentInertContext'
import { StudioCommandBarProvider } from './context/StudioCommandBarContext'
import { StudioNavigationTrailProvider } from './context/StudioNavigationTrailContext'
import { autonomyMaturityFeatureEnabled, blueprintsWizardFeatureEnabled } from './util/experimentalFlags'

const HomePage = lazy(() => import('./pages/HomePage').then((m) => ({ default: m.HomePage })))

const OverviewChartsPage = lazy(() =>
  import('./pages/OverviewChartsPage').then((m) => ({ default: m.OverviewChartsPage })),
)
const PlanPage = lazy(() => import('./pages/PlanPage').then((m) => ({ default: m.PlanPage })))
const PlanMatrixPage = lazy(() =>
  import('./pages/PlanMatrixPage').then((m) => ({ default: m.PlanMatrixPage })),
)
const TimelinePage = lazy(() =>
  import('./pages/TimelinePage').then((m) => ({ default: m.TimelinePage })),
)
const BoardHubPage = lazy(() =>
  import('./pages/BoardHubPage').then((m) => ({ default: m.BoardHubPage })),
)
const BoardEditorPage = lazy(() =>
  import('./pages/BoardEditorPage').then((m) => ({ default: m.BoardEditorPage })),
)
const BlueprintsWizardLayout = lazy(() =>
  import('./pages/BlueprintsWizardLayout').then((m) => ({ default: m.BlueprintsWizardLayout })),
)
const BlueprintsWizardHub = lazy(() =>
  import('./blueprints-wizard/BlueprintsWizardHub').then((m) => ({ default: m.BlueprintsWizardHub })),
)
const BlueprintsWizardSessionPage = lazy(() =>
  import('./pages/BlueprintsWizardSessionPage').then((m) => ({ default: m.BlueprintsWizardSessionPage })),
)
const MethodologyEvidenceRegistryPage = lazy(() =>
  import('./pages/MethodologyBridgePages').then((m) => ({ default: m.MethodologyEvidenceRegistryPage })),
)
const MethodologyDecisionsRegistryPage = lazy(() =>
  import('./pages/MethodologyBridgePages').then((m) => ({ default: m.MethodologyDecisionsRegistryPage })),
)
const MethodologyGraphRecordPage = lazy(() =>
  import('./pages/MethodologyBridgePages').then((m) => ({ default: m.MethodologyGraphRecordPage })),
)
const MethodologyReadinessPage = lazy(() =>
  import('./pages/MethodologyBridgePages').then((m) => ({ default: m.MethodologyReadinessPage })),
)
const AgenticBridgePage = lazy(() =>
  import('./pages/AgenticBridgePage').then((m) => ({ default: m.AgenticBridgePage })),
)
const FoundryPage = lazy(() => import('./pages/FoundryPage').then((m) => ({ default: m.FoundryPage })))
const FoundryRunPage = lazy(() =>
  import('./pages/FoundryRunPage').then((m) => ({ default: m.FoundryRunPage })),
)
const ProjectAutonomyMaturityPage = lazy(() =>
  import('./pages/ProjectAutonomyMaturityPage').then((m) => ({ default: m.ProjectAutonomyMaturityPage })),
)

const Layout = lazy(() => import('./components/Layout').then((m) => ({ default: m.Layout })))

const ProjectsPage = lazy(() => import('./pages/ProjectsPage').then((m) => ({ default: m.ProjectsPage })))
const ProjectDetailPage = lazy(() => import('./pages/ProjectDetailPage').then((m) => ({ default: m.ProjectDetailPage })))
const ProjectChartsPage = lazy(() => import('./pages/ProjectChartsPage').then((m) => ({ default: m.ProjectChartsPage })))
const ProjectStrategyPage = lazy(() => import('./pages/ProjectStrategyPage').then((m) => ({ default: m.ProjectStrategyPage })))
const ProjectBranchingPage = lazy(() => import('./pages/ProjectBranchingPage').then((m) => ({ default: m.ProjectBranchingPage })))
const ProjectForgeRunPage = lazy(() => import('./pages/ProjectForgeRunPage').then((m) => ({ default: m.ProjectForgeRunPage })))
const DocManagementHubPage = lazy(() => import('./pages/DocManagementHubPage').then((m) => ({ default: m.DocManagementHubPage })))
const DocManagementSessionPage = lazy(() => import('./pages/DocManagementSessionPage').then((m) => ({ default: m.DocManagementSessionPage })))
const ProjectDocsHealthPage = lazy(() => import('./pages/ProjectDocsHealthPage').then((m) => ({ default: m.ProjectDocsHealthPage })))
const ProjectDocsHealthMasterPage = lazy(() => import('./pages/ProjectDocsHealthMasterPage').then((m) => ({ default: m.ProjectDocsHealthMasterPage })))
const ProjectDocsHealthSessionPage = lazy(() => import('./pages/ProjectDocsHealthSessionPage').then((m) => ({ default: m.ProjectDocsHealthSessionPage })))
const SearchPage = lazy(() => import('./pages/SearchPage').then((m) => ({ default: m.SearchPage })))
const ChatPage = lazy(() => import('./pages/ChatPage').then((m) => ({ default: m.ChatPage })))
const LlmSettingsPage = lazy(() => import('./pages/LlmSettingsPage').then((m) => ({ default: m.LlmSettingsPage })))
const FleetSettingsPage = lazy(() => import('./pages/FleetSettingsPage').then((m) => ({ default: m.FleetSettingsPage })))
const UxInsightsPage = lazy(() => import('./pages/UxInsightsPage').then((m) => ({ default: m.UxInsightsPage })))
const AutonomyMaturityPage = lazy(() => import('./pages/AutonomyMaturityPage').then((m) => ({ default: m.AutonomyMaturityPage })))
const AgentRuntimeInspectPage = lazy(() => import('./pages/AgentRuntimeInspectPage').then((m) => ({ default: m.AgentRuntimeInspectPage })))
const ToolsetPage = lazy(() => import('./pages/ToolsetPage').then((m) => ({ default: m.ToolsetPage })))
const ToolsetRunPage = lazy(() => import('./pages/ToolsetRunPage').then((m) => ({ default: m.ToolsetRunPage })))
const WebsitesPage = lazy(() => import('./pages/WebsitesPage').then((m) => ({ default: m.WebsitesPage })))
const WebsitesBrowsePage = lazy(() => import('./pages/WebsitesBrowsePage').then((m) => ({ default: m.WebsitesBrowsePage })))
const WbsPage = lazy(() => import('./pages/WbsPage').then((m) => ({ default: m.WbsPage })))
const WbsViewPage = lazy(() => import('./pages/WbsViewPage').then((m) => ({ default: m.WbsViewPage })))
const TutorialsPage = lazy(() => import('./pages/TutorialsPage').then((m) => ({ default: m.TutorialsPage })))
const WorkspaceMdPage = lazy(() => import('./pages/WorkspaceMdPage').then((m) => ({ default: m.WorkspaceMdPage })))
const GovernanceAuditPage = lazy(() => import('./pages/GovernanceAuditPage').then((m) => ({ default: m.GovernanceAuditPage })))
const GovernanceConnectorsPage = lazy(() => import('./pages/GovernanceConnectorsPage').then((m) => ({ default: m.GovernanceConnectorsPage })))
const RoadmapSectionPage = lazy(() => import('./pages/RoadmapSectionPage').then((m) => ({ default: m.RoadmapSectionPage })))
const FeatureShowcaseDemoPage = lazy(() => import('./pages/FeatureShowcaseDemoPage').then((m) => ({ default: m.FeatureShowcaseDemoPage })))
const VirtualCameraStudioPage = lazy(() =>
  import('./pages/VirtualCameraStudioPage').then((m) => ({ default: m.VirtualCameraStudioPage })),
)
const BlogPage = lazy(() => import('./pages/BlogPage').then((m) => ({ default: m.BlogPage })))
const BlogPostPage = lazy(() => import('./pages/BlogPostPage').then((m) => ({ default: m.BlogPostPage })))
const StaticEmbedPage = lazy(() => import('./pages/StaticEmbedPage').then((m) => ({ default: m.StaticEmbedPage })))
const LocalSiteRedirect = lazy(() => import('./pages/LocalSiteRedirect').then((m) => ({ default: m.LocalSiteRedirect })))

function RouteFallback() {
  return (
    <div style={{ padding: '1.5rem', maxWidth: '36rem' }}>
      <StatePanel
        variant="loading"
        title="Loading this area"
        description="Opening charts, plan, boards, or wizard — your place in the workspace is preserved."
      />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter basename="/studio">
      <StudioCommandBarProvider>
      <MainContentInertProvider>
      <NavModeProvider>
        <StudioNavigationTrailProvider>
        <WorkspaceProvider>
          <DocsHealthLiveProvider>
          <ForgesdlcBlogProvider>
          <ShellChromeProvider>
          <OverviewTelemetryProvider>
          <DocsHealthSummaryProvider>
          <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<HomePage />} />
              <Route path="overview/charts" element={<OverviewChartsPage />} />
              <Route path="projects" element={<ProjectsPage />} />
              <Route path="projects/:name" element={<ProjectDetailPage />} />
              <Route path="projects/:name/charts" element={<ProjectChartsPage />} />
            <Route path="projects/:name/strategy" element={<ProjectStrategyPage />} />
            <Route path="projects/:name/branching" element={<ProjectBranchingPage />} />
            <Route path="projects/:name/forge-run" element={<ProjectForgeRunPage />} />
            <Route path="projects/:name/docs-health/session/:sessionId" element={<ProjectDocsHealthSessionPage />} />
              <Route path="projects/:name/docs-health/master" element={<ProjectDocsHealthMasterPage />} />
              <Route path="projects/:name/docs-health" element={<ProjectDocsHealthPage />} />
              <Route path="search" element={<SearchPage />} />
              <Route path="chat" element={<ChatPage />} />
              <Route path="settings/llm" element={<LlmSettingsPage />} />
              <Route path="settings/fleet" element={<FleetSettingsPage />} />
              <Route path="settings/ux-insights" element={<UxInsightsPage />} />
              <Route path="settings/agent-runtime" element={<AgentRuntimeInspectPage />} />
              <Route path="governance/connectors" element={<GovernanceConnectorsPage />} />
              <Route path="governance/audit" element={<GovernanceAuditPage />} />
              <Route path="toolset" element={<ToolsetPage />} />
              <Route path="toolset/:name" element={<ToolsetRunPage />} />
              <Route path="websites" element={<WebsitesPage />} />
              <Route path="websites/browse/:site/*" element={<WebsitesBrowsePage />} />
              <Route path="wbs" element={<WbsPage />} />
              <Route path="wbs/view" element={<WbsViewPage />} />
              <Route path="plan" element={<PlanPage />} />
              <Route path="plan/matrix" element={<PlanMatrixPage />} />
              <Route path="timeline" element={<TimelinePage />} />
              <Route path="board" element={<BoardHubPage />} />
              <Route path="board/:id" element={<BoardEditorPage />} />
              <Route path="tutorials" element={<TutorialsPage />} />
              <Route path="view/docs/*" element={<StaticEmbedPage />} />
              <Route path="view/local-site/*" element={<LocalSiteRedirect />} />
              <Route path="blog" element={<BlogPage />} />
              <Route path="blog/post/:slug" element={<BlogPostPage />} />
              <Route path="doc-management" element={<DocManagementHubPage />} />
              <Route path="doc-management/session/:sessionId" element={<DocManagementSessionPage />} />
              <Route path="workspace-md" element={<WorkspaceMdPage />} />
              <Route path="workspace-md/view" element={<WorkspaceMdPage />} />
              <Route path="knowledge/methodology/evidence" element={<MethodologyEvidenceRegistryPage />} />
              <Route path="knowledge/methodology/decisions" element={<MethodologyDecisionsRegistryPage />} />
              <Route path="knowledge/methodology/record/:entityId" element={<MethodologyGraphRecordPage />} />
              <Route path="knowledge/methodology/readiness" element={<MethodologyReadinessPage />} />
              <Route path="knowledge/agentic-bridge" element={<AgenticBridgePage />} />
              <Route path="foundry" element={<FoundryPage />} />
              <Route path="foundry/runs/:runId" element={<FoundryRunPage />} />
              <Route path="labs/virtual-camera" element={<VirtualCameraStudioPage />} />
              {autonomyMaturityFeatureEnabled() ? (
                <>
                  <Route path="autonomy-maturity" element={<AutonomyMaturityPage />} />
                  <Route path="projects/:name/autonomy-maturity" element={<ProjectAutonomyMaturityPage />} />
                </>
              ) : null}
              <Route path="roadmap-section" element={<RoadmapSectionPage />} />
              <Route path="feature-showcase" element={<FeatureShowcaseDemoPage />} />
              {/* Blueprints Wizard: hub is primary UX; `session/:sessionId` is a probe/deep-link surface
                  (see `probeKind` on `SR.blueprintsWizardSession` in studioRouteRegistry). Keep both routes
                  registered for E2E and API debugging—framed empty/error states live in the session page. */}
              {blueprintsWizardFeatureEnabled() ? (
                <Route path="blueprints/wizard" element={<BlueprintsWizardLayout />}>
                  <Route index element={<BlueprintsWizardHub />} />
                  <Route path="session/:sessionId" element={<BlueprintsWizardSessionPage />} />
                </Route>
              ) : null}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
          </Suspense>
          </DocsHealthSummaryProvider>
          </OverviewTelemetryProvider>
          </ShellChromeProvider>
          </ForgesdlcBlogProvider>
          </DocsHealthLiveProvider>
        </WorkspaceProvider>
        </StudioNavigationTrailProvider>
      </NavModeProvider>
      </MainContentInertProvider>
      </StudioCommandBarProvider>
    </BrowserRouter>
  )
}
