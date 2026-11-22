/**
 * 阅读数据迁移：旧站 PET/js/reading-data.js（window.PET_GRAMMAR + window.PET_READING）
 * → frontend/public/data/reading.json
 *
 * 校验项：id 唯一 / key∈en / gram.c∈1-42 / parse≥3 / gq 四选项+答案合法+why / quiz 题型合法
 * 规范化：test3-6 缺 no（源 dict 用 "test" 字段，合并脚本丢包了）→ 从 title 或 test 回填
 *
 * 用法：node tools/build_reading_v2.js [--dry]
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "..", "PET", "js", "reading-data.js");
const OUT = path.join(ROOT, "frontend", "public", "data", "reading.json");
const DRY = process.argv.includes("--dry");

// ---------- 读旧站数据 ----------
const code = fs.readFileSync(SRC, "utf8");
const sandbox = { window: {} };
new Function("window", code)(sandbox.window);
const GRAMMAR = sandbox.window.PET_GRAMMAR;
const RD = sandbox.window.PET_READING;

const CNAME = {};
GRAMMAR.days.forEach((d) => d.points.forEach((p) => { CNAME[p.c] = p.name; }));

const problems = [];
const seenIds = new Set();

function checkSentence(s, where) {
  const tag = `${where}:${s.id || "?"}`;
  if (!s.id) problems.push(`${tag} 缺 id`);
  if (seenIds.has(s.id)) problems.push(`${tag} id 重复`);
  seenIds.add(s.id);
  if (!s.en || !s.en.trim()) problems.push(`${tag} en 为空`);
  if (!s.cn || !s.cn.trim()) problems.push(`${tag} cn 为空`);
  if (s.key && s.en.indexOf(s.key) < 0) problems.push(`${tag} key 不在 en 中 -> ${s.key}`);
  if (!Array.isArray(s.gram) || !s.gram.length) problems.push(`${tag} 缺 gram`);
  else s.gram.forEach((g) => { if (!CNAME[g.c]) problems.push(`${tag} 考点编号非法 ${g.c}`); });
  if (!Array.isArray(s.parse) || s.parse.length < 3) problems.push(`${tag} parse 少于 3 块`);
  if (!Array.isArray(s.gq) || !s.gq.length) problems.push(`${tag} 缺 gq`);
  else s.gq.forEach((q, i) => {
    if (!Array.isArray(q.opts) || q.opts.length !== 4) problems.push(`${tag} gq${i} 不是 4 个选项`);
    if (typeof q.a !== "number" || q.a < 0 || q.a > 3) problems.push(`${tag} gq${i} 答案下标非法`);
    if (!q.why) problems.push(`${tag} gq${i} 缺 why`);
    if (q.c == null || !CNAME[q.c]) problems.push(`${tag} gq${i} 缺考点编号`);
  });
  (s.quiz || []).forEach((t) => {
    if (["meaning", "blank", "grammar"].indexOf(t) < 0) problems.push(`${tag} 未知题型 ${t}`);
  });
}

// ---------- 规范化 tests ----------
const tests = RD.tests.map((t, i) => {
  // no 回填：源里 test3-6 的编号在 "test" 字段或 title 中
  let no = t.no;
  if (no == null) {
    const m = /Test\s*(\d+)/.exec(t.title || "");
    no = m ? Number(m[1]) : i + 1;
    if (t.book !== "t1") no = t.test != null ? t.test : no;
  }
  return { ...t, no };
});

tests.forEach((t) => {
  if (!Array.isArray(t.parts) || !t.parts.length) problems.push(`test ${t.no} 无 parts`);
  t.parts.forEach((p) => (p.sentences || []).forEach((s) => checkSentence(s, `t${t.book}#${t.no}`)));
  // id 应含 test 编号段：t1 书为 1xx 开头，t2 为 1-6 开头（仅警告级别，不阻断）
});

// ---------- meta / 考点覆盖 ----------
const stat = {};
let total = 0, gqTotal = 0;
tests.forEach((t) => t.parts.forEach((p) => p.sentences.forEach((s) => {
  total += 1;
  gqTotal += (s.gq || []).length;
  (s.gram || []).forEach((g) => { stat[g.c] = (stat[g.c] || 0) + 1; });
})));
const miss = [];
for (let c = 1; c <= 42; c++) if (!stat[c]) miss.push(c);

const out = {
  grammar: GRAMMAR,
  books: RD.books,
  tests,
  meta: {
    sentences: total,
    gq: gqTotal,
    points_covered: Object.keys(stat).length,
    points_missing: miss,
    built: new Date().toISOString().slice(0, 10),
    source: "PET/js/reading-data.js (build_reading.js 产物)",
  },
};

console.log(`books ${out.books.length}，tests ${tests.length}，句子 ${total}，语法题 ${gqTotal}，考点覆盖 ${Object.keys(stat).length}/42`);
if (miss.length) console.log("未覆盖考点：", miss.join(","));
if (problems.length) {
  console.log(`问题 ${problems.length} 条：`);
  problems.slice(0, 30).forEach((p) => console.log("  - " + p));
  if (problems.length > 30) console.log("  ...");
}
if (problems.some((p) => !p.includes("（警告）"))) {
  console.log("校验未通过，未写文件。");
  process.exit(1);
}
if (DRY) { console.log("（dry run，未写文件）"); process.exit(0); }

fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out, null, 1), "utf8");
console.log(`已写入 ${path.relative(ROOT, OUT)}，大小 ${(fs.statSync(OUT).size / 1024).toFixed(0)} KB`);
