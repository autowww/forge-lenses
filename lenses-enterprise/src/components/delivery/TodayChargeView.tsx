import type { TodaySections } from '../../lib/todayCharge'

const SECTION_ORDER = [
  'active',
  'blocked',
  'banked',
  'recently_resolved',
  'pending_versona',
] as const

type Props = {
  payload: Record<string, unknown>
  /** If set, only render these section keys (order preserved from SECTION_ORDER) */
  sectionFilter?: readonly string[]
}

export function TodayChargeView({ payload, sectionFilter }: Props) {
  const charge = payload.charge as { view_href?: string; hat?: string; date?: string } | undefined
  const sections = payload.sections as TodaySections | undefined
  const sparkRows = (payload.spark_rows as Record<string, unknown>[]) ?? []

  const order = sectionFilter?.length
    ? SECTION_ORDER.filter((k) => sectionFilter.includes(k))
    : [...SECTION_ORDER]

  return (
    <div>
      {charge && (
        <p className="forge-support">
          Charge: {charge.hat} {charge.date}
          {charge.view_href ? (
            <>
              {' '}
              <a href={charge.view_href}>Open charge.md</a>
            </>
          ) : null}
        </p>
      )}
      {sections &&
        order.map((key) => {
          const rows = sections[key] ?? []
          if (!rows.length) return null
          return (
            <section key={key} className="le-panel" style={{ marginBottom: '1rem' }}>
              <h3 className="le-panel__title" style={{ textTransform: 'capitalize' }}>
                {key.replace(/_/g, ' ')}
              </h3>
              <SparkTable rows={rows} />
            </section>
          )
        })}
      {sparkRows.length > 0 && !sectionFilter?.length && (
        <section className="le-panel">
          <h3 className="le-panel__title">All sparks</h3>
          <SparkTable rows={sparkRows} />
        </section>
      )}
    </div>
  )
}

export function SparkTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (!rows.length) return null
  const keys = Object.keys(rows[0] ?? {}).filter((k) => k !== 'flags')
  return (
    <div className="le-table-wrap">
      <table className="le-table">
        <thead>
          <tr>
            {keys.map((k) => (
              <th key={k}>{k}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {keys.map((k) => (
                <td key={k} className="le-mono" style={{ fontSize: '0.75rem' }}>
                  {formatCell(r[k])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function formatCell(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
