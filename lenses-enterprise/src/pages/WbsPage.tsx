import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { apiGetJson } from '../api/http'
import { PlanningClusterLocalNav, PlanningClusterPageHeader } from '../components/plan'
import { StatePanel, TechnicalDetails } from '../components/page'
import { mergePlanningScopeIntoTo } from '../lib/planningClusterScope'
import { resolveUxFailure, type UxResolvedFailure } from '../lib/uxPageState'
import { useNavigationMode } from '../nav/useNavigationMode'
import { getPlanningClusterPageIdentity } from '../nav/planningClusterPageIdentity'
import { FULL_WORKSPACE_UI, STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { useLensesCopilotPage } from '../hooks/useLensesCopilotPage'

export function WbsPage() {
  useLensesCopilotPage({ route: 'wbs' })
  const location = useLocation()
  const { mode } = useNavigationMode()
  const pageIdentity = useMemo(
    () => getPlanningClusterPageIdentity(location.pathname, location.search, mode),
    [location.pathname, location.search, mode],
  )
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [failure, setFailure] = useState<UxResolvedFailure | null>(null)

  useEffect(() => {
    void (async () => {
      await Promise.resolve()
      setLoading(true)
      setFailure(null)
      try {
        const payload = await apiGetJson<Record<string, unknown>>('/api/wbs-management')
        setData(payload)
        setFailure(null)
      } catch (e: unknown) {
        setData(null)
        setFailure(resolveUxFailure(e))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const projects = (
    data as {
      projects?: {
        key: string
        label?: string
        wbs: { rel_path: string; repo_hint?: string }[]
      }[]
    }
  )?.projects

  const rows = (projects ?? []).flatMap((proj) =>
    (proj.wbs ?? []).map((r) => ({
      key: `${proj.key}:${r.rel_path}`,
      proj,
      r,
    })),
  )

  return (
    <>
      <PlanningClusterLocalNav />
      <PlanningClusterPageHeader identity={pageIdentity}>
        <p className="forge-support">
          Prefer this list for scoped work breakdown paths. For the full multi-pane experience, open the{' '}
          <a href="/wbs" title={FULL_WORKSPACE_UI.navHint}>
            {FULL_WORKSPACE_UI.pill} {STUDIO_VOCAB.workBreakdown.toLowerCase()}
          </a>{' '}
          in the workspace shell.
        </p>
        <TechnicalDetails summary="Technical — classic route">
          <p className="forge-support" style={{ margin: 0 }}>
            Same scan data is available at <code className="le-mono">/wbs</code> outside Studio navigation.
          </p>
        </TechnicalDetails>
      </PlanningClusterPageHeader>

      {loading ? (
        <StatePanel
          variant="loading"
          title="Loading work breakdown list"
          description="Gathering WBS paths from your workspace scan for the current scope."
        />
      ) : null}

      {!loading && failure ? (
        <StatePanel
          variant="unavailable"
          title={failure.title}
          description={failure.description}
          technicalDetail={failure.technical}
          assistShortcuts={{ context: 'Work breakdown' }}
          aiRecovery={{
            prompt:
              'Work breakdown list in Forge Lenses failed to load. What should I verify (workspace scan, server) and what is the next step?',
            label: 'Ask Chat how to recover',
          }}
          actions={
            <button type="button" className="le-btn le-btn--primary" onClick={() => window.location.reload()}>
              Reload page
            </button>
          }
          telemetryTag="wbs_index_fetch_failed"
        />
      ) : null}

      {!loading && !failure && rows.length === 0 ? (
        <StatePanel
          variant="empty"
          title="No WBS files found for this scope"
          description="Pick a repository and plan scope from the Work strip or Plan summary, then return here. When the workspace scan finds WBS paths, they appear as links below."
          assistShortcuts={{ context: 'Work breakdown' }}
          actions={
            <Link className="le-btn le-btn--primary" to="/plan">
              Open Plan summary
            </Link>
          }
          telemetryTag="wbs_index_empty"
        />
      ) : null}

      {!loading && !failure && rows.length > 0 ? (
        <ul className="le-list" style={{ listStyle: 'none', paddingLeft: 0 }}>
          {rows.map(({ key, proj, r }) => (
            <li key={key} className="le-card" style={{ marginBottom: '0.35rem' }}>
              <Link
                to={mergePlanningScopeIntoTo(
                  `/wbs/view?p=${encodeURIComponent(r.rel_path)}&wbs_p=${encodeURIComponent(r.rel_path)}`,
                  location.search,
                )}
              >
                {r.rel_path}
              </Link>
              <span className="le-muted">
                {' '}
                — {r.repo_hint || proj.label || proj.key}
              </span>
            </li>
          ))}
        </ul>
      ) : null}

      {!loading && !failure && data ? (
        <TechnicalDetails summary="Technical — raw WBS management payload">
          <pre className="le-preview le-json">{JSON.stringify(data, null, 2)}</pre>
        </TechnicalDetails>
      ) : null}
    </>
  )
}
