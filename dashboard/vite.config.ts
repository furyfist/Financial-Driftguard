import { defineConfig, loadEnv } from "vite"
import react from "@vitejs/plugin-react"

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "")
  const apiUrl = env.VITE_API_URL || "http://localhost:8000"

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api-proxy": {
          target: apiUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api-proxy/, ""),
        },
      },
    },
  }
})
