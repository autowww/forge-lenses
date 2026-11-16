import { useId, type ReactNode } from 'react'
import { STUDIO_GLOSSARY, type StudioGlossaryId } from '../../nav/studioVisibleCopy'

export type GlossaryHintProps = {
  term: StudioGlossaryId
  children: ReactNode
  className?: string
}

/**
 * Inline term with tooltip (`title`) and a longer screen-reader description.
 */
export function GlossaryHint({ term, children, className }: GlossaryHintProps) {
  const id = useId()
  const g = STUDIO_GLOSSARY[term]
  return (
    <span className={className}>
      <abbr className="le-glossary-hint" title={g.short} aria-describedby={id}>
        {children}
      </abbr>
      <span id={id} className="le-glossary-sr-only">
        {g.long}
      </span>
    </span>
  )
}
