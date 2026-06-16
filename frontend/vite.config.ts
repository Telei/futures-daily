import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 前端开发服务器；/api 代理到后端 FastAPI（默认 8000 端口）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
