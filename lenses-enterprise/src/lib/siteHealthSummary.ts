export function siteHealthSummary(htmlTotal: number | null | undefined): {
  healthSummary: string
  readinessScore: string
} {
  if (htmlTotal == null || htmlTotal <= 0) {
    return { healthSummary: 'No HTML pages detected in scan', readinessScore: 'Not ready to preview' }
  }
  if (htmlTotal < 5) {
    return { healthSummary: `${htmlTotal} page(s) — thin site tree`, readinessScore: 'Early draft' }
  }
  return { healthSummary: `${htmlTotal} HTML pages indexed`, readinessScore: 'Ready to browse' }
}
