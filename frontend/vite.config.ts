import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Docker 开发环境里 api 是服务名；本机直接跑 vite 时用默认的 localhost:8000
const apiTarget = process.env.VITE_API_TARGET || "http://localhost:8000";
// Docker Desktop（macOS/Windows）文件事件偶尔丢失时，用 DEV_POLL=1 开轮询
const usePolling = (process.env.VITE_USE_POLLING ?? "").toLowerCase();
const polling = usePolling === "1" || usePolling === "true";

export default defineConfig({
  plugins: [vue()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": apiTarget,
      "/media": apiTarget,
    },
    watch: {
      // 85MB 音频不会改动，排除后 HMR 更轻
      ignored: ["**/public/audio/**"],
      usePolling: polling,
    },
  },
  build: {
    outDir: "dist",
    assetsInlineLimit: 0,
    // dist 内有 85MB 音频（public/ 拷贝），避免每次构建清空整个目录
    emptyOutDir: false,
  },
  test: {
    environment: "jsdom",
  },
});
