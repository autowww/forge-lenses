import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useResilientJsonBlock } from '../hooks/useResilientJsonBlock'
import { ChartMountSection, ObjectMetaBar, PageHeader } from '../components/page'
import { ProjectLocalNav } from '../components/projects'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'
import { PROJECT_OBJECT_HOME, STUDIO_VOCAB } from '../nav/studioVisibleCopy'

const BLOCKS: { kind: string; title: string }[] = [
  { kind: 'commit_weekly', title: 'Activity (90 days)' },
  { kind: 'commit_daily', title: 'Activity (7 days)' },
  { kind: 'contributors', title: 'Contributors' },
  { kind: 'extension_heatmap', title: 'File types' },
  { kind: 'compliance_bars', title: 'Standards compliance (score)' },
  { kind: 'submodule_layout', title: 'Submodule layout' },
]

export function ProjectChartsPage() {
  const { name = '' } = useParams()
  const decoded = decodeURIComponent(name)
  const copilotEvidence = useMemo(
    () => ({
      pageContextSummary: decoded
        ? `Forge Studio · Repository charts · ${decoded}`
        : 'Forge Studio · Repository charts',
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
        title={`${decoded} · ${STUDIO_VOCAB.repositoryCharts}`}
        preface={
          <Link to={`/projects/${enc}`} className="forge-support">
            ← {STUDIO_VOCAB.projectDashboard}
          </Link>
        }
        subtitle={PROJECT_OBJECT_HOME.chartsPageLead}
      />
      <ProjectLocalNav projectName={decoded} />
      <ObjectMetaBar
        label="Chart bundle"
        items={[
          { label: 'Repository', value: decoded },
          { label: 'Endpoint', value: apiUrl },
        ]}
      />
      {BLOCKS.map(({ kind, title }) => (
        <ChartMountSection
          key={kind}
          title={title}
          chartKind={kind}
          dataUrl={apiUrl}
          recoveryProjectName={decoded}
          chartBundle={chartBundle}
        />
      ))}
    </>
  )
}
