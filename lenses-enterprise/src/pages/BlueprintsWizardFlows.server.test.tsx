import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, beforeEach, vi } from 'vitest'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { postWizardCursorLaunchPackExport, postWizardCursorLaunchPackPreview } from '../api/blueprintsWizard'
import { BlueprintsWizardLayout } from './BlueprintsWizardLayout'
import { BlueprintsWizardSessionPage } from './BlueprintsWizardSessionPage'
import { BlueprintsWizardHub } from '../blueprints-wizard/BlueprintsWizardHub'
import { MainContentInertProvider } from '../context/MainContentInertContext'
import { LensesCopilotPageScopeProvider } from '../context/LensesCopilotPageScopeContext'

const newProductDraft = {
  repo_name: '',
  visibility: 'private',
  account_type: 'user',
  owner: '',
  license: '',
  description: '',
}

function basePayload(mission: { mode: string; title: string; outcome: string; notes: string }) {
  return {
    title: '',
    purpose: '',
    state: 'draft',
    mode: 'existing_workspace',
    scope: { wbs_rel: null, roadmap_rel: null, roadmap_section_id: null },
    parent_session_id: null,
    new_product_draft: newProductDraft,
    created_repo_url: null,
    stepNotes: {},
    mission,
  }
}

const defaultSessionPayload = basePayload({
  mode: 'start_from_idea',
  title: 'Seed',
  outcome: 'Seed outcome text for validation.',
  notes: '',
})

const mocks = vi.hoisted(() => ({
  getBlueprintsWizardEnabled: vi.fn(() => Promise.resolve(true)),
  getWizardSession: vi.fn(() =>
    Promise.resolve({
      version: 2,
      updated_at: '2026-01-01T00:00:00Z',
      step_index: 0,
      payload: defaultSessionPayload,
    }),
  ),
  listWizardSessions: vi.fn(() => Promise.resolve([])),
  createWizardSession: vi.fn(() => Promise.resolve({ session_id: 'new-sid' })),
  putWizardSession: vi.fn(() => Promise.resolve()),
  postWizardRefine: vi.fn(() => Promise.resolve({ ok: true, session: undefined })),
  postWizardArtifactRecheck: vi.fn(() =>
    Promise.resolve({
      ok: true,
      session: {
        version: 2,
        updated_at: '2026-01-01T00:00:01Z',
        step_index: 10,
        payload: basePayload({
          mode: 'start_from_idea',
          title: 'Seed',
          outcome: 'Seed outcome text for validation.',
          notes: '',
        }),
      },
    }),
  ),
  postWizardCursorLaunchPackPreview: vi.fn(() =>
    Promise.resolve({ ok: true, files: [{ path: 'a.md', kind: 'file', size: 10 }], warnings: [] }),
  ),
  postWizardCursorLaunchPackExport: vi.fn(() =>
    Promise.resolve({ ok: true, export_path_relative: 'out/pack', file_count: 1, warnings: ['note'] }),
  ),
  postWizardTelemetry: vi.fn(() => Promise.resolve({ ok: true })),
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
    postWizardArtifactRecheck: mocks.postWizardArtifactRecheck,
    postWizardCursorLaunchPackPreview: mocks.postWizardCursorLaunchPackPreview,
    postWizardCursorLaunchPackExport: mocks.postWizardCursorLaunchPackExport,
    postWizardTelemetry: mocks.postWizardTelemetry,
  }
})

vi.mock('../util/experimentalFlags', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../util/experimentalFlags')>()
  return {
    ...actual,
    blueprintsWizardTelemetryClientEnabled: () => true,
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
      <LensesCopilotPageScopeProvider>
        <RouterProvider router={router} />
      </LensesCopilotPageScopeProvider>
    </MainContentInertProvider>,
  )
}

describe('BlueprintsWizard flows (mocked API)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.getWizardSession.mockImplementation(() =>
      Promise.resolve({
        version: 2,
        updated_at: '2026-01-01T00:00:00Z',
        step_index: 0,
        payload: defaultSessionPayload,
      }),
    )
  })

  it('start_from_idea: advances Mission to Contribution with monotonic step_index', async () => {
    renderSession('/blueprints/wizard/session/flow-idea')

    expect(await screen.findByRole('heading', { level: 2, name: 'Mission' })).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText(/Mission title/i), { target: { value: 'Idea mission' } })
    fireEvent.change(screen.getByLabelText(/Outcome \/ problem/i), {
      target: { value: 'Ship a blueprint pack for internal use.' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Next' }))

    await waitFor(() => {
      expect(mocks.putWizardSession).toHaveBeenCalledWith(
        'flow-idea',
        expect.objectContaining({ step_index: 1 }),
      )
    })

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Contribution Setup' })).toBeInTheDocument()
    })
  })

  it('assess_current_project: shows Mission with assess mode from session payload', async () => {
    mocks.getWizardSession.mockImplementation(() =>
      Promise.resolve({
        version: 2,
        updated_at: '2026-01-01T00:00:00Z',
        step_index: 0,
        payload: basePayload({
          mode: 'assess_current_project',
          title: 'Assess',
          outcome: 'Understand current delivery posture.',
          notes: '',
        }),
      }),
    )

    renderSession('/blueprints/wizard/session/flow-assess')

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2, name: 'Mission' })).toBeInTheDocument()
    })

    expect(screen.getByRole('radio', { name: /Assess current project/i })).toBeChecked()
  })

  it('recheck step: Refresh recheck calls artifact-recheck API', async () => {
    mocks.getWizardSession.mockImplementation(() =>
      Promise.resolve({
        version: 2,
        updated_at: '2026-01-01T00:00:00Z',
        step_index: 10,
        payload: basePayload({
          mode: 'start_from_idea',
          title: 'Seed',
          outcome: 'Seed outcome text for validation.',
          notes: '',
        }),
      }),
    )

    renderSession('/blueprints/wizard/session/flow-recheck')

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Recheck / Repair' })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Refresh recheck' }))

    await waitFor(() => {
      expect(mocks.postWizardArtifactRecheck).toHaveBeenCalledWith('flow-recheck', {})
    })
  })

  it('experimental build: preview and workspace export happy path', async () => {
    mocks.getWizardSession.mockImplementation(() =>
      Promise.resolve({
        version: 2,
        updated_at: '2026-01-01T00:00:00Z',
        step_index: 11,
        payload: {
          ...basePayload({
            mode: 'start_from_idea',
            title: 'Seed',
            outcome: 'Seed outcome text for validation.',
            notes: '',
          }),
          wizard_domain: {
            artifact_generation: {
              artifacts: {
                foundation_brief_final: { content: { x: 1 }, provenance: { generation_id: 'g1' } },
              },
            },
          },
        },
      }),
    )

    renderSession('/blueprints/wizard/session/flow-export')

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Experimental Build — Cursor Launch Pack/i })).toBeInTheDocument()
    })

    await postWizardCursorLaunchPackPreview('flow-export', {
      artifact_keys: ['foundation_brief_final'],
      closure_options: ['exact_only'],
      strict_approval: false,
    })
    expect(mocks.postWizardCursorLaunchPackPreview).toHaveBeenCalled()

    await postWizardCursorLaunchPackExport('flow-export', {
      artifact_keys: ['foundation_brief_final'],
      closure_options: ['exact_only'],
      destination: 'workspace',
      strict_approval: false,
    })
    expect(mocks.postWizardCursorLaunchPackExport).toHaveBeenCalled()
  })
})
