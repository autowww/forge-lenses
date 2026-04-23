/**
 * Rich tile listbox — canonical Kitchen Sink React primitive.
 * Styles: ../css/tile-dropdown.css (`.ks-tile-dropdown`).
 */
import {
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from 'react'
import type {
  TileDropdownOption,
  TileDropdownRenderTile,
  TileRenderContext,
} from './tileDropdownTypes'

export type TileDropdownControlProps = {
  /** Selected option `value`. */
  value: string
  onChange: (value: string) => void
  options: TileDropdownOption[]
  placeholder?: string
  /** Visible label above the trigger (not inside the button). */
  label?: string
  className?: string
  id?: string
  disabled?: boolean
  emptyMessage?: string
  /** Max height of the option panel (scroll). */
  panelMaxHeight?: string
  /** Optional `aria-label` on the trigger when there is no visible `label` prop. */
  ariaLabel?: string
  /** `aria-label` on the listbox when `label` is omitted (default: "Options"). */
  panelAriaLabel?: string
  /** Full custom tile body; default layout still wraps focus/selection semantics. */
  renderTile?: TileDropdownRenderTile
}

function enabledIndices(options: TileDropdownOption[]): number[] {
  return options.map((o, i) => (o.disabled ? -1 : i)).filter((i) => i >= 0)
}

function defaultRenderTile(option: TileDropdownOption, _ctx: TileRenderContext): ReactNode {
  const statusClass = option.status?.variant
    ? `ks-tile-dropdown__status ks-tile-dropdown__status--${option.status.variant}`
    : 'ks-tile-dropdown__status ks-tile-dropdown__status--default'

  return (
    <>
      <div className="ks-tile-dropdown__tile-head">
        <span className="ks-tile-dropdown__tile-title">{option.title}</span>
        {option.status ? <span className={statusClass}>{option.status.text}</span> : null}
      </div>
      {option.subtitle ? (
        <p className="ks-tile-dropdown__tile-subtitle">{option.subtitle}</p>
      ) : null}
      {option.description ? (
        <p className="ks-tile-dropdown__tile-desc">{option.description}</p>
      ) : null}
      {option.meta && option.meta.length > 0 ? (
        <dl className="ks-tile-dropdown__meta">
          {option.meta.map((row) => (
            <div key={row.label} className="ks-tile-dropdown__meta-row">
              <dt>{row.label}</dt>
              <dd>{row.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </>
  )
}

export function TileDropdownControl({
  value,
  onChange,
  options,
  placeholder = 'Select…',
  label,
  className = '',
  id: idProp,
  disabled = false,
  emptyMessage = 'No options',
  panelMaxHeight = 'min(70vh, 22rem)',
  ariaLabel,
  panelAriaLabel = 'Options',
  renderTile,
}: TileDropdownControlProps) {
  const rootRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const optionRefs = useRef<Array<HTMLDivElement | null>>([])

  const baseId = useId()
  const labelId = idProp ? `${idProp}-label` : `${baseId}-label`
  const triggerId = idProp ? `${idProp}-trigger` : `${baseId}-trigger`
  const panelId = idProp ? `${idProp}-panel` : `${baseId}-panel`

  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)

  const indices = useMemo(() => enabledIndices(options), [options])
  const selected = useMemo(() => options.find((o) => o.value === value) ?? null, [options, value])

  const highlightOptionIndex = useCallback(
    (listIndex: number) => {
      if (indices.length === 0) return 0
      const pos = Math.max(0, Math.min(listIndex, indices.length - 1))
      return indices[pos]!
    },
    [indices],
  )

  const posOfOptionIndex = useCallback(
    (optionIndex: number) => {
      const p = indices.indexOf(optionIndex)
      return p < 0 ? 0 : p
    },
    [indices],
  )

  useEffect(() => {
    if (!open) return
    if (indices.length === 0) return
    const selIdx = options.findIndex((o) => o.value === value)
    const start =
      selIdx >= 0 && !options[selIdx]?.disabled ? selIdx : highlightOptionIndex(0)
    setHighlight(start)
    const t = window.requestAnimationFrame(() => {
      optionRefs.current[start]?.focus()
    })
    return () => window.cancelAnimationFrame(t)
  }, [open, value, options, highlightOptionIndex, indices])

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

  function pick(optionIndex: number) {
    const o = options[optionIndex]
    if (!o || o.disabled) return
    onChange(o.value)
    setOpen(false)
    triggerRef.current?.focus()
  }

  function onTriggerKeyDown(e: ReactKeyboardEvent<HTMLButtonElement>) {
    if (disabled) return
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setOpen(true)
    }
  }

  function onPanelKeyDown(e: ReactKeyboardEvent<HTMLDivElement>) {
    if (indices.length === 0) return
    const pos = posOfOptionIndex(highlight)

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = pos >= indices.length - 1 ? 0 : pos + 1
      const idx = highlightOptionIndex(next)
      setHighlight(idx)
      optionRefs.current[idx]?.focus()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const next = pos <= 0 ? indices.length - 1 : pos - 1
      const idx = highlightOptionIndex(next)
      setHighlight(idx)
      optionRefs.current[idx]?.focus()
    } else if (e.key === 'Home') {
      e.preventDefault()
      const idx = highlightOptionIndex(0)
      setHighlight(idx)
      optionRefs.current[idx]?.focus()
    } else if (e.key === 'End') {
      e.preventDefault()
      const idx = highlightOptionIndex(indices.length - 1)
      setHighlight(idx)
      optionRefs.current[idx]?.focus()
    }
  }

  function onOptionKeyDown(e: ReactKeyboardEvent<HTMLDivElement>, optionIndex: number) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      pick(optionIndex)
    }
  }

  const triggerText = selected
    ? selected.subtitle
      ? `${selected.title} — ${selected.subtitle}`
      : selected.title
    : placeholder

  const defaultTriggerAria = `Select option. ${selected ? `Current: ${selected.title}` : placeholder}`
  const triggerAriaResolved = ariaLabel ?? (label ? undefined : defaultTriggerAria)

  const rootClass = ['ks-tile-dropdown', open ? 'ks-tile-dropdown--open' : '', className]
    .filter(Boolean)
    .join(' ')

  const renderBody = renderTile ?? defaultRenderTile

  return (
    <div ref={rootRef} className={rootClass}>
      {label ? (
        <label id={labelId} htmlFor={triggerId} className="ks-tile-dropdown__label">
          {label}
        </label>
      ) : null}
      <button
        ref={triggerRef}
        id={triggerId}
        type="button"
        className="ks-tile-dropdown__trigger"
        disabled={disabled}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-controls={panelId}
        aria-label={triggerAriaResolved}
        onClick={() => !disabled && setOpen((o) => !o)}
        onKeyDown={onTriggerKeyDown}
      >
        <span className="ks-tile-dropdown__trigger-main">{triggerText}</span>
        <span className="ks-tile-dropdown__trigger-chevron" aria-hidden="true" />
      </button>

      <div
        id={panelId}
        className="ks-tile-dropdown__panel"
        hidden={!open}
        role="listbox"
        aria-labelledby={label ? labelId : undefined}
        aria-label={label ? undefined : panelAriaLabel}
        tabIndex={-1}
        style={{ maxHeight: panelMaxHeight }}
        onKeyDown={onPanelKeyDown}
      >
        {options.length === 0 ? (
          <p className="ks-tile-dropdown__empty">{emptyMessage}</p>
        ) : (
          options.map((opt, optionIndex) => {
            const isSelected = opt.value === value
            const isHighlighted = optionIndex === highlight
            const ctx: TileRenderContext = { selected: isSelected, highlighted: isHighlighted }
            const isDisabled = !!opt.disabled

            return (
              <div
                key={opt.value}
                ref={(el) => {
                  optionRefs.current[optionIndex] = el
                }}
                role="option"
                tabIndex={open && !isDisabled ? (isHighlighted ? 0 : -1) : -1}
                aria-selected={isSelected}
                aria-disabled={isDisabled}
                data-highlighted={isHighlighted ? 'true' : undefined}
                className={
                  'ks-tile-dropdown__tile' +
                  (isSelected ? ' ks-tile-dropdown__tile--selected' : '') +
                  (isHighlighted ? ' ks-tile-dropdown__tile--highlighted' : '') +
                  (isDisabled ? ' ks-tile-dropdown__tile--disabled' : '')
                }
                onMouseEnter={() => !isDisabled && setHighlight(optionIndex)}
                onClick={() => !isDisabled && pick(optionIndex)}
                onKeyDown={(e) => !isDisabled && onOptionKeyDown(e, optionIndex)}
              >
                {renderBody(opt, ctx)}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
