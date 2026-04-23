import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useResilientJsonBlock } from '../hooks/useResilientJsonBlock'
import { ChartMountSection, PageHeader } from '../components/page'
import { ProjectLocalNav } from '../components/projects'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { FULL_WORKSPACE_UI, PROJECT_OBJECT_HOME, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

export function ProjectStrategyPage() {
  const { name = '' } = useParams()
  const decoded = decodeURIComponent(name)
  const copilotEvidence = useMemo(
    () => ({
      pageContextSummary: decoded
        ? `Forge Studio · Architecture & strategy · ${decoded}`
        : 'Forge Studio · Architecture & strategy',
      relatedMdRelPaths: chargeMdCandidates(decoded || undefined),
    }),
    [decoded],
  )
  useLensesCopilotPage({
    route: 'projects',
    projectSlug: decoded || undefined,
    scopeSite: decoded || undefined,
    pageContextSummary: copilotEvidence.pageContextSummary,
    relatedMdRelPaths: copilotEvidence.relatedMdRelPaths,
  })
  const apiUrl = `/api/project/${encodeURIComponent(decoded)}/chart-data`
  const enc = encodeURIComponent(decoded)
  const chartBundle = useResilientJsonBlock<Record<string, unknown>>(apiUrl, {
    snapshotKey: `project-chart-data:${decoded}`,
  })

  return (
    <>
      <PageHeader
        title={`${decoded} · ${STUDIO_VOCAB.architectureStrategy}`}
        preface={
          <Link to={`/projects/${enc}`} className="forge-support">
            ← {STUDIO_VOCAB.projectDashboard}
          </Link>
        }
        subtitle={
          <>
            {PROJECT_OBJECT_HOME.strategyPageLead}{' '}
            <a href={`/projects/${enc}/strategy`} title={FULL_WORKSPACE_UI.navHint}>
              {FULL_WORKSPACE_UI.openFullProjectPage}
            </a>
          </>
        }
      />
      <ProjectLocalNav projectName={decoded} />
      <ChartMountSection
        title="Submodule layout"
        chartKind="submodule_layout"
        dataUrl={apiUrl}
        recoveryProjectName={decoded}
        chartBundle={chartBundle}
      />
    </>
  )
}
