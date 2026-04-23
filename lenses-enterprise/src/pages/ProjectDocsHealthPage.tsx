import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError, lensesJsonApiOrigin } from '../api/http'
import {
  getProjectDocsHealth,
  postProjectDocsHealth,
  type DocsHealthCluster,
  type DocsHealthFinding,
  type DocsHealthProjectPayload,
  type DocsHealthScore,
} from '../api/docsHealth'
import { DocsHealthCategorySwimlane, type CategoryCount } from '../components/docs-health/DocsHealthCategorySwimlane'
import { DocsHealthFindingsPagedBlock } from '../components/docs-health/DocsHealthFindingsPagedBlock'
import { DocsHealthKpiTileRow } from '../components/docs-health/DocsHealthKpiTileRow'
import { DocsHealthProjectDashboardHero } from '../components/docs-health/DocsHealthProjectDashboardHero'
import { DocsHealthProjectSubNav, type DocsHealthProjectView } from '../components/docs-health/DocsHealthProjectSubNav'
import { DocsHealthRunLifecyclePanels } from '../components/docs-health/DocsHealthRunLifecyclePanels'
import { ProjectLocalNav } from '../components/projects'
import { PageHeader, StatePanel, TechnicalDetails } from '../components/page'
import { chargeMdCandidates } from '../lib/copilotPageEvidence'
import {
  bucketRecentSessions,
  bucketTaskletRuns,
  pickLatestSessionModel,
  sumSessionTokens,
} from '../lib/docsHealthProjectRunBuckets'
import { formatDocsHealthProjectCopilotContext } from '../lib/docsHealthCopilotContext'
import { useSetLensesCopilotPageScope } from '../context/LensesCopilotPageScopeContext'
import { useStudioCommandBar } from '../context/StudioCommandBarContext'
import { ROUTE_SUBTITLE as SUB, STUDIO_VOCAB } from '../nav/studioVisibleCopy'
import { collectDocsHealthScanDiagnosticsFromBrowser } from '../lib/docsHealthScanDiagnostics'

const FINDINGS_PAGE_SIZE = 15

const UNCATEGORIZED_KEY = '__uncategorized__'

type LatestRun = {
  id?: string
  score?: DocsHealthScore
  finding_count?: number
  findings?: DocsHealthFinding[]
  clusters?: DocsHealthCluster[]
  finding_diff?: {
    resolved_from_prior_scan?: string[]
    new_since_prior_scan?: string[]
    reopened_findings?: string[]
  }
}

export function ProjectDocsHealthPage() {
  const { name = '' } = useParams()
  const navigate = useNavigate()
  const decoded = decodeURIComponent(name)
  const enc = encodeURIComponent(decoded)
  const dashOverviewId = useId()
  const cmd = useStudioCommandBar()
  const setCopilotScope = useSetLensesCopilotPageScope()
  const relatedMdRelPaths = useMemo(
    () => chargeMdCandidates(decoded || undefined),
    [decoded],
  )

  const [data, setData] = useState<DocsHealthProjectPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [banner, setBanner] = useState<string | null>(null)
  const [scanning, setScanning] = useState(false)
  const [indexing, setIndexing] = useState(false)
  const [severityFilter, setSeverityFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [suppressBusyId, setSuppressBusyId] = useState<string | null>(null)
  /** Shown under the scan controls so feedback is visible when the page is scrolled past the top banner. */
  const [scanInlineMessage, setScanInlineMessage] = useState<{ tone: 'ok' | 'err'; text: string } | null>(null)
  /** Last full scan error string (including hints) for the diagnostics bundle — cleared on new scan / success. */
  const [lastScanFailureUiMessage, setLastScanFailureUiMessage] = useState<string | null>(null)
  const [copyDiagStatus, setCopyDiagStatus] = useState<'idle' | 'ok' | 'err'>('idle')
  const [projectView, setProjectView] = useState<DocsHealthProjectView>('dashboard')
  const [selectedScoreArea, setSelectedScoreArea] = useState<string | null>(null)
  const [findingsPage, setFindingsPage] = useState(0)

  const diagnosticReport = useMemo(() => {
    if (!decoded) return ''
    return collectDocsHealthScanDiagnosticsFromBrowser(decoded, lensesJsonApiOrigin(), lastScanFailureUiMessage)
  }, [decoded, lastScanFailureUiMessage])

  const load = useCallback((mode: 'full' | 'soft' = 'full') => {
    if (!decoded) return
    if (mode === 'soft') {
      setRefreshing(true)
      void getProjectDocsHealth(decoded)
        .then((d) => setData(d))
        .catch(() => {
          setBanner('Could not refresh docs health — still showing the previous data.')
        })
        .finally(() => setRefreshing(false))
      return
    }
    setLoading(true)
    void getProjectDocsHealth(decoded)
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [decoded])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!decoded) return
    const head = `Forge Studio · Docs health · ${decoded}`
    const detail = formatDocsHealthProjectCopilotContext(decoded, 'summary', data)
    const pageContextSummary = detail ? `${head}\n\n${detail}` : head
    setCopilotScope({
      route: 'docs-health',
      projectSlug: decoded,
      scopeSite: decoded,
      pageContextSummary,
      relatedMdRelPaths,
    })
  }, [data, decoded, relatedMdRelPaths, setCopilotScope])

  useEffect(() => {
    if (!decoded) return
    const hash = window.location.hash || ''
    if (!hash.startsWith('#finding-')) return
    const el = document.getElementById(hash.slice(1))
    el?.scrollIntoView({ block: 'nearest' })
  }, [decoded, data?.latest_run])

  const runInventory = async () => {
    if (!decoded) return
    setIndexing(true)
    setBanner(null)
    try {
      const out = await postProjectDocsHealth(decoded, { op: 'inventory' })
      if (out.ok) {
        setBanner('Documentation list updated from your repository.')
        load('soft')
      } else {
        setBanner('Could not refresh the documentation list.')
      }
    } catch {
      setBanner('Indexing failed.')
    } finally {
      setIndexing(false)
    }
  }

  const copyDiagnosticsReport = useCallback(async () => {
    if (!diagnosticReport) return
    setCopyDiagStatus('idle')
    try {
      await navigator.clipboard.writeText(diagnosticReport)
      setCopyDiagStatus('ok')
      window.setTimeout(() => setCopyDiagStatus('idle'), 2000)
    } catch {
      setCopyDiagStatus('err')
      window.setTimeout(() => setCopyDiagStatus('idle'), 3000)
    }
  }, [diagnosticReport])

  const runScan = async () => {
    if (!decoded) return
    setScanning(true)
    setBanner(null)
    setScanInlineMessage(null)
    setLastScanFailureUiMessage(null)
    try {
      const out = (await postProjectDocsHealth(decoded, { op: 'scan' })) as {
        ok?: boolean
        error?: string
        detail?: string
        work_items_upserted?: number
      }
      if (out.ok) {
        const w = out.work_items_upserted
        const msg =
          typeof w === 'number'
            ? `Scan finished. ${w} documentation follow-up row(s) synced to Work.`
            : 'Scan finished.'
        setBanner(msg)
        setScanInlineMessage({ tone: 'ok', text: msg })
        setLastScanFailureUiMessage(null)
        load('soft')
      } else {
        const hint =
          out.error === 'static_museum'
            ? 'Docs health actions need the live Lenses Python server (same host as Studio, not the static museum build).'
            : out.detail || out.error || 'Scan could not complete.'
        setBanner(hint)
        setScanInlineMessage({ tone: 'err', text: hint })
        setLastScanFailureUiMessage(hint)
      }
    } catch (e) {
      const base =
        e instanceof ApiError
          ? `${e.message}${e.technicalNote ? ` (${e.technicalNote})` : ''}`
          : `Scan could not reach Lenses — ${e instanceof Error && e.message ? e.message : 'check that the Python Lenses process is running, VITE_LENSES_API_BASE matches that server when Studio is on another origin, and from non-loopback hosts set LENSES_ALLOW_ACTIONS=1 if appropriate.'}`
      const apiOrigin = lensesJsonApiOrigin()
      const pageOrigin = typeof window !== 'undefined' ? window.location.origin : ''
      const crossOriginApi = Boolean(pageOrigin && apiOrigin && pageOrigin !== apiOrigin)
      const networkLines: string[] = []
      if (e instanceof Error && /failed to fetch|networkerror|load failed/i.test(e.message)) {
        networkLines.push(
          '\n\nIf you saw “Scanning…” first, the server may still be working — long scans can hit dev or reverse-proxy timeouts.',
        )
        if (crossOriginApi) {
          networkLines.push(
            `• Open ${apiOrigin}/studio/ so Studio and /api share one origin (this tab is ${pageOrigin}), or set VITE_LENSES_API_BASE to the Lenses server and rebuild.`,
          )
        } else {
          networkLines.push(
            `• This tab already uses the JSON API origin (${apiOrigin}). Confirm the Lenses process is running, try the ping curl under Score formula → API, and check server logs; from non-loopback clients you may need LENSES_ALLOW_ACTIONS=1.`,
          )
          networkLines.push(
            '• DevTools → Network: select the docs-health POST — (failed) or “pending” with no status usually means the TCP connection dropped (server exit, firewall, or shell wrapper), not a JSON error from the scanner.',
          )
        }
        if (import.meta.env.DEV) {
          networkLines.push(
            '• Vite dev: restart `npm run dev` after changing the `/api` proxy in vite.config (long timeout there).',
          )
        }
      }
      const hint = networkLines.join('\n')
      const msg = `${base}${hint}`
      setBanner(hint ? base : msg)
      setScanInlineMessage({ tone: 'err', text: msg })
      setLastScanFailureUiMessage(msg)
    } finally {
      setScanning(false)
    }
  }

  const startSession = async (clusterId: string, runId: string) => {
    if (!decoded) return
    setBanner(null)
    try {
      const out = await postProjectDocsHealth(decoded, {
        op: 'create_session',
        cluster_id: clusterId,
        run_id: runId,
      })
      const sid = (out.session as { id?: string } | undefined)?.id
      if (sid) {
        navigate(`/projects/${enc}/docs-health/session/${encodeURIComponent(sid)}`)
      } else {
        setBanner('Could not start session.')
      }
    } catch {
      setBanner('Session start failed.')
    }
  }

  const openAskForCluster = (label: string) => {
    cmd.open('ask', {
      initialQuery: `In project “${decoded}”, help remediate Docs Health cluster: ${label}. Summarize safe next edits.`,
    })
  }

  const openAskForFinding = (f: DocsHealthFinding) => {
    cmd.open('ask', {
      initialQuery: `In project “${decoded}”, address Docs Health finding “${f.title ?? ''}” (${f.rule_code ?? f.id}).`,
    })
  }

  const waiveFinding = async (f: DocsHealthFinding, mode: 'suppress' | 'manual') => {
    if (!decoded || !f.id) return
    const reason = window.prompt(
      mode === 'manual'
        ? 'Describe manual follow-up (min 3 characters). This keeps the finding visible but marks it for human action:'
        : 'Reason for suppressing this finding (min 3 characters):',
      mode === 'manual' ? 'Manual fix scheduled; leaving note for owners.' : 'Risk accepted with documented rationale.',
    )
    if (!reason || reason.trim().length < 3) return
    setSuppressBusyId(f.id)
    setBanner(null)
    try {
      const out = await postProjectDocsHealth(decoded, {
        op: 'suppress_finding',
        finding_id: f.id,
        reason: reason.trim(),
        mode,
        run_id: latest?.id,
      })
      if (out.ok) {
        setBanner(mode === 'manual' ? 'Marked for manual follow-up.' : 'Finding suppressed for this project.')
        load('soft')
      } else {
        setBanner('Could not record waiver — check write access or server logs.')
      }
    } catch {
      setBanner('Waiver request failed.')
    } finally {
      setSuppressBusyId(null)
    }
  }

  const latest = data?.latest_run as LatestRun | null | undefined
  const findings = latest?.findings ?? []
  const categories = useMemo(() => {
    const s = new Set<string>()
    for (const f of findings) {
      if (f.category) s.add(f.category)
    }
    return Array.from(s).sort()
  }, [findings])

  const findingsHaveScoreArea = useMemo(() => findings.some((f) => Boolean(f.score_area)), [findings])

  const findingMatchesSevScoreOnly = useCallback(
    (f: DocsHealthFinding) => {
      if (severityFilter && (f.severity || '') !== severityFilter) return false
      if (selectedScoreArea && findingsHaveScoreArea && (f.score_area || '') !== selectedScoreArea) return false
      return true
    },
    [severityFilter, selectedScoreArea, findingsHaveScoreArea],
  )

  const categorySwimlaneTiles = useMemo((): CategoryCount[] => {
    let allMatching = 0
    const perCat = new Map<string, number>()
    let uncategorized = 0
    for (const f of findings) {
      if (!findingMatchesSevScoreOnly(f)) continue
      allMatching += 1
      const c = (f.category || '').trim()
      if (!c) uncategorized += 1
      else perCat.set(c, (perCat.get(c) || 0) + 1)
    }
    const tiles: CategoryCount[] = [{ key: '', label: 'All', count: allMatching }]
    for (const c of categories) {
      tiles.push({ key: c, label: c.replace(/_/g, ' '), count: perCat.get(c) ?? 0 })
    }
    if (uncategorized > 0) {
      tiles.push({ key: UNCATEGORIZED_KEY, label: 'Uncategorized', count: uncategorized })
    }
    return tiles
  }, [findings, categories, findingMatchesSevScoreOnly])

  const findingMatchesFilters = useCallback(
    (f: DocsHealthFinding) => {
      if (severityFilter && (f.severity || '') !== severityFilter) return false
      if (categoryFilter) {
        if (categoryFilter === UNCATEGORIZED_KEY) {
          if ((f.category || '').trim()) return false
        } else if ((f.category || '') !== categoryFilter) return false
      }
      if (selectedScoreArea && findingsHaveScoreArea && (f.score_area || '') !== selectedScoreArea) return false
      return true
    },
    [severityFilter, categoryFilter, selectedScoreArea, findingsHaveScoreArea],
  )

  const filteredFindings = useMemo(() => findings.filter((f) => findingMatchesFilters(f)), [findings, findingMatchesFilters])

  const filteredClusters = useMemo(() => {
    const clusters = latest?.clusters ?? []
    return clusters.filter((c) =>
      (c.finding_ids ?? []).some((id) => {
        const f = findings.find((x) => x.id === id)
        return f ? findingMatchesFilters(f) : false
      }),
    )
  }, [latest?.clusters, findings, findingMatchesFilters])

  const runBuckets = useMemo(() => bucketTaskletRuns(data?.tasklet_runs ?? undefined), [data?.tasklet_runs])
  const sessionBuckets = useMemo(() => bucketRecentSessions(data?.recent_sessions ?? undefined), [data?.recent_sessions])
  const remediationTokenTotal = useMemo(() => sumSessionTokens(data?.recent_sessions ?? undefined), [data?.recent_sessions])
  const latestSessionModel = useMemo(
    () => pickLatestSessionModel(data?.recent_sessions ?? undefined),
    [data?.recent_sessions],
  )

  const onToggleScoreArea = useCallback((k: string) => {
    setSelectedScoreArea((prev) => (prev === k ? null : k))
  }, [])

  useEffect(() => {
    setFindingsPage(0)
  }, [categoryFilter, severityFilter, selectedScoreArea, findings.length, decoded])

  const findingsTotalPages = Math.max(1, Math.ceil(filteredFindings.length / FINDINGS_PAGE_SIZE) || 1)
  const clampedFindingsPage = Math.min(findingsPage, findingsTotalPages - 1)

  useEffect(() => {
    if (findingsPage !== clampedFindingsPage) setFindingsPage(clampedFindingsPage)
  }, [findingsPage, clampedFindingsPage])

  const findingsCategoryTitle = useMemo(() => {
    if (!categoryFilter) return 'all categories'
    if (categoryFilter === UNCATEGORIZED_KEY) return 'uncategorized'
    return categoryFilter.replace(/_/g, ' ')
  }, [categoryFilter])

  const score = latest?.score
  const hasRun = Boolean(latest?.id)
  const allClear = hasRun && findings.length === 0

  if (!decoded) {
    return <StatePanel variant="not_configured" title="Missing project" description="Pick a project from the list." />
  }

  return (
    <>
      <PageHeader
        title={STUDIO_VOCAB.docsHealth}
        purpose={SUB.docsHealth}
        secondaryMenuItems={[
          { key: 'dash', to: `/projects/${enc}`, label: STUDIO_VOCAB.projectDashboard },
          { key: 'master', to: `/projects/${enc}/docs-health/master`, label: STUDIO_VOCAB.docsHealthMaster },
          { key: 'llm', to: '/settings/llm', label: STUDIO_VOCAB.llmPreferences },
        ]}
      />
      <ProjectLocalNav projectName={decoded} />
      {banner ? (
        <p className="forge-support" role="status" aria-live="polite">
          {banner}
        </p>
      ) : null}

      {loading ? (
        <StatePanel variant="loading" title="Loading docs health" description="Reading the latest scan for this repository." />
      ) : !data?.ok ? (
        <StatePanel variant="error" title="Docs Health unavailable" description="The server did not return docs health data for this project." />
      ) : (
        <>
          <DocsHealthProjectSubNav active={projectView} onChange={setProjectView} />

          {projectView === 'dashboard' ? (
            <>
              <section className="le-panel" aria-labelledby={dashOverviewId}>
                <h2 id={dashOverviewId} className="le-panel__title">
                  Docs health overview
                </h2>
                <DocsHealthProjectDashboardHero
                  encProject={enc}
                  score={score}
                  hasRun={hasRun}
                  allClear={allClear}
                  latest={latest}
                  data={data}
                  scanning={scanning}
                  refreshing={refreshing}
                  indexing={indexing}
                  scanInlineMessage={scanInlineMessage}
                  onRunScan={() => void runScan()}
                  onRunInventory={() => void runInventory()}
                />
                <DocsHealthKpiTileRow
                  score={score}
                  selectedScoreArea={selectedScoreArea}
                  onToggleScoreArea={onToggleScoreArea}
                />
                <p className="le-dh-token-line forge-support">
                  Remediation sessions (LLM tokens, this project):{' '}
                  <strong>{remediationTokenTotal.toLocaleString()}</strong>
                  {latestSessionModel ? (
                    <span className="le-muted"> · latest model {latestSessionModel}</span>
                  ) : null}
                </p>

                {hasRun ? (
                  <>
                    <DocsHealthCategorySwimlane
                      tiles={categorySwimlaneTiles}
                      selectedKey={categoryFilter}
                      onSelect={(key) => setCategoryFilter(key)}
                    />
                    <DocsHealthFindingsPagedBlock
                      findings={filteredFindings}
                      page={clampedFindingsPage}
                      pageSize={FINDINGS_PAGE_SIZE}
                      onPageChange={setFindingsPage}
                      categoryLabel={findingsCategoryTitle}
                      suppressBusyId={suppressBusyId}
                      onOpenAsk={openAskForFinding}
                      onWaive={waiveFinding}
                    />
                  </>
                ) : null}
              </section>

              <TechnicalDetails summary="Severity and more filters" defaultOpen={false}>
                <div role="group" aria-label="Filter findings by severity">
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'flex-end' }}>
                    <div>
                      <label htmlFor="le-docs-sev" className="le-muted" style={{ display: 'block', fontSize: '0.85rem' }}>
                        Severity
                      </label>
                      <select
                        id="le-docs-sev"
                        className="le-btn"
                        style={{ minWidth: '10rem' }}
                        value={severityFilter}
                        onChange={(e) => setSeverityFilter(e.target.value)}
                      >
                        <option value="">All</option>
                        <option value="critical">Critical</option>
                        <option value="major">Major</option>
                        <option value="minor">Minor</option>
                      </select>
                    </div>
                    <button
                      type="button"
                      className="le-btn le-btn--small"
                      onClick={() => {
                        setSeverityFilter('')
                        setCategoryFilter('')
                        setSelectedScoreArea(null)
                      }}
                    >
                      Clear all filters
                    </button>
                  </div>
                </div>
                <p className="forge-support" style={{ marginTop: '0.5rem' }}>
                  Use the <strong>category swimlanes</strong> above for category. Showing <strong>{filteredFindings.length}</strong>{' '}
                  of {findings.length} finding(s); <strong>{filteredClusters.length}</strong> cluster(s) match
                  {selectedScoreArea ? (
                    <>
                      {' '}
                      (score area: <strong>{selectedScoreArea.replace(/_/g, ' ')}</strong>)
                    </>
                  ) : null}
                  .
                </p>
              </TechnicalDetails>

              <section className="le-panel" aria-label="Grouped findings">
                <h2 className="le-panel__title">Finding clusters</h2>
                <p className="forge-support">
                  Click a score tile above to focus clusters on that area. Use {STUDIO_VOCAB.docsHealthMaster} for guided
                  flow, Ask for open chat, or start a remediation session for patch steps.
                </p>
                {!filteredClusters.length ? (
                  <p className="le-muted">No clusters match the current filters — clear filters or run a scan.</p>
                ) : (
                  <ul style={{ listStyle: 'none', padding: 0 }}>
                    {filteredClusters.map((c) => (
                      <li key={c.id} className="le-panel" style={{ marginTop: '0.5rem', padding: '0.75rem' }}>
                        <div style={{ fontWeight: 600 }}>{c.label}</div>
                        <p className="forge-support" style={{ margin: '0.35rem 0' }}>
                          {c.finding_ids?.length ?? 0} finding(s)
                          {typeof c.expected_score_gain_if_cleared === 'number' ? (
                            <>
                              {' '}
                              · up to <strong>+{c.expected_score_gain_if_cleared}</strong> pts if cleared
                            </>
                          ) : null}
                        </p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                          {latest?.id && c.id ? (
                            <button
                              type="button"
                              className="le-btn le-btn--small le-btn--primary"
                              onClick={() => void startSession(c.id!, latest!.id!)}
                            >
                              Remediate in session
                            </button>
                          ) : null}
                          <button type="button" className="le-btn le-btn--small" onClick={() => openAskForCluster(c.label ?? '')}>
                            Open in Ask (Master-style)
                          </button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>

              <TechnicalDetails summary="Checklist and file list" defaultOpen={false}>
                <p className="forge-support">
                  {data.contract_status?.mode === 'configured'
                    ? 'Your team added a documentation checklist file in the repository.'
                    : 'No checklist file yet — Forge is using sensible defaults for this repository.'}
                </p>
                <ul className="le-muted" style={{ paddingLeft: '1.25rem' }}>
                  <li>
                    Markdown pages listed: <strong>{data.inventory_summary?.document_count ?? '—'}</strong>
                  </li>
                  <li>
                    Documentation types in the checklist: <strong>{data.required_doc_type_count ?? '—'}</strong>
                  </li>
                  <li>
                    Last list refresh:{' '}
                    <strong>
                      {data.inventory_summary?.updated_at
                        ? new Date(data.inventory_summary.updated_at).toLocaleString(undefined, {
                            dateStyle: 'medium',
                            timeStyle: 'short',
                          })
                        : 'Not yet'}
                    </strong>
                  </li>
                </ul>
                <p className="forge-support" style={{ marginTop: '0.65rem' }}>
                  Indexed pages are tagged for later links to evidence, decisions, and diagrams in Knowledge — no extra
                  setup required.
                </p>
              </TechnicalDetails>

              {data.closure_status ? (
                <TechnicalDetails summary="Current scope status" defaultOpen={false}>
                  <p className="forge-support" role="status">
                    {data.closure_status.complete ? (
                      <span>
                        <strong>Scope looks complete</strong> for automated remediation: no unsuppressed critical or
                        major findings in the latest scan. Open work items:{' '}
                        <strong>{data.closure_status.open_docs_work_items ?? '—'}</strong>.
                      </span>
                    ) : (
                      <span>
                        <strong>Scope still has critical or major findings</strong> (
                        {data.closure_status.open_critical_or_major ?? '—'}) — continue in Master, remediate in a session,
                        or waive with rationale. Suppressed in view:{' '}
                        <strong>{data.closure_status.suppressed_findings_in_view ?? 0}</strong>.
                      </span>
                    )}
                  </p>
                  {data.closure_status.notes ? <p className="le-muted">{data.closure_status.notes}</p> : null}
                </TechnicalDetails>
              ) : null}

              <TechnicalDetails summary="All findings" defaultOpen={false}>
                {!findings.length && hasRun ? (
                  <p className="le-muted">No findings — this run is clean.</p>
                ) : !findings.length ? (
                  <p className="le-muted">No findings yet — run a first scan.</p>
                ) : !filteredFindings.length ? (
                  <p className="le-muted">No findings match the filters.</p>
                ) : (
                  <ul style={{ paddingLeft: '1.1rem' }}>
                    {filteredFindings.map((f) => (
                      <li key={f.id} id={f.id ? `finding-${f.id}` : undefined} style={{ marginBottom: '0.85rem' }}>
                        <strong>{f.title}</strong>
                        {f.user_suppressed ? (
                          <span className="le-muted" style={{ marginLeft: '0.35rem', fontSize: '0.85rem' }}>
                            (waived / suppressed)
                          </span>
                        ) : null}
                        <div className="le-muted" style={{ fontSize: '0.9rem' }}>
                          {f.severity} · {f.category} · {f.fixability}
                          {f.expected_score_impact != null ? ` · up to +${f.expected_score_impact} pts` : null}
                        </div>
                        {f.summary ? <p className="forge-support">{f.summary}</p> : null}
                        {f.why_it_matters ? <p className="le-muted" style={{ fontSize: '0.85rem' }}>{f.why_it_matters}</p> : null}
                        {f.affected_paths?.length ? (
                          <p className="le-muted" style={{ fontSize: '0.85rem' }}>
                            Files: {f.affected_paths.join(', ')}
                          </p>
                        ) : null}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem', marginTop: '0.35rem' }}>
                          <button type="button" className="le-btn le-btn--small" onClick={() => openAskForFinding(f)}>
                            Open in Ask (Master-style)
                          </button>
                          {!f.user_suppressed && f.id ? (
                            <>
                              <button
                                type="button"
                                className="le-btn le-btn--small"
                                disabled={suppressBusyId === f.id}
                                onClick={() => void waiveFinding(f, 'suppress')}
                              >
                                {suppressBusyId === f.id ? 'Saving…' : 'Waive / suppress'}
                              </button>
                              <button
                                type="button"
                                className="le-btn le-btn--small"
                                disabled={suppressBusyId === f.id}
                                onClick={() => void waiveFinding(f, 'manual')}
                              >
                                Manual follow-up
                              </button>
                            </>
                          ) : null}
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </TechnicalDetails>

              <TechnicalDetails summary="Score formula and API" defaultOpen={false}>
            <p className="forge-support" style={{ whiteSpace: 'pre-wrap' }}>
              {score?.formula ?? 'Formula unavailable until a scan is stored.'}
            </p>
            {score?.sum_based_score != null ? (
              <p className="forge-support">Diagnostic sum-based score (legacy-style): {score.sum_based_score}/100</p>
            ) : null}
            <p className="forge-support">
              Checklist file (preferred): <code>forge/docs-contract.yaml</code>. Older repos may still use{' '}
              <code>lenses-docs-contract.yaml</code>. API: <code>GET /api/project/{enc}/docs-health</code>,{' '}
              <code>POST</code> with <code>op: inventory | scan | create_session | …</code>
            </p>
            <p className="forge-support">
              Route docs health tasks under <Link to="/settings/llm">AI Setup</Link> using the Docs Health studio task rows
              (local-first routing prefers Ollama when smart routing is on).
            </p>
            <p className="forge-support">
              <strong>“Failed to fetch” on Run markdown scan</strong> means the browser never finished the HTTP POST (it
              is not the deterministic scanner “rejecting” your repo). Requests go to the same origin as other Studio
              API calls (this tab, or <code>VITE_LENSES_API_BASE</code>); with <code>npm run dev</code>,{' '}
              <code>/api</code> is proxied to the Lenses process (see <code>vite.config.ts</code> <code>target</code>).
              Quick check (fast, no scan):{' '}
              <code className="le-mono" style={{ wordBreak: 'break-all' }}>
                {`curl -sS -X POST "${lensesJsonApiOrigin()}/api/project/${enc}/docs-health" -H "Content-Type: application/json" -d '{"op":"ping"}'`}
              </code>{' '}
              — expect <code>&quot;ok&quot;:true</code>. Maintainer notes:{' '}
              <code className="le-mono">forge-lenses/docs/maintainer/docs-health-mvp.md</code>.
            </p>
            <details className="forge-support" style={{ marginTop: '0.65rem' }}>
              <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
                Diagnostics bundle (if scan fails again — copy for maintainers)
              </summary>
              <p className="forge-support" style={{ marginTop: '0.45rem' }}>
                Lenses often listens on a <strong>different port each run</strong>; this report uses{' '}
                <strong>this tab&apos;s</strong> resolved API origin (same as <code>fetch</code> for <code>/api</code>),
                not a hardcoded port. After a failed scan, the block includes your last on-screen error text. Also
                attach DevTools → Network row for the <code>docs-health</code> POST (status or <code>(failed)</code>).
              </p>
              <p className="forge-support" style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem' }}>
                <button type="button" className="le-btn le-btn--small" onClick={() => void copyDiagnosticsReport()}>
                  {copyDiagStatus === 'ok' ? 'Copied' : copyDiagStatus === 'err' ? 'Copy failed — select below' : 'Copy report to clipboard'}
                </button>
              </p>
              <pre
                className="le-preview"
                style={{ fontSize: '0.68rem', maxHeight: '16rem', overflow: 'auto', marginTop: '0.35rem' }}
              >
                {diagnosticReport}
              </pre>
            </details>
          </TechnicalDetails>
            </>
          ) : (
            <DocsHealthRunLifecyclePanels
              view={projectView}
              encProject={enc}
              projectSlug={decoded}
              queueRuns={runBuckets.queue}
              runningRuns={runBuckets.running}
              runningSessions={sessionBuckets.running}
              completedRuns={runBuckets.completed}
              completedSessions={sessionBuckets.completed}
              failedRuns={runBuckets.failed}
              failedSessions={sessionBuckets.failed}
              runHistory={data.run_history}
              scanning={scanning}
            />
          )}
        </>
      )}
    </>
  )
}
