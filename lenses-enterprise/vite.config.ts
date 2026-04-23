import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { studioBuildMetaPlugin } from './vite-plugin-studio-build-meta'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/** Long-running POSTs (e.g. Docs Health markdown scan) must not hit the proxy default ~120s socket timeout. */
const apiProxy = {
  target: 'http://127.0.0.1:8080',
  changeOrigin: true,
  /** ms — deterministic scans on large repos can exceed 2–3 minutes behind this proxy. */
  timeout: 900000,
  proxyTimeout: 900000,
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [studioBuildMetaPlugin(__dirname), react(), tailwindcss()],
  base: '/studio/',
  build: {
    outDir: path.resolve(__dirname, '../lenses/static/studio'),
    emptyOutDir: true,
  },
  // Single-port workflow: run `python3 -m lenses` (default :8080), open /studio/, and use
  // `npm run watch` to rebuild the SPA into ../lenses/static/studio on file changes.
  // When using `npm run dev` (Vite :5173), proxy API routes to the Python server so
  // `/api/llm/chat` is not 404 — start Lenses on :8080 in another terminal.
  /** Classic Lenses routes + kitchensink assets — proxied so sidebar links work on :5173 (Python on :8080). */
  server: {
    proxy: {
      '/api': apiProxy,
      '/roadmaps': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/plan': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/wbs': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/timeline': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/workspace-md': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/__ks': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
  preview: {
    proxy: {
      '/api': apiProxy,
      '/roadmaps': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/plan': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/wbs': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/timeline': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/workspace-md': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
      '/__ks': {
        target: 'http://127.0.0.1:8080',
        changeOrigin: true,
      },
    },
  },
})
