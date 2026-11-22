import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
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
