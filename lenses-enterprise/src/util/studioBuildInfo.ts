import {
  studioBuildCommit,
  studioBuildTime,
  studioVersion,
} from 'virtual:studio-build-meta'

export function getStudioVersion(): string {
  return studioVersion
}

export function getStudioBuildCommit(): string {
  return studioBuildCommit
}

export function getStudioBuildTime(): string {
  return studioBuildTime
}

/**
 * One line for About / support: semver, git short SHA (or `no-git`), and UTC build
 * timestamp — changes on every bundle rebuild even when `package.json` is unchanged.
 */
export function getStudioAboutVersionLine(): string {
  const v = getStudioVersion()
  const c = getStudioBuildCommit()
  const t = getStudioBuildTime()
  const commitPart = c && c !== 'unknown' ? c : 'no-git'
  const timePart = t || '—'
  return `${v} · ${commitPart} · ${timePart}`
}

/**
 * Splash footer: `v{semver} · {commit|no-git} · {ISO UTC}` — same bundle identity as
 * About, so the line changes every rebuild even when release semver stays `1.0.0`.
 */
export function studioSplashBuildLine(): string {
  const v = getStudioVersion()
  const c = getStudioBuildCommit()
  const t = getStudioBuildTime()
  const commitPart = c && c !== 'unknown' ? c : 'no-git'
  const timePart = t || '—'
  return `v${v} · ${commitPart} · ${timePart}`
}

/** One-line footer: version and short commit when known. */
export function studioBuildFooterLine(): string {
  const v = getStudioVersion()
  const c = getStudioBuildCommit()
  if (c && c !== 'unknown') return `Forge Studio ${v} · ${c}`
  return `Forge Studio ${v}`
}

/** Tooltip / support copy with full build metadata. */
export function studioBuildDetails(): string {
  const t = getStudioBuildTime()
  const base = `${studioBuildFooterLine()}`
  return t ? `${base}\nBuilt: ${t} (UTC)` : base
}
