import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// CareLoop frontend — Alexa+-style simulated voice experience.
// API base URL is configurable: VITE_API_URL (defaults to http://localhost:8000)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
})
