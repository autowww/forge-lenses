import { test, expect } from '@playwright/test'

/**
 * Regression: first-time workspace must persist scan runs (store creates ``runs/``).
 * Also verifies the browser completes POST scan (no empty TCP / "Failed to fetch" from missing dirs).
 */
test('Docs health — Run markdown scan returns JSON ok and UI shows Scan finished', async ({ page }) => {
  await page.goto('/studio/projects/e2e_doc_proj/docs-health')
  const scanBtn = page.getByRole('button', { name: 'Run markdown scan' })
  await expect(scanBtn).toBeVisible({ timeout: 120_000 })

  const [resp] = await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().includes('/api/project/e2e_doc_proj/docs-health') &&
        r.request().method() === 'POST' &&
        (() => {
          try {
            const j = r.request().postDataJSON() as { op?: string }
            return j?.op === 'scan'
          } catch {
            return false
          }
        })(),
    ),
    scanBtn.click(),
  ])

  expect(resp.ok(), `scan HTTP status ${resp.status()}`).toBeTruthy()
  const body = (await resp.json()) as { ok?: boolean; error?: string }
  expect(body.ok, JSON.stringify(body)).toBeTruthy()

  await expect(page.getByText(/Scan finished/).first()).toBeVisible({ timeout: 120_000 })
})
