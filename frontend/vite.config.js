import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Cấu hình Vite: plugin React + proxy API tới FastAPI cổng 8000 (tránh CORS khi dev).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
      "/ws": {
        target: "ws://127.0.0.1:8000",
        ws: true,
      },
    },
  },
});
