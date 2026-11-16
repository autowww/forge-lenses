import { test, expect, type Page } from '@playwright/test'

const RUN_ID = 'frun_e2e_exec'

async function mockExecuteFlow(page: Page) {
  await page.route('**/api/foundry/enabled', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, enabled: true }) })
  })
  await page.route('**/api/foundry/capabilities', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, ladder: { L1: { status: 'available', label: 'L1' } } }),
    })
  })
  await page.route('**/api/foundry/plan', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        goal: 'fix failing multiply',
        level: 'L1',
        units: [{ id: 'u1', summary: 'Fix multiply', allowed_files: ['src/dfcalc/engine.py'] }],
      }),
    })
  })
  await page.route('**/api/foundry/runs', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, id: RUN_ID, status: 'running', goal: 'fix failing multiply' }),
      })
      return
    }
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, runs: [] }) })
  })
  await page.route(`**/api/foundry/runs/${RUN_ID}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        id: RUN_ID,
        status: 'completed',
        goal: 'fix failing multiply',
        final_status: 'pass',
        assay_ok: true,
        phases: [{ id: 'assay', label: 'assay', status: 'completed' }],
        assay: { ok: true, tests_pass: true },
      }),
    })
  })
}

test('Foundry execute draft — navigates to run with assay', async ({ page }) => {
  await mockExecuteFlow(page)
  await page.goto('/studio/foundry')
  await page.getByRole('button', { name: /Propose plan/i }).click()
  await page.getByRole('button', { name: /Run L1 draft/i }).click()
  await expect(page).toHaveURL(/\/studio\/foundry\/runs\//, { timeout: 120_000 })
  await expect(page.getByText(/Assay passed/i).first()).toBeVisible()
})
