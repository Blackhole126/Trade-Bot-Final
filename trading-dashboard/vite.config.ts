import path from 'path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: '/', // required for SPA: asset URLs must be root-absolute so /market-scan etc. load JS/CSS correctly
  plugins: [react()],
  publicDir: 'public',
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    host: true,
    open: false,
  },
})










