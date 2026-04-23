import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, vi } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { BlueprintsWizardLayout } from './BlueprintsWizardLayout'
import { BlueprintsWizardSessionPage } from './BlueprintsWizardSessionPage'
import { BlueprintsWizardHub } from '../blueprints-wizard/BlueprintsWizardHub'
import { MainContentInertProvider } from '../context/MainContentInertContext'

const samplePayload = {
  title: '',
  purpose: '',
  state: 'draft',
  mode: 'existing_workspace',
  scope: { wbs_rel: null, roadmap_rel: null, roadmap_section_id: null },
  parent_session_id: null,
  new_product_draft: {
    repo_name: '',
    visibility: 'private',
    account_type: 'user',
    owner: '',
    license: '',
    description: '',
  },
  created_repo_url: null,
  stepNotes: {},
}

const mocks = vi.hoisted(() => ({
  getBlueprintsWizardEnabled: vi.fn(() => Promise.resolve(true)),
  getWizardSession: vi.fn(() =>
    Promise.resolve({
      version: 2,
      updated_at: '2026-01-01T00:00:00Z',
      step_index: 0,
      payload: samplePayload,
    }),
  ),
  listWizardSessions: vi.fn(() => Promise.resolve([])),
  createWizardSession: vi.fn(() => Promise.resolve({ session_id: 'new-sid' })),
  putWizardSession: vi.fn(() => Promise.resolve()),
  postWizardRefine: vi.fn(() => Promise.resolve({ ok: true, session: undefined })),
}))

vi.mock('../api/blueprintsWizard', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/blueprintsWizard')>()
  return {
    ...actual,
    getBlueprintsWizardEnabled: mocks.getBlueprintsWizardEnabled,
    getWizardSession: mocks.getWizardSession,
    listWizardSessions: mocks.listWizardSessions,
    createWizardSession: mocks.createWizardSession,
    putWizardSession: mocks.putWizardSession,
    postWizardRefine: mocks.postWizardRefine,
  }
})

function renderSession(path: string) {
  const router = createMemoryRouter(
    [
      {
        path: '/blueprints/wizard',
        element: <BlueprintsWizardLayout />,
        children: [
          { index: true, element: <BlueprintsWizardHub /> },
          { path: 'session/:sessionId', element: <BlueprintsWizardSessionPage /> },
        ],
      },
    ],
    { initialEntries: [path] },
  )
  return render(
    <MainContentInertProvider>
      <RouterProvider router={router} />
    </MainContentInertProvider>,
  )
}

describe('BlueprintsWizardSessionPage (server session)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getWizardSession.mockImplementation(() =>
      Promise.resolve({
        version: 2,
        updated_at: '2026-01-01T00:00:00Z',
        step_index: 0,
        payload: samplePayload,
      }),
    )
  })

  it(
    'loads session by route and persists step on Next',
    async () => {
      renderSession('/blueprints/wizard/session/test-session-id')

      await waitFor(() => {
        expect(mocks.getWizardSession).toHaveBeenCalledWith('test-session-id')
      })

      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 2, name: 'Mission' })).toBeInTheDocument()
      })

      fireEvent.change(screen.getByLabelText(/Mission title/i), { target: { value: 'Server mission' } })
      fireEvent.change(screen.getByLabelText(/Outcome \/ problem/i), {
        target: { value: 'Validate session persistence on Next.' },
      })

      fireEvent.click(screen.getByRole('button', { name: 'Next' }))

      await waitFor(() => {
        expect(mocks.putWizardSession).toHaveBeenCalledWith(
          'test-session-id',
          expect.objectContaining({ step_index: 1 }),
        )
      })

      await waitFor(() => {
        expect(screen.getByRole('heading', { level: 2, name: 'Contribution Setup' })).toBeInTheDocument()
      })
    },
    12_000,
  )

  it('shows LLM refine panel', async () => {
    renderSession('/blueprints/wizard/session/s2')

    await waitFor(() => {
      expect(screen.getByText(/Foundation Brief \(LLM\)/i)).toBeInTheDocument()
    })
  })

  it('resumes at saved step_index when reopening a session', async () => {
    mocks.getWizardSession.mockImplementation(() =>
      Promise.resolve({
        version: 2,
        updated_at: '2026-01-01T00:00:00Z',
        step_index: 3,
        payload: samplePayload,
      }),
    )

    renderSession('/blueprints/wizard/session/resume-step-3')

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Understanding' })).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(mocks.getWizardSession).toHaveBeenCalledWith('resume-step-3')
    })
  })
})
