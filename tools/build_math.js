#!/usr/bin/env node
/**
 * 数学课程清单构建：data-src/math/yongle.json → frontend/public/data/math.json
 *
 * 用法：node tools/build_math.js
 * 产物由 vite 拷贝到 dist/data/，部署时随 dist 上传；public/data 不入 git。
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "data-src/math/yongle.json");
const OUT = path.join(ROOT, "frontend/public/data/math.json");

function fail(msg) {
  console.error(`[×] ${msg}`);
  process.exit(1);
}

const data = JSON.parse(fs.readFileSync(SRC, "utf8"));
if (!data.course?.id || !data.course?.title) fail("course.id / course.title 不能为空");
if (!Array.isArray(data.books) || data.books.length === 0) fail("books 不能为空");

const seen = new Set();
let total = 0;
for (const b of data.books) {
  for (const k of ["id", "gradeName", "mediaDir"]) {
    if (!b[k]) fail(`教材缺少 ${k}`);
  }
  if (!Number.isInteger(b.grade) || b.grade < 1) fail(`${b.id} grade 必须是正整数`);
  if (!Array.isArray(b.lessons)) fail(`${b.id} lessons 必须是数组`);
  if (!b.comingSoon && b.lessons.length === 0) fail(`${b.id} 未上线教材不能没有课程`);
  for (const l of b.lessons) {
    // tag 允许为空：文件名没标注难度时不显示胶囊，不臆造难度
    for (const k of ["id", "no", "title", "group", "file"]) {
      if (!l[k]) fail(`${b.id}/${l.id ?? "?"} 缺少 ${k}`);
    }
    if (typeof l.tag !== "string") fail(`${b.id}/${l.id ?? "?"} tag 必须是字符串（可为空）`);
    if (!/\.mp4$/i.test(l.file)) fail(`${l.id} 只支持 mp4：${l.file}`);
    if (seen.has(l.id)) fail(`课程 id 重复（跨年级也要唯一）：${l.id}`);
    seen.add(l.id);
    total += 1;
  }
  // 按课号数值排序（43 < 43.1 < 43.2 < 44）；非数字课号（如「练」）排最后
  const key = (l) => {
    const n = Number(l.no);
    return Number.isFinite(n) ? [0, n] : [1, 0];
  };
  b.lessons.sort((a, c) => {
    const [ga, na] = key(a);
    const [gc, nc] = key(c);
    return ga - gc || na - nc || String(a.no).localeCompare(String(c.no));
  });
}

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(data, null, 2) + "\n", "utf8");
console.log(`[✓] ${OUT}（${data.course.title}：${data.books.length} 本教材 / ${total} 节课）`);
