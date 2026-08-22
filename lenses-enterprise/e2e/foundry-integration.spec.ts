import { test, expect } from '@playwright/test'

/**
 * Real Foundry APIs (no route mocks). Requires forge-df-test-project seeded by
 * scripts/e2e-lenses-with-fixture.sh and forge-dark-factory sibling checkout.
 */
test('Foundry integration — propose plan for project + file target', async ({ page }) => {
  await page.goto('/studio/foundry')
  await expect(page.getByRole('heading', { name: /^Foundry$/i })).toBeVisible({ timeout: 120_000 })

  const projectSelect = page.getByRole('combobox', { name: '@project' })
  await expect(projectSelect).toBeVisible()
  await projectSelect.selectOption('forge-df-test-project')

  await page.getByRole('textbox', { name: '#target' }).fill('src/dfcalc/engine.py')
  await page.getByRole('textbox', { name: 'goal' }).fill('fix failing multiply')

  await page.getByRole('button', { name: /Propose plan/i }).click()
  await expect(page.getByText(/Proposed plan/i).first()).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText(/src\/dfcalc\/engine\.py/).first()).toBeVisible()
  await expect(page.getByText(/Action failed/i)).toHaveCount(0)
})

test('Foundry integration — run L1 draft navigates to run page', async ({ page }) => {
  test.setTimeout(300_000)
  await page.goto('/studio/foundry')
  await expect(page.getByRole('heading', { name: /^Foundry$/i })).toBeVisible({ timeout: 120_000 })
  await page.getByRole('combobox', { name: '@project' }).selectOption('forge-df-test-project')
  await page.getByRole('button', { name: /Propose plan/i }).click()
  await expect(page.getByRole('button', { name: /Run L1 draft/i })).toBeVisible({ timeout: 30_000 })
  await page.getByRole('button', { name: /Run L1 draft/i }).click()
  await expect(page).toHaveURL(/\/studio\/foundry\/runs\/frun_/, { timeout: 60_000 })
  await expect(page.getByText(/Action failed/i)).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 2, name: /fix failing multiply/i })).toBeVisible({
    timeout: 60_000,
  })
  // Run may finish failed in minimal E2E fixture (no venv pytest); navigation + run record is the gate.
  await expect(page.getByText(/failed|running|completed/i).first()).toBeVisible()
})
