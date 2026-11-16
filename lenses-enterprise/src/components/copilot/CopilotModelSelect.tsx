import type { CSSProperties } from 'react'
import { useEffect, useMemo, useState } from 'react'
import { apiPostJson } from '../../api/http'

export type CopilotModelSelectProps = {
  provider: string
  providers: Record<string, boolean> | null
  modelOverride: string
  onModelOverride: (v: string) => void
  /** ``main_models[provider]`` from AI Setup (GET); shown in the default option label. */
  setupDefaultModelId: string
  disabled?: boolean
  id?: string
  className?: string
  style?: CSSProperties
}

/**
 * Non-editable model picker: loads ids from ``/api/llm/provider-probe`` and keeps a native ``<select>``.
 */
export function CopilotModelSelect({
  provider,
  providers,
  modelOverride,
  onModelOverride,
  setupDefaultModelId,
  disabled,
  id,
  className,
  style,
}: CopilotModelSelectProps) {
  const [catalog, setCatalog] = useState<string[]>([])
  const [catalogState, setCatalogState] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle')

  useEffect(() => {
    if (!providers?.[provider]) {
      setCatalog([])
      setCatalogState('idle')
      return
    }
    let cancel = false
    setCatalogState('loading')
    void apiPostJson<{ ok?: boolean; models?: string[] }>('/api/llm/provider-probe', { provider, action: 'models' })
      .then((out) => {
        if (cancel) return
        if (out.ok && Array.isArray(out.models)) {
          const sorted = [...out.models]
            .map((m) => String(m).trim())
            .filter(Boolean)
            .sort((a, b) => a.localeCompare(b))
          setCatalog(sorted)
          setCatalogState('ok')
        } else {
          setCatalog([])
          setCatalogState('error')
        }
      })
      .catch(() => {
        if (cancel) return
        setCatalog([])
        setCatalogState('error')
      })
    return () => {
      cancel = true
    }
  }, [provider, providers])

  const optionIds = useMemo(() => {
    const set = new Set<string>()
    const def = setupDefaultModelId.trim()
    for (const mid of catalog) set.add(mid)
    const mo = modelOverride.trim()
    if (mo) set.add(mo)
    // First <option value=""> is "use AI Setup default". Drop `def` from the explicit list only when
    // the session override is empty or a *different* id — if session still holds the same id string
    // as the default, keep it so <select value={modelOverride}> matches an <option> (otherwise the
    // browser resets the control to the blank default row).
    if (def && mo !== def) set.delete(def)
    return Array.from(set).sort((a, b) => a.localeCompare(b))
  }, [catalog, setupDefaultModelId, modelOverride])

  const defTrim = setupDefaultModelId.trim()
  const defaultLabel = (() => {
    if (catalogState === 'loading') return 'Use AI Setup default (loading catalog…)'
    if (!defTrim) return 'Use AI Setup default'
    if (
      provider === 'openai_compatible' &&
      catalogState === 'ok' &&
      catalog.length > 0 &&
      !catalog.includes(defTrim)
    ) {
      return `Use AI Setup default (${defTrim} — not on this gateway; pick a model below)`
    }
    return `Use AI Setup default (${defTrim})`
  })()

  const selectValue = modelOverride.trim() === '' ? '' : modelOverride.trim()
  const ready = Boolean(providers?.[provider])

  return (
    <select
      id={id}
      className={className}
      style={style}
      value={selectValue}
      onChange={(e) => onModelOverride(e.target.value)}
      disabled={disabled || !ready}
      aria-busy={catalogState === 'loading'}
      aria-label="Model override"
    >
      <option value="">{defaultLabel}</option>
      {optionIds.map((mid) => (
        <option key={mid} value={mid}>
          {mid}
        </option>
      ))}
    </select>
  )
}
