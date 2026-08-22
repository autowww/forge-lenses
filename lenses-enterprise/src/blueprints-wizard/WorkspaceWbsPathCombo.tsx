import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'

const WORKSPACE_ROOT_KEY = '__workspace__'

export type WbsProjectPayload = {
  key?: string
  label?: string
  is_git?: boolean
  has_wbs_md?: boolean
  wbs?: { rel_path?: string; kind?: string }[]
}

type Suggestion =
  | { kind: 'existing'; relPath: string; projectLabel: string; isGit?: boolean }
  | { kind: 'suggested'; relPath: string; projectLabel: string }

type Props = {
  id: string
  value: string
  onChange: (next: string) => void
  disabled?: boolean
  projects: WbsProjectPayload[]
  placeholder?: string
}

function buildSuggestions(projects: WbsProjectPayload[]): Suggestion[] {
  const out: Suggestion[] = []
  const seen = new Set<string>()

  for (const p of projects) {
    const projectLabel = typeof p.label === 'string' ? p.label : String(p.key ?? '')
    const wbs = Array.isArray(p.wbs) ? p.wbs : []
    for (const w of wbs) {
      const rel = typeof w?.rel_path === 'string' ? w.rel_path : ''
      if (!rel) continue
      const low = rel.toLowerCase()
      if (!low.endsWith('wbs.md')) continue
      if (seen.has(rel)) continue
      seen.add(rel)
      out.push({ kind: 'existing', relPath: rel, projectLabel, isGit: p.is_git })
    }
  }

  for (const p of projects) {
    const key = typeof p.key === 'string' ? p.key : ''
    if (!key) continue
    if (p.has_wbs_md !== false) continue
    const relPath =
      key === WORKSPACE_ROOT_KEY ? 'docs/requirements/WBS.md' : `${key}/docs/requirements/WBS.md`
    if (seen.has(relPath)) continue
    seen.add(relPath)
    const projectLabel = typeof p.label === 'string' ? p.label : key
    out.push({ kind: 'suggested', relPath, projectLabel })
  }

  out.sort((a, b) => a.relPath.localeCompare(b.relPath, undefined, { sensitivity: 'base' }))
  return out
}

function filterSuggestions(rows: Suggestion[], q: string): Suggestion[] {
  const t = q.trim().toLowerCase()
  if (!t) return rows
  return rows.filter(
    (r) =>
      r.relPath.toLowerCase().includes(t) || r.projectLabel.toLowerCase().includes(t),
  )
}

/**
 * Editable path field with a Studio-themed list: pick an existing workspace WBS path
 * or keep typing a custom relative path for a new product folder.
 */
export function WorkspaceWbsPathCombo({
  id,
  value,
  onChange,
  disabled = false,
  projects,
  placeholder = 'e.g. myproject/docs/requirements/WBS.md',
}: Props) {
  const listId = useId()
  const wrapRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)

  const allSuggestions = useMemo(() => buildSuggestions(projects), [projects])
  const filtered = useMemo(() => filterSuggestions(allSuggestions, value), [allSuggestions, value])

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
    (relPath: string) => {
      onChange(relPath)
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
      pick(filtered[highlight]?.relPath ?? '')
    }
  }

  return (
    <div ref={wrapRef} className="le-wbs-combo">
      <div className="le-wbs-combo__field">
        <input
          ref={inputRef}
          id={id}
          className="le-input le-wbs-combo__input"
          type="text"
          value={value}
          disabled={disabled}
          placeholder={placeholder}
          autoComplete="off"
          aria-expanded={open}
          aria-controls={open ? listId : undefined}
          aria-autocomplete="list"
          role="combobox"
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setOpen(true)}
          onKeyDown={onInputKeyDown}
          style={{ width: '100%', boxSizing: 'border-box' }}
        />
        <button
          type="button"
          className="le-wbs-combo__toggle le-btn"
          disabled={disabled}
          tabIndex={-1}
          aria-label="Show workspace paths"
          onClick={() => {
            setOpen((o) => !o)
            if (!open) setHighlight(0)
          }}
        >
          ▾
        </button>
      </div>
      {open && filtered.length > 0 && (
        <ul id={listId} className="le-wbs-combo__list" role="listbox">
          {filtered.map((row, i) => (
            <li key={`${row.kind}-${row.relPath}`} role="none">
              <button
                type="button"
                role="option"
                aria-selected={i === highlight}
                className={`le-wbs-combo__option${i === highlight ? ' le-wbs-combo__option--active' : ''}`}
                onMouseEnter={() => setHighlight(i)}
                onClick={() => pick(row.relPath)}
              >
                <span className="le-wbs-combo__path le-mono">{row.relPath}</span>
                <span className="le-wbs-combo__meta">
                  {row.kind === 'suggested' ? (
                    <span className="le-wbs-combo__badge le-wbs-combo__badge--new">New folder</span>
                  ) : row.isGit ? (
                    <span className="le-wbs-combo__badge">git</span>
                  ) : null}
                  <span className="le-wbs-combo__proj">{row.projectLabel}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && filtered.length === 0 && allSuggestions.length === 0 && (
        <p className="le-wbs-combo__empty forge-support">
          No workspace projects discovered yet. Type a relative path to your WBS file.
        </p>
      )}
      {open && filtered.length === 0 && allSuggestions.length > 0 && (
        <p className="le-wbs-combo__empty forge-support">
          No matching paths. Continue typing to use a new relative path, or clear the filter.
        </p>
      )}
    </div>
  )
}
