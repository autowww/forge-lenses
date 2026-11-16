/** Qualitative impact / effort tiers (workshop + Stickerboard guest). */

export const IMPACT_TIERS = [
  {
    value: 'negligible',
    label: 'Negligible',
    hint: 'Nice-to-have; little effect on outcomes',
  },
  {
    value: 'moderate',
    label: 'Moderate',
    hint: 'Noticeable value; not strategic on its own',
  },
  {
    value: 'strong',
    label: 'Strong',
    hint: 'Clear lift to product or customers',
  },
  {
    value: 'critical',
    label: 'Critical',
    hint: 'Must-have for the roadmap bet',
  },
] as const

export const EFFORT_TIERS = [
  { value: 'quick', label: 'Quick', hint: 'Hours to a couple of days' },
  { value: 'short', label: 'Short', hint: 'About a week of focused work' },
  { value: 'medium', label: 'Medium', hint: 'Multi-week slice; some unknowns' },
  { value: 'large', label: 'Large', hint: 'Quarter-scale or major dependency' },
] as const

export type ImpactLabel = (typeof IMPACT_TIERS)[number]['value']
export type EffortLabel = (typeof EFFORT_TIERS)[number]['value']

const IMPACT_ORD: Record<string, number> = {
  negligible: 1,
  moderate: 2,
  strong: 3,
  critical: 4,
}

const EFFORT_ORD: Record<string, number> = {
  quick: 1,
  short: 2,
  medium: 3,
  large: 4,
}

export function priorityFromLabels(
  impactLabel: string | null | undefined,
  effortLabel: string | null | undefined,
): number | null {
  const i = impactLabel ? IMPACT_ORD[impactLabel] : null
  const e = effortLabel ? EFFORT_ORD[effortLabel] : null
  if (i == null || e == null || e < 1) return null
  return Math.round((i / e) * 10) / 10
}

export function impactEffortLabel(
  impactLabel: string | null | undefined,
  effortLabel: string | null | undefined,
): string {
  const il = IMPACT_TIERS.find((t) => t.value === impactLabel)?.label
  const el = EFFORT_TIERS.find((t) => t.value === effortLabel)?.label
  if (!il && !el) return ''
  if (il && el) return `${il} · ${el}`
  return il || el || ''
}
