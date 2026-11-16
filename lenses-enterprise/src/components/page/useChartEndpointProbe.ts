import { useEffect, useState } from 'react'

export type ChartEndpointPhase = 'loading' | 'ok' | 'error'

/**
 * Lightweight GET probe so we can show recovery UI before/for chart mounts that rely on `forge-data-charts`.
 */
export function useChartEndpointProbe(dataUrl: string): ChartEndpointPhase {
  const [phase, setPhase] = useState<ChartEndpointPhase>('loading')

  useEffect(() => {
    let cancelled = false
    // Reset when URL changes; fetch below is the async subscription.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- sync phase reset before network
    setPhase('loading')
    void fetch(dataUrl, { credentials: 'same-origin' })
      .then((r) => {
        if (!cancelled) setPhase(r.ok ? 'ok' : 'error')
      })
      .catch(() => {
        if (!cancelled) setPhase('error')
      })
    return () => {
      cancelled = true
    }
  }, [dataUrl])

  return phase
}
