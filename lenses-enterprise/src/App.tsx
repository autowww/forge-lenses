import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { StatePanel } from './components/page'
import { WorkspaceProvider } from './context/WorkspaceContext'
import { DocsHealthLiveProvider } from './context/DocsHealthLiveContext'
import { ShellChromeProvider } from './context/ShellChromeContext'
import { NavModeProvider } from './context/NavModeProvider'
import { ForgesdlcBlogProvider } from './context/ForgesdlcBlogContext'
import { Layout } from './components/Layout'
import { MainContentInertProvider } from './context/MainContentInertContext'
import { StudioCommandBarProvider } from './context/StudioCommandBarContext'
import { StudioNavigationTrailProvider } from './context/StudioNavigationTrailContext'
import { HomePage } from './pages/HomePage'
import { ProjectsPage } from './pages/ProjectsPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { ProjectChartsPage } from './pages/ProjectChartsPage'
import { ProjectStrategyPage } from './pages/ProjectStrategyPage'
import { ProjectBranchingPage } from './pages/ProjectBranchingPage'
import { ProjectForgeRunPage } from './pages/ProjectForgeRunPage'
import { ProjectDocsHealthPage } from './pages/ProjectDocsHealthPage'
import { ProjectDocsHealthMasterPage } from './pages/ProjectDocsHealthMasterPage'
import { ProjectDocsHealthSessionPage } from './pages/ProjectDocsHealthSessionPage'
import { SearchPage } from './pages/SearchPage'
import { ChatPage } from './pages/ChatPage'
import { LlmSettingsPage } from './pages/LlmSettingsPage'
import { FleetSettingsPage } from './pages/FleetSettingsPage'
import { UxInsightsPage } from './pages/UxInsightsPage'
import { AgentRuntimeInspectPage } from './pages/AgentRuntimeInspectPage'
import { ToolsetPage } from './pages/ToolsetPage'
import { ToolsetRunPage } from './pages/ToolsetRunPage'
import { WebsitesPage } from './pages/WebsitesPage'
import { WebsitesBrowsePage } from './pages/WebsitesBrowsePage'
import { WbsPage } from './pages/WbsPage'
import { WbsViewPage } from './pages/WbsViewPage'
import { TutorialsPage } from './pages/TutorialsPage'
import { WorkspaceMdPage } from './pages/WorkspaceMdPage'
import { GovernanceAuditPage } from './pages/GovernanceAuditPage'
import { GovernanceConnectorsPage } from './pages/GovernanceConnectorsPage'
import { RoadmapSectionPage } from './pages/RoadmapSectionPage'
import { FeatureShowcaseDemoPage } from './pages/FeatureShowcaseDemoPage'
import { BlogPage } from './pages/BlogPage'
import { BlogPostPage } from './pages/BlogPostPage'
import { StaticEmbedPage } from './pages/StaticEmbedPage'
import { blueprintsWizardFeatureEnabled } from './util/experimentalFlags'

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
              <Route path="websites/browse/:site" element={<WebsitesBrowsePage />} />
              <Route path="wbs" element={<WbsPage />} />
              <Route path="wbs/view" element={<WbsViewPage />} />
              <Route path="plan" element={<PlanPage />} />
              <Route path="plan/matrix" element={<PlanMatrixPage />} />
              <Route path="timeline" element={<TimelinePage />} />
              <Route path="board" element={<BoardHubPage />} />
              <Route path="board/:id" element={<BoardEditorPage />} />
              <Route path="tutorials" element={<TutorialsPage />} />
              <Route path="view/docs/*" element={<StaticEmbedPage kind="docs" />} />
              <Route path="view/local-site/*" element={<StaticEmbedPage kind="local-site" />} />
              <Route path="blog" element={<BlogPage />} />
              <Route path="blog/post/:slug" element={<BlogPostPage />} />
              <Route path="workspace-md" element={<WorkspaceMdPage />} />
              <Route path="workspace-md/view" element={<WorkspaceMdPage />} />
              <Route path="knowledge/methodology/evidence" element={<MethodologyEvidenceRegistryPage />} />
              <Route path="knowledge/methodology/decisions" element={<MethodologyDecisionsRegistryPage />} />
              <Route path="knowledge/methodology/record/:entityId" element={<MethodologyGraphRecordPage />} />
              <Route path="knowledge/methodology/readiness" element={<MethodologyReadinessPage />} />
              <Route path="knowledge/agentic-bridge" element={<AgenticBridgePage />} />
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
