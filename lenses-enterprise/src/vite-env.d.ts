/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_EXPERIMENTAL_BLUEPRINTS_WIZARD?: string
}

declare module 'virtual:studio-build-meta' {
  /** App semver from `package.json` when the bundle was built. */
  export const studioVersion: string
  /** Short git SHA from `lenses-enterprise/`, or `unknown`. */
  export const studioBuildCommit: string
  /** ISO-8601 UTC timestamp when the bundle was produced. */
  export const studioBuildTime: string
}

declare module '*.sh?raw' {
  const src: string
  export default src
}

declare module '*.md?raw' {
  const src: string
  export default src
}
