#!/usr/bin/env node
/**
 * 数学课程清单构建：data-src/math/yongle_grade3.json → frontend/public/data/math.json
 *
 * 用法：node tools/build_math.js
 * 产物由 vite 拷贝到 dist/data/，部署时随 dist 上传；public/data 不入 git。
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "data-src/math/yongle_grade3.json");
const OUT = path.join(ROOT, "frontend/public/data/math.json");

function fail(msg) {
  console.error(`[×] ${msg}`);
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(SRC, "utf8"));
if (!Array.isArray(data.series) || data.series.length === 0) fail("series 不能为空");

const seen = new Set();
let total = 0;
for (const s of data.series) {
  for (const k of ["id", "title", "gradeName", "mediaDir"]) {
    if (!s[k]) fail(`series 缺少 ${k}`);
  }
  if (!Array.isArray(s.lessons) || s.lessons.length === 0) fail(`${s.id} lessons 不能为空`);
  for (const l of s.lessons) {
    for (const k of ["id", "no", "title", "tag", "group", "file"]) {
      if (!l[k]) fail(`${s.id}/${l.id ?? "?"} 缺少 ${k}`);
    }
    if (!/\.mp4$/i.test(l.file)) fail(`${l.id} 只支持 mp4：${l.file}`);
    if (seen.has(l.id)) fail(`课程 id 重复：${l.id}`);
    seen.add(l.id);
    total += 1;
  }
  // 按课号数值排序（43 < 43.1 < 43.2 < 44）
  s.lessons.sort((a, b) => Number(a.no) - Number(b.no) || String(a.no).localeCompare(String(b.no)));
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(data, null, 2) + "\n", "utf8");
console.log(`[✓] ${OUT}（${data.series.length} 个系列 / ${total} 节课）`);
