import { useWorkspace } from '../../context/WorkspaceContext'
import {
  useShellChrome,
  type CompareModeId,
  type TimeHorizonId,
} from '../../context/ShellChromeContext'

function labelHorizon(h: TimeHorizonId): string {
  switch (h) {
    case 'day':
      return 'Last 24 hours'
    case 'week':
      return 'This week'
    case 'month':
      return 'This month'
    case 'quarter':
      return 'This quarter'
    default:
      return 'This week'
  }
}

function labelCompare(c: CompareModeId): string {
  return c === 'previous_period' ? 'Previous period' : 'None'
}

export function ContextBar() {
  const { state } = useWorkspace()
  const {
    timeHorizon,
    setTimeHorizon,
    compareMode,
    setCompareMode,
    overviewDataLoading,
  } = useShellChrome()

  const root = state?.workspace_root?.trim() || 'Workspace'
  const short =
    root.length > 56 ? `${root.slice(0, 24)}…${root.slice(-20)}` : root

  return (
    <div className="le-context-bar" role="region" aria-label="Scope and time">
      <div className="le-context-bar__cluster">
        <span className="le-context-bar__label">Scope</span>
        <span className="le-context-bar__value" title={root}>
          {short}
        </span>
      </div>
      <div
        className={
          overviewDataLoading
            ? 'le-context-bar__cluster le-context-bar__cluster--data-loading'
            : 'le-context-bar__cluster'
        }
      >
        {overviewDataLoading ? (
          <div className="le-context-bar__cluster-blade le-loading-blade" aria-hidden />
        ) : null}
        <label className="le-context-bar__label" htmlFor="le-horizon">
          Time horizon
        </label>
        <select
          id="le-horizon"
          className="le-context-bar__select"
          value={timeHorizon}
          aria-busy={overviewDataLoading}
          onChange={(e) => setTimeHorizon(e.target.value as TimeHorizonId)}
        >
          <option value="day">{labelHorizon('day')}</option>
          <option value="week">{labelHorizon('week')}</option>
          <option value="month">{labelHorizon('month')}</option>
          <option value="quarter">{labelHorizon('quarter')}</option>
        </select>
      </div>
      <div className="le-context-bar__cluster">
        <label className="le-context-bar__label" htmlFor="le-compare">
          Compare to
        </label>
        <select
          id="le-compare"
          className="le-context-bar__select"
          value={compareMode}
          onChange={(e) => setCompareMode(e.target.value as CompareModeId)}
        >
          <option value="none">{labelCompare('none')}</option>
          <option value="previous_period">{labelCompare('previous_period')}</option>
        </select>
      </div>
      <div className="le-context-bar__cluster le-context-bar__cluster--muted">
        <span className="le-context-bar__label">Saved view</span>
        <button type="button" className="le-context-bar__stub" disabled title="Coming soon">
          Default
        </button>
      </div>
      <div className="le-context-bar__cluster le-context-bar__cluster--muted">
        <span className="le-context-bar__label">Filters</span>
        <button type="button" className="le-context-bar__stub" disabled title="Coming soon">
          None
        </button>
      </div>
    </div>
  )
}
