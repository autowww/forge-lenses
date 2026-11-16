import { NestedRoadmapHorizon } from './NestedRoadmapHorizon'

type Props = {
  /** Shown in the Studio preview toolbar. */
  frameTitle?: string
  frameMinHeight?: string
}

/**
 * React roadmap horizon — structured config from ``GET /api/nested-roadmap-config``.
 * Reads ``repo``, ``roadmap_p``, ``wbs_p`` from the current URL (``p`` aliases ``roadmap_p``).
 */
export function NestedRoadmapWorkspaceFrame({
  frameTitle = 'Roadmap horizon',
  frameMinHeight = 'min(52vh, 28rem)',
}: Props) {
  return (
    <NestedRoadmapHorizon frameTitle={frameTitle} frameMinHeight={frameMinHeight} />
  )
}
