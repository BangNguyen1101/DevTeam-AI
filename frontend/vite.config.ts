import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The backend is reached through the dev proxy, so the browser only ever talks to
// the Vite origin and no backend secrets/config live in the frontend bundle.
const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': BACKEND_URL,
      '/ws': { target: BACKEND_URL, ws: true },
    },
  },
})
