import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { EmbeddedPreviewFrame } from '../EmbeddedPreviewFrame'

type Props = {
  /** Shown in the Studio preview toolbar. */
  frameTitle?: string
  frameMinHeight?: string
}

/**
 * Same-origin iframe to ``/nested-roadmap-view.html`` — workspace matrix data with Kitchen Sink drill-down.
 * Reads ``repo``, ``roadmap_p``, ``wbs_p`` from the current URL (``p`` is accepted as an alias for ``roadmap_p``).
 */
export function NestedRoadmapWorkspaceFrame({
  frameTitle = 'Roadmap horizon',
  frameMinHeight = 'min(52vh, 28rem)',
}: Props) {
  const [sp] = useSearchParams()
  const src = useMemo(() => {
    const repo = sp.get('repo')?.trim() ?? ''
    const roadmapP = sp.get('roadmap_p')?.trim() ?? sp.get('p')?.trim() ?? ''
    const wbsP = sp.get('wbs_p')?.trim() ?? ''
    const q = new URLSearchParams()
    if (repo) q.set('repo', repo)
    if (roadmapP) q.set('roadmap_p', roadmapP)
    if (wbsP) q.set('wbs_p', wbsP)
    const tail = q.toString()
    return `/nested-roadmap-view.html${tail ? `?${tail}` : ''}`
  }, [sp])

  return (
    <EmbeddedPreviewFrame
      title={frameTitle}
      src={src}
      frameMinHeight={frameMinHeight}
      showRecoveryHint={false}
    />
  )
}
