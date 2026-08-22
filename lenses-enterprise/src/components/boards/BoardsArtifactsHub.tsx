import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { apiGetJson, apiPostJson } from '../../api/http'
import { useBoardRegistry } from '../../hooks/useBoardRegistry'
import {
  type BoardDirectoryRow,
  type BoardSortKey,
  type SortDir,
  formatPreviewMtime,
  flattenRegistryToRows,
  isBoardFresh,
  isBoardStale,
  isUnowned,
  sortBoardRows,
} from '../../lib/boardDirectory'
import { classifyBoardRegistryData, formatRegistrySnapshotLabel } from '../../lib/boardRegistrySurface'
import { mergePlanningScopeIntoTo } from '../../lib/planningClusterScope'
import { DELIVERY_LENS, STUDIO_VOCAB } from '../../nav/studioVisibleCopy'
import { useWorkspace } from '../../context/WorkspaceContext'
import { PageHeader, ResourceFetchStatus, StatePanel } from '../page'
import { BoardPlanningShortcutStrip } from './BoardPlanningShortcutStrip'

type BoardPayload = {
  template?: string
  version?: number
}

const TEMPLATES: {
  title: string
  hint: string
  sessionTemplate: string
  project?: string
}[] = [
  {
    title: 'Product map workshop',
    hint: 'Prefill from project WBS: actors, journey, capabilities, and systems.',
    sessionTemplate: 'product_map_workshop',
  },
  {
    title: 'Workshop kickoff (from Markdown)',
    hint: 'Import a product kickoff .md: validation decisions, feature map, agenda, and journey stickers.',
    sessionTemplate: 'workshop_kickoff',
  },
  {
    title: 'Roadmap session',
    hint: 'Horizons and dependencies; align to roadmap artifacts.',
    sessionTemplate: 'roadmap_session',
  },
  {
    title: 'Executive review',
    hint: 'Priorities, risks, and decisions visible on one surface.',
    sessionTemplate: 'executive_review',
  },
  {
    title: 'Dependency mapping',
    hint: 'Connect work across teams before locking commitments.',
    sessionTemplate: 'dependency_mapping',
  },
  {
    title: 'Architecture decision',
    hint: 'Options and tradeoffs; link outcomes in charge or work logs.',
    sessionTemplate: 'architecture_decision',
  },
]

export type BoardsHubVariant = 'flow' | 'artifacts'

type BoardDirFilter = 'all' | 'active' | 'stale' | 'attention'

function parseBoardDirFilter(raw: string | null, variant: BoardsHubVariant): BoardDirFilter {
  if (raw === 'all' || raw === 'active' || raw === 'stale' || raw === 'attention') return raw
  return variant === 'flow' ? 'active' : 'all'
}

function scrollToCreate() {
  document.getElementById('board-create')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

export type BoardsArtifactsHubProps = {
  variant?: BoardsHubVariant
}

function BoardsHubHeader({ variant }: { variant: BoardsHubVariant }) {
  if (variant === 'flow') {
    return <PageHeader title={STUDIO_VOCAB.boards} subtitle={DELIVERY_LENS.boardHubLeadFlow} />
  }
  return <PageHeader title={STUDIO_VOCAB.boards} subtitle={DELIVERY_LENS.boardHubLeadArtifacts} />
}

export function BoardsArtifactsHub({ variant = 'artifacts' }: BoardsArtifactsHubProps) {
  const navigate = useNavigate()
  const { search } = useLocation()
  const [sp, setSp] = useSearchParams()
  const { state: workspaceState } = useWorkspace()
  const filterParam = sp.get('filter')
  const projectFilter = sp.get('project') || ''

  const {
    displayPayload: data,
    displaySnapshotAt,
    isFetching,
    isHydrating,
    lastError,
    servingFromCacheAfterFailure,
    refresh,
    workspaceReady,
  } = useBoardRegistry()

  const [label, setLabel] = useState('')
  const [project, setProject] = useState(projectFilter || '_unassigned')
  const [storage, setStorage] = useState<'local' | 'shared'>('local')

  const [filter, setFilter] = useState<BoardDirFilter>(() => parseBoardDirFilter(filterParam, variant))
  const [sortKey, setSortKey] = useState<BoardSortKey>('previewMtime')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [templates, setTemplates] = useState<Record<string, string | undefined>>({})
  const [loadingTemplate, setLoadingTemplate] = useState<Record<string, boolean>>({})
  const templateFetchedRef = useRef<Record<string, boolean>>({})

  const now = useMemo(() => new Date(), [])

  const hasDisplayPayload = data !== null
  const dataKind = classifyBoardRegistryData(data)
  const snapshotLabel = formatRegistrySnapshotLabel(displaySnapshotAt)

  const recoveryActions = (
    <>
      <Link className="le-btn" to={mergePlanningScopeIntoTo('/plan?tab=today&from=boards', search)}>
        {STUDIO_VOCAB.today}
        <span className="le-shortcut-pill">Shortcut</span>
      </Link>
      <Link className="le-btn" to={mergePlanningScopeIntoTo('/plan', search)}>
        {STUDIO_VOCAB.planSummary}
        <span className="le-shortcut-pill">Shortcut</span>
      </Link>
      <Link className="le-btn" to="/projects">
        {STUDIO_VOCAB.projects}
        <span className="le-shortcut-pill">Shortcut</span>
      </Link>
    </>
  )

  useEffect(() => {
    setFilter(parseBoardDirFilter(filterParam, variant))
  }, [filterParam, variant])

  useEffect(() => {
    setProject(projectFilter || '_unassigned')
  }, [projectFilter])

  const setBoardFilter = (f: BoardDirFilter) => {
    setFilter(f)
    const next = new URLSearchParams(sp)
    const defaultF = variant === 'flow' ? 'active' : 'all'
    if (f === defaultF) next.delete('filter')
    else next.set('filter', f)
    setSp(next, { replace: true })
  }

  const rows = useMemo(() => flattenRegistryToRows(data), [data])

  const projectScoped = useMemo(() => {
    if (!projectFilter) return rows
    return rows.filter((x) => x.project === projectFilter)
  }, [rows, projectFilter])

  const filtered = useMemo(() => {
    if (filter === 'stale') return projectScoped.filter((r) => isBoardStale(r, now))
    if (filter === 'active') return projectScoped.filter((r) => isBoardFresh(r, now))
    if (filter === 'attention') return projectScoped.filter((r) => isUnowned(r) || isBoardStale(r, now))
    return projectScoped
  }, [projectScoped, filter, now])

  const sorted = useMemo(
    () => sortBoardRows(filtered, sortKey, sortDir),
    [filtered, sortKey, sortDir],
  )

  const recentBoards = useMemo(() => {
    if (!projectScoped.length) return []
    return sortBoardRows([...projectScoped], 'previewMtime', 'desc').slice(0, 8)
  }, [projectScoped])

  const summary = useMemo(() => {
    let unowned = 0
    let stale = 0
    let active = 0
    let attention = 0
    for (const r of projectScoped) {
      if (isUnowned(r)) unowned += 1
      if (isBoardStale(r, now)) stale += 1
      else active += 1
      if (isUnowned(r) || isBoardStale(r, now)) attention += 1
    }
    return {
      total: projectScoped.length,
      unowned,
      stale,
      active,
      attention,
      validationIssues: data?.validation_issues?.length ?? 0,
    }
  }, [projectScoped, data, now])

  const kpiPending = !workspaceReady || (!hasDisplayPayload && (isHydrating || isFetching))

  const projectOptions = useMemo(() => {
    const children = workspaceState?.children ?? []
    const names = children
      .map((c) => (typeof c === 'object' && c && 'name' in c ? String((c as { name?: string }).name) : ''))
      .filter(Boolean)
    return ['_unassigned', ...names.sort((a, b) => a.localeCompare(b))]
  }, [workspaceState])

  const [productMapProject, setProductMapProject] = useState(projectFilter || '_unassigned')
  const [workshopImportBusy, setWorkshopImportBusy] = useState(false)
  const [workshopImportMessage, setWorkshopImportMessage] = useState<string | null>(null)
  const workshopFileInputRef = useRef<HTMLInputElement>(null)

  async function createBoardFromTemplate(
    sessionTemplate: string,
    opts?: {
      label?: string
      prefill?: boolean
      projectKey?: string
      workshopMdText?: string
      workshopMdPath?: string
    },
  ) {
    const proj = opts?.projectKey ?? project
    const lab =
      opts?.label?.trim() ||
      label.trim() ||
      TEMPLATES.find((t) => t.sessionTemplate === sessionTemplate)?.title ||
      'New board'
    const r = await apiPostJson<{
      ok?: boolean
      error?: string
      board_id?: string
      prefill_message?: string
      prefill?: { sections?: string[]; stickers_added?: number; warnings?: string[] }
    }>('/api/sticker-board-registry', {
      action: 'create',
      payload: {
        project: proj,
        label: lab,
        storage,
        session_template: sessionTemplate,
        prefill: opts?.prefill,
        workshop_md_text: opts?.workshopMdText,
        workshop_md_path: opts?.workshopMdPath,
      },
    })
    if (r.ok === false || r.error) {
      setWorkshopImportMessage(r.error || 'Board create failed')
      return null
    }
    const bid = r.board_id
    if (bid) {
      const q = new URLSearchParams({ phase: 'discover' })
      const repoSlug = proj && proj !== '_unassigned' ? proj : ''
      if (repoSlug) q.set('repo', repoSlug)
      if (r.prefill_message && r.prefill_message !== 'ok') {
        q.set('prefill', r.prefill_message)
      } else if (r.prefill?.sections?.length) {
        q.set(
          'prefill',
          `${r.prefill.stickers_added ?? 0} stickers · ${r.prefill.sections.join(', ')}`,
        )
      }
      navigate(`/board/${encodeURIComponent(bid)}?${q.toString()}`)
      return bid
    }
    void refresh()
    return null
  }

  async function importWorkshopMarkdownFile(file: File) {
    setWorkshopImportBusy(true)
    setWorkshopImportMessage(null)
    try {
      const text = await file.text()
      const base = file.name.replace(/\.md$/i, '').trim() || 'Workshop kickoff'
      const bid = await createBoardFromTemplate('workshop_kickoff', {
        label: base,
        prefill: true,
        projectKey: project,
        workshopMdText: text,
      })
      if (bid) {
        setWorkshopImportMessage(
          `Created board from ${file.name}. Facilitate in Discover → Score → Prioritize → Capture.`,
        )
      }
    } catch (e) {
      setWorkshopImportMessage(e instanceof Error ? e.message : String(e))
    } finally {
      setWorkshopImportBusy(false)
      if (workshopFileInputRef.current) workshopFileInputRef.current.value = ''
    }
  }

  async function createBoard(e: React.FormEvent) {
    e.preventDefault()
    await createBoardFromTemplate('blank', { label: label.trim() || 'New board' })
    setLabel('')
  }

  async function repairRegistry() {
    await apiPostJson('/api/sticker-board-registry', { action: 'repair_registry', payload: {} })
    void refresh()
  }

  function toggleSort(key: BoardSortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir(key === 'label' || key === 'project' || key === 'owner' ? 'asc' : 'desc')
    }
  }

  const toggleExpand = useCallback((id: string) => {
    setExpanded((e) => {
      const next = !e[id]
      if (next && !templateFetchedRef.current[id]) {
        templateFetchedRef.current[id] = true
        setLoadingTemplate((l) => ({ ...l, [id]: true }))
        void apiGetJson<BoardPayload>(`/api/sticker-board?board_id=${encodeURIComponent(id)}`)
          .then((b) => {
            setTemplates((t) => ({ ...t, [id]: b.template }))
          })
          .catch(() => {
            setTemplates((t) => ({ ...t, [id]: undefined }))
          })
          .finally(() => {
            setLoadingTemplate((l) => ({ ...l, [id]: false }))
          })
      }
      return { ...e, [id]: next }
    })
  }, [])

  const issues = data?.validation_issues ?? []

  return (
    <>
      <BoardsHubHeader variant={variant} />

      <BoardPlanningShortcutStrip />

      <ResourceFetchStatus
        resourceLabel="board registry"
        isFetching={isFetching}
        hasDisplayPayload={hasDisplayPayload}
        isHydrating={isHydrating}
        lastError={lastError}
        servingFromCacheAfterFailure={servingFromCacheAfterFailure}
        snapshotAtLabel={snapshotLabel}
        onRetry={refresh}
        recoveryActions={recoveryActions}
      />

      <section className="le-boards-section" aria-labelledby="le-boards-summary-h">
        <h2 id="le-boards-summary-h" className="le-boards-section__title">
          Operational snapshot
        </h2>
        <p className="le-boards-section__lead forge-support">
          Registry snapshot: <strong>{snapshotLabel}</strong>
          {servingFromCacheAfterFailure ? ' · serving from last good data' : null}. Preview image mtime proxies last
          capture, not every sticker edit. Unowned means no <code className="le-mono">owner_login</code> in the
          registry entry.
        </p>
        <div className="le-boards-kpis">
          <div className="le-boards-kpi">
            <span className={`le-boards-kpi__value${kpiPending ? ' le-boards-kpi__value--pending' : ''}`}>
              {kpiPending ? '—' : summary.total}
            </span>
            <span className="le-boards-kpi__label">Total boards{projectFilter ? ' (project filter)' : ''}</span>
          </div>
          <div className="le-boards-kpi">
            <span className={`le-boards-kpi__value${kpiPending ? ' le-boards-kpi__value--pending' : ''}`}>
              {kpiPending ? '—' : summary.active}
            </span>
            <span className="le-boards-kpi__label">{DELIVERY_LENS.activeBoardsFilterLabel}</span>
          </div>
          <div className="le-boards-kpi">
            <span className={`le-boards-kpi__value${kpiPending ? ' le-boards-kpi__value--pending' : ''}`}>
              {kpiPending ? '—' : summary.unowned}
            </span>
            <span className="le-boards-kpi__label">Unowned</span>
          </div>
          <div className="le-boards-kpi">
            <span
              className={`le-boards-kpi__value${kpiPending ? ' le-boards-kpi__value--pending' : ''}${!kpiPending && summary.stale > 0 ? ' le-boards-kpi__value--warn' : ''}`}
            >
              {kpiPending ? '—' : summary.stale}
            </span>
            <span className="le-boards-kpi__label">{DELIVERY_LENS.staleBoardsFilterLabel}</span>
          </div>
          {!kpiPending && summary.validationIssues > 0 ? (
            <div className="le-boards-kpi">
              <span className="le-boards-kpi__value le-boards-kpi__value--warn">{summary.validationIssues}</span>
              <span className="le-boards-kpi__label">Registry issues</span>
            </div>
          ) : null}
        </div>
        {dataKind === 'partial' && hasDisplayPayload ? (
          <StatePanel
            variant="invalid"
            density="compact"
            className="le-boards-partial-notice"
            title="Partial or filtered registry"
            description={
              data?.access_enforced
                ? 'Workspace access policy is enforced — you only see boards your session may view. The on-disk registry can list more.'
                : 'The registry loaded with validation warnings. Some rows may be missing or inconsistent with files on disk.'
            }
            telemetryTag="boards-registry-partial"
          />
        ) : null}
        {issues.length > 0 ? (
          <>
            <ul className="le-boards-issues">
              {issues.slice(0, 8).map((x) => (
                <li key={x}>{x}</li>
              ))}
              {issues.length > 8 ? <li>…and {issues.length - 8} more</li> : null}
            </ul>
            <button type="button" className="le-btn le-btn--primary" onClick={() => void repairRegistry()}>
              Fix registry
            </button>
          </>
        ) : null}
      </section>

      {dataKind === 'empty' && hasDisplayPayload ? (
        <StatePanel
          variant="empty"
          title="No boards in this workspace yet"
          description="Create a board below, or open Plan / Today to line up work before you capture it on a board."
          actions={
            <>
              <button type="button" className="le-btn le-btn--primary" onClick={scrollToCreate}>
                Create board
              </button>
              <Link className="le-btn" to={mergePlanningScopeIntoTo('/plan?tab=today&from=boards', search)}>
                {STUDIO_VOCAB.today}
                <span className="le-shortcut-pill">Shortcut</span>
              </Link>
            </>
          }
          telemetryTag="boards-registry-empty"
        />
      ) : null}

      {recentBoards.length > 0 ? (
        <section className="le-boards-section" aria-labelledby="le-boards-recent-h">
          <h2 id="le-boards-recent-h" className="le-boards-section__title">
            Recent boards
          </h2>
          <p className="le-boards-section__lead forge-support">By latest preview capture in the current view.</p>
          <ul className="le-boards-recent-list">
            {recentBoards.map((r) => (
              <li key={r.id} className="le-boards-recent-item">
                <Link className="le-boards-recent-link" to={`/board/${encodeURIComponent(r.id)}`}>
                  {r.label}
                </Link>
                <span className="forge-support le-boards-card-face">
                  owner {r.ownerLogin ?? '—'} · lastUpdated {formatPreviewMtime(r.previewMtime)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="le-boards-section" aria-labelledby="le-boards-templates-h">
        <h2 id="le-boards-templates-h" className="le-boards-section__title">
          Templates by use case
        </h2>
        <p className="le-boards-section__lead">
          Each template creates a real board with workshop columns. Product map workshop can prefill stickers from the
          project WBS. Workshop kickoff imports a structured product kickoff Markdown file.
        </p>
        {workshopImportMessage ? (
          <p className="forge-support" style={{ marginBottom: '0.75rem' }}>
            {workshopImportMessage}
          </p>
        ) : null}
        <div className="le-boards-template-grid">
          {TEMPLATES.map((t) => (
            <div key={t.sessionTemplate} className="le-boards-template-card">
              <h3 className="le-boards-template-card__title">{t.title}</h3>
              <p className="le-boards-template-card__hint">{t.hint}</p>
              {t.sessionTemplate === 'workshop_kickoff' ? (
                <input
                  ref={workshopFileInputRef}
                  type="file"
                  accept=".md,text/markdown,text/plain"
                  hidden
                  disabled={workshopImportBusy}
                  onChange={(e) => {
                    const f = e.target.files?.[0]
                    if (f) void importWorkshopMarkdownFile(f)
                  }}
                />
              ) : null}
              {t.sessionTemplate === 'product_map_workshop' ? (
                <div className="le-form-row" style={{ flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                  <label className="forge-support">
                    Project{' '}
                    <select
                      className="le-select"
                      value={productMapProject}
                      onChange={(e) => setProductMapProject(e.target.value)}
                    >
                      {projectOptions.map((p) => (
                        <option key={p} value={p}>
                          {p}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
              ) : null}
              <button
                type="button"
                className="le-btn le-btn--primary"
                disabled={t.sessionTemplate === 'workshop_kickoff' && workshopImportBusy}
                onClick={() => {
                  if (t.sessionTemplate === 'workshop_kickoff') {
                    workshopFileInputRef.current?.click()
                    return
                  }
                  void createBoardFromTemplate(t.sessionTemplate, {
                    label: t.title,
                    prefill: t.sessionTemplate === 'product_map_workshop',
                    projectKey:
                      t.sessionTemplate === 'product_map_workshop' ? productMapProject : project,
                  })
                }}
              >
                {t.sessionTemplate === 'product_map_workshop'
                  ? 'Create from project'
                  : t.sessionTemplate === 'workshop_kickoff'
                    ? workshopImportBusy
                      ? 'Importing…'
                      : 'Import Markdown'
                    : 'Use template'}
              </button>
            </div>
          ))}
        </div>
      </section>

      <section className="le-boards-section le-boards-create" id="board-create" aria-labelledby="le-boards-create-h">
        <h2 id="le-boards-create-h" className="le-boards-section__title">
          {DELIVERY_LENS.createBoardSectionTitle}
        </h2>
        <p className="le-boards-section__lead">{DELIVERY_LENS.createBoardSectionLead}</p>
        <form className="le-boards-create-form" onSubmit={createBoard}>
          <div className="le-form-row" style={{ flexWrap: 'wrap' }}>
            <label>
              Label{' '}
              <input className="le-input" value={label} onChange={(e) => setLabel(e.target.value)} />
            </label>
            <label>
              Project key{' '}
              <input className="le-input" value={project} onChange={(e) => setProject(e.target.value)} />
            </label>
            <label>
              Storage{' '}
              <select
                className="le-select"
                value={storage}
                onChange={(e) => setStorage(e.target.value as 'local' | 'shared')}
              >
                <option value="local">local</option>
                <option value="shared">shared</option>
              </select>
            </label>
            <button className="le-btn le-btn--primary" type="submit">
              Create board
            </button>
          </div>
        </form>
      </section>

      <section className="le-boards-section" aria-labelledby="le-boards-dir-h">
        <div className="le-boards-table-toolbar">
          <h2 id="le-boards-dir-h" className="le-boards-section__title">
            {DELIVERY_LENS.boardManagementSectionTitle}
          </h2>
          <p className="le-boards-section__lead">{DELIVERY_LENS.boardManagementSectionLead}</p>
          <div className="le-boards-filters" role="group" aria-label="Board filters">
            <button
              type="button"
              className={`le-btn${filter === 'active' ? ' le-btn--primary' : ''}`}
              onClick={() => setBoardFilter('active')}
              disabled={kpiPending}
            >
              {DELIVERY_LENS.activeBoardsFilterLabel} ({kpiPending ? '—' : summary.active})
            </button>
            <button
              type="button"
              className={`le-btn${filter === 'stale' ? ' le-btn--primary' : ''}`}
              onClick={() => setBoardFilter('stale')}
              disabled={kpiPending}
            >
              {DELIVERY_LENS.staleBoardsFilterLabel} ({kpiPending ? '—' : summary.stale})
            </button>
            <button
              type="button"
              className={`le-btn${filter === 'attention' ? ' le-btn--primary' : ''}`}
              onClick={() => setBoardFilter('attention')}
              disabled={kpiPending}
            >
              Needs attention ({kpiPending ? '—' : summary.attention})
            </button>
            <button
              type="button"
              className={`le-btn${filter === 'all' ? ' le-btn--primary' : ''}`}
              onClick={() => setBoardFilter('all')}
              disabled={kpiPending}
            >
              All ({kpiPending ? '—' : projectScoped.length})
            </button>
          </div>
          {projectFilter ? (
            <p className="forge-support">
              Filtered by project <code className="le-mono">{projectFilter}</code>{' '}
              <button type="button" className="le-btn" onClick={() => setSp({})}>
                Clear
              </button>
            </p>
          ) : null}
        </div>

        {!hasDisplayPayload && isHydrating && isFetching ? (
          <StatePanel
            variant="loading"
            density="compact"
            title="Directory waiting on registry"
            description="Filters and the table populate as soon as the first registry response arrives (or use cached data if the network is slow)."
          />
        ) : null}

        {hasDisplayPayload && sorted.length === 0 && projectScoped.length > 0 ? (
          <StatePanel
            variant="empty"
            title="No boards match this filter"
            description="Try another filter, clear the project query, or create a board above."
            actions={
              <>
                <button type="button" className="le-btn le-btn--primary" onClick={() => setBoardFilter('all')}>
                  Show all in view
                </button>
                <a className="le-btn" href="#board-create">
                  Create board
                </a>
              </>
            }
          />
        ) : null}

        {hasDisplayPayload && sorted.length > 0 ? (
          <div className="le-table-wrap le-boards-table-wrap">
            <table className="le-table le-boards-table">
              <thead>
                <tr>
                  <th className="le-boards-col-expand" aria-label="Expand" />
                  {(
                    [
                      ['label', 'Label'],
                      ['project', 'Project'],
                      ['storage', 'Storage'],
                      ['owner', 'Owner'],
                      ['previewMtime', 'Last activity'],
                      ['editorsCount', 'Editors'],
                    ] as const
                  ).map(([key, labelCol]) => (
                    <th key={key}>
                      <button type="button" className="le-boards-th-btn" onClick={() => toggleSort(key)}>
                        {labelCol}
                        {sortKey === key ? (sortDir === 'asc' ? ' ▲' : ' ▼') : ''}
                      </button>
                    </th>
                  ))}
                  <th>Next action</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((r) => (
                  <BoardTableRow
                    key={r.id}
                    row={r}
                    expanded={Boolean(expanded[r.id])}
                    onToggleExpand={() => toggleExpand(r.id)}
                    template={templates[r.id]}
                    loadingTemplate={Boolean(loadingTemplate[r.id])}
                    isStale={isBoardStale(r, now)}
                    unowned={isUnowned(r)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      <section className="le-boards-section" aria-labelledby="le-boards-outcomes-h">
        <h2 id="le-boards-outcomes-h" className="le-boards-section__title">
          Outcomes and evidence
        </h2>
        <p className="le-boards-section__lead">
          Workshop outcomes are not modeled in the registry. Capture decisions in{' '}
          <Link to="/workspace-md">
            {STUDIO_VOCAB.workspaceNotes} <span className="le-shortcut-pill">Shortcut</span>
          </Link>
          , charge artifacts, or sticker bodies in the editor.
        </p>
      </section>

      <section className="le-boards-section" aria-labelledby="le-boards-linked-h">
        <h2 id="le-boards-linked-h" className="le-boards-section__title">
          Projects
        </h2>
        <p className="le-boards-section__lead">
          The <strong>project</strong> column is the registry key—often a repo slug. Open{' '}
          <Link to="/projects">
            {STUDIO_VOCAB.projects} <span className="le-shortcut-pill">Shortcut</span>
          </Link>{' '}
          for dashboards, or add <code className="le-mono">?project=</code> to this page.
        </p>
      </section>
    </>
  )
}

function BoardTableRow({
  row,
  expanded,
  onToggleExpand,
  template,
  loadingTemplate,
  isStale,
  unowned,
}: {
  row: BoardDirectoryRow
  expanded: boolean
  onToggleExpand: () => void
  template: string | undefined
  loadingTemplate: boolean
  isStale: boolean
  unowned: boolean
}) {
  const enc = encodeURIComponent(row.id)
  const nextLabel = unowned
    ? 'Set owner in registry'
    : isStale
      ? 'Refresh preview in editor'
      : 'Edit in Studio'

  return (
    <>
      <tr className="le-boards-data-row">
        <td>
          <button
            type="button"
            className="le-boards-expand-btn"
            onClick={onToggleExpand}
            aria-expanded={expanded}
            aria-label={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? '▼' : '▶'}
          </button>
        </td>
        <td className="le-name">
          <Link to={`/board/${enc}`}>{row.label}</Link>
          {unowned || isStale ? (
            <span className="le-boards-badges">
              {unowned ? <span className="le-badge le-badge--dirty">Unowned</span> : null}
              {isStale ? <span className="le-cc-chip le-cc-chip--warn">Stale</span> : null}
            </span>
          ) : null}
        </td>
        <td>
          <Link className="le-boards-project-link" to={`/board?project=${encodeURIComponent(row.project)}`}>
            {row.project}
          </Link>{' '}
          {row.project !== '_unassigned' ? (
            <>
              <Link className="forge-support" to={`/projects/${encodeURIComponent(row.project)}`}>
                dashboard <span className="le-shortcut-pill">Shortcut</span>
              </Link>
            </>
          ) : null}
        </td>
        <td>{row.storage}</td>
        <td className="le-mono">{row.ownerLogin ?? '—'}</td>
        <td className="le-mono">{formatPreviewMtime(row.previewMtime)}</td>
        <td className="le-mono">{row.editorsCount}</td>
        <td>
          <Link className="le-btn le-btn--primary" to={`/board/${enc}`}>
            {nextLabel}
          </Link>
        </td>
      </tr>
      {expanded && (
        <tr className="le-boards-detail-row">
          <td colSpan={8}>
            <div className="le-boards-detail">
              <p>
                <strong>Board id:</strong> <code className="le-mono">{row.id}</code>
              </p>
              <p>
                <strong>Viewers:</strong> {row.viewersCount}
              </p>
              <p>
                <strong>Template</strong> (loaded on expand):{' '}
                {loadingTemplate ? 'Loading…' : template ?? '—'}
              </p>
              <p className="le-boards-detail-links">
                <Link className="le-btn le-btn--primary" to={`/board/${enc}`}>
                  Studio editor
                </Link>
              </p>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
