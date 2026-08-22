import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FoundryPlanCard } from './FoundryPlanCard'

describe('FoundryPlanCard', () => {
  it('renders proposed units', () => {
    render(
      <FoundryPlanCard
        plan={{
          ok: true,
          goal: 'fix failing multiply',
          level: 'L1',
          units: [{ id: 'u1', summary: 'Fix multiply', allowed_files: ['src/dfcalc/engine.py'] }],
        }}
      />,
    )
    expect(screen.getByText(/Proposed plan/i)).toBeInTheDocument()
    expect(screen.getByText(/Fix multiply/i)).toBeInTheDocument()
  })
})
