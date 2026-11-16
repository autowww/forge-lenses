import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiGetJson, apiPostJson } from '../api/http'
import { PageHeader, StatePanel } from '../components/page'
import { buildPipelineDiagramModel, PipelineSchemaDiagram } from '../components/deploy/PipelineSchemaDiagram'
import { PromoteDialog } from '../components/deploy/PromoteDialog'
import { EnvironmentHealthPanel } from '../components/deploy/EnvironmentHealthPanel'
import { useWorkspace } from '../context/WorkspaceContext'
import { deployOrchestrationFeatureEnabled } from '../util/experimentalFlags'
import { ROUTE_SUBTITLE } from '../nav/studioVisibleCopy'

type PipelineResponse = {
  ok?: boolean
  pipeline?: Record<string, unknown>
  error?: string
}

type PipelineEnv = {
  id?: string
  host_port?: number
  gateway_slug?: string
  promotes_to?: string
  auto_deploy?: boolean
}

type PipelinesResponse = {
  ok?: boolean
  pipelines?: Record<string, string>
  error?: string
}
type DeployState = {
  ok?: boolean
  releases?: Array<{
    id: string
    environment: string
    digest?: string
    status?: string
    ref?: string
  }>
  reconcile?: { drift?: unknown[] }
}

const DEFAULT_PROJECT = 'forge-market'

export function DeliveryPipelinePage() {
  const { state: workspace } = useWorkspace()
  const projects = useMemo(
    () => (workspace?.children ?? []).filter((c) => c.is_git !== false).map((c) => c.name),
    [workspace],
  )
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [project, setProject] = useState(DEFAULT_PROJECT)
  const [pipelineId, setPipelineId] = useState('default')
  const [pipelineIds, setPipelineIds] = useState<string[]>(['default'])
  const [pipeline, setPipeline] = useState<PipelineResponse | null>(null)
  const [deployState, setDeployState] = useState<DeployState | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [promoteOpen, setPromoteOpen] = useState(false)
  const [promoteError, setPromoteError] = useState<string | null>(null)
  const [selectedRelease, setSelectedRelease] = useState<string>('')

  const clientEnabled = deployOrchestrationFeatureEnabled()

  const diagramModel = useMemo(
    () => (pipeline?.pipeline ? buildPipelineDiagramModel({ pipeline: pipeline.pipeline as never }) : null),
    [pipeline],
  )

  const pipelineEnvs = useMemo(
    () => ((pipeline?.pipeline?.environments as PipelineEnv[] | undefined) ?? []).filter(Boolean),
    [pipeline],
  )

  const promotePair = useMemo(() => {
    const dev = pipelineEnvs.find((e) => e.id === 'dev')
    const prod = pipelineEnvs.find((e) => e.id === 'prod')
    const fromEnv = dev?.id ?? pipelineEnvs[0]?.id ?? 'dev'
    const toEnv = dev?.promotes_to ?? prod?.id ?? 'prod'
    return { fromEnv, toEnv }
  }, [pipelineEnvs])

  const healthUrls = useMemo(
    () =>
      pipelineEnvs
        .map((e) => (e.host_port ? `http://127.0.0.1:${e.host_port}/health` : ''))
        .filter(Boolean),
    [pipelineEnvs],
  )

  const load = useCallback(async () => {
    try {
      const [en, pls, pl, st] = await Promise.all([
        apiGetJson<{ enabled?: boolean }>('/api/deploy/enabled'),
        apiGetJson<PipelinesResponse>(`/api/deploy/pipelines?project=${encodeURIComponent(project)}`),
        apiGetJson<PipelineResponse>(
          `/api/deploy/pipeline?project=${encodeURIComponent(project)}&pipeline_id=${encodeURIComponent(pipelineId)}`,
        ),
        apiGetJson<DeployState>(`/api/deploy/state?project=${encodeURIComponent(project)}`),
      ])
      const ids = Object.keys(pls.pipelines ?? {})
      setPipelineIds(ids.length ? ids : ['default'])
      if (ids.length && !ids.includes(pipelineId)) setPipelineId(ids[0])
      setEnabled(Boolean(en.enabled))
      setPipeline(pl)
      setDeployState(st)
      setError(null)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load deploy pipeline')
    }
  }, [project, pipelineId])

  useEffect(() => {
    if (projects.length && !projects.includes(project)) setProject(projects[0])
  }, [projects, project])

  useEffect(() => {
    void load()
  }, [load])

  const onDeployDev = async () => {
    const target = pipelineEnvs.find((e) => e.auto_deploy)?.id ?? pipelineEnvs[0]?.id ?? 'dev'
    setBusy(true)
    try {
      await apiPostJson('/api/deploy/deploy', { project, environment: target, pipeline_id: pipelineId })
      await load()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Deploy failed')
    } finally {
      setBusy(false)
    }
  }

  const onPromote = async () => {
    if (!selectedRelease) return
    setBusy(true)
    setPromoteError(null)
    try {
      const out = await apiPostJson<{ ok?: boolean; error?: string }>('/api/deploy/promote', {
        release_id: selectedRelease,
        from: promotePair.fromEnv,
        to: promotePair.toEnv,
        confirm_human_approval: true,
      })
      if (!out.ok) setPromoteError(out.error ?? 'Promotion failed')
      else {
        setPromoteOpen(false)
        await load()
      }
    } catch (e: unknown) {
      setPromoteError(e instanceof Error ? e.message : 'Promotion failed')
    } finally {
      setBusy(false)
    }
  }

  if (!clientEnabled) {
    return (
      <StatePanel
        variant="not_configured"
        title="Delivery pipeline"
        description="Deploy orchestration is disabled in this Studio build. Set VITE_EXPERIMENTAL_DEPLOY_ORCHESTRATION=1 and LENSES_EXPERIMENTAL_DEPLOY_ORCHESTRATION=1 on the Lenses host."
      />
    )
  }

  if (enabled === false) {
    return (
      <StatePanel
        variant="not_configured"
        title="Delivery pipeline"
        description="Server feature flag LENSES_EXPERIMENTAL_DEPLOY_ORCHESTRATION is off."
      />
    )
  }

  return (
    <div className="ks-page">
      <PageHeader title="Delivery pipeline" subtitle={ROUTE_SUBTITLE.deliveryPipeline} />
      {error ? <p className="ks-error">{error}</p> : null}
      <div className="ks-toolbar" style={{ marginBottom: '1rem' }}>
        <label>
          Project{' '}
          <select value={project} onChange={(e) => setProject(e.target.value)}>
            {(projects.length ? projects : [DEFAULT_PROJECT]).map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label>
          Pipeline{' '}
          <select value={pipelineId} onChange={(e) => setPipelineId(e.target.value)}>
            {(pipelineIds.length ? pipelineIds : ['default']).map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="ks-btn ks-btn-primary" onClick={() => void onDeployDev()} disabled={busy}>
          Deploy {pipelineEnvs.find((e) => e.auto_deploy)?.id ?? pipelineEnvs[0]?.id ?? 'environment'}
        </button>
      </div>
      {pipeline && !pipeline.ok ? (
        <StatePanel variant="empty" title="Pipeline descriptor" description={pipeline.error ?? 'Pipeline not found for project'} />
      ) : (
        <PipelineSchemaDiagram model={diagramModel} appName={String(pipeline?.pipeline?.app ?? project)} />
      )}
      <EnvironmentHealthPanel healthUrls={healthUrls} />
      <section style={{ marginTop: '1.5rem' }}>
        <h2>Releases</h2>
        <table className="ks-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Environment</th>
              <th>Digest</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(deployState?.releases ?? []).map((r) => (
              <tr key={r.id}>
                <td>
                  <code>{r.id}</code>
                </td>
                <td>{r.environment}</td>
                <td>
                  <code>{r.digest || r.ref || '—'}</code>
                </td>
                <td>{r.status}</td>
                <td>
                  {r.environment === promotePair.fromEnv ? (
                    <button
                      type="button"
                      className="ks-btn"
                      onClick={() => {
                        setSelectedRelease(r.id)
                        setPromoteOpen(true)
                      }}
                    >
                      Promote…
                    </button>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <PromoteDialog
        open={promoteOpen}
        model={diagramModel}
        releaseId={selectedRelease}
        fromEnv={promotePair.fromEnv}
        toEnv={promotePair.toEnv}
        busy={busy}
        error={promoteError}
        onClose={() => setPromoteOpen(false)}
        onConfirm={() => void onPromote()}
      />
    </div>
  )
}
