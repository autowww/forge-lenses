import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { friendlyRepoLabel } from '../../util/planDisplayNames'
import {
  clusterByRepoHint,
  clusterHeadingLabel,
  filterRoadmapsForRepoHint,
  repoHintForWbsPath,
  roadmapLocationLabel,
  wbsBacklogPickerLabel,
} from '../../util/planScopeCluster'
import { PlanScopeFilePathChip } from './PlanScopeFilePathChip'

type WbsOpt = { rel_path: string; repo_hint?: string }
type RmOpt = { rel_path: string; repo_hint?: string }

type PickerKind = 'wbs' | 'roadmap' | 'repo' | 'workitem' | null

type Props = {
  repo: string
  wbsP: string
  roadmapP: string
  nodeId: string
  wbsList: WbsOpt[]
  rmList: RmOpt[]
  setFields: (patch: Record<string, string | undefined>) => void
  focusStoryTitle?: string
  defaultScopeOpen?: boolean
}

export function PlanScopeBar({
  repo,
  wbsP,
  roadmapP,
  nodeId,
  wbsList,
  rmList,
  setFields,
  focusStoryTitle,
  defaultScopeOpen = false,
}: Props) {
  const [picker, setPicker] = useState<PickerKind>(null)
  const [advancedOpen, setAdvancedOpen] = useState(defaultScopeOpen)
  const [repoDraft, setRepoDraft] = useState(repo)
  const [idDraft, setIdDraft] = useState(nodeId)
  const wrapRef = useRef<HTMLDivElement>(null)
  const baseId = useId()

  const selectedWbs = useMemo(() => wbsList.find((w) => w.rel_path === wbsP), [wbsList, wbsP])
  const scopeRepoHint = useMemo(() => repoHintForWbsPath(wbsList, wbsP), [wbsList, wbsP])
  const wbsClusters = useMemo(() => clusterByRepoHint(wbsList), [wbsList])
  const filteredRoadmaps = useMemo(
    () => filterRoadmapsForRepoHint(rmList, scopeRepoHint),
    [rmList, scopeRepoHint],
  )

  const hasWbs = Boolean(wbsP.trim())
  const wbsHintKey = (selectedWbs?.repo_hint || '').trim() || '__root__'
  const wbsTileProduct = hasWbs ? clusterHeadingLabel(wbsHintKey) : ''
  const roadmapTilePrimary = roadmapP.trim()
    ? roadmapLocationLabel(roadmapP, scopeRepoHint)
    : ''
  const repoSynced = !scopeRepoHint || repo.trim() === scopeRepoHint

  useEffect(() => {
    setRepoDraft(repo)
  }, [repo])

  useEffect(() => {
    setIdDraft(nodeId)
  }, [nodeId])

  /** Roadmap must belong to the same product as the selected WBS. */
  useEffect(() => {
    if (!wbsP.trim() || !roadmapP.trim()) return
    const ok = filteredRoadmaps.some((r) => r.rel_path === roadmapP)
    if (!ok) setFields({ roadmap_p: undefined })
  }, [wbsP, roadmapP, filteredRoadmaps, setFields])

  useEffect(() => {
    if (!picker) return
    function onDoc(e: MouseEvent) {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setPicker(null)
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [picker])

  useEffect(() => {
    if (!picker) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setPicker(null)
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [picker])

  const toggle = (k: Exclude<PickerKind, null>) => {
    setPicker((p) => (p === k ? null : k))
  }

  const onPickWbs = (rel: string) => {
    const row = wbsList.find((w) => w.rel_path === rel)
    setFields({
      wbs_p: rel || undefined,
      roadmap_p: undefined,
      id: undefined,
      repo: row?.repo_hint?.trim() ? row.repo_hint.trim() : undefined,
    })
    setPicker(null)
  }

  const onPickRoadmap = (rel: string) => {
    if (!rel.trim()) {
      setFields({ roadmap_p: undefined, id: undefined })
      setPicker(null)
      return
    }
    const rm = rmList.find((r) => r.rel_path === rel)
    const rh = (rm?.repo_hint || '').trim()
    setFields({
      roadmap_p: rel,
      id: undefined,
      repo: rh || scopeRepoHint || undefined,
    })
    setPicker(null)
  }

  const syncRepoToBacklog = () => {
    if (!scopeRepoHint) return
    setFields({ repo: scopeRepoHint, id: undefined })
    setPicker(null)
  }

  const applyRepoDraft = () => {
    const t = repoDraft.trim()
    setFields({ repo: t || undefined, id: undefined })
    setPicker(null)
  }

  const applyIdDraft = () => {
    const t = idDraft.trim()
    setFields({ id: t || undefined })
    setPicker(null)
  }

  const clearWorkItem = () => {
    setFields({ id: undefined })
    setIdDraft('')
    setPicker(null)
  }

  const wbsMenuId = `${baseId}-wbs-menu`
  const rmMenuId = `${baseId}-rm-menu`
  const repoMenuId = `${baseId}-repo-menu`
  const workMenuId = `${baseId}-work-menu`

  const productScopeLine = scopeRepoHint
    ? `Showing only ${clusterHeadingLabel(scopeRepoHint)} — same product as this backlog.`
    : 'This backlog has no product folder prefix; all roadmaps are listed.'

  return (
    <section className="le-plan-scope" id="le-plan-scope-anchor" aria-label="Plan scope" ref={wrapRef}>
      <div className="le-plan-scope__row le-plan-scope__row--tiles">
        <div className="le-plan-scope__tiles">
          {/* Work backlog — compound shell so the MD path chip is not nested inside the main tile button. */}
          <div className="le-plan-scope__tile-wrap">
            <div
              className={`le-plan-scope__tile le-plan-scope__tile--compound le-plan-scope__tile--wbs${picker === 'wbs' ? ' le-plan-scope__tile--active' : ''}`}
            >
              <button
                type="button"
                className="le-plan-scope__tile-primary"
                aria-expanded={picker === 'wbs'}
                aria-haspopup="true"
                aria-controls={wbsMenuId}
                onClick={() => toggle('wbs')}
              >
                <span className="le-plan-scope__tile-primary-head">
                  <span className="le-plan-scope__tile-label">Work backlog</span>
                  <span className="le-plan-scope__tile-chev" aria-hidden>
                    ▾
                  </span>
                </span>
                <span className="le-plan-scope__tile-value">
                  {hasWbs ? wbsTileProduct : 'Choose a product backlog'}
                </span>
                {hasWbs ? (
                  <span className="le-plan-scope__tile-secondary le-plan-scope__tile-secondary--human">
                    {wbsBacklogPickerLabel(wbsP, scopeRepoHint)}
                  </span>
                ) : (
                  <span className="le-plan-scope__tile-hint">
                    One product · often one WBS file (or a small cluster)
                  </span>
                )}
              </button>
              {hasWbs ? (
                <div className="le-plan-scope__tile-side-tools">
                  <PlanScopeFilePathChip filePath={wbsP} stacked />
                </div>
              ) : null}
            </div>
            {picker === 'wbs' ? (
              <div id={wbsMenuId} className="le-plan-scope__popover" role="menu">
                <p className="le-plan-scope__popover-title">Backlog by product</p>
                <p className="le-plan-scope__popover-note forge-support">
                  Picking a different backlog clears roadmap and work item. Repository hint follows the file you pick.
                </p>
                <ul className="le-plan-scope__popover-list">
                  <li>
                    <button
                      type="button"
                      role="menuitem"
                      className={`le-plan-scope__popover-item${!wbsP.trim() ? ' le-plan-scope__popover-item--current' : ''}`}
                      onClick={() => onPickWbs('')}
                    >
                      <span className="le-plan-scope__popover-item-title">None</span>
                      <span className="le-plan-scope__popover-item-sub">Clear backlog scope</span>
                    </button>
                  </li>
                </ul>
                {wbsClusters.map((cl) => {
                  const showClusterHead = cl.items.length > 1
                  return (
                    <div key={cl.repoHint} className="le-plan-scope__cluster">
                      {showClusterHead ? (
                        <div className="le-plan-scope__cluster-head" aria-hidden>
                          {clusterHeadingLabel(cl.repoHint)}
                        </div>
                      ) : null}
                      <ul className="le-plan-scope__cluster-list">
                        {cl.items.map((w) => {
                          const itemRh = (w.repo_hint || '').trim()
                          const primary = showClusterHead
                            ? wbsBacklogPickerLabel(w.rel_path, itemRh)
                            : clusterHeadingLabel(cl.repoHint)
                          const secondary = showClusterHead
                            ? null
                            : wbsBacklogPickerLabel(w.rel_path, itemRh)
                          const current = w.rel_path === wbsP
                          return (
                            <li key={w.rel_path}>
                              <div
                                className={`le-plan-scope__picker-block le-plan-scope__picker-block--grid${current ? ' le-plan-scope__picker-block--current' : ''}`}
                              >
                                <button
                                  type="button"
                                  role="menuitem"
                                  className="le-plan-scope__popover-item le-plan-scope__popover-item--clustered le-plan-scope__picker-grid-main"
                                  onClick={() => onPickWbs(w.rel_path)}
                                >
                                  <span className="le-plan-scope__popover-item-title">{primary}</span>
                                  {secondary ? (
                                    <span className="le-plan-scope__popover-item-sub le-plan-scope__popover-item-sub--human">
                                      {secondary}
                                    </span>
                                  ) : null}
                                </button>
                                <PlanScopeFilePathChip filePath={w.rel_path} />
                              </div>
                            </li>
                          )
                        })}
                      </ul>
                    </div>
                  )
                })}
              </div>
            ) : null}
          </div>

          {/* Roadmap */}
          <div className="le-plan-scope__tile-wrap">
            <div
              className={`le-plan-scope__tile le-plan-scope__tile--compound le-plan-scope__tile--roadmap${picker === 'roadmap' ? ' le-plan-scope__tile--active' : ''}${!hasWbs ? ' le-plan-scope__tile--disabled' : ''}`}
            >
              <button
                type="button"
                className="le-plan-scope__tile-primary"
                aria-expanded={picker === 'roadmap'}
                aria-haspopup="true"
                aria-controls={rmMenuId}
                disabled={!hasWbs}
                title={!hasWbs ? 'Choose a work backlog first' : undefined}
                onClick={() => hasWbs && toggle('roadmap')}
              >
                <span className="le-plan-scope__tile-primary-head">
                  <span className="le-plan-scope__tile-label">Product roadmap</span>
                  <span className="le-plan-scope__tile-chev" aria-hidden>
                    ▾
                  </span>
                </span>
                <span className="le-plan-scope__tile-value">
                  {roadmapP.trim() ? roadmapTilePrimary : 'No roadmap'}
                </span>
                <span className="le-plan-scope__tile-hint">
                  {hasWbs
                    ? scopeRepoHint
                      ? `Only ${clusterHeadingLabel(scopeRepoHint)} roadmaps`
                      : 'Filtered to this backlog’s product when possible'
                    : 'Timeline / release context (optional)'}
                </span>
              </button>
              {hasWbs && roadmapP.trim() ? (
                <div className="le-plan-scope__tile-side-tools">
                  <PlanScopeFilePathChip filePath={roadmapP} stacked />
                </div>
              ) : null}
            </div>
            {picker === 'roadmap' && hasWbs ? (
              <div id={rmMenuId} className="le-plan-scope__popover" role="menu">
                <p className="le-plan-scope__popover-title">Roadmap in this product</p>
                <p className="le-plan-scope__popover-note forge-support">{productScopeLine}</p>
                <p className="le-plan-scope__popover-note forge-support">
                  Changing roadmap clears the focused work item and aligns the repository hint.
                </p>
                <ul className="le-plan-scope__popover-list">
                  <li>
                    <button
                      type="button"
                      role="menuitem"
                      className={`le-plan-scope__popover-item${!roadmapP.trim() ? ' le-plan-scope__popover-item--current' : ''}`}
                      onClick={() => onPickRoadmap('')}
                    >
                      <span className="le-plan-scope__popover-item-title">None</span>
                      <span className="le-plan-scope__popover-item-sub">WBS-only planning</span>
                    </button>
                  </li>
                  {filteredRoadmaps.length === 0 ? (
                    <li className="le-plan-scope__popover-empty forge-support">
                      No ROADMAP.md found under this product. Add one under the same folder as the backlog, or pick
                      another backlog.
                    </li>
                  ) : (
                    filteredRoadmaps.map((r) => {
                      const rh = (r.repo_hint || '').trim()
                      const current = r.rel_path === roadmapP
                      return (
                        <li key={r.rel_path}>
                          <div
                            className={`le-plan-scope__picker-block le-plan-scope__picker-block--grid${current ? ' le-plan-scope__picker-block--current' : ''}`}
                          >
                            <button
                              type="button"
                              role="menuitem"
                              className="le-plan-scope__popover-item le-plan-scope__picker-grid-main"
                              onClick={() => onPickRoadmap(r.rel_path)}
                            >
                              <span className="le-plan-scope__popover-item-product">
                                {rh ? clusterHeadingLabel(rh) : clusterHeadingLabel('__root__')}
                              </span>
                              <span className="le-plan-scope__popover-item-title">
                                {roadmapLocationLabel(r.rel_path, rh || scopeRepoHint)}
                              </span>
                            </button>
                            <PlanScopeFilePathChip filePath={r.rel_path} />
                          </div>
                        </li>
                      )
                    })
                  )}
                </ul>
              </div>
            ) : null}
          </div>

          {/* Repository */}
          <div className="le-plan-scope__tile-wrap">
            <button
              type="button"
              className={`le-plan-scope__tile le-plan-scope__tile--repo${picker === 'repo' ? ' le-plan-scope__tile--active' : ''}${!hasWbs ? ' le-plan-scope__tile--disabled' : ''}`}
              aria-expanded={picker === 'repo'}
              aria-haspopup="true"
              aria-controls={repoMenuId}
              disabled={!hasWbs}
              title={!hasWbs ? 'Choose a work backlog first' : undefined}
              onClick={() => hasWbs && toggle('repo')}
            >
              <span className="le-plan-scope__tile-label">Repository</span>
              <span className="le-plan-scope__tile-value">
                {hasWbs && scopeRepoHint ? clusterHeadingLabel(scopeRepoHint) : friendlyRepoLabel(repo) || '—'}
              </span>
              <span className="le-plan-scope__tile-hint">
                {hasWbs && scopeRepoHint
                  ? repoSynced
                    ? 'Matches backlog product'
                    : 'Out of sync with backlog — open to fix'
                  : 'Hint for API / scan'}
              </span>
              <span className="le-plan-scope__tile-chev" aria-hidden>
                ▾
              </span>
            </button>
            {picker === 'repo' && hasWbs ? (
              <div id={repoMenuId} className="le-plan-scope__popover" role="menu">
                <p className="le-plan-scope__popover-title">Repository hint</p>
                {scopeRepoHint ? (
                  <>
                    <p className="le-plan-scope__popover-note forge-support">
                      Scoped to backlog product <strong>{clusterHeadingLabel(scopeRepoHint)}</strong>. The hint should
                      match this folder so plan APIs and roadmaps stay consistent.
                    </p>
                    {!repoSynced ? (
                      <div className="le-plan-scope__popover-field">
                        <button type="button" className="le-btn le-btn--small" onClick={syncRepoToBacklog}>
                          Sync to backlog product
                        </button>
                      </div>
                    ) : (
                      <p className="le-plan-scope__popover-note forge-support">Hint is aligned with this backlog.</p>
                    )}
                  </>
                ) : (
                  <p className="le-plan-scope__popover-note forge-support">
                    This backlog path has no product prefix. You can set any repository hint; changing it clears the
                    focused work item.
                  </p>
                )}
                {!scopeRepoHint ? (
                  <div className="le-plan-scope__popover-field">
                    <label className="le-plan-scope__popover-field-label" htmlFor={`${baseId}-repo-input`}>
                      Custom hint
                    </label>
                    <input
                      id={`${baseId}-repo-input`}
                      className="le-input"
                      value={repoDraft}
                      onChange={(e) => setRepoDraft(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && applyRepoDraft()}
                    />
                    <button type="button" className="le-btn le-btn--small" onClick={applyRepoDraft}>
                      Apply
                    </button>
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>

          {/* Work item */}
          <div className="le-plan-scope__tile-wrap">
            <button
              type="button"
              className={`le-plan-scope__tile le-plan-scope__tile--work${picker === 'workitem' ? ' le-plan-scope__tile--active' : ''}${!hasWbs ? ' le-plan-scope__tile--disabled' : ''}`}
              aria-expanded={picker === 'workitem'}
              aria-haspopup="true"
              aria-controls={workMenuId}
              disabled={!hasWbs}
              title={!hasWbs ? 'Choose a work backlog first' : undefined}
              onClick={() => hasWbs && toggle('workitem')}
            >
              <span className="le-plan-scope__tile-label">Work item</span>
              <span className="le-plan-scope__tile-value">
                {nodeId.trim() ? nodeId : 'None selected'}
              </span>
              {focusStoryTitle && nodeId.trim() ? (
                <span className="le-plan-scope__tile-path">{focusStoryTitle}</span>
              ) : (
                <span className="le-plan-scope__tile-hint">Story / task id from WBS</span>
              )}
              <span className="le-plan-scope__tile-chev" aria-hidden>
                ▾
              </span>
            </button>
            {picker === 'workitem' && hasWbs ? (
              <div id={workMenuId} className="le-plan-scope__popover" role="menu">
                <p className="le-plan-scope__popover-title">Focused work item</p>
                <button type="button" className="le-btn le-btn--small" onClick={clearWorkItem}>
                  Clear selection
                </button>
                <div className="le-plan-scope__popover-field">
                  <label className="le-plan-scope__popover-field-label" htmlFor={`${baseId}-id-input`}>
                    Set by id
                  </label>
                  <input
                    id={`${baseId}-id-input`}
                    className="le-input"
                    value={idDraft}
                    onChange={(e) => setIdDraft(e.target.value)}
                    placeholder="e.g. M1E1S1"
                    onKeyDown={(e) => e.key === 'Enter' && applyIdDraft()}
                  />
                  <button type="button" className="le-btn le-btn--small" onClick={applyIdDraft}>
                    Apply
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>

        <button
          type="button"
          className="le-btn le-plan-scope__toggle"
          onClick={() => setAdvancedOpen(!advancedOpen)}
          aria-expanded={advancedOpen}
        >
          {advancedOpen ? 'Hide advanced' : 'Advanced'}
        </button>
      </div>

      {!hasWbs ? (
        <p className="le-plan-scope__empty-lead le-plan-scope__empty-lead--compact">
          Start with <strong>Work backlog</strong> — pick a product cluster, then roadmap and repository stay in that
          product.
        </p>
      ) : null}

      {advancedOpen ? (
        <div className="le-plan-scope__pickers le-form-row" style={{ flexDirection: 'column', alignItems: 'stretch' }}>
          <p className="le-plan-scope__pickers-hint forge-support">
            Raw query fields. Roadmap list is filtered to the same <code className="le-mono">repo_hint</code> as the
            selected WBS when the scanner provided one.
          </p>
          <label>
            Repository hint{' '}
            <input
              className="le-input"
              value={repo}
              onChange={(e) => setFields({ repo: e.target.value || undefined, id: undefined })}
              style={{ width: '100%', maxWidth: '28rem' }}
            />
          </label>
          <label>
            WBS file (backlog){' '}
            <select
              className="le-select"
              value={wbsP}
              onChange={(e) => {
                const rel = e.target.value
                const row = wbsList.find((w) => w.rel_path === rel)
                setFields({
                  wbs_p: rel || undefined,
                  roadmap_p: undefined,
                  id: undefined,
                  repo: row?.repo_hint?.trim() ? row.repo_hint.trim() : undefined,
                })
              }}
            >
              <option value="">— choose —</option>
              {wbsClusters.flatMap((cl) =>
                cl.items.map((w) => {
                  const itemRh = (w.repo_hint || '').trim()
                  const label = wbsBacklogPickerLabel(w.rel_path, itemRh)
                  return (
                    <option key={w.rel_path} value={w.rel_path} title={w.rel_path}>
                      [{clusterHeadingLabel(cl.repoHint)}] {label}
                    </option>
                  )
                }),
              )}
            </select>
          </label>
          <label>
            Roadmap (optional){' '}
            <select
              className="le-select"
              value={roadmapP}
              onChange={(e) => setFields({ roadmap_p: e.target.value || undefined, id: undefined })}
            >
              <option value="">— none —</option>
              {filteredRoadmaps.map((r) => {
                const rh = (r.repo_hint || '').trim() || scopeRepoHint
                const label = roadmapLocationLabel(r.rel_path, rh)
                return (
                  <option key={r.rel_path} value={r.rel_path} title={r.rel_path}>
                    {label}
                  </option>
                )
              })}
            </select>
          </label>
          <label>
            Work item id{' '}
            <input
              className="le-input"
              value={nodeId}
              onChange={(e) => setFields({ id: e.target.value || undefined })}
              placeholder="e.g. M1E1S1"
            />
          </label>
        </div>
      ) : null}
    </section>
  )
}
