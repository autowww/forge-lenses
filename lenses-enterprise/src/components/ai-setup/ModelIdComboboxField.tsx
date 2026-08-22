import type { CSSProperties, ReactNode } from 'react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

type Props = {
  inputId: string
  listId: string
  label: ReactNode
  /** Shown under the field (e.g. loading / catalog error). */
  hint?: string | null
  value: string
  onChange: (next: string) => void
  optionIds: string[]
  disabled?: boolean
  /** When true, input shows busy state for catalog fetch. */
  catalogBusy?: boolean
  placeholder?: string
  className?: string
  style?: CSSProperties
}

function filterModelOptions(optionIds: string[], query: string): string[] {
  const t = query.trim().toLowerCase()
  if (!t) return optionIds
  return optionIds.filter((id) => id.toLowerCase().includes(t))
}

/**
 * Editable model id control: searchable dropdown from the catalog plus free-text entry.
 * Empty value means “use routing / server default”.
 */
export function ModelIdComboboxField({
  inputId,
  listId,
  label,
  hint,
  value,
  onChange,
  optionIds,
  disabled,
  catalogBusy,
  placeholder = 'Search or type a model id…',
  className,
  style,
}: Props) {
  const wrapRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)

  const filtered = useMemo(() => filterModelOptions(optionIds, value), [optionIds, value])

  useEffect(() => {
    if (!open) return
    setHighlight((h) => Math.min(h, Math.max(0, filtered.length - 1)))
  }, [open, filtered.length])

  useEffect(() => {
    if (!open) return
    const onDocDown = (e: MouseEvent) => {
      const el = wrapRef.current
      if (el && !el.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDocDown)
    return () => document.removeEventListener('mousedown', onDocDown)
  }, [open])

  const pick = useCallback(
    (modelId: string) => {
      onChange(modelId)
      setOpen(false)
      inputRef.current?.focus()
    },
    [onChange],
  )

  const onInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (disabled) return
    if (e.key === 'Escape') {
      setOpen(false)
      return
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (!open) {
        setOpen(true)
        setHighlight(0)
        return
      }
      setHighlight((h) => Math.min(h + 1, Math.max(0, filtered.length - 1)))
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (!open) return
      setHighlight((h) => Math.max(h - 1, 0))
      return
    }
    if (e.key === 'Enter' && open && filtered.length > 0) {
      e.preventDefault()
      pick(filtered[highlight] ?? '')
    }
  }

  return (
    <div className={className} style={style}>
      <label className="forge-support" style={{ display: 'block', fontSize: '0.8rem', margin: 0 }} htmlFor={inputId}>
        {label}
      </label>
      {hint ? (
        <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0.15rem 0 0.25rem', opacity: 0.78 }}>
          {hint}
        </p>
      ) : null}
      <div ref={wrapRef} className="le-search-combo" style={{ marginTop: hint ? 0 : '0.2rem' }}>
        <div className="le-search-combo__field">
          <input
            ref={inputRef}
            id={inputId}
            type="text"
            className="le-input le-mono le-search-combo__input"
            value={value}
            onChange={(e) => {
              onChange(e.target.value)
              setOpen(true)
              setHighlight(0)
            }}
            disabled={disabled}
            aria-busy={catalogBusy || undefined}
            autoComplete="off"
            spellCheck={false}
            placeholder={placeholder}
            aria-expanded={open}
            aria-controls={open ? listId : undefined}
            aria-autocomplete="list"
            role="combobox"
            title="Search the catalog or type any model id. Leave empty for the default model."
            onFocus={() => setOpen(true)}
            onKeyDown={onInputKeyDown}
          />
          <button
            type="button"
            className="le-search-combo__toggle le-btn"
            disabled={disabled}
            tabIndex={-1}
            aria-label="Show model list"
            onClick={() => {
              setOpen((o) => !o)
              if (!open) setHighlight(0)
            }}
          >
            ▾
          </button>
        </div>
        {open && filtered.length > 0 ? (
          <ul id={listId} className="le-search-combo__list" role="listbox">
            {filtered.map((mid, i) => (
              <li key={mid} role="none">
                <button
                  type="button"
                  role="option"
                  aria-selected={i === highlight}
                  className={`le-search-combo__option${i === highlight ? ' le-search-combo__option--active' : ''}`}
                  onMouseEnter={() => setHighlight(i)}
                  onClick={() => pick(mid)}
                >
                  <span className="le-mono">{mid}</span>
                </button>
              </li>
            ))}
          </ul>
        ) : null}
        {open && filtered.length === 0 ? (
          <p className="le-search-combo__empty forge-support">
            {optionIds.length === 0
              ? 'No models in the catalog yet — type a model id or run Discover models on this provider.'
              : 'No matches — keep typing a custom id or clear the filter to see all models.'}
          </p>
        ) : null}
      </div>
    </div>
  )
}
