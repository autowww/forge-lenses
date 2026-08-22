import { Link } from 'react-router-dom'
import { useEffect } from 'react'
import { useWorkspace } from '../../context/WorkspaceContext'
import { isWorkspaceSparse } from '../../lib/workspaceSparse'
import { STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { recordStatePanelView } from '../../telemetry/studioTelemetry'

const SAMPLE_CARDS = [
  {
    title: 'Multi-repo portfolio',
    hint: 'Point LENSES_WORKSPACE_ROOT at your Code hub to see cross-repo health, planning artifacts, and publish targets.',
  },
  {
    title: 'Backlog + roadmap files',
    hint: 'WBS and roadmap markdown in sibling repos unlock Plan summary, matrix, and timeline depth.',
  },
  {
    title: 'First-run wizard',
    hint: 'Pick a project and backlog scope on Home, then jump to Today with a guided path.',
  },
] as const

type Props = {
  /** Telemetry tag for empty-state impressions. */
  telemetryTag: string
  /** Optional page-specific lead before sample cards. */
  lead?: string
}

/**
 * Progressive empty-state storytelling when the workspace scan is sparse (single folder, no WBS/roadmaps).
 */
export function WorkspaceSparseGuide({ telemetryTag, lead }: Props) {
  const { state } = useWorkspace()
  const sparse = state != null && isWorkspaceSparse(state)

  useEffect(() => {
    if (sparse) recordStatePanelView('empty', `sparse_workspace:${telemetryTag}`)
  }, [sparse, telemetryTag])

  if (!sparse) return null

  return (
    <section
      className="le-card le-workspace-sparse-guide"
      aria-label="What you will see with a fuller workspace"
      data-ks-type="onboarding"
    >
      <h2 className="le-cc-section__title">What you&apos;ll see with a multi-repo workspace</h2>
      <p className="forge-support le-workspace-sparse-guide__lead">
        {lead ??
          'This scan only sees a thin folder tree. Widen your workspace root or add backlog and roadmap files to unlock portfolio signals, planning depth, and publish health.'}
      </p>
      <div className="le-card-grid le-workspace-sparse-guide__cards">
        {SAMPLE_CARDS.map((card) => (
          <article key={card.title} className="le-card le-workspace-sparse-guide__card">
            <h3 style={{ fontSize: '0.95rem', margin: '0 0 0.35rem' }}>{card.title}</h3>
            <p className="forge-support" style={{ margin: 0 }}>
              {card.hint}
            </p>
          </article>
        ))}
      </div>
      <p className="forge-support" style={{ marginTop: '0.75rem' }}>
        <Link to="/">{STUDIO_VOCAB.overview}</Link>
        {' · '}
        <Link to="/plan?tab=today">Open {STUDIO_VOCAB.today}</Link>
        {' · '}
        <a
          href="https://github.com/autowww/forge-lenses/blob/main/docs/handbook-public/studio-troubleshooting.md"
          target="_blank"
          rel="noreferrer"
        >
          Workspace root troubleshooting
        </a>
      </p>
    </section>
  )
}
