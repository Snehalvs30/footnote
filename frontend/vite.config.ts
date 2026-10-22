import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server forwards /api/* to FastAPI, which serves every route under /api,
// so the browser sees one origin (no CORS setup needed). In production, FastAPI
// serves this app itself, and the paths are identical.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})