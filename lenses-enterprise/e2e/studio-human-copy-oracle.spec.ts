import { test, expect } from '@playwright/test'

/** Routes checked for human-facing copy — no API paths, ports, or internal jargon in default chrome. */
const CORE_ROUTES = [
  '/studio/',
  '/studio/projects',
  '/studio/plan',
  '/studio/settings/llm',
  '/studio/knowledge/methodology/evidence',
] as const

const FORBIDDEN_RE = /(GET \/api|:8080|workspace-md|ogs:demo|Trace sample)/i

test.describe('Studio human-copy oracle', () => {
  for (const route of CORE_ROUTES) {
    test(`no jargon on ${route}`, async ({ page }) => {
      await page.goto(route, { waitUntil: 'domcontentloaded' })
      await page.waitForFunction(
        () => {
          const t = document.body?.innerText ?? ''
          return !t.includes('Receiving workspace') && !t.includes('Scanning workspace')
        },
        { timeout: 120_000 },
      )
      const bodyText = await page.locator('body').innerText()
      expect(bodyText).not.toMatch(FORBIDDEN_RE)
    })
  }
})
