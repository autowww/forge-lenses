#!/usr/bin/env node
/**
 * Increments MAJOR.MINOR.PATCH → PATCH+1 in package.json before `vite build`.
 * Set SKIP_STUDIO_VERSION_BUMP=1 (or true) to skip (e.g. CI that only checks compile).
 */
import { readFileSync, writeFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const skip = process.env.SKIP_STUDIO_VERSION_BUMP
if (skip === '1' || skip === 'true') {
  console.log('[bump-studio-version] SKIP_STUDIO_VERSION_BUMP set; leaving version unchanged.')
  process.exit(0)
}

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..')
const pkgPath = path.join(root, 'package.json')
const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'))
const v = pkg.version
if (typeof v !== 'string') {
  console.error('[bump-studio-version] package.json has no string "version".')
  process.exit(1)
}

const m = v.match(/^(\d+)\.(\d+)\.(\d+)/)
if (!m) {
  console.error(
    `[bump-studio-version] Cannot bump "${v}" — expected to start with MAJOR.MINOR.PATCH (digits only).`,
  )
  process.exit(1)
}

const major = m[1]
const minor = m[2]
const patch = String(parseInt(m[3], 10) + 1)
const tail = v.slice(m[0].length)
const newVersion = `${major}.${minor}.${patch}${tail}`

pkg.version = newVersion
writeFileSync(pkgPath, `${JSON.stringify(pkg, null, 2)}\n`, 'utf8')
console.log(`[bump-studio-version] ${v} → ${newVersion}`)
