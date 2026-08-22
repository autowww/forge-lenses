import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useResilientJsonBlock } from '../hooks/useResilientJsonBlock'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { ProjectLocalNav } from '../components/projects'
import { STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { ForgeKeyValueGrid, type ForgeKeyValueItem } from '../forgesdlc-kitchensink'
import {
  BranchingCategoryMixBar,
  BranchingKsRoadmapHint,
  BranchingLaneBarChart,
  BranchingPayloadSchemaGrid,
  BranchingPolicyLadder,
  BranchingPrSpine,
  BranchingTopologyFigure,
} from '../components/projects/BranchingVisuals'
import {
  type BranchingPayload,
  PAYLOAD_SCHEMA_CARDS,
  POLICY_RESOLUTION_STEPS,
  branchNamingRows,
  categoryMixFromBranches,
  formatBranchingModel,
  formatDocsHealthStyle,
  formatMergeGuardrails,
  formatTeamProfileSentence,
  isForgeLanesModel,
  laneVolumesForChart,
  matchPolicyResolutionStepIndex,
  recommendationRows,
} from '../lib/branchingViewModel'

export type { BranchingPayload } from '../lib/branchingViewModel'

const H_MODEL = 'branching-governed-model'
const H_GATES = 'branching-merge-gates'
const H_POLICY = 'branching-policy-resolution'
const H_PAYLOAD = 'branching-payload-map'
const H_TOPO = 'branching-topology'
const H_NAMING = 'branching-naming'
const H_LIVE = 'branching-live'
const H_PLAYBOOK = 'branching-playbook'
const JSON_ANCHOR = 'branching-payload-json'

export function ProjectBranchingPage() {
  const { name = '' } = useParams()
  const decoded = decodeURIComponent(name)
  const enc = encodeURIComponent(decoded)
  const apiUrl = decoded ? `/api/project/${enc}/branching` : null
  const data = useResilientJsonBlock<BranchingPayload>(apiUrl, {
    snapshotKey: `project-branching:${decoded}`,
  })

  const payload = data.data
  const policy = payload?.policy

  const laneRows = useMemo(() => {
    const laneBuckets = payload?.structure?.branches_by_lane ?? {}
    return Object.entries(laneBuckets)
      .map(([lane, rows]) => ({ lane, count: Array.isArray(rows) ? rows.length : 0 }))
      .filter((row) => row.count > 0)
      .sort((a, b) => b.count - a.count)
  }, [payload?.structure?.branches_by_lane])
  const prs = payload?.structure?.pull_requests ?? []
  const branchProtection = payload?.structure?.branch_protection ?? []
  const hints = payload?.hints ?? []

  const modelView = useMemo(() => formatBranchingModel(policy?.model), [policy?.model])
  const guardrails = useMemo(() => formatMergeGuardrails(policy), [policy])
  const namingTable = useMemo(() => branchNamingRows(policy), [policy])
  const playbook = useMemo(() => recommendationRows(payload?.recommendations), [payload?.recommendations])
  const lanesModel = useMemo(() => isForgeLanesModel(policy), [policy])
  const laneChartRows = useMemo(
    () => laneVolumesForChart(payload?.structure?.branches_by_lane),
    [payload?.structure?.branches_by_lane],
  )
  const categoryRows = useMemo(
    () => categoryMixFromBranches(payload?.structure?.branches),
    [payload?.structure?.branches],
  )
  const policyStepActive = useMemo(() => matchPolicyResolutionStepIndex(policy?.source), [policy?.source])

  const integrationItems: ForgeKeyValueItem[] = useMemo(() => {
    if (!payload) return []
    const p = payload.policy
    return [
      {
        label: 'Policy source',
        value: <code>{p?.source || 'unknown'}</code>,
        title: p?.source,
      },
      {
        label: 'Integration model',
        value: (
          <>
            {modelView.title}
            <span className="le-muted"> ({modelView.code})</span>
          </>
        ),
      },
      {
        label: 'Trunk branch',
        value: <code>{p?.trunk || 'main'}</code>,
      },
      {
        label: 'Team profile',
        value: formatTeamProfileSentence(p),
      },
      {
        label: 'Docs Health branch style',
        value: formatDocsHealthStyle(p?.docs_health_style),
      },
    ]
  }, [payload, modelView])

  if (!decoded) {
    return (
      <StatePanel
        variant="invalid"
        title="Missing project name"
        description="Use a URL like /studio/projects/my-repo/branching, or pick a repository from the projects list."
        actions={<Link to="/projects">All projects</Link>}
      />
    )
  }

  return (
    <>
      <PageHeader
        title={`${decoded} · ${STUDIO_VOCAB.projectBranching}`}
        preface={
          <Link to={`/projects/${enc}`} className="forge-support">
            ← {STUDIO_VOCAB.projectDashboard}
          </Link>
        }
        subtitle="Governed branching at a glance: how this repository integrates to trunk, which prefixes apply, what your workspace scan sees today, and how operators and agents should name branches."
      />
      <ProjectLocalNav projectName={decoded} />

      {data.phase === 'stale' && (
        <StatePanel variant="stale" title="Showing saved branching snapshot" description="Live refresh did not complete; rendered from the most recent successful payload in this browser." />
      )}
      {data.phase === 'error' && payload && (
        <StatePanel variant="unavailable" title="Live branching refresh failed" description="Showing cached branching data from an earlier successful load." />
      )}

      {data.phase === 'loading' && !payload && (
        <StatePanel variant="loading" title="Loading branching strategy" description="Resolving policy and branch structure…" />
      )}
      {data.phase === 'error' && !payload && (
        <StatePanel
          variant="error"
          title="Branching strategy unavailable"
          description="Could not load project branching information."
          actions={<button onClick={() => data.retry()}>Retry</button>}
        />
      )}

      {payload && (
        <div className="forge-support" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <section className="le-panel" aria-labelledby={H_MODEL}>
            <h2 id={H_MODEL} className="le-panel__title">
              Governed integration model
            </h2>
            <p className="forge-support" style={{ marginTop: 0 }}>
              This block summarizes the Branch Steward policy resolved for the repository root. It is configuration-first; your Git host may add stronger rules.
            </p>
            <ForgeKeyValueGrid items={integrationItems} aria-label="Branching policy summary" dense={false} />
          </section>

          <section className="le-panel" aria-labelledby={H_GATES}>
            <h2 id={H_GATES} className="le-panel__title">
              Merge and quality gates
            </h2>
            <p style={{ marginTop: 0 }}>{guardrails.summary}</p>
            {guardrails.bullets.length > 0 ? (
              <ul style={{ marginTop: '0.35rem', paddingLeft: '1.2rem' }}>
                {guardrails.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            ) : null}
          </section>

          <section className="le-panel" aria-labelledby={H_POLICY}>
            <h2 id={H_POLICY} className="le-panel__title">
              Policy resolution order
            </h2>
            <p style={{ marginTop: 0 }}>
              Branch Steward walks these sources in order until one matches. The highlighted step reflects{' '}
              <code>{payload.policy?.source || 'unknown'}</code>.
            </p>
            <BranchingPolicyLadder steps={POLICY_RESOLUTION_STEPS} activeIndex={policyStepActive} />
          </section>

          <section className="le-panel" aria-labelledby={H_PAYLOAD}>
            <h2 id={H_PAYLOAD} className="le-panel__title">
              Payload map (schema v1)
            </h2>
            <p style={{ marginTop: 0 }}>
              High-level blocks returned by <code>GET /api/project/…/branching</code>. Open the JSON panel below for the
              full machine-readable object.
            </p>
            <BranchingPayloadSchemaGrid cards={PAYLOAD_SCHEMA_CARDS} jsonAnchorId={JSON_ANCHOR} />
          </section>

          <section className="le-panel" aria-labelledby={H_TOPO}>
            <h2 id={H_TOPO} className="le-panel__title">
              Branching topology
            </h2>
            <p style={{ marginTop: 0 }}>
              Visual shorthand for the resolved integration model. Host rules and additional lanes may still apply.
            </p>
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '1.25rem',
                alignItems: 'flex-start',
              }}
            >
              <BranchingTopologyFigure policy={policy} lanesModel={lanesModel} />
              <BranchingKsRoadmapHint />
            </div>
            <p className="le-muted" style={{ fontSize: '0.88rem', marginBottom: 0 }}>
              For <strong>repository structure</strong> (submodules, registry notes), open{' '}
              <a href={`/projects/${enc}/strategy`}>Classic Repo &amp; strategy</a> — the branching API does not embed
              <code>.gitmodules</code> today.
            </p>
          </section>

          <section className="le-panel" aria-labelledby={H_NAMING}>
            <h2 id={H_NAMING} className="le-panel__title">
              Branch naming conventions
            </h2>
            <p style={{ marginTop: 0 }}>
              Prefixes below are <strong>policy defaults</strong> from the resolved source, not a live inventory of remote branches.{' '}
              {lanesModel
                ? 'This repository is using the Forge lanes model: prefer lane parents (product / iteration / spark) for structured work.'
                : 'Under the team tier model, day-to-day work usually lands on feature and fix prefixes unless your team documents lanes.'}
            </p>
            <div className="le-table-wrap" style={{ overflowX: 'auto' }}>
              <table className="le-table" aria-label="Branch prefixes by lane">
                <thead>
                  <tr>
                    <th scope="col">Lane</th>
                    <th scope="col">Prefix</th>
                    <th scope="col">Typical use</th>
                  </tr>
                </thead>
                <tbody>
                  {namingTable.map((row) => (
                    <tr key={row.lane}>
                      <td>{row.lane}</td>
                      <td>
                        <code>{row.prefix || '—'}</code>
                      </td>
                      <td>{row.usage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="le-panel" aria-labelledby={H_LIVE}>
            <h2 id={H_LIVE} className="le-panel__title">
              Live repository signals
            </h2>
            <ForgeKeyValueGrid
              items={[
                {
                  label: 'Current branch',
                  value: <code>{payload.current?.branch || 'n/a'}</code>,
                },
                {
                  label: 'HEAD (short)',
                  value: <code>{payload.current?.head_short || 'n/a'}</code>,
                },
                {
                  label: 'Origin',
                  value: payload.current?.origin_url ? (
                    <code style={{ wordBreak: 'break-all' }}>{payload.current.origin_url}</code>
                  ) : (
                    '—'
                  ),
                },
                {
                  label: 'Git metadata in scan',
                  value: payload.current?.is_git ? 'Present' : 'Not detected for this child',
                },
              ]}
              aria-label="Current clone and scan"
              dense={false}
            />

            {hints.length > 0 ? (
              <div style={{ marginTop: '1rem' }}>
                <h3 className="le-panel__title" style={{ fontSize: '1rem' }}>
                  Workspace hints
                </h3>
                <ul style={{ marginTop: '0.35rem', paddingLeft: '1.2rem' }}>
                  {hints.map((h) => (
                    <li key={h}>{h}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <h3 className="le-panel__title" style={{ fontSize: '1rem', marginTop: '1.25rem' }}>
              Branches grouped by lane (from payload)
            </h3>
            <BranchingLaneBarChart rows={laneChartRows} />
            {laneRows.length ? (
              <ul style={{ paddingLeft: '1.2rem', marginTop: '0.5rem' }}>
                {laneRows.map((row) => (
                  <li key={row.lane}>
                    <code>{row.lane}</code>: {row.count} branch{row.count === 1 ? '' : 'es'}
                  </li>
                ))}
              </ul>
            ) : (
              <p style={{ marginTop: '0.5rem' }}>
                No lane-grouped branches in the current payload. Add <code>.lenses-local/repo-workflow.json</code>, set{' '}
                <code>LENSES_REPO_WORKFLOW_SEED_DEMO=1</code>, or connect provider snapshots to populate lanes and PRs.
              </p>
            )}

            {categoryRows.length > 0 ? (
              <>
                <h3 className="le-panel__title" style={{ fontSize: '1rem', marginTop: '1.1rem' }}>
                  Branch categories (mix)
                </h3>
                <BranchingCategoryMixBar rows={categoryRows} />
              </>
            ) : null}

            <p style={{ marginBottom: 0 }}>
              Open pull requests: <strong>{prs.length}</strong>
              {' · '}
              Branch protection rules in payload: <strong>{branchProtection.length}</strong>
            </p>

            <BranchingPrSpine prs={prs} />

            {prs.length > 0 ? (
              <div className="le-table-wrap" style={{ overflowX: 'auto', marginTop: '0.75rem' }}>
                <table className="le-table" aria-label="Open pull requests">
                  <thead>
                    <tr>
                      <th scope="col">#</th>
                      <th scope="col">Title</th>
                      <th scope="col">Head</th>
                      <th scope="col">Base</th>
                      <th scope="col">State</th>
                    </tr>
                  </thead>
                  <tbody>
                    {prs.map((pr, idx) => (
                      <tr key={`${pr.number ?? 'pr'}-${pr.head_ref ?? ''}-${idx}`}>
                        <td>{pr.number != null ? String(pr.number) : '—'}</td>
                        <td>{pr.title || '—'}</td>
                        <td>
                          <code>{pr.head_ref || '—'}</code>
                        </td>
                        <td>
                          <code>{pr.base_ref || '—'}</code>
                        </td>
                        <td>{pr.state || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {branchProtection.length > 0 ? (
              <div className="le-table-wrap" style={{ overflowX: 'auto', marginTop: '0.75rem' }}>
                <table className="le-table" aria-label="Branch protection rules">
                  <thead>
                    <tr>
                      <th scope="col">Pattern</th>
                      <th scope="col">Required reviews</th>
                    </tr>
                  </thead>
                  <tbody>
                    {branchProtection.map((bp, idx) => (
                      <tr key={`${bp.pattern ?? 'pat'}-${idx}`}>
                        <td>
                          <code>{bp.pattern || '—'}</code>
                        </td>
                        <td>{bp.required_reviews != null ? String(bp.required_reviews) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>

          <section className="le-panel" aria-labelledby={H_PLAYBOOK}>
            <h2 id={H_PLAYBOOK} className="le-panel__title">
              Operator and agent playbook
            </h2>
            <p style={{ marginTop: 0 }}>
              Use these branch choices when coordinating humans and automation. Text is generated from the resolved policy for this repository.
            </p>
            {playbook.length === 0 ? (
              <p>No recommendations were returned.</p>
            ) : (
              <dl style={{ margin: 0 }}>
                {playbook.map((row) => (
                  <div key={row.key} style={{ marginBottom: '0.85rem' }}>
                    <dt style={{ fontWeight: 600 }}>{row.title}</dt>
                    <dd style={{ margin: '0.25rem 0 0', paddingLeft: 0 }}>{row.body}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>

          <div id={JSON_ANCHOR}>
            <TechnicalDetails summary="Branching payload details (JSON)">
              <pre>{JSON.stringify(payload, null, 2)}</pre>
            </TechnicalDetails>
          </div>
        </div>
      )}
    </>
  )
}
