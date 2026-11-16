import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach } from 'vitest'
import { createMemoryRouter, RouterProvider, useNavigate } from 'react-router-dom'
import { BlueprintsWizardLocalMode } from './BlueprintsWizardLocalMode'
import { WIZARD_SHELL_STORAGE_KEY } from '../blueprints-wizard/wizardPersistence'

function LocalExitHost() {
  const navigate = useNavigate()
  return <BlueprintsWizardLocalMode onExit={() => navigate('/')} />
}

function renderWizard(initialPath = '/blueprints/wizard') {
  const router = createMemoryRouter(
    [
      { path: '/blueprints/wizard', element: <LocalExitHost /> },
      { path: '/', element: <div data-testid="home">Home</div> },
    ],
    { initialEntries: [initialPath] },
  )
  return { router, ...render(<RouterProvider router={router} />) }
}

describe('BlueprintsWizardLocalMode', () => {
  beforeEach(() => {
    sessionStorage.removeItem(WIZARD_SHELL_STORAGE_KEY)
  })

  it('renders Mission as first step', async () => {
    renderWizard()
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Mission' })).toBeInTheDocument()
    })
    expect(screen.getByRole('navigation', { name: 'Wizard steps' })).toBeInTheDocument()
  })

  it('advances and returns with Next / Back', async () => {
    renderWizard()
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Mission' })).toBeInTheDocument()
    })

    fireEvent.change(screen.getByLabelText(/Mission title/i), { target: { value: 'Test mission' } })
    fireEvent.change(screen.getByLabelText(/Outcome \/ problem/i), {
      target: { value: 'Deliver a working blueprint pack.' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Contribution Setup' })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Mission' })).toBeInTheDocument()
    })
  })

  it('navigates home on Exit', async () => {
    const { router } = renderWizard()
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Exit' })).toBeInTheDocument()
    })
    fireEvent.click(screen.getByRole('button', { name: 'Exit' }))
    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/')
    })
    expect(screen.getByTestId('home')).toBeInTheDocument()
  })
})
