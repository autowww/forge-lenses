import { defineConfig, devices } from '@playwright/test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const port = process.env.E2E_LENSES_PORT ?? '17555'
const origin = `http://127.0.0.1:${port}`

/**
 * Docs Health scan E2E: starts Lenses + disposable workspace (see scripts/e2e-lenses-with-fixture.sh).
 * Uses a fixed default port; override with E2E_LENSES_PORT if 17555 is busy.
 *
 * **baseURL must be origin-only:** Playwright resolves `page.goto('/projects/…')` against baseURL by replacing
 * the path when the argument starts with `/`, so `baseURL` with a `/studio` path would incorrectly open
 * `/projects/…` (404) instead of `/studio/projects/…`.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  timeout: 180_000,
  expect: { timeout: 30_000 },
  use: {
    baseURL: origin,
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `bash "${path.join(__dirname, 'scripts', 'e2e-lenses-with-fixture.sh')}"`,
    cwd: __dirname,
    url: `${origin}/api/workspace-state`,
    timeout: 300_000,
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    stderr: 'pipe',
    env: {
      ...process.env,
      E2E_LENSES_PORT: port,
      LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH: process.env.LENSES_EXPERIMENTAL_ORCHESTRATION_GRAPH ?? '1',
      LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3: process.env.LENSES_EXPERIMENTAL_AGENTIC_BRIDGE_B3 ?? '1',
      LENSES_EXPERIMENTAL_FOUNDRY: process.env.LENSES_EXPERIMENTAL_FOUNDRY ?? '1',
      FOUNDRY_DARK_FACTORY_ROOT: process.env.FOUNDRY_DARK_FACTORY_ROOT ?? path.join(__dirname, '..', '..', '..', 'forge-dark-factory'),
    },
  },
})
