#!/usr/bin/env node
/**
 * listening-v2 数据迁移：
 *   旧 PET/js/listening-data.js (window.PET_LISTENING) → frontend/public/data/listening.json
 * 媒体文件（audio/img）由 deploy 阶段整目录拷贝，不在本脚本职责内。
 *
 * 用法：node tools/build_listening_v2.js [--dry]
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "..", "PET", "js", "listening-data.js");
const OUT = path.join(ROOT, "frontend", "public", "data", "listening.json");
const dry = process.argv.includes("--dry");

const window = {};
new Function("window", fs.readFileSync(SRC, "utf8"))(window);
const L = window.PET_LISTENING;

// ---- 规范化 ----
const errors = [];
const tests = (L.tests || []).map((t) => ({
  no: t.no,
  book: t.book || "t1",
  title: t.title || `Test ${t.no}`,
  duration: t.duration || 0,
  parts: (t.parts || []).map((p) => ({
    part: p.part,
    qRange: p.qRange || "",
    label: p.label || "",
    kind: p.kind,
    audio: normAudio(p.audio),
    duration: p.duration || 0,
    transcript: p.transcript || "",
    // 旧数据存在少量 t0 乱序（OCR 时间轴拼接所致），规范化为升序
    sentences: (p.sentences || [])
      .map((s) => ({ t0: s.t0, t1: s.t1 ?? null, text: s.text, no: s.no ?? null }))
      .sort((a, b) => a.t0 - b.t0),
    items: (p.items || []).map((it) => ({
      no: it.no,
      stem: it.stem,
      answer: it.answer,
      img: it.img ? normImg(it.img) : null,
      options: it.options || null,
      t0: it.t0 || 0,
    })),
  })),
}));

function normAudio(a) {
  if (!a) return "";
  return "/" + String(a).replace(/^\/+/, "").replace(/^audio\//, "audio/");
}
function normImg(a) {
  return "/" + String(a).replace(/^\/+/, "").replace(/^img\//, "img/");
}

// ---- 校验 ----
let counts = { picture: 0, choice: 0, fill: 0 };
for (const t of tests) {
  for (const p of t.parts) {
    const tag = `t${t.no}p${p.part}`;
    if (!["picture", "choice", "fill"].includes(p.kind)) errors.push(`${tag} kind 非法: ${p.kind}`);
    if (!p.audio) errors.push(`${tag} 缺 audio`);
    if (!p.transcript) errors.push(`${tag} 缺 transcript`);
    if (!p.items.length) errors.push(`${tag} 无题`);
    for (const it of p.items) {
      counts[p.kind] = (counts[p.kind] || 0) + 1;
      if (p.kind === "choice" && (!it.options || it.options.length !== 3)) errors.push(`${tag}q${it.no} choice 选项≠3`);
      if (p.kind === "choice" && (typeof it.answer !== "number" || it.answer < 0 || it.answer > 2)) errors.push(`${tag}q${it.no} choice answer 非法`);
      if (p.kind === "picture" && !it.img) errors.push(`${tag}q${it.no} picture 缺 img`);
      if (p.kind === "fill" && typeof it.answer !== "string") errors.push(`${tag}q${it.no} fill answer 非字符串`);
      if (p.kind !== "fill" && typeof it.answer === "string") errors.push(`${tag}q${it.no} 非填空 answer 不应为字符串`);
    }
    // 字幕按 t0 升序
    for (let i = 1; i < p.sentences.length; i++) {
      if (p.sentences[i].t0 < p.sentences[i - 1].t0) { errors.push(`${tag} 字幕 t0 非升序 @${i}`); break; }
    }
  }
}
// 音频文件存在性
for (const t of tests) {
  for (const p of t.parts) {
    const f = path.join(ROOT, "frontend", "public", p.audio.slice(1));
    if (!fs.existsSync(f)) errors.push(`音频不存在: ${p.audio}`);
  }
}
// 图片存在性
for (const t of tests) for (const p of t.parts) for (const it of p.items) {
  if (it.img) {
    const f = path.join(ROOT, "frontend", "public", it.img.slice(1));
    if (!fs.existsSync(f)) errors.push(`图片不存在: ${it.img}`);
  }
}

const itemTotal = tests.reduce((a, t) => a + t.parts.reduce((b, p) => b + p.items.length, 0), 0);
const partTotal = tests.reduce((a, t) => a + t.parts.length, 0);
if (tests.length !== 6) errors.push(`tests=${tests.length} ≠ 6`);
if (partTotal !== 24) errors.push(`parts=${partTotal} ≠ 24`);
if (itemTotal !== 150) errors.push(`items=${itemTotal} ≠ 150`);

const out = {
  books: L.books || [{ id: "t1", name: "Trainer 1", desc: "2020 改版官方真题训练 1（6 套）" }],
  tests,
  meta: {
    tests: tests.length,
    parts: partTotal,
    items: itemTotal,
    items_by_kind: counts,
    sentences: tests.reduce((a, t) => a + t.parts.reduce((b, p) => b + p.sentences.length, 0), 0),
    built: new Date().toISOString().slice(0, 10),
  },
};

console.log(`校验: ${errors.length ? errors.join("\n") : "0 问题"}`);
console.log(`统计: tests=${tests.length} parts=${partTotal} items=${itemTotal} kinds=${JSON.stringify(counts)} sentences=${out.meta.sentences}`);
if (dry) { console.log("(dry run, 未写入)"); process.exit(errors.length ? 1 : 0); }
if (errors.length) process.exit(1);
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out));
console.log(`写入 ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)}KB)`);
