import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { InterpretationCanvas } from './InterpretationCanvas'
import { emptyInterpretationPayload } from './interpretationPayload'

describe('InterpretationCanvas', () => {
  it('renders three column headings and Run interpretation when handler provided', () => {
    render(
      <InterpretationCanvas
        value={emptyInterpretationPayload()}
        onChange={() => {}}
        onRunInterpret={() => {}}
      />,
    )
    expect(screen.getByRole('heading', { name: 'What you said' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'What Blueprints inferred' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Needs confirmation' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Run interpretation' })).toBeInTheDocument()
  })

  it('renders Foundation Brief draft heading', () => {
    render(<InterpretationCanvas value={emptyInterpretationPayload()} onChange={() => {}} />)
    expect(screen.getByRole('heading', { name: 'Foundation Brief draft' })).toBeInTheDocument()
  })
})
