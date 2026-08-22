import type { DocsHealthCluster, DocsHealthFinding, DocsHealthProjectPayload } from '../../api/docsHealth'

type LatestRunShape = {
  clusters?: DocsHealthCluster[]
  findings?: DocsHealthFinding[]
}

/** Paths from findings in the session cluster (same logic as context rail). */
export function getClusterAffectedPaths(
  projectSnapshot: DocsHealthProjectPayload | null,
  sessionClusterId: string | undefined,
  sessionClusterLabel: string | undefined,
): { paths: string[]; count: number } {
  const latest = projectSnapshot?.latest_run as LatestRunShape | null | undefined
  const cluster =
    latest?.clusters?.find((c) => (sessionClusterId ? c.id === sessionClusterId : false)) ??
    latest?.clusters?.find((c) => c.label && c.label === sessionClusterLabel)
  const findingIds = new Set(cluster?.finding_ids ?? [])
  const affected = (latest?.findings ?? [])
    .filter((f) => f.id && findingIds.has(f.id))
    .flatMap((f) => f.affected_paths ?? [])
  const uniq = Array.from(new Set(affected))
  return { paths: uniq, count: uniq.length }
}
