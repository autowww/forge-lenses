import { test, expect, type Page } from '@playwright/test'

function mockPlanApi(page: Page) {
  return page.route('**/api/foundry/plan', async (route) => {
    if (route.request().method() !== 'POST') {
      await route.continue()
      return
    }
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        goal: 'fix failing multiply',
        level: 'L1',
        units: [{ id: 'multiply', summary: 'Fix engine.multiply', allowed_files: ['src/dfcalc/engine.py'] }],
      }),
    })
  })
}

async function mockHub(page: Page) {
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
  await page.route('**/api/foundry/runs', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, runs: [] }) })
      return
    }
    await route.continue()
  })
}

test('Foundry plan card — propose plan shows units', async ({ page }) => {
  await mockHub(page)
  await mockPlanApi(page)
  await page.goto('/foundry')
  await page.getByRole('button', { name: /Propose plan/i }).click()
  await expect(page.getByText(/Proposed plan/i).first()).toBeVisible({ timeout: 120_000 })
  await expect(page.getByText(/Fix engine.multiply/i).first()).toBeVisible()
})
