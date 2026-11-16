const SEP = ' · '

function titleCaseWords(s: string): string {
  const t = s.trim().replace(/_/g, ' ')
  if (!t) return ''
  return t
    .split(/\s+/g)
    .map((w) => (w ? w[0]!.toUpperCase() + w.slice(1).toLowerCase() : ''))
    .join(' ')
}

/**
 * Short heading for the remediation run hero (decision-first; avoids repeating repo slug from context banner).
 * Parses canonical display names like `Docs remediation · my-proj · Minor · diagram`.
 */
export function deriveShortRemediationRunTitle(opts: {
  displayName?: string | null
  clusterLabel?: string | null
  category?: string | null
}): string {
  const dn = opts.displayName?.trim() || ''
  if (dn) {
    const parts = dn.split(SEP).map((p) => p.trim()).filter(Boolean)
    if (parts.length >= 4 && /^docs remediation$/i.test(parts[0]!)) {
      const tail = parts[parts.length - 1]!
      return `${titleCaseWords(tail)} remediation`
    }
    if (parts.length === 3 && /^docs remediation$/i.test(parts[0]!)) {
      const tail = parts[parts.length - 1]!
      if (tail.length <= 48) return `${titleCaseWords(tail)} remediation`
    }
  }
  const cat = opts.category?.trim()
  if (cat) return `${titleCaseWords(cat)} remediation`
  const cl = opts.clusterLabel?.trim()
  if (cl) return `${titleCaseWords(cl)} remediation`
  return 'Documentation remediation run'
}
