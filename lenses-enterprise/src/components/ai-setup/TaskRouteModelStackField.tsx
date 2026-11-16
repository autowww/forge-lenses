import type { CSSProperties } from 'react'
import { useId, useMemo } from 'react'
import { ModelIdComboboxField } from './ModelIdComboboxField'
import { mergeModelOptionIds, suggestedModelsForTask } from './taskModelHints'
import { useLlmProviderModelCatalog } from './useLlmProviderModelCatalog'

export type TaskRouteModelStackFieldProps = {
  taskId: string
  /** Provider used for catalog probe (task override or workspace primary). */
  probeProvider: string
  providersMap: Record<string, boolean> | null
  /** ``main_models[probeProvider]`` — listed first in each dropdown. */
  mainModelHint: string
  /** Persisted priority list; only the first id is used by the server today. */
  modelStack: string[]
  onStackChange: (next: string[]) => void
  /** When the first slot is empty, Studio uses this provider + main model from Workspace defaults. */
  resolvedRouting?: { providerId: string; modelSummary: string }
  maxSlots?: number
  disabled?: boolean
  className?: string
  style?: CSSProperties
  /** ``embedded`` — tighter copy when the parent already has a section title (e.g. advanced matrix). */
  variant?: 'standalone' | 'embedded'
}

function applySlotChange(stack: string[], index: number, value: string): string[] {
  const t = value.trim()
  const out = [...stack]
  if (!t) {
    out.splice(index, 1)
    return out
  }
  if (index < out.length) {
    out[index] = t
    return out
  }
  return [...out, t]
}

/**
 * Per-task model stack: searchable model comboboxes fed by a cached ``/api/llm/provider-probe`` catalog
 * plus task-aware suggestions.
 */
export function TaskRouteModelStackField({
  taskId,
  probeProvider,
  providersMap,
  mainModelHint,
  modelStack,
  onStackChange,
  resolvedRouting,
  maxSlots = 6,
  disabled,
  className,
  style,
  variant = 'standalone',
}: TaskRouteModelStackFieldProps) {
  const pid = (probeProvider || '').trim().toLowerCase()
  const catalog = useLlmProviderModelCatalog(providersMap, pid)
  const taskHints = useMemo(() => suggestedModelsForTask(pid, taskId), [pid, taskId])
  const baseId = useId()

  const numSlots = useMemo(() => {
    if (modelStack.length === 0) return 1
    if (modelStack.length >= maxSlots) return maxSlots
    return modelStack.length + 1
  }, [modelStack.length, maxSlots])

  const blockHint =
    catalog.state === 'loading'
      ? 'Loading model catalog…'
      : catalog.state === 'error' && catalog.models.length === 0
        ? 'Catalog unavailable — type a model id or pick a suggestion when listed.'
        : null

  return (
    <div className={className} style={style}>
      {variant === 'standalone' && blockHint ? (
        <p className="forge-support" style={{ fontSize: '0.72rem', margin: '0 0 0.35rem', opacity: 0.78 }}>
          {blockHint}
        </p>
      ) : null}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        {Array.from({ length: numSlots }, (_, i) => {
          const val = modelStack[i] ?? ''
          const optionIds = mergeModelOptionIds(mainModelHint, taskHints, catalog.models, [...modelStack, val])
          const slotHint = variant === 'embedded' && i === 0 ? blockHint : null
          return (
            <ModelIdComboboxField
              key={`slot-${i}`}
              inputId={`${baseId}-slot-${i}-in`}
              listId={`${baseId}-slot-${i}-list`}
              label={
                i === 0 ? (
                  <span style={{ display: 'block', marginBottom: '0.15rem', opacity: 0.9 }}>
                    {variant === 'embedded' ? 'Primary model' : 'Model (optional)'}
                    {resolvedRouting ? (
                      <span
                        className="forge-support"
                        style={{
                          display: 'block',
                          fontSize: '0.72rem',
                          fontWeight: 400,
                          marginTop: '0.2rem',
                          opacity: 0.82,
                          lineHeight: 1.35,
                        }}
                      >
                        If empty: primary source{' '}
                        <span className="le-mono">{resolvedRouting.providerId}</span>
                        {' · '}
                        {resolvedRouting.modelSummary === 'server default' ? (
                          <span style={{ opacity: 0.9 }}>server default model</span>
                        ) : (
                          <>
                            main model <span className="le-mono">{resolvedRouting.modelSummary}</span>
                          </>
                        )}
                      </span>
                    ) : null}
                  </span>
                ) : (
                  <span style={{ display: 'block', marginBottom: '0.15rem', opacity: 0.85 }}>
                    {variant === 'embedded' ? (
                      <>
                        Alternate <span className="le-mono" style={{ fontSize: '0.7rem', opacity: 0.75 }}>#{i + 1}</span>{' '}
                        (stored only)
                      </>
                    ) : (
                      <>
                        Then try (stored only){' '}
                        <span className="le-mono" style={{ fontSize: '0.7rem', opacity: 0.75 }}>
                          #{i + 1}
                        </span>
                      </>
                    )}
                  </span>
                )
              }
              hint={slotHint}
              value={val}
              onChange={(v) => onStackChange(applySlotChange(modelStack, i, v))}
              optionIds={optionIds}
              disabled={disabled}
              catalogBusy={catalog.state === 'loading' && i === 0}
            />
          )
        })}
      </div>
      {variant === 'standalone' ? (
        <p
          className="forge-support"
          style={{ fontSize: '0.68rem', margin: '0.35rem 0 0', opacity: 0.72, lineHeight: 1.35 }}
        >
          {resolvedRouting ? (
            <>
              Leave empty for <strong>no override</strong> — same as Workspace defaults:{' '}
              <span className="le-mono">{resolvedRouting.providerId}</span>
              {' + '}
              {resolvedRouting.modelSummary === 'server default' ? (
                <span>server default model.</span>
              ) : (
                <>
                  main model <span className="le-mono">{resolvedRouting.modelSummary}</span>.
                </>
              )}{' '}
              Suggestions refresh from the catalog while that provider is connected.
            </>
          ) : (
            <>
              Leave empty for <strong>no override</strong> — routing uses the primary main model. Suggestions refresh
              from the server catalog while this provider is connected.
            </>
          )}
        </p>
      ) : null}
    </div>
  )
}
