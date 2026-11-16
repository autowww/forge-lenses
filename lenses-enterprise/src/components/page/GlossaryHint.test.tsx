import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { STUDIO_GLOSSARY } from '../../nav/studioVisibleCopy'
import { GlossaryHint } from './GlossaryHint'

describe('GlossaryHint', () => {
  it('renders abbr with glossary short text as title', () => {
    render(<GlossaryHint term="timelineVsRoadmap">Timeline</GlossaryHint>)
    expect(screen.getByText('Timeline')).toBeInTheDocument()
    expect(screen.getByTitle(STUDIO_GLOSSARY.timelineVsRoadmap.short)).toBeInTheDocument()
  })

  it('supports workspace lens glossary term', () => {
    render(<GlossaryHint term="workspaceLens">Lens</GlossaryHint>)
    expect(screen.getByTitle(STUDIO_GLOSSARY.workspaceLens.short)).toBeInTheDocument()
  })
})
