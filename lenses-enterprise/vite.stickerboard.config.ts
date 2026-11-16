import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const apiProxy = {
  target: 'http://127.0.0.1:8080',
  changeOrigin: true,
  timeout: 120000,
  proxyTimeout: 120000,
}

export default defineConfig({
  plugins: [react()],
  // Relative assets: ``/stickerboard/assets/…`` on leo, ``/assets/…`` on local :9999 root.
  base: './',
  root: __dirname,
  publicDir: false,
  build: {
    outDir: path.resolve(__dirname, '../lenses/static/stickerboard'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        index: path.resolve(__dirname, 'stickerboard-index.html'),
      },
    },
  },
  server: {
    port: 9999,
    strictPort: true,
    proxy: {
      '/api': apiProxy,
      '/__ks': apiProxy,
    },
  },
  preview: {
    port: 9999,
    proxy: {
      '/api': apiProxy,
      '/__ks': apiProxy,
    },
  },
})
