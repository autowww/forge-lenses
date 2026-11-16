import type { Plugin } from 'vite'
import path from 'node:path'
import { readFileSync, writeFileSync } from 'node:fs'
import { execSync } from 'node:child_process'

/** Public id importers use; Rollup resolves to `VIRTUAL_ID`. */
export const STUDIO_BUILD_META_MODULE = 'virtual:studio-build-meta' as const
const VIRTUAL_ID = '\0' + STUDIO_BUILD_META_MODULE

export type StudioBuildMeta = {
  studioVersion: string
  studioBuildCommit: string
  studioBuildTime: string
}

/** Fresh metadata from package.json, git, and clock (call on each bundle build). */
export function computeStudioBuildMeta(projectRoot: string): StudioBuildMeta {
  const pkgPath = path.resolve(projectRoot, 'package.json')
  const pkg = JSON.parse(readFileSync(pkgPath, 'utf-8')) as { version?: string }
  const studioVersion = typeof pkg.version === 'string' ? pkg.version : '0.0.0'
  let studioBuildCommit = 'unknown'
  try {
    studioBuildCommit = execSync('git rev-parse --short HEAD', {
      cwd: projectRoot,
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim()
  } catch {
    /* shallow clone, missing .git, or git not on PATH */
  }
  const studioBuildTime = new Date().toISOString()
  return { studioVersion, studioBuildCommit, studioBuildTime }
}

function virtualModuleSource(m: StudioBuildMeta): string {
  return [
    `export const studioVersion = ${JSON.stringify(m.studioVersion)};`,
    `export const studioBuildCommit = ${JSON.stringify(m.studioBuildCommit)};`,
    `export const studioBuildTime = ${JSON.stringify(m.studioBuildTime)};`,
  ].join('\n')
}

/**
 * Serves Studio semver + git short SHA + UTC build time via a virtual module, and
 * invalidates it on each Rollup `buildStart` so `vite build --watch` picks up a new
 * timestamp (and commit when HEAD moves) every rebuild — unlike static `define`, which
 * is fixed for the lifetime of the Vite process.
 */
export function studioBuildMetaPlugin(projectRoot: string): Plugin {
  /** Meta for the bundle currently being emitted (virtual `load` + sidecar JSON stay in sync). */
  let bundleMetaForOutput: StudioBuildMeta | null = null
  return {
    name: 'studio-build-meta',
    enforce: 'pre',
    resolveId(id) {
      if (id === STUDIO_BUILD_META_MODULE) return VIRTUAL_ID
    },
    load(id) {
      if (id !== VIRTUAL_ID) return null
      bundleMetaForOutput = computeStudioBuildMeta(projectRoot)
      return virtualModuleSource(bundleMetaForOutput)
    },
    buildStart() {
      // Rollup watch / production build; Vitest dev server has no `invalidate`.
      ;(this as { invalidate?: (id: string) => void }).invalidate?.(VIRTUAL_ID)
    },
    writeBundle(options) {
      if (process.env.VITEST) return
      const dir = options.dir
      if (!dir || !bundleMetaForOutput) return
      const outPath = path.join(dir, 'studio-build-meta.json')
      writeFileSync(outPath, `${JSON.stringify(bundleMetaForOutput, null, 2)}\n`, 'utf-8')
    },
  }
}
