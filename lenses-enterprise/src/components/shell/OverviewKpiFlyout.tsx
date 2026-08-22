import { useEffect, useId, useRef } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import type { OverviewChartPayload } from '../../api/chartOverview'
import {
  complianceByRepo,
  topReposByLinesAdded,
} from '../../api/chartOverview'
import { commitsKpiLabel, horizonPeriodPhrase, linesAddedKpiLabel } from '../../api/chartOverview'
import { sumCommitDailySevenDay } from '../../api/chartOverview'
import type { TimeHorizonId } from '../../context/ShellChromeContext'

export type OverviewKpiFlyoutKind = 'commits' | 'lines' | 'standards'

type Props = {
  open: boolean
  kind: OverviewKpiFlyoutKind
  onClose: () => void
  payload: OverviewChartPayload | null
  timeHorizon: TimeHorizonId
  anchorRef: React.RefObject<HTMLElement | null>
}

export function OverviewKpiFlyout({
  open,
  kind,
  onClose,
  payload,
  timeHorizon,
  anchorRef,
}: Props) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open || !payload) return null

  const commitsTotal = sumCommitDailySevenDay(payload)
  const linesTop = topReposByLinesAdded(payload, 8)
  const compliance = [...complianceByRepo(payload).entries()].sort((a, b) => a[1] - b[1])

  let title = 'Overview detail'
  let summary = ''
  let list: { key: string; primary: string; secondary: string }[] = []

  if (kind === 'commits') {
    title = commitsKpiLabel(timeHorizon)
    summary = `${commitsTotal ?? '—'} commits in the ${horizonPeriodPhrase(timeHorizon)}.`
    const series = payload.charts?.commit_daily?.series ?? []
    list = series.slice(-7).map((row) => ({
      key: String(row.day ?? ''),
      primary: String(row.day ?? '—'),
      secondary: `${row.count ?? 0} commits`,
    }))
  } else if (kind === 'lines') {
    title = linesAddedKpiLabel(timeHorizon)
    const cur = payload.kpi_trends?.lines_added?.current_total
    summary = `${typeof cur === 'number' ? cur.toLocaleString() : '—'} lines added in the ${horizonPeriodPhrase(timeHorizon)}.`
    list = linesTop.map((row) => ({
      key: row.name,
      primary: row.name,
      secondary: `${row.linesAdded.toLocaleString()} lines`,
    }))
  } else {
    title = 'Standards (avg)'
    const avg =
      payload.kpi_trends?.snapshots?.standards_avg?.current ??
      (compliance.length
        ? Math.round(compliance.reduce((s, [, v]) => s + v, 0) / compliance.length)
        : null)
    summary = avg != null ? `Workspace average compliance score: ${avg}/100.` : 'No standards scores in scan.'
    list = compliance.slice(0, 10).map(([name, score]) => ({
      key: name,
      primary: name,
      secondary: `${score}/100`,
    }))
  }

  return createPortal(
    <div className="le-publish-health-popover le-overview-kpi-flyout" role="presentation">
      <button
        type="button"
        className="le-publish-health-popover__backdrop"
        aria-label="Close KPI details"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        className="le-publish-health-popover__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        style={
          anchorRef.current
            ? {
                top: anchorRef.current.getBoundingClientRect().bottom + 8,
                left: Math.max(8, anchorRef.current.getBoundingClientRect().left - 80),
              }
            : undefined
        }
      >
        <header className="le-publish-health-popover__header">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="le-btn le-btn--ghost" onClick={onClose}>
            Close
          </button>
        </header>
        <p className="le-publish-health-popover__summary">{summary}</p>
        {list.length ? (
          <ul className="le-publish-health-popover__sites">
            {list.map((row) => (
              <li key={row.key}>
                <strong>{row.primary}</strong>
                <span className="forge-support">{row.secondary}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="forge-support">No rows for this metric yet.</p>
        )}
        <footer className="le-publish-health-popover__footer">
          {kind === 'standards' ? (
            <Link className="le-btn le-btn--primary" to={{ pathname: '/', hash: 'le-cc-standards' }} onClick={onClose}>
              Open standards section
            </Link>
          ) : (
            <Link className="le-btn le-btn--primary" to="/projects" onClick={onClose}>
              Open projects
            </Link>
          )}
        </footer>
      </div>
    </div>,
    document.body,
  )
}
