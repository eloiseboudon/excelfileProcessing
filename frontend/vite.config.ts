/// <reference types="vitest" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  root: './',
  build: {
    outDir: 'build',
    sourcemap: false,
    minify: 'esbuild',
    emptyOutDir: true
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    strictPort: true
  }
})