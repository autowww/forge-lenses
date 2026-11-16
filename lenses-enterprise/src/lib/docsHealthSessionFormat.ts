/**
 * Readable local timestamps in UI; UTC ISO available for tooltips and machine use.
 */
export function formatSessionInstant(iso?: string | null): { text: string; utcTitle?: string; dateTime?: string } {
  if (iso == null || String(iso).trim() === '') return { text: 'Not recorded' }
  const raw = String(iso)
  try {
    const d = new Date(raw)
    if (Number.isNaN(d.getTime())) return { text: raw }
    return {
      text: d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }),
      utcTitle: d.toISOString(),
      dateTime: d.toISOString(),
    }
  } catch {
    return { text: raw }
  }
}
