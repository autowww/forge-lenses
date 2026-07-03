import { test, expect, type Page } from '@playwright/test'

const RUN_ID = 'frun_e2e_approve'

async function mockApprovalRun(page: Page) {
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
        promoted: false,
        phases: [{ id: 'assay', label: 'assay', status: 'completed' }],
        assay: { ok: true },
      }),
    })
  })
  await page.route(`**/api/foundry/runs/${RUN_ID}/approve`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ ok: true, run: { id: RUN_ID, promoted: true } }),
    })
  })
}

test('Foundry approval — checkbox gates promote button', async ({ page }) => {
  await mockApprovalRun(page)
  await page.goto(`/foundry/runs/${RUN_ID}`)
  await expect(page.getByText(/Review before apply/i).first()).toBeVisible({ timeout: 120_000 })
  const btn = page.getByRole('button', { name: /Approve and promote/i })
  await expect(btn).toBeDisabled()
  await page.getByRole('checkbox').check()
  await expect(btn).toBeEnabled()
})
