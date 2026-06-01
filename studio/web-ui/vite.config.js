import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Backend default port is 8077 (8000 is the LLM server's port).
      '/api': {
        target: 'http://localhost:8077',
        changeOrigin: true,
      },
    },
  },
})
