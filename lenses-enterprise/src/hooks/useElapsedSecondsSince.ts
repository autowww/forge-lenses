import { useEffect, useState } from 'react'

/** Wall-clock seconds since `iso` (UTC), ticking every second while mounted. */
export function useElapsedSecondsSince(iso: string | undefined | null): number {
  const [sec, setSec] = useState(0)
  useEffect(() => {
    if (!iso) {
      setSec(0)
      return
    }
    const start = Date.parse(String(iso))
    if (Number.isNaN(start)) {
      setSec(0)
      return
    }
    const tick = () => setSec(Math.max(0, Math.floor((Date.now() - start) / 1000)))
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [iso])
  return sec
}

export function formatElapsedWallClock(totalSec: number): string {
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  if (m >= 60) {
    const h = Math.floor(m / 60)
    const mm = m % 60
    return `${h}h ${mm}m ${s}s`
  }
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}
