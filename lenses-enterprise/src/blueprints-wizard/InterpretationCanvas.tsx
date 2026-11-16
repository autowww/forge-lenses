import type { InterpretationPayloadV1 } from './interpretationPayload'
import { FOUNDATION_BRIEF_DRAFT_KEYS } from './interpretationPayload'
import type { InterpretationFieldStatus } from './wizardDomainTypes'

function statusLabel(s: InterpretationFieldStatus): string {
  switch (s) {
    case 'explicit':
      return 'Explicit'
    case 'inferred':
      return 'Inferred'
    case 'needs_confirmation':
      return 'Needs confirmation'
    default:
      return 'Unknown'
  }
}

function SectionChip({ status, confidence }: { status: InterpretationFieldStatus; confidence?: number }) {
  return (
    <span
      className="forge-support"
      style={{
        display: 'inline-block',
        fontSize: '0.75rem',
        padding: '0.1rem 0.45rem',
        borderRadius: '4px',
        background: 'var(--le-surface-2, rgba(255,255,255,0.06))',
        marginRight: '0.35rem',
      }}
      title={confidence !== undefined ? `Confidence: ${Math.round(confidence * 100)}%` : undefined}
    >
      {statusLabel(status)}
      {confidence !== undefined ? ` · ${Math.round(confidence * 100)}%` : ''}
    </span>
  )
}

function briefKeyLabel(k: string): string {
  return k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

type Props = {
  value: InterpretationPayloadV1
  onChange: (next: InterpretationPayloadV1) => void
  disabled?: boolean
  onRunInterpret?: () => void
  interpreting?: boolean
  interpretError?: string | null
  runInterpretAvailable?: boolean
}

export function InterpretationCanvas({
  value,
  onChange,
  disabled = false,
  onRunInterpret,
  interpreting = false,
  interpretError = null,
  runInterpretAvailable = true,
}: Props) {
  const busy = disabled || interpreting

  const setWhat = (what_user_said: string) => {
    onChange({ ...value, what_user_said })
  }

  const setUnknowns = (unknowns: string[]) => {
    onChange({ ...value, unknowns })
  }

  const updateBlock = (
    list: 'inferred' | 'needs_confirmation',
    id: string,
    text: string,
  ) => {
    const arr = value[list].map((b) => (b.id === id ? { ...b, text } : b))
    onChange({ ...value, [list]: arr })
  }

  const updateFoundation = (key: (typeof FOUNDATION_BRIEF_DRAFT_KEYS)[number], text: string) => {
    onChange({
      ...value,
      foundation_brief_draft: {
        ...value.foundation_brief_draft,
        [key]: { ...value.foundation_brief_draft[key], text },
      },
    })
  }

  return (
    <div className="forge-support">
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '0.75rem',
        }}
      >
        {onRunInterpret && (
          <button
            type="button"
            className="forge-support"
            disabled={!runInterpretAvailable || busy}
            onClick={() => onRunInterpret()}
          >
            {interpreting ? 'Running interpretation…' : 'Run interpretation'}
          </button>
        )}
        {interpretError && (
          <span role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
            {interpretError}
          </span>
        )}
      </div>

      <div
        className="le-bpwizard-interpret-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(16rem, 1fr))',
          gap: '1rem',
          alignItems: 'start',
        }}
      >
        <div style={{ minWidth: 0 }}>
          <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            What you said
          </h3>
          <label className="forge-support" htmlFor="bpw-interpret-what" style={{ display: 'block' }}>
            Restatement <span aria-hidden="true">*</span>
          </label>
          <textarea
            id="bpw-interpret-what"
            className="le-input"
            value={value.what_user_said}
            disabled={busy}
            onChange={(e) => setWhat(e.target.value)}
            placeholder="Your intent and facts from earlier steps, normalized."
            style={{ width: '100%', minHeight: '8rem', marginTop: '0.35rem' }}
          />
          <h4 className="forge-support" style={{ fontSize: '0.95rem', fontWeight: 600, marginTop: '1rem' }}>
            Unknowns / missing context
          </h4>
          <ul style={{ listStyle: 'none', padding: 0, margin: '0.35rem 0 0' }}>
            {value.unknowns.map((u, i) => (
              <li key={`u-${i}`} style={{ marginBottom: '0.35rem' }}>
                <input
                  type="text"
                  className="le-input"
                  value={u}
                  disabled={busy}
                  onChange={(e) => {
                    const next = [...value.unknowns]
                    next[i] = e.target.value
                    setUnknowns(next)
                  }}
                  style={{ width: '100%' }}
                  aria-label={`Unknown ${i + 1}`}
                />
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="forge-support"
            style={{ marginTop: '0.35rem' }}
            disabled={busy}
            onClick={() => setUnknowns([...value.unknowns, ''])}
          >
            Add unknown
          </button>
        </div>

        <div style={{ minWidth: 0 }}>
          <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            What Blueprints inferred
          </h3>
          {value.inferred.length === 0 ? (
            <p className="forge-support" style={{ opacity: 0.85 }}>
              No inferred items yet. Run interpretation or add notes on prior steps.
            </p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {value.inferred.map((b) => (
                <li key={b.id} style={{ marginBottom: '0.75rem' }}>
                  <SectionChip status={b.status} confidence={b.confidence} />
                  <textarea
                    className="le-input"
                    value={b.text}
                    disabled={busy}
                    onChange={(e) => updateBlock('inferred', b.id, e.target.value)}
                    style={{ width: '100%', minHeight: '4rem', marginTop: '0.25rem' }}
                    aria-label={`Inferred ${b.id}`}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div style={{ minWidth: 0 }}>
          <h3 className="forge-support" style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            Needs confirmation
          </h3>
          {value.needs_confirmation.length === 0 ? (
            <p className="forge-support" style={{ opacity: 0.85 }}>
              Nothing flagged for confirmation.
            </p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {value.needs_confirmation.map((b) => (
                <li key={b.id} style={{ marginBottom: '0.75rem' }}>
                  <SectionChip status={b.status} confidence={b.confidence} />
                  <textarea
                    className="le-input"
                    value={b.text}
                    disabled={busy}
                    onChange={(e) => updateBlock('needs_confirmation', b.id, e.target.value)}
                    style={{ width: '100%', minHeight: '4rem', marginTop: '0.25rem' }}
                    aria-label={`Needs confirmation ${b.id}`}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <section style={{ marginTop: '1.25rem' }} aria-labelledby="bpw-fb-draft-heading">
        <h3 id="bpw-fb-draft-heading" className="forge-support" style={{ fontSize: '1rem', fontWeight: 600 }}>
          Foundation Brief draft
        </h3>
        <p className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.9 }}>
          Structured draft only — Refine Markdown is separate. Edit text below; provenance tags are read-only from the
          last interpretation run.
        </p>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(18rem, 1fr))',
            gap: '0.75rem',
            marginTop: '0.75rem',
          }}
        >
          {FOUNDATION_BRIEF_DRAFT_KEYS.map((key) => {
            const sec = value.foundation_brief_draft[key]
            return (
              <div key={key} style={{ minWidth: 0 }}>
                <div style={{ marginBottom: '0.25rem' }}>
                  <span className="forge-support" style={{ fontWeight: 600 }}>
                    {briefKeyLabel(key)}
                  </span>{' '}
                  <SectionChip status={sec.status} confidence={sec.confidence} />
                </div>
                <textarea
                  className="le-input"
                  value={sec.text}
                  disabled={busy}
                  onChange={(e) => updateFoundation(key, e.target.value)}
                  style={{ width: '100%', minHeight: '3.5rem' }}
                  aria-label={briefKeyLabel(key)}
                />
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
