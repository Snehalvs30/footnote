import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The dev server forwards /api/* to FastAPI, so the browser sees one origin
// (no CORS setup needed). /api/documents -> http://127.0.0.1:8000/documents
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})