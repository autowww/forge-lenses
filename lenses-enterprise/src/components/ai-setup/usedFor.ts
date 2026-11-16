/** Human labels for Studio tasks that route to a given provider id. */

export function usedForLabels(
  providerId: string,
  taskRoutes: Record<string, { provider?: string; model?: string } | undefined> | undefined,
  taskRowMeta: Array<{ id: string; label: string }>,
): string[] {
  const pid = providerId.trim()
  if (!pid || !taskRoutes) return []
  const out: string[] = []
  for (const row of taskRowMeta) {
    const tr = taskRoutes[row.id]
    const p = (tr?.provider ?? '').trim()
    if (p === pid) {
      out.push(row.label)
    }
  }
  return out
}
