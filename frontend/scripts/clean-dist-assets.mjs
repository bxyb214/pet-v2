/**
 * 只清理 dist/assets，不碰 dist/audio、dist/data、dist/img。
 * 配合 vite emptyOutDir:false 使用：避免每次构建重拷 85MB 音频，
 * 同时清掉历史构建留下的哈希 JS/CSS（否则每次发布都会带上几十 MB 僵尸文件）。
 */
import { rmSync } from "node:fs";
import { resolve } from "node:path";

const dir = resolve(process.cwd(), "dist", "assets");
rmSync(dir, { recursive: true, force: true });
console.log(`[clean] removed ${dir}`);
