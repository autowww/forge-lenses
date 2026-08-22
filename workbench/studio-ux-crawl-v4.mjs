#!/usr/bin/env node
/**
 * Forge Lenses Studio UX crawl v4 — post FLS3 UX3 PDCA remediation.
 * Usage: node workbench/studio-ux-crawl-v4.mjs [baseUrl]
 * Output: workbench/studio-ux-crawl-v4/report.json
 */
import { createRequire } from 'module'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const require = createRequire(path.join(__dirname, '../lenses-enterprise/package.json'))
const { chromium } = require('@playwright/test')
const BASE = (process.argv[2] || 'http://127.0.0.1:8080/studio').replace(/\/$/, '')
const OUT_DIR = path.join(__dirname, 'studio-ux-crawl-v4')
const REPORT = path.join(OUT_DIR, 'report.json')

const ROUTES = [
  '/',
  '/projects',
  '/plan',
  '/plan/matrix',
  '/timeline',
  '/board',
  '/search',
  '/chat',
  '/settings/llm',
  '/settings/fleet',
  '/knowledge/methodology/evidence',
  '/knowledge/agentic-bridge',
  '/tutorials',
  '/websites',
  '/doc-management',
  '/autonomy-maturity',
]

const TECHNICAL_RE =
  /\b(workspace snapshot|GET \/api|\/api\/|:8080|workspace-md|ogs:demo|Trace sample|scan_only|local_fixture|Legacy UI|Classic UI)\b/gi

function uniq(arr) {
  return [...new Set(arr.filter(Boolean))]
}

async function extractPage(page) {
  return page.evaluate(() => {
    const text = (el) => (el?.innerText || '').trim()
    const visible = (el) => {
      if (!el) return false
      const s = getComputedStyle(el)
      return s.display !== 'none' && s.visibility !== 'hidden' && s.opacity !== '0'
    }
    const h1 = [...document.querySelectorAll('h1')].filter(visible).map(text)
    const bodyText = text(document.body).slice(0, 6000)
    const onSplash = bodyText.includes('Receiving workspace') || bodyText.includes('Scanning workspace')
    const hasSparseGuide = bodyText.includes("What you'll see with a multi-repo workspace")
    const matrixRich = bodyText.includes('Roadmap matrix') && bodyText.length > 800
    return {
      title: document.title,
      h1,
      bodyLen: text(document.body).length,
      onSplash,
      hasSparseGuide,
      matrixRich,
      bodyPreview: bodyText.slice(0, 1200),
    }
  })
}

function analyze(route, data) {
  const techHits = uniq((data.bodyPreview.match(TECHNICAL_RE) || []).map((s) => s))
  const issues = []
  if (data.onSplash) issues.push('stuck_on_splash')
  if (techHits.length) issues.push('technical_jargon')
  if (!data.h1.length && !data.onSplash) issues.push('missing_h1')
  if (route === '/plan/matrix' && !data.matrixRich && !data.onSplash) issues.push('matrix_sparse')
  if (data.bodyLen < 300 && !data.onSplash && !data.hasSparseGuide) issues.push('sparse')
  return { techHits, issues }
}

fs.mkdirSync(OUT_DIR, { recursive: true })

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
page.setDefaultTimeout(45000)

const results = []
let splashCleared = false

for (const route of ROUTES) {
  const url = BASE + (route === '/' ? '/' : route)
  const entry = { route, url, ok: false, data: null, analysis: null, error: null }
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 })
    await page.waitForTimeout(2500)
    const data = await extractPage(page)
    entry.ok = true
    entry.data = data
    entry.analysis = analyze(route, data)
    if (!data.onSplash && route === '/') splashCleared = true
  } catch (e) {
    entry.error = String(e)
  }
  results.push(entry)
  console.log(JSON.stringify({ route, issues: entry.analysis?.issues, splash: entry.data?.onSplash }))
}

await browser.close()

const summary = {
  capturedAt: new Date().toISOString(),
  base: BASE,
  splashCleared,
  routeCount: results.length,
  jargonRoutes: results.filter((r) => r.analysis?.issues?.includes('technical_jargon')).map((r) => r.route),
  splashRoutes: results.filter((r) => r.analysis?.issues?.includes('stuck_on_splash')).map((r) => r.route),
  sparseRoutes: results.filter((r) => r.analysis?.issues?.includes('sparse')).map((r) => r.route),
  matrixSparseRoutes: results.filter((r) => r.analysis?.issues?.includes('matrix_sparse')).map((r) => r.route),
  results,
}

fs.writeFileSync(REPORT, JSON.stringify(summary, null, 2))
console.log('WROTE', REPORT)
console.log('splashCleared', splashCleared)
