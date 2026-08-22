import type { ReactElement } from 'react'
import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { StatePanel } from './StatePanel'

function renderWithRouter(ui: ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>)
}

describe('StatePanel', () => {
  it('uses alert role for error variant', () => {
    renderWithRouter(<StatePanel variant="error" title="Failed" description="Try again." />)
    expect(screen.getByRole('alert')).toBeTruthy()
    expect(screen.getByText('Failed')).toBeTruthy()
  })

  it('uses status role for loading variant', () => {
    renderWithRouter(<StatePanel variant="loading" title="Loading" />)
    expect(screen.getByRole('status')).toBeTruthy()
  })

  it('shows technical detail inside details', () => {
    renderWithRouter(
      <StatePanel variant="invalid" title="Bad" technicalDetail="ENOENT" />,
    )
    expect(screen.getByText('Show technical details')).toBeTruthy()
    expect(screen.getByText('ENOENT')).toBeTruthy()
  })

  it('renders assist shortcuts when provided', () => {
    renderWithRouter(
      <StatePanel
        variant="empty"
        title="Nothing here"
        assistShortcuts={{ context: 'Test page' }}
      />,
    )
    expect(screen.getByRole('group', { name: 'Guided help in Copilot' })).toBeTruthy()
    expect(screen.getByText('Explain this state')).toBeTruthy()
  })

  it('uses status role for unavailable variant', () => {
    renderWithRouter(<StatePanel variant="unavailable" title="Down" description="Try later." />)
    expect(screen.getByRole('status')).toBeTruthy()
  })
})
