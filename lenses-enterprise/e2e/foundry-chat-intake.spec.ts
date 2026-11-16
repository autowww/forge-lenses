import { test, expect, type Page } from '@playwright/test'

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
  await page.route('**/api/foundry/intake', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        goal: 'fix failing multiply',
        level: 'L1',
        target: 'src/dfcalc/engine.py',
        project: 'forge-df-test-project',
        source: 'fallback_parser',
      }),
    })
  })
}

test('Foundry chat intake — parses into composer fields', async ({ page }) => {
  await mockHub(page)
  await page.goto('/studio/foundry')
  await page.getByPlaceholder(/fix failing multiply/i).fill(
    'fix failing multiply for @forge-df-test-project #src/dfcalc/engine.py L1',
  )
  await page.getByRole('button', { name: /Parse into composer/i }).click()
  await expect(page.getByRole('textbox', { name: 'goal' })).toHaveValue('fix failing multiply', { timeout: 120_000 })
  await expect(page.getByRole('textbox', { name: '#target' })).toHaveValue('src/dfcalc/engine.py')
})
