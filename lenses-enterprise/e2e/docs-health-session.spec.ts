import { test, expect, type Page } from '@playwright/test'

/** Same disposable-workspace project as `docs-health-scan.spec.ts` (see e2e fixture script). */
const PROJECT = 'e2e_doc_proj'

function mockSessionGet(
  page: Page,
  sessionId: string,
  session: Record<string, unknown>,
): Promise<void> {
  return page.route(`**/api/project/${encodeURIComponent(PROJECT)}/docs-health`, async (route) => {
    if (route.request().method() !== 'POST') {
      await route.continue()
      return
    }
    let body: { op?: string; session_id?: string }
    try {
      body = route.request().postDataJSON() as { op?: string; session_id?: string }
    } catch {
      await route.continue()
      return
    }
    if (body.op === 'session_get' && body.session_id === sessionId) {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true, session }),
      })
      return
    }
    await route.continue()
  })
}

test('Docs health session — cancelled run shows banner and resume CTA', async ({ page }) => {
  const sid = 'e2e-mock-cancelled'
  await mockSessionGet(page, sid, {
    id: sid,
    status: 'cancelled',
    display_name: 'E2E cancelled',
    cluster: { label: 'Cluster A' },
    step_metrics: [],
    header_stats: { files_changed: 0 },
  })
  await page.goto(`/studio/projects/${PROJECT}/docs-health/session/${encodeURIComponent(sid)}`)
  await expect(page.getByText(/Run cancelled/i).first()).toBeVisible({ timeout: 120_000 })
  await expect(page.getByRole('button', { name: /Resume run/i })).toBeVisible()
})

test('Docs health session — awaiting approval shows review banner and approve CTA', async ({ page }) => {
  const sid = 'e2e-mock-approval'
  await mockSessionGet(page, sid, {
    id: sid,
    status: 'awaiting_approval',
    display_name: 'E2E approval',
    cluster: { label: 'Cluster A' },
    proposed_patch: { path: 'README.md', content: 'hello' },
    suggested_git_branch: 'docs/e2e-branch',
  })
  await page.goto(`/studio/projects/${PROJECT}/docs-health/session/${encodeURIComponent(sid)}`)
  await expect(page.getByText(/Review before apply/i).first()).toBeVisible({ timeout: 120_000 })
  const primaryBar = page.getByRole('toolbar', { name: /Primary run actions/i })
  await expect(primaryBar.getByRole('button', { name: /^Approve and apply to branch$/ })).toBeVisible()
})

test('Docs health session — post-apply shows verify banner and Re-scan CTA', async ({ page }) => {
  const sid = 'e2e-mock-applied'
  await mockSessionGet(page, sid, {
    id: sid,
    status: 'running',
    display_name: 'E2E post-apply',
    cluster: { label: 'Cluster A' },
    step_metrics: [{ step: 'apply' }],
  })
  await page.goto(`/studio/projects/${PROJECT}/docs-health/session/${encodeURIComponent(sid)}`)
  await expect(page.getByText(/Apply completed — verify next/i).first()).toBeVisible({ timeout: 120_000 })
  const primaryBar = page.getByRole('toolbar', { name: /Primary run actions/i })
  await expect(primaryBar.getByRole('button', { name: /Re-scan and verify/i })).toBeVisible()
})

test('Docs health session — completed shows View results', async ({ page }) => {
  const sid = 'e2e-mock-verified'
  await mockSessionGet(page, sid, {
    id: sid,
    status: 'completed',
    display_name: 'E2E verified',
    cluster: { label: 'Cluster A' },
    completion_summary: { verification_pipeline_ok: true },
  })
  await page.goto(`/studio/projects/${PROJECT}/docs-health/session/${encodeURIComponent(sid)}`)
  await expect(page.getByText(/Run complete/i).first()).toBeVisible({ timeout: 120_000 })
  const primaryBar = page.getByRole('toolbar', { name: /Primary run actions/i })
  await expect(primaryBar.getByRole('link', { name: /View results/i })).toBeVisible()
})
