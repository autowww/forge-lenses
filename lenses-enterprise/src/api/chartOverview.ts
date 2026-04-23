import { apiGetJson } from './http'
import type { TimeHorizonId } from '../context/ShellChromeContext'

/** Per-repo lines trend (seven period totals, same order as workspace `period_totals`). */
export type PerRepoLinesEntry = {
  period_totals?: number[]
  median_prior_6?: number | null
  tier?: string
}

/** Git- or snapshot-derived trend block from overview API. */
export type KpiTrendBlock = {
  current_total?: number
  previous_total?: number
  current?: number
  period_totals?: number[]
  median_prior_6?: number | null
  tier?: string
  cumulative_daily?: { day?: string; cumulative?: number }[]
  prev_by_repo?: Record<string, number>
  /** Trimmed repo name keys; use trim + lowercase for lookups (see `linesAddedByRepo`). */
  per_repo_lines?: Record<string, PerRepoLinesEntry>
  history_entries?: number
}

export type SnapshotKpiBlock = {
  current?: number | null
  previous_total?: number | null
  period_totals?: number[]
  median_prior_6?: number | null
  tier?: string
  history_entries?: number
}

/** Subset of `GET /api/chart-data/overview` used by Studio KPI strip and Home command center. */
export type OverviewChartPayload = {
  version?: number
  scope?: string
  horizon?: string
  window_days?: number
  kpi_trends?: {
    commits?: KpiTrendBlock
    lines_added?: KpiTrendBlock
    snapshots?: {
      git_repos?: SnapshotKpiBlock
      sites?: SnapshotKpiBlock
      plan_artifacts?: SnapshotKpiBlock
      standards_avg?: SnapshotKpiBlock & { current?: number | null }
    }
  }
  charts?: {
    commit_daily?: {
      series?: { day?: string; count?: number }[]
    }
    loc_added_horizontal?: {
      rows?: { name?: string; value?: number }[]
    }
    /** Top repos by approximate LoC (subset). */
    loc_total_bars?: {
      rows?: { name?: string; value?: number }[]
    }
    /** Full per-repo approximate LoC (same source as donut). */
    loc_share_donut?: {
      rows?: { name?: string; value?: number }[]
      top_n?: number
    }
    compliance_bars?: {
      rows?: (string | number)[][]
    }
  }
}

/** How many recent periods to show on KPI sparklines (each point = one period). */
export const SPARKLINE_PERIOD_POINTS = 5

/** Rolling git window length for each shell time horizon (matches server `horizon_query_days`). */
export function horizonToWindowDays(h: TimeHorizonId): number {
  if (h === 'day') return 1
  if (h === 'month') return 30
  if (h === 'quarter') return 90
  return 7
}

/** Human label for one period length (sparkline x-axis). */
export function horizonPeriodUnitPhrase(h: TimeHorizonId): string {
  if (h === 'day') return 'calendar day'
  if (h === 'week') return 'week'
  if (h === 'month') return '30-day window'
  if (h === 'quarter') return '90-day window'
  return 'period'
}

/**
 * One-line explanation of what each KPI sparkline point aggregates (matches server
 * `horizon_query_days` / `period_totals_seven`). Shown under the executive strip
 * so “week” is not mistaken for daily ticks.
 */
export function kpiSparklineBucketExplanation(h: TimeHorizonId): string {
  if (h === 'day') {
    return 'Each sparkline point is one UTC calendar day (commits by author date).'
  }
  if (h === 'week') {
    return 'Each sparkline point is one full week (7 consecutive UTC days), not a single day.'
  }
  if (h === 'month') {
    return 'Each sparkline point is one 30-day window.'
  }
  if (h === 'quarter') {
    return 'Each sparkline point is one 90-day window.'
  }
  return 'Each sparkline point is one period of the selected length.'
}

export function horizonPeriodPhrase(h: TimeHorizonId): string {
  if (h === 'day') return 'last 24 hours'
  if (h === 'month') return 'last 30 days'
  if (h === 'quarter') return 'last 90 days'
  return 'last 7 days'
}

export function whatChangedSectionTitle(h: TimeHorizonId): string {
  if (h === 'day') return 'What changed today'
  if (h === 'month') return 'What changed this month'
  if (h === 'quarter') return 'What changed this quarter'
  return 'What changed this week'
}

export function commitsKpiLabel(h: TimeHorizonId): string {
  if (h === 'day') return 'Commits (24h)'
  if (h === 'month') return 'Commits (30 days)'
  if (h === 'quarter') return 'Commits (90 days)'
  return 'Commits (7 days)'
}

/** Workspace lines added (git numstat) — matches overview `kpi_trends.lines_added` window. */
export function linesAddedKpiLabel(h: TimeHorizonId): string {
  if (h === 'day') return 'LoC added (24h)'
  if (h === 'month') return 'LoC added (30d)'
  if (h === 'quarter') return 'LoC added (90d)'
  return 'LoC added (7d)'
}

/**
 * Approximate workspace LoC: sum of per-repo tracked line estimates from the overview bundle
 * (`loc_share_donut.rows` when present, else `loc_total_bars.rows`, which may be top-N only).
 */
export function workspaceLocTotal(payload: OverviewChartPayload | null): number | null {
  const donut = payload?.charts?.loc_share_donut?.rows
  if (Array.isArray(donut) && donut.length > 0) {
    let sum = 0
    for (const row of donut) {
      const v = row?.value
      if (typeof v === 'number' && !Number.isNaN(v)) sum += v
    }
    return sum
  }
  const bars = payload?.charts?.loc_total_bars?.rows
  if (!Array.isArray(bars) || bars.length === 0) return null
  let sum = 0
  for (const row of bars) {
    const v = row?.value
    if (typeof v === 'number' && !Number.isNaN(v)) sum += v
  }
  return sum
}

/**
 * Values for period sparklines: last N periods from API `period_totals` (oldest→newest within slice;
 * rightmost = current period). Duplicates a single point so the line can render.
 */
export function sparklinePeriodTotals(
  totals: number[] | undefined,
  maxPoints: number = SPARKLINE_PERIOD_POINTS,
): number[] {
  if (!totals?.length) return []
  const take = Math.min(maxPoints, totals.length)
  const slice = totals.slice(-take)
  if (slice.length === 1) return [slice[0]!, slice[0]!]
  return slice
}

/** Explains x-axis: one point per period; right = current (sparse when only two points). */
export function sparklinePeriodHint(timeHorizon: TimeHorizonId, values: number[]): string {
  const bucket = kpiSparklineBucketExplanation(timeHorizon)
  const unit = horizonPeriodUnitPhrase(timeHorizon)
  const n = values.length
  if (n < 2) {
    return `${bucket} Need at least two periods to draw a trend.`
  }
  const right = 'Rightmost = current period.'
  if (n === 2) {
    return `${bucket} 2 points · 1 ${unit} each · ${right} Sparse history.`
  }
  return `${bucket} Last ${n} periods · 1 ${unit} each · ${right}`
}

export function getOverviewChartPayload(
  horizon: TimeHorizonId = 'week',
): Promise<OverviewChartPayload> {
  const q =
    horizon === 'week' ? '' : `?horizon=${encodeURIComponent(horizon)}`
  return apiGetJson<OverviewChartPayload>(`/api/chart-data/overview${q}`)
}

/** Cumulative commit counts within the current window (not used for KPI period sparklines). */
export function cumulativeSeriesFromOverview(payload: OverviewChartPayload | null): number[] {
  const cd = payload?.kpi_trends?.commits?.cumulative_daily
  if (Array.isArray(cd) && cd.length > 0) {
    const nums = cd.map((x) => Number(x.cumulative ?? 0))
    if (nums.length >= 2) return nums
    if (nums.length === 1) return [nums[0], nums[0]]
  }
  const series = payload?.charts?.commit_daily?.series
  if (!Array.isArray(series) || series.length === 0) return []
  let cum = 0
  const out: number[] = []
  for (const row of series) {
    cum += Number(row?.count ?? 0)
    out.push(cum)
  }
  if (out.length === 1) return [out[0], out[0]]
  return out
}

export function sumCommitDailySevenDay(payload: OverviewChartPayload): number | null {
  const ct = payload.kpi_trends?.commits?.current_total
  if (typeof ct === 'number' && !Number.isNaN(ct)) return ct
  const series = payload.charts?.commit_daily?.series
  if (!Array.isArray(series)) return null
  let n = 0
  for (const row of series) {
    const c = row?.count
    if (typeof c === 'number' && !Number.isNaN(c)) n += c
  }
  return n
}

/**
 * Per-repo lines tier/median from `kpi_trends.lines_added.per_repo_lines`.
 * Keys are normalized (trim + lowercase) for lookup by repository display name.
 */
export function perRepoLinesByKey(
  payload: OverviewChartPayload | null,
): Map<string, PerRepoLinesEntry> {
  const m = new Map<string, PerRepoLinesEntry>()
  const pr = payload?.kpi_trends?.lines_added?.per_repo_lines
  if (!pr || typeof pr !== 'object') return m
  for (const [k, v] of Object.entries(pr)) {
    if (!v || typeof v !== 'object') continue
    m.set(k.trim().toLowerCase(), v as PerRepoLinesEntry)
  }
  return m
}

/** Map normalized repo key (trim + lowercase) -> lines added in current window from overview chart. */
export function linesAddedByRepo(payload: OverviewChartPayload): Map<string, number> {
  const m = new Map<string, number>()
  const rows = payload.charts?.loc_added_horizontal?.rows
  if (!Array.isArray(rows)) return m
  for (const row of rows) {
    const name = row?.name != null ? String(row.name).trim() : ''
    const v = row?.value
    if (name && typeof v === 'number' && !Number.isNaN(v)) m.set(name.toLowerCase(), v)
  }
  return m
}

/** Map repo name -> compliance score from overview chart (when present). */
export function complianceByRepo(payload: OverviewChartPayload): Map<string, number> {
  const m = new Map<string, number>()
  const rows = payload.charts?.compliance_bars?.rows
  if (!Array.isArray(rows)) return m
  for (const row of rows) {
    if (!Array.isArray(row) || row.length < 2) continue
    const name = String(row[0] ?? '').trim()
    const score = Number(row[1])
    if (name && !Number.isNaN(score)) m.set(name, score)
  }
  return m
}

export function topReposByLinesAdded(
  payload: OverviewChartPayload,
  limit: number,
): { name: string; linesAdded: number }[] {
  const rows = payload.charts?.loc_added_horizontal?.rows
  if (!Array.isArray(rows)) return []
  const parsed: { name: string; linesAdded: number }[] = []
  for (const row of rows) {
    const name = row?.name != null ? String(row.name).trim() : ''
    const v = row?.value
    if (name && typeof v === 'number' && !Number.isNaN(v)) parsed.push({ name, linesAdded: v })
  }
  parsed.sort((a, b) => b.linesAdded - a.linesAdded)
  return parsed.slice(0, Math.max(0, limit))
}
