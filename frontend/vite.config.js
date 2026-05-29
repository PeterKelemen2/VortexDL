import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '') // load all vars, not just VITE_*
  const BACKEND_PROXY_TARGET = env.BACKEND_PROXY_URL || 'http://localhost:8000'

  return {
    plugins: [
      vue(),
      tailwindcss(),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      },
    },
    server: {
      host: true,
      proxy: {
        '/auth': {
          target: BACKEND_PROXY_TARGET,
          changeOrigin: true,
        },
        '/admin': {
          target: BACKEND_PROXY_TARGET,
          changeOrigin: true,
        },
        '/uploads': {
          target: BACKEND_PROXY_TARGET,
          changeOrigin: true,
        },
      },
    },
  }
})
