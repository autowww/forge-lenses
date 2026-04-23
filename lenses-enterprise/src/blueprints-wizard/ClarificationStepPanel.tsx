import type { ClarificationFieldErrors, ClarificationPayloadV1 } from './clarificationStep'
import { CLARIFICATION_DECISIONS_MAX, CLARIFICATION_QUESTIONS_MAX } from './clarificationStep'
import type { ClarificationResponse } from './clarificationTypes'
import type { AssumptionLedgerEntryJson } from './wizardDomainTypes'
import { isUnresolvedAssumption } from './clarificationMerge'

function setResponse(
  c: ClarificationPayloadV1,
  questionId: string,
  patch: ClarificationResponse,
): ClarificationPayloadV1 {
  return {
    ...c,
    responses: { ...c.responses, [questionId]: patch },
  }
}

type Props = {
  clarification: ClarificationPayloadV1
  onClarificationChange: (c: ClarificationPayloadV1) => void
  clarificationFieldErrors?: ClarificationFieldErrors
  showClarificationErrors?: boolean
  assumptionLedger: AssumptionLedgerEntryJson[]
  onRefreshQuestions: () => void
  onClarifyLlmSuggest?: () => void
  /** When false, LLM suggest is disabled (e.g. no server session). */
  clarifySuggestAvailable?: boolean
  clarifyLlmBusy?: boolean
  clarifyLlmError?: string | null
  disabled?: boolean
}

export function ClarificationStepPanel({
  clarification,
  onClarificationChange,
  clarificationFieldErrors = {},
  showClarificationErrors = false,
  assumptionLedger,
  onRefreshQuestions,
  onClarifyLlmSuggest,
  clarifySuggestAvailable = true,
  clarifyLlmBusy = false,
  clarifyLlmError = null,
  disabled = false,
}: Props) {
  const structured = clarification.questions.length > 0
  const busy = disabled || clarifyLlmBusy
  const llmButtonDisabled = busy || !clarifySuggestAvailable
  const errR = showClarificationErrors ? clarificationFieldErrors.responses : undefined
  const errQ = showClarificationErrors ? clarificationFieldErrors.openQuestions : undefined
  const errD = showClarificationErrors ? clarificationFieldErrors.decisionsNeeded : undefined

  const unresolved = assumptionLedger.filter(isUnresolvedAssumption)

  return (
    <div className="forge-support">
      <p className="forge-support" style={{ marginTop: '0.5rem' }}>
        Answer the highest-value questions first. Skips record the default assumption until you change them.
      </p>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: '0.75rem',
          marginBottom: '0.75rem',
        }}
      >
        <button type="button" className="forge-support" disabled={busy} onClick={onRefreshQuestions}>
          Refresh questions
        </button>
        {onClarifyLlmSuggest && (
          <button
            type="button"
            className="forge-support"
            disabled={llmButtonDisabled}
            onClick={() => onClarifyLlmSuggest()}
          >
            {clarifyLlmBusy ? 'Suggesting clarification…' : 'Suggest more (LLM)'}
          </button>
        )}
        {clarifyLlmError && (
          <span role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
            {clarifyLlmError}
          </span>
        )}
      </div>

      {structured ? (
        <div style={{ marginTop: '1rem' }}>
          {clarification.questions.map((q) => {
            const r = clarification.responses[q.id]
            return (
              <div
                key={q.id}
                className="le-card"
                style={{
                  marginBottom: '1rem',
                  padding: '0.75rem 1rem',
                }}
              >
                <p className="forge-support" style={{ fontWeight: 600, marginBottom: '0.35rem' }}>
                  {q.text}
                </p>
                <p className="forge-support" style={{ fontSize: '0.9rem', opacity: 0.9, marginBottom: '0.35rem' }}>
                  <strong>Why it matters:</strong> {q.why_it_matters}
                </p>
                <p className="forge-support" style={{ fontSize: '0.85rem', opacity: 0.85, marginBottom: '0.5rem' }}>
                  <strong>If skipped:</strong> {q.default_assumption_if_skipped}
                </p>
                <p className="forge-support" style={{ fontSize: '0.8rem', opacity: 0.75, marginBottom: '0.5rem' }}>
                  Answer type: {q.answer_type.replace(/_/g, ' ')}
                </p>

                {q.answer_type === 'yes_no' && (
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                    <button
                      type="button"
                      className="le-btn le-btn--primary"
                      disabled={busy}
                      onClick={() =>
                        onClarificationChange(setResponse(clarification, q.id, { kind: 'answered', value: 'yes' }))
                      }
                    >
                      Yes
                    </button>
                    <button
                      type="button"
                      className="le-btn le-btn--primary"
                      disabled={busy}
                      onClick={() =>
                        onClarificationChange(setResponse(clarification, q.id, { kind: 'answered', value: 'no' }))
                      }
                    >
                      No
                    </button>
                  </div>
                )}

                {(q.answer_type === 'short_text' || q.answer_type === 'long_text') && (
                  <textarea
                    className="le-input"
                    disabled={busy}
                    value={r?.kind === 'answered' ? (r.value ?? '') : ''}
                    onChange={(e) =>
                      onClarificationChange(
                        setResponse(clarification, q.id, { kind: 'answered', value: e.target.value }),
                      )
                    }
                    placeholder="Your answer"
                    style={{ width: '100%', minHeight: q.answer_type === 'long_text' ? '5rem' : '2.5rem', marginBottom: '0.5rem' }}
                  />
                )}

                {q.answer_type === 'single_choice' && q.choice_options && q.choice_options.length > 0 && (
                  <div style={{ marginBottom: '0.5rem' }}>
                    {q.choice_options.map((opt) => (
                      <label key={opt.key} className="forge-support" style={{ display: 'block', marginBottom: '0.25rem' }}>
                        <input
                          type="radio"
                          name={`clarify-${q.id}`}
                          disabled={busy}
                          checked={r?.kind === 'answered' && r.choice_key === opt.key}
                          onChange={() =>
                            onClarificationChange(
                              setResponse(clarification, q.id, { kind: 'answered', choice_key: opt.key, value: opt.label }),
                            )
                          }
                        />{' '}
                        {opt.label}
                      </label>
                    ))}
                  </div>
                )}

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <ActionBtn
                    label="Skip (use default)"
                    disabled={busy}
                    active={r?.kind === 'skipped'}
                    onClick={() => onClarificationChange(setResponse(clarification, q.id, { kind: 'skipped' }))}
                  />
                  <ActionBtn
                    label="Mark unknown"
                    disabled={busy}
                    active={r?.kind === 'unknown'}
                    onClick={() => onClarificationChange(setResponse(clarification, q.id, { kind: 'unknown' }))}
                  />
                  <ActionBtn
                    label="Accept system assumption"
                    disabled={busy}
                    active={r?.kind === 'accepted_default'}
                    onClick={() => onClarificationChange(setResponse(clarification, q.id, { kind: 'accepted_default' }))}
                  />
                </div>
                {r && (
                  <p className="forge-support" style={{ marginTop: '0.5rem', fontSize: '0.85rem', opacity: 0.85 }}>
                    Status: <strong>{r.kind.replace(/_/g, ' ')}</strong>
                  </p>
                )}
              </div>
            )
          })}
          {errR && (
            <p className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
              {errR}
            </p>
          )}
        </div>
      ) : (
        <div style={{ marginTop: '0.75rem' }}>
          <p className="forge-support" style={{ fontSize: '0.9rem' }}>
            No structured question set yet — use Refresh, or fill legacy open questions below.
          </p>
          <div style={{ marginTop: '0.75rem' }}>
            <label className="forge-support" htmlFor="bpw-clarify-q" style={{ display: 'block' }}>
              Open questions <span aria-hidden="true">*</span>
            </label>
            <textarea
              id="bpw-clarify-q"
              className="le-input"
              maxLength={CLARIFICATION_QUESTIONS_MAX}
              value={clarification.openQuestions}
              disabled={busy}
              onChange={(e) => onClarificationChange({ ...clarification, openQuestions: e.target.value })}
              aria-invalid={Boolean(errQ)}
              style={{ width: '100%', minHeight: '6rem', marginTop: '0.35rem' }}
            />
            {errQ && (
              <p className="forge-support" role="alert" style={{ marginTop: '0.35rem', color: 'var(--le-danger, #f87171)' }}>
                {errQ}
              </p>
            )}
          </div>
          <div style={{ marginTop: '0.75rem' }}>
            <label className="forge-support" htmlFor="bpw-clarify-d" style={{ display: 'block' }}>
              Decisions needed <span style={{ opacity: 0.85 }}>(optional)</span>
            </label>
            <textarea
              id="bpw-clarify-d"
              className="le-input"
              maxLength={CLARIFICATION_DECISIONS_MAX}
              value={clarification.decisionsNeeded ?? ''}
              disabled={busy}
              onChange={(e) => onClarificationChange({ ...clarification, decisionsNeeded: e.target.value })}
              style={{ width: '100%', minHeight: '3.5rem', marginTop: '0.35rem' }}
            />
            {errD && (
              <p className="forge-support" role="alert" style={{ color: 'var(--le-danger, #f87171)' }}>
                {errD}
              </p>
            )}
          </div>
        </div>
      )}

      <details style={{ marginTop: '1.25rem' }}>
        <summary className="forge-support" style={{ cursor: 'pointer', fontWeight: 600 }}>
          Assumption ledger ({unresolved.length} unresolved)
        </summary>
        <ul className="forge-support" style={{ marginTop: '0.5rem', paddingLeft: '1.25rem' }}>
          {assumptionLedger.length === 0 ? (
            <li>No assumptions recorded yet.</li>
          ) : (
            assumptionLedger.map((e) => (
              <li
                key={e.id}
                style={{
                  marginBottom: '0.35rem',
                  opacity: isUnresolvedAssumption(e) ? 1 : 0.85,
                }}
              >
                <code className="le-mono" style={{ fontSize: '0.75rem' }}>
                  {e.status ?? 'open'}
                </code>{' '}
                {e.text.slice(0, 500)}
                {e.text.length > 500 ? '…' : ''}
              </li>
            ))
          )}
        </ul>
      </details>
    </div>
  )
}

function ActionBtn({
  label,
  onClick,
  disabled,
  active,
}: {
  label: string
  onClick: () => void
  disabled?: boolean
  active?: boolean
}) {
  return (
    <button
      type="button"
      className={active ? 'le-btn le-btn--primary' : 'le-btn'}
      disabled={disabled}
      onClick={onClick}
    >
      {label}
    </button>
  )
}
