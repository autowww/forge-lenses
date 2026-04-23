/**
 * Workspace Lens — Flow / Artifacts (canonical). Lenses Studio copies into `src/forgesdlc-kitchensink/`; run `npm run sync-kitchensink-react` there after edits.
 */
import { useEffect, useId, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import type { WorkspaceLensMode } from './workspaceLensTypes'

export type WorkspaceLensControlProps = {
  mode: WorkspaceLensMode
  onModeChange: (mode: WorkspaceLensMode) => void
  /** When set and different from `mode`, shows a dismissible hint (e.g. route heuristic). */
  suggestedLens?: WorkspaceLensMode | null
  hintDismissed?: boolean
  onDismissHint?: () => void
  /** Appended to root `className` (e.g. `le-workspace-lens le-lens`). */
  className?: string
  /**
   * `toggle` — two-pane segmented control (enterprise chrome).
   * `dropdown` — compact trigger + listbox panel (original).
   */
  presentation?: 'dropdown' | 'toggle'
}

const HELPER: Record<WorkspaceLensMode, string> = {
  flow: 'Planning through delivery and release',
  artifacts: 'Browse workspace objects directly',
}

const PANEL_DESC: Record<WorkspaceLensMode, string> = {
  flow: 'Follow work from planning to release — lifecycle order.',
  artifacts:
    'Browse plans, projects, boards, sites, and documentation — by asset type.',
}

const HINT: Record<WorkspaceLensMode, string> = {
  flow: 'Roadmap and story views often feel clearer in Flow.',
  artifacts: 'Repositories and site previews are quick to reach in Artifacts.',
}

const MODES: WorkspaceLensMode[] = ['flow', 'artifacts']

/** Eye icon — shown only on the active Flow | Artifacts segment (toggle presentation). */
function LensEyeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="14"
      height="14"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="currentColor"
        d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"
      />
    </svg>
  )
}

/**
 * Flow / Artifacts workspace lens switcher (listbox popover).
 * Styles: load `css/workspace-lens.css` from kitchensink; optional `.le-lens` refinements ship in the same file.
 */
export function WorkspaceLensControl({
  mode,
  onModeChange,
  suggestedLens = null,
  hintDismissed = false,
  onDismissHint,
  className = '',
  presentation = 'dropdown',
}: WorkspaceLensControlProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const segRefs = useRef<Array<HTMLButtonElement | null>>([null, null])

  const labelId = useId()
  const panelId = useId()
  const hintId = useId()

  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)

  const showHint =
    suggestedLens !== null &&
    suggestedLens !== undefined &&
    suggestedLens !== mode &&
    !hintDismissed
  const modeIndex = mode === 'flow' ? 0 : 1

  useEffect(() => {
    if (!open) return
    setHighlight(modeIndex)
    const t = window.requestAnimationFrame(() => {
      segRefs.current[modeIndex]?.focus()
    })
    return () => window.cancelAnimationFrame(t)
  }, [open, modeIndex])

  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault()
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    function onPointerDown(e: MouseEvent) {
      const el = rootRef.current
      if (el && !el.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('keydown', onKey, true)
    document.addEventListener('mousedown', onPointerDown)
    return () => {
      document.removeEventListener('keydown', onKey, true)
      document.removeEventListener('mousedown', onPointerDown)
    }
  }, [open])

  function pick(m: WorkspaceLensMode) {
    onModeChange(m)
    setOpen(false)
    triggerRef.current?.focus()
  }

  function onTriggerKeyDown(e: ReactKeyboardEvent<HTMLButtonElement>) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setOpen(true)
    }
  }

  function onPanelKeyDown(e: ReactKeyboardEvent<HTMLDivElement>) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = highlight >= 1 ? 0 : highlight + 1
      setHighlight(next)
      segRefs.current[next]?.focus()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const next = highlight <= 0 ? 1 : highlight - 1
      setHighlight(next)
      segRefs.current[next]?.focus()
    } else if (e.key === 'Home') {
      e.preventDefault()
      setHighlight(0)
      segRefs.current[0]?.focus()
    } else if (e.key === 'End') {
      e.preventDefault()
      setHighlight(1)
      segRefs.current[1]?.focus()
    }
  }

  function onSegmentKeyDown(e: ReactKeyboardEvent<HTMLButtonElement>, m: WorkspaceLensMode) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      pick(m)
    }
  }

  const describedBy = showHint && suggestedLens ? hintId : undefined
  const triggerLabel =
    mode === 'flow'
      ? 'Workspace lens: Flow. Open to switch lens.'
      : 'Workspace lens: Artifacts. Open to switch lens.'

  if (presentation === 'toggle') {
    const toggleClass = ['ks-workspace-lens', 'ks-workspace-lens--toggle', 'le-lens', 'le-lens--compact', className]
      .filter(Boolean)
      .join(' ')
    return (
      <div className={toggleClass}>
        <div className="le-lens-toggle__row le-lens-toggle__row--compact">
          <span id={labelId} className="sr-only">
            Workspace lens
          </span>
          <div
            className="le-lens-toggle le-lens-toggle--compact"
            role="group"
            aria-labelledby={labelId}
            aria-describedby={describedBy}
          >
            <button
              type="button"
              className={`le-lens-toggle__seg le-lens-toggle__seg--left${mode === 'flow' ? ' le-lens-toggle__seg--active' : ''}`}
              aria-pressed={mode === 'flow'}
              aria-label={`Flow — ${PANEL_DESC.flow}`}
              onClick={() => onModeChange('flow')}
            >
              <span className="le-lens-toggle__seg-inner">
                {mode === 'flow' ? <LensEyeIcon className="le-lens-toggle__eye" /> : null}
                <span className="le-lens-toggle__label">Flow</span>
              </span>
              <span className="le-lens-toggle__tip" aria-hidden="true">
                {PANEL_DESC.flow}
              </span>
            </button>
            <button
              type="button"
              className={`le-lens-toggle__seg le-lens-toggle__seg--right${mode === 'artifacts' ? ' le-lens-toggle__seg--active' : ''}`}
              aria-pressed={mode === 'artifacts'}
              aria-label={`Artifacts — ${PANEL_DESC.artifacts}`}
              onClick={() => onModeChange('artifacts')}
            >
              <span className="le-lens-toggle__seg-inner">
                {mode === 'artifacts' ? <LensEyeIcon className="le-lens-toggle__eye" /> : null}
                <span className="le-lens-toggle__label">Artifacts</span>
              </span>
              <span className="le-lens-toggle__tip" aria-hidden="true">
                {PANEL_DESC.artifacts}
              </span>
            </button>
          </div>
        </div>
        {showHint && suggestedLens && (
          <div id={hintId} className="ks-workspace-lens__suggestion le-lens__hint le-lens-toggle__route-hint" role="note">
            <span className="le-lens__hint-text">{HINT[suggestedLens]}</span>
            {onDismissHint ? (
              <button
                type="button"
                className="ks-workspace-lens__suggestion-dismiss le-lens__hint-dismiss"
                onClick={() => onDismissHint()}
              >
                Dismiss
              </button>
            ) : null}
          </div>
        )}
      </div>
    )
  }

  const rootClass = ['ks-workspace-lens', 'le-lens', className, open ? 'ks-workspace-lens--open' : '']
    .filter(Boolean)
    .join(' ')

  return (
    <div ref={rootRef} className={rootClass}>
      <div className="le-lens__header">
        <span id={labelId} className="ks-workspace-lens__eyebrow le-lens__eyebrow">
          Workspace lens
        </span>
        <button
          ref={triggerRef}
          type="button"
          className="ks-workspace-lens__trigger le-lens__trigger"
          aria-expanded={open}
          aria-haspopup="listbox"
          aria-controls={panelId}
          aria-labelledby={labelId}
          aria-describedby={describedBy}
          aria-label={triggerLabel}
          onClick={() => setOpen((openPrev: boolean) => !openPrev)}
          onKeyDown={onTriggerKeyDown}
        >
          <span className="ks-workspace-lens__trigger-label le-lens__trigger-value" aria-hidden="true">
            {mode === 'flow' ? 'Flow' : 'Artifacts'}
          </span>
          <span className="le-lens__trigger-chevron" aria-hidden="true" />
        </button>
      </div>

      <p className="ks-workspace-lens__helper le-lens__helper" aria-hidden="true">
        {HELPER[mode]}
      </p>

      {showHint && suggestedLens && (
        <div id={hintId} className="ks-workspace-lens__suggestion le-lens__hint" role="note">
          <span className="le-lens__hint-text">{HINT[suggestedLens]}</span>
          {onDismissHint ? (
            <button
              type="button"
              className="ks-workspace-lens__suggestion-dismiss le-lens__hint-dismiss"
              onClick={() => onDismissHint()}
            >
              Dismiss
            </button>
          ) : null}
        </div>
      )}

      <div
        id={panelId}
        className="ks-workspace-lens__panel le-lens__panel"
        hidden={!open}
        role="listbox"
        aria-labelledby={labelId}
        tabIndex={-1}
        onKeyDown={onPanelKeyDown}
      >
        <p className="le-lens__panel-intro">
          Choose how the workspace is organized. Your choice is saved in this browser.
        </p>
        <div className="ks-workspace-lens__segments le-lens__segments" role="presentation">
          {MODES.map((m, idx) => (
            <button
              key={m}
              ref={(el) => {
                segRefs.current[idx] = el
              }}
              type="button"
              role="option"
              tabIndex={open ? (highlight === idx ? 0 : -1) : -1}
              aria-selected={mode === m}
              className={`ks-workspace-lens__segment le-lens__segment${mode === m ? ' ks-workspace-lens__segment--active' : ''}`}
              onClick={() => pick(m)}
              onMouseEnter={() => setHighlight(idx)}
              onKeyDown={(e) => onSegmentKeyDown(e, m)}
            >
              <span className="ks-workspace-lens__segment-title">{m === 'flow' ? 'Flow' : 'Artifacts'}</span>
              <span className="ks-workspace-lens__segment-desc">{PANEL_DESC[m]}</span>
            </button>
          ))}
        </div>
        <p className="ks-workspace-lens__remember le-lens__remember" role="note">
          Preference persists for this browser on this device.
        </p>
      </div>
    </div>
  )
}
