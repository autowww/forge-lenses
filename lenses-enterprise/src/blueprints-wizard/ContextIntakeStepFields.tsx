import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiGetJson } from '../api/http'
import type { ContextIntakeFieldErrors, ContextIntakePayloadV1 } from './contextIntakeStep'
import { CONTEXT_REFERENCE_HINTS_MAX, CONTEXT_ROUGH_MAX } from './contextIntakeStep'
import { MockContextSnippetProvider } from './contextIntakeAdapters'
import type { ContextSnippetKind } from './contextIntakeAdapters'

type WbsRow = { key?: string; label?: string; wbs?: { rel_path?: string }[] }

type Props = {
  value: ContextIntakePayloadV1
  onChange: (next: ContextIntakePayloadV1) => void
  fieldErrors?: ContextIntakeFieldErrors
  showErrors?: boolean
  disabled?: boolean
}

export function ContextIntakeStepFields({ value, onChange, fieldErrors = {}, showErrors = false, disabled = false }: Props) {
  const [wbsChoices, setWbsChoices] = useState<{ rel: string; label: string }[]>([])
  const [preview, setPreview] = useState<string | null>(null)
  const [previewBusy, setPreviewBusy] = useState<ContextSnippetKind | null>(null)
  const mock = useMemo(() => new MockContextSnippetProvider(), [])

  useEffect(() => {
    let cancelled = false
    void (async () => {
      try {
        const data = await apiGetJson<{ projects?: WbsRow[] }>('/api/wbs-management')
        const projects = Array.isArray(data.projects) ? data.projects : []
        const hints: { rel: string; label: string }[] = []
        for (const p of projects) {
          const label = typeof p.label === 'string' ? p.label : String(p.key ?? '')
          const wbs = Array.isArray(p.wbs) ? p.wbs : []
          for (const w of wbs) {
            const rel = typeof w?.rel_path === 'string' ? w.rel_path : ''
            if (rel) hints.push({ rel, label })
          }
        }
        if (!cancelled) setWbsChoices(hints)
      } catch {
        if (!cancelled) setWbsChoices([])
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const toggleFlag = useCallback(
    (key: keyof ContextIntakePayloadV1['sourceFlags']) => {
      onChange({
        ...value,
        sourceFlags: { ...value.sourceFlags, [key]: !value.sourceFlags[key] },
      })
    },
    [onChange, value],
  )

  const runPreview = useCallback(
    async (kind: ContextSnippetKind) => {
      setPreviewBusy(kind)
      setPreview(null)
      try {
        const ref = value.referenceHints.trim() || value.attachments[0]?.ref
        const text = await mock.getSnippet(kind, ref)
        setPreview(text)
      } finally {
        setPreviewBusy(null)
      }
    },
    [mock, value.attachments, value.referenceHints],
  )

  const errRough = showErrors ? fieldErrors.roughNotes : undefined
  const errRef = showErrors ? fieldErrors.referenceHints : undefined

  const [wbsSelectKey, setWbsSelectKey] = useState(0)
  const onWbsPick = (rel: string) => {
    if (!rel) return
    const label = wbsChoices.find((h) => h.rel === rel)?.label ?? rel
    const next = [...value.attachments]
    if (!next.some((a) => a.kind === 'wbs' && a.ref === rel)) {
      next.push({ kind: 'wbs', label, ref: rel })
    }
    onChange({ ...value, attachments: next })
    setWbsSelectKey((k) => k + 1)
  }

  return (
    <>
      <fieldset style={{ border: 'none', padding: 0, marginTop: '0.75rem' }}>
        <legend className="forge-support" style={{ marginBottom: '0.35rem' }}>
          Context sources
        </legend>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {(
            [
              ['pastedPrompt', 'Pasted prompt / notes'] as const,
              ['existingDocs', 'Existing docs / artifacts'] as const,
              ['repoSummary', 'Repo context summary'] as const,
              ['ticketsBacklog', 'Tickets / backlog references'] as const,
            ] as const
          ).map(([key, lab]) => (
            <label key={key} className="forge-support" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="checkbox"
                checked={value.sourceFlags[key]}
                disabled={disabled}
                onChange={() => toggleFlag(key)}
              />
              {lab}
            </label>
          ))}
        </div>
      </fieldset>

      <div style={{ marginTop: '0.75rem' }}>
        <label className="forge-support" htmlFor="bpw-ctx-rough" style={{ display: 'block' }}>
          Rough notes <span className="forge-support" style={{ opacity: 0.85 }}>(primary)</span>
        </label>
        <textarea
          id="bpw-ctx-rough"
          className="le-input"
          maxLength={CONTEXT_ROUGH_MAX}
          value={value.roughNotes}
          disabled={disabled}
          onChange={(e) => onChange({ ...value, roughNotes: e.target.value })}
          placeholder="Paste intent, constraints, or anything the blueprint should respect."
          aria-invalid={Boolean(errRough)}
          aria-describedby={errRough ? 'bpw-ctx-rough-err' : undefined}
          style={{ width: '100%', minHeight: '6rem', marginTop: '0.35rem' }}
        />
        {errRough && (
          <p id="bpw-ctx-rough-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
            {errRough}
          </p>
        )}
      </div>

      <div style={{ marginTop: '0.75rem' }}>
        <label className="forge-support" htmlFor="bpw-ctx-refs" style={{ display: 'block' }}>
          References <span className="forge-support" style={{ opacity: 0.85 }}>(paths, ticket IDs, links)</span>
        </label>
        <textarea
          id="bpw-ctx-refs"
          className="le-input"
          maxLength={CONTEXT_REFERENCE_HINTS_MAX}
          value={value.referenceHints}
          disabled={disabled}
          onChange={(e) => onChange({ ...value, referenceHints: e.target.value })}
          placeholder="e.g. JIRA-123, docs/onboarding.md"
          aria-invalid={Boolean(errRef)}
          aria-describedby={errRef ? 'bpw-ctx-refs-err' : undefined}
          style={{ width: '100%', minHeight: '3.5rem', marginTop: '0.35rem' }}
        />
        {errRef && (
          <p id="bpw-ctx-refs-err" className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
            {errRef}
          </p>
        )}
      </div>

      {wbsChoices.length > 0 && (
        <div style={{ marginTop: '0.75rem' }}>
          <label className="forge-support" htmlFor="bpw-ctx-wbs" style={{ display: 'block' }}>
            Attach workspace WBS path <span className="forge-support" style={{ opacity: 0.85 }}>(optional)</span>
          </label>
          <select
            key={wbsSelectKey}
            id="bpw-ctx-wbs"
            className="le-select"
            defaultValue=""
            disabled={disabled}
            onChange={(e) => {
              const rel = e.target.value
              onWbsPick(rel)
            }}
            style={{ marginTop: '0.35rem', minWidth: '100%', maxWidth: '100%' }}
            aria-label="Attach WBS path from workspace"
          >
            <option value="">— Select a WBS file —</option>
            {wbsChoices.map((h) => (
              <option key={h.rel} value={h.rel}>
                {h.label} — {h.rel}
              </option>
            ))}
          </select>
        </div>
      )}

      {value.attachments.length > 0 && (
        <ul className="forge-support" style={{ marginTop: '0.5rem', paddingLeft: '1.1rem' }}>
          {value.attachments.map((a, i) => (
            <li key={`${a.kind}-${a.ref ?? i}`}>
              <span className="le-mono">{a.kind}</span>: {a.label}
              {a.ref ? <span className="forge-support" style={{ opacity: 0.85 }}> — {a.ref}</span> : null}
              {!disabled && (
                <button
                  type="button"
                  className="forge-support"
                  style={{ marginLeft: '0.5rem' }}
                  onClick={() =>
                    onChange({
                      ...value,
                      attachments: value.attachments.filter((_, j) => j !== i),
                    })
                  }
                >
                  Remove
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      <div style={{ marginTop: '0.75rem' }}>
        <span className="forge-support" style={{ display: 'block', marginBottom: '0.35rem' }}>
          Preview snippets <span className="forge-support" style={{ opacity: 0.85 }}>(mock)</span>
        </span>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
          {(['repo', 'docs', 'tickets'] as const).map((k) => (
            <button
              key={k}
              type="button"
              className="le-btn"
              disabled={disabled || previewBusy !== null}
              onClick={() => void runPreview(k)}
            >
              {previewBusy === k ? '…' : `Preview ${k}`}
            </button>
          ))}
        </div>
        {preview && (
          <pre
            className="forge-support le-preview"
            style={{ marginTop: '0.5rem', whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}
          >
            {preview}
          </pre>
        )}
      </div>
    </>
  )
}
