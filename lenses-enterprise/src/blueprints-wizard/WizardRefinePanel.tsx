import type { AssumptionLedgerEntryJson } from './wizardDomainTypes'
import { CONTEXT_SOURCES, INTERPRETATION_FIELD_STATUSES, type InterpretationFieldStatus } from './wizardDomainTypes'

const REFINE_PROVIDER_IDS = [
  'anthropic',
  'openai',
  'gemini',
  'ollama',
  'openai_compatible',
] as const

type Props = {
  /** Prefer `wizard_domain.foundation_brief.markdown`; falls back to legacy string for display. */
  domainFoundationMarkdown: string
  legacyFoundationBrief: string
  foundationBriefFieldStatuses: Record<string, InterpretationFieldStatus>
  onFoundationBriefFieldStatusesChange: (next: Record<string, InterpretationFieldStatus>) => void
  assumptionLedger: AssumptionLedgerEntryJson[]
  onAppendAssumption: () => void
  onRemoveAssumption: (id: string) => void
  onChangeAssumptionText: (id: string, text: string) => void
  onChangeAssumptionSource: (id: string, source: string | undefined) => void
  refineProvider: string
  refineModel: string
  refineChain: boolean
  refining: boolean
  refineError: string | null
  disabled: boolean
  onRefineProviderChange: (v: string) => void
  onRefineModelChange: (v: string) => void
  onRefineChainChange: (v: boolean) => void
  onRefine: () => void
  /** True when `interpretation.foundation_brief_draft` has at least one non-empty section. */
  interpretationDraftReady: boolean
  /** Fills `wizard_domain.foundation_brief.markdown` from the structured draft (no LLM). */
  onSyncDraftToMarkdown: () => void
  syncingDraft: boolean
  syncDraftError: string | null
}

export function WizardRefinePanel({
  domainFoundationMarkdown,
  legacyFoundationBrief,
  foundationBriefFieldStatuses,
  onFoundationBriefFieldStatusesChange,
  assumptionLedger,
  onAppendAssumption,
  onRemoveAssumption,
  onChangeAssumptionText,
  onChangeAssumptionSource,
  refineProvider,
  refineModel,
  refineChain,
  refining,
  refineError,
  disabled,
  onRefineProviderChange,
  onRefineModelChange,
  onRefineChainChange,
  onRefine,
  interpretationDraftReady,
  onSyncDraftToMarkdown,
  syncingDraft,
  syncDraftError,
}: Props) {
  const displayBrief =
    domainFoundationMarkdown.trim() || legacyFoundationBrief.trim() || ''

  const statusRows = Object.entries(foundationBriefFieldStatuses)

  const addFieldStatusRow = () => {
    const base = `field_${Date.now().toString(36)}`
    let key = base
    let n = 0
    while (key in foundationBriefFieldStatuses) {
      n += 1
      key = `${base}_${n}`
    }
    onFoundationBriefFieldStatusesChange({
      ...foundationBriefFieldStatuses,
      [key]: 'unknown',
    })
  }

  const removeFieldStatus = (key: string) => {
    const next = { ...foundationBriefFieldStatuses }
    delete next[key]
    onFoundationBriefFieldStatusesChange(next)
  }

  const renameFieldStatusKey = (oldKey: string, newKey: string) => {
    const t = newKey.trim()
    if (!t || t === oldKey) return
    if (t in foundationBriefFieldStatuses && t !== oldKey) return
    const next = { ...foundationBriefFieldStatuses }
    const v = next[oldKey]
    delete next[oldKey]
    next[t] = v
    onFoundationBriefFieldStatusesChange(next)
  }

  const setFieldStatusValue = (key: string, status: InterpretationFieldStatus) => {
    onFoundationBriefFieldStatusesChange({
      ...foundationBriefFieldStatuses,
      [key]: status,
    })
  }

  return (
    <details className="le-bpwizard-refine">
      <summary className="forge-support le-bpwizard-refine__summary">
        Foundation Brief (LLM) — experimental
      </summary>
      <div className="le-bpwizard-refine__body forge-support">
        <p className="forge-support" style={{ marginBottom: '0.5rem', fontSize: '0.9rem' }}>
          Uses the same LLM path as Chat (loopback / allow-actions only). Saves the current step notes to
          the session, then drafts Markdown into{' '}
          <code className="le-mono">payload.foundation_brief</code> and{' '}
          <code className="le-mono">payload.wizard_domain.foundation_brief.markdown</code>. Assumptions and
          field statuses persist with <code className="le-mono">PUT</code> session.
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
          <label className="forge-support" htmlFor="bpw-refine-provider" style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            Provider
            <select
              id="bpw-refine-provider"
              className="le-select"
              value={refineProvider}
              disabled={disabled || refining}
              onChange={(e) => onRefineProviderChange(e.target.value)}
              aria-label="Refine LLM provider"
            >
              {REFINE_PROVIDER_IDS.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          </label>
          <label className="forge-support" htmlFor="bpw-refine-model" style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            Model (optional)
            <input
              id="bpw-refine-model"
              className="le-input"
              type="text"
              value={refineModel}
              disabled={disabled || refining}
              onChange={(e) => onRefineModelChange(e.target.value)}
              placeholder="optional"
              style={{ minWidth: '10rem' }}
            />
          </label>
          <label className="forge-support" style={{ display: 'flex', gap: '0.35rem', alignItems: 'center' }}>
            <input
              type="checkbox"
              checked={refineChain}
              disabled={disabled || refining}
              onChange={(e) => onRefineChainChange(e.target.checked)}
            />
            Refine chain
          </label>
          <button
            type="button"
            className="le-btn le-btn--primary"
            disabled={disabled || refining}
            onClick={() => onRefine()}
          >
            {refining ? 'Refining…' : 'Refine to Foundation Brief'}
          </button>
          <button
            type="button"
            className="le-btn"
            disabled={disabled || refining || syncingDraft || !interpretationDraftReady}
            onClick={() => onSyncDraftToMarkdown()}
            title={
              interpretationDraftReady
                ? 'Replace Markdown with headings generated from the Understanding step structured draft'
                : 'Fill at least one Foundation Brief draft field on Understanding first'
            }
          >
            {syncingDraft ? 'Syncing draft…' : 'Sync draft to Markdown'}
          </button>
        </div>
        <p className="forge-support" style={{ marginTop: '0.5rem', fontSize: '0.85rem', opacity: 0.9 }}>
          <strong>Merge rules:</strong> Refine calls the LLM and overwrites Markdown. Sync draft renders the structured
          interpretation draft into Markdown and overwrites the current Markdown (a two-column preview appears when
          Markdown is already present). Legacy sessions may still have <code className="le-mono">payload.foundation_brief</code> as a
          string; sync updates that field when present. After sync, field statuses record `fb_*` per section and mark
          that the blob is no longer a pure LLM Refine output.
        </p>
        {syncDraftError && (
          <p className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
            {syncDraftError}
          </p>
        )}
        {refineError && (
          <div className="forge-support" style={{ marginTop: '0.5rem' }}>
            <p role="alert">{refineError}</p>
            <button
              type="button"
              className="le-btn le-btn--primary"
              style={{ marginTop: '0.35rem' }}
              disabled={disabled || refining}
              onClick={() => onRefine()}
            >
              Retry refine
            </button>
          </div>
        )}

        <section style={{ marginTop: '0.75rem' }} aria-labelledby="bpw-domain-brief-heading">
          <h3 id="bpw-domain-brief-heading" className="forge-support" style={{ fontSize: '0.95rem', fontWeight: 600 }}>
            Foundation Brief <span style={{ fontWeight: 400, opacity: 0.9 }}>(wizard_domain)</span>
          </h3>
          {displayBrief ? (
            <pre
              className="le-preview"
              style={{
                marginTop: '0.35rem',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                maxHeight: '12rem',
                overflow: 'auto',
              }}
            >
              {displayBrief}
            </pre>
          ) : (
            <p className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.85 }}>
              No brief in domain yet — add step notes and click Refine.
            </p>
          )}
        </section>

        <section style={{ marginTop: '0.65rem' }} aria-labelledby="bpw-field-status-heading">
          <h3 id="bpw-field-status-heading" className="forge-support" style={{ fontSize: '0.95rem', fontWeight: 600 }}>
            Interpretation field status <span style={{ fontWeight: 400, opacity: 0.9 }}>(optional)</span>
          </h3>
          <p className="forge-support" style={{ marginTop: '0.25rem', fontSize: '0.88rem', opacity: 0.9 }}>
            Mark confidence per field key (e.g. problem_outcome). Refine may set{' '}
            <code className="le-mono">llm_foundation_brief</code> to <code className="le-mono">inferred</code>.
          </p>
          {statusRows.length > 0 ? (
            <ul className="forge-support" style={{ marginTop: '0.5rem', paddingLeft: 0, listStyle: 'none' }}>
              {statusRows.map(([key, st]) => (
                <li
                  key={key}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr minmax(8rem, auto) auto',
                    gap: '0.35rem',
                    alignItems: 'center',
                    marginBottom: '0.4rem',
                  }}
                >
                  <input
                    key={key}
                    className="le-input"
                    type="text"
                    defaultValue={key}
                    disabled={disabled || refining}
                    aria-label="Field key"
                    onBlur={(e) => renameFieldStatusKey(key, e.target.value)}
                    style={{ minWidth: 0 }}
                  />
                  <select
                    className="le-select"
                    value={st}
                    disabled={disabled || refining}
                    aria-label={`Status for ${key}`}
                    onChange={(e) => setFieldStatusValue(key, e.target.value as InterpretationFieldStatus)}
                  >
                    {INTERPRETATION_FIELD_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="forge-support"
                    disabled={disabled || refining}
                    onClick={() => removeFieldStatus(key)}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.85 }}>
              No field keys yet.
            </p>
          )}
          <button type="button" className="le-btn" style={{ marginTop: '0.35rem' }} disabled={disabled || refining} onClick={addFieldStatusRow}>
            Add field key
          </button>
        </section>

        <section style={{ marginTop: '0.65rem' }} aria-labelledby="bpw-assumption-heading">
          <h3 id="bpw-assumption-heading" className="forge-support" style={{ fontSize: '0.95rem', fontWeight: 600 }}>
            Assumption ledger
          </h3>
          {assumptionLedger.length > 0 ? (
            <ul className="forge-support" style={{ marginTop: '0.5rem', paddingLeft: 0, listStyle: 'none' }}>
              {assumptionLedger.map((e) => (
                <li
                  key={e.id}
                  style={{
                    border: '1px solid rgba(128,128,128,0.25)',
                    borderRadius: '4px',
                    padding: '0.5rem',
                    marginBottom: '0.5rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.5rem' }}>
                    <span className="le-mono" style={{ fontSize: '0.8rem', opacity: 0.85 }}>
                      {e.id}
                    </span>
                    <button type="button" className="forge-support" disabled={disabled || refining} onClick={() => onRemoveAssumption(e.id)}>
                      Remove
                    </button>
                  </div>
                  <label className="forge-support" style={{ display: 'block', marginTop: '0.35rem' }} htmlFor={`bpw-asmp-text-${e.id}`}>
                    Text
                  </label>
                  <textarea
                    id={`bpw-asmp-text-${e.id}`}
                    className="le-input"
                    value={e.text}
                    disabled={disabled || refining}
                    onChange={(ev) => onChangeAssumptionText(e.id, ev.target.value)}
                    rows={3}
                    style={{ width: '100%', marginTop: '0.25rem' }}
                  />
                  <label className="forge-support" style={{ display: 'block', marginTop: '0.35rem' }} htmlFor={`bpw-asmp-src-${e.id}`}>
                    Source (optional)
                  </label>
                  <select
                    id={`bpw-asmp-src-${e.id}`}
                    className="le-select"
                    value={e.source ?? ''}
                    disabled={disabled || refining}
                    onChange={(ev) => {
                      const v = ev.target.value
                      onChangeAssumptionSource(e.id, v === '' ? undefined : v)
                    }}
                  >
                    <option value="">—</option>
                    {CONTEXT_SOURCES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </li>
              ))}
            </ul>
          ) : (
            <p className="forge-support" style={{ marginTop: '0.35rem', opacity: 0.85 }}>
              No assumptions yet — add a row below.
            </p>
          )}
          <button type="button" className="le-btn" style={{ marginTop: '0.35rem' }} disabled={disabled || refining} onClick={onAppendAssumption}>
            Add assumption
          </button>
        </section>
      </div>
    </details>
  )
}
