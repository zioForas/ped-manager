import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Build servito da Flask: gli asset stanno sotto /static/spa/, l'app è servita
// da Flask su qualunque rotta non-API (vedi webapp/app.py).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: '/static/spa/',
  build: {
    outDir: '../webapp/static/spa',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://localhost:7777',
      '/design': 'http://localhost:7777',
      '/story-media': 'http://localhost:7777',
      '/pdf': 'http://localhost:7777',
    },
  },
})
