import type { CompareModeId } from '../context/ShellChromeContext'
import type { OverviewChartPayload } from '../api/chartOverview'

export type TrendTier = 'green' | 'amber' | 'red' | 'unknown'

export function tierToClass(tier: string | undefined): string {
  if (tier === 'green') return 'le-trend--green'
  if (tier === 'amber') return 'le-trend--amber'
  if (tier === 'red') return 'le-trend--red'
  return 'le-trend--unknown'
}

/** Numeric values for SVG sparkline (0..1 y). Min–max scaling so variation uses the full height;
 * identical values map to midline (0.5) instead of the top edge, which looked like a broken chart. */
export function normalizeSparklineValues(raw: number[]): number[] {
  if (raw.length === 0) return []
  const vals = raw.map((x) => Number(x))
  const minV = Math.min(...vals)
  const maxV = Math.max(...vals)
  const range = maxV - minV
  if (range < 1e-12) {
    return vals.map(() => 0.5)
  }
  return vals.map((x) => (x - minV) / range)
}

export function formatDelta(
  current: number,
  previous: number,
  compareMode: CompareModeId,
): { text: string; label: string } | null {
  if (compareMode !== 'previous_period') return null
  const d = current - previous
  if (d === 0) return { text: '±0', label: 'No change vs previous period' }
  if (d > 0) return { text: `+${d.toLocaleString()}`, label: `Up ${d.toLocaleString()} vs previous period` }
  return { text: `−${Math.abs(d).toLocaleString()}`, label: `Down ${Math.abs(d).toLocaleString()} vs previous period` }
}

/** Normalize keys so lookups match workspace names (trim + case-insensitive). */
export function linesPrevByRepo(payload: OverviewChartPayload | null): Map<string, number> {
  const m = new Map<string, number>()
  const rows = payload?.kpi_trends?.lines_added?.prev_by_repo
  if (!rows || typeof rows !== 'object') return m
  for (const [k, v] of Object.entries(rows)) {
    if (typeof v === 'number' && !Number.isNaN(v)) m.set(k.trim().toLowerCase(), v)
  }
  return m
}

export function lookupPrevLinesAdded(
  payload: OverviewChartPayload | null,
  repoName: string,
): number | undefined {
  const m = linesPrevByRepo(payload)
  return m.get(repoName.trim().toLowerCase())
}

