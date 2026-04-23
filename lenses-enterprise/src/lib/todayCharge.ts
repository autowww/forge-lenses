/** Helpers for `GET /api/today-charge` payload (Studio Delivery / Today). */

export type TodayChargeCharge = {
  view_href?: string
  hat?: string
  date?: string
}

export type TodaySections = Record<string, Record<string, unknown>[]>

export function parseTodayCharge(payload: Record<string, unknown> | null): {
  charge: TodayChargeCharge | undefined
  sections: TodaySections
  sparkRows: Record<string, unknown>[]
} {
  if (!payload) {
    return { charge: undefined, sections: {}, sparkRows: [] }
  }
  const charge = payload.charge as TodayChargeCharge | undefined
  const sections = (payload.sections as TodaySections) ?? {}
  const sparkRows = Array.isArray(payload.spark_rows)
    ? (payload.spark_rows as Record<string, unknown>[])
    : []
  return { charge, sections, sparkRows }
}

export function sectionRowCounts(sections: TodaySections): Record<string, number> {
  const keys = ['active', 'blocked', 'banked', 'recently_resolved', 'pending_versona'] as const
  const out: Record<string, number> = {}
  for (const k of keys) {
    out[k] = Array.isArray(sections[k]) ? sections[k]!.length : 0
  }
  return out
}

/** Rough "at risk" signal: blocked rows + active rows (work in flight). */
export function commitmentsAtRiskCounts(sections: TodaySections): {
  active: number
  blocked: number
  pendingVersona: number
} {
  return {
    active: sectionRowCounts(sections).active ?? 0,
    blocked: sectionRowCounts(sections).blocked ?? 0,
    pendingVersona: sectionRowCounts(sections).pending_versona ?? 0,
  }
}
