import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // binds to 0.0.0.0 so both localhost and 127.0.0.1 work
    port: 5173,
  },
})
