import { test, expect, type Page } from '@playwright/test'

const MOCK_RUN = {
  ok: true,
  id: 'frun_e2e_mock',
  status: 'completed',
  goal: 'fix failing multiply',
  target: '/tmp/forge-df-test-project',
  level: 'L1',
  execution_mode: 'draft',
  final_status: 'pass',
  assay_ok: true,
  phases: [
    { id: 'classify', label: 'classify', status: 'completed' },
    { id: 'route', label: 'route', status: 'completed' },
    { id: 'assay', label: 'assay', status: 'completed' },
  ],
  activity: [
    { id: 'act_1', ts: '2026-07-04T04:00:00Z', text: 'Run queued — L1 draft', tone: 'busy' },
    { id: 'act_2', ts: '2026-07-04T04:00:01Z', text: 'Building context pack — 8 items', tone: 'ok' },
  ],
  current_phase: 'assay',
  assay: { ok: true, tests_pass: true },
  review: {
    ok: true,
    proof_markdown: '# Proof\n\n- changed engine.py\n',
    narrative: {
      ok: true,
      root_cause: '`multiply()` returned the sum instead of the product.',
      change_summary: 'Corrected multiply() to use multiplication.',
      why_it_works: 'Verification re-ran pytest.',
    },
    files: [
      {
        path: 'src/dfcalc/engine.py',
        unified_diff: '--- before\n+++ after\n@@\n-return a + b\n+return a * b\n',
        has_changes: true,
        source: 'fixture',
      },
    ],
  },
}

function mockFoundryApis(page: Page) {
  return Promise.all([
    page.route('**/api/foundry/enabled', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, enabled: true }) })
    }),
    page.route('**/api/foundry/capabilities', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ok: true,
          ladder: { L1: { status: 'available', label: 'Function-level' }, L2: { status: 'stub', label: 'Change-set' } },
        }),
      })
    }),
    page.route('**/api/foundry/runs', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ ok: true, runs: [MOCK_RUN] }),
        })
        return
      }
      await route.continue()
    }),
    page.route('**/api/foundry/runs/frun_e2e_mock', async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_RUN) })
    }),
  ])
}

test('Foundry hub — capabilities ladder and recent runs', async ({ page }) => {
  await mockFoundryApis(page)
  await page.goto('/studio/foundry')
  await expect(page.getByText(/Autonomy ladder/i).first()).toBeVisible({ timeout: 120_000 })
  await expect(page.getByText(/L1/i).first()).toBeVisible()
  await expect(page.getByText(/fix failing multiply/i).first()).toBeVisible()
})

test('Foundry run viewer — stage bar and assay card', async ({ page }) => {
  await mockFoundryApis(page)
  await page.goto('/studio/foundry/runs/frun_e2e_mock')
  await expect(page.getByText(/fix failing multiply/i).first()).toBeVisible({ timeout: 120_000 })
  await expect(page.getByLabel(/Dark Factory workflow stages/i)).toBeVisible()
  await expect(page.getByText(/Assay passed/i).first()).toBeVisible()
  await expect(page.getByText(/Review changes/i).first()).toBeVisible()
  await expect(page.getByText(/Stage details/i).first()).toBeVisible()
  await expect(page.getByText(/Agent activity/i).first()).toBeVisible()
  await expect(page.getByText(/Root cause/i).first()).toBeVisible()
  await expect(page.getByText(/return a \* b/i).first()).toBeVisible()
})
