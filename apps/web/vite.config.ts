import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const maplibreAssets = {
  name: 'maplibre-worker-assets',
  generateBundle() {
    for (const file of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) {
      this.emitFile({
        type: 'asset',
        fileName: `assets/${file}`,
        source: readFileSync(resolve('node_modules/maplibre-gl/dist', file)),
      })
    }
  },
}

export default defineConfig({
  plugins: [react(), maplibreAssets],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
