#!/usr/bin/env node
/**
 * speak-v4 数据构建：45 个统一口语场景 → frontend/public/data/speak.json
 *
 * 数据源（data-src/speak/）：
 *   curriculum_v4.json  45 个场景：每场 3 条跟读句（B1+ 完整句）+ 2 道造句题
 *   part1_85.json       85 题 Part1 问答（保留为题库原件）
 *   part1_130.json      131 条话题范文（保留）
 *   patterns.json       78 句型（造句的句型标签来源，保留）
 *   rubric.json         剑桥评分标准
 *   toc_zhen2/34.json   24-26 真题目录（原始编号，供 sourceRefs 追溯）
 *   demos.json          Part2/Part3 示范（保留）
 * 旧数据保留：free（300 句）/ plan（90 天计划）从旧站 speak-data.js 迁移。
 *
 * 用法：node tools/build_speak_v4.js [--dry]
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(ROOT, "data-src", "speak");
const LEGACY = path.join(ROOT, "..", "PET", "js", "speak-data.js");
const OUT = path.join(ROOT, "frontend", "public", "data", "speak.json");
const dry = process.argv.includes("--dry");

const read = (f) => JSON.parse(fs.readFileSync(path.join(SRC_DIR, f), "utf8"));
const curriculum = read("curriculum_v4.json");
const p85 = read("part1_85.json");
const p130 = read("part1_130.json");
const patterns = read("patterns.json");
const rubric = read("rubric.json");
const zhen2 = read("toc_zhen2.json");
const zhen34 = read("toc_zhen34.json");
const demos = read("demos.json");

// 旧 free / plan
const window = {};
new Function("window", fs.readFileSync(LEGACY, "utf8"))(window);
const S = window.PET_SPEAK;
const free = (S.free || []).map((f) => ({ id: f.id, pack: f.pack, en: f.en, cn: f.cn || "" }));
const plan = S.plan || { title: "90 天 PET 口语计划", phases: [] };

const errors = [];
const SENT_END = /[.?!]$/;
// 选句用的停用词：只保留有信息量的词作为 focus，便于与最近读错的词匹配
const STOP = new Set(
  ("a an the and or but so because if when while which who whom whose that this these those " +
    "i you he she it we they me him her us them my your his its our their " +
    "is am are was were be been being do does did can could will would shall should may might " +
    "to of in on at for from with by about into over under than then there here very really " +
    "not no yes have has had too also just some any all one two three").split(" "),
);

function wordCount(en) {
  return en.split(/\s+/).filter(Boolean).length;
}

/** 难度规则：1=A1 … 5=B2；句长为主，连接词/从句加分，图片描述类减分。 */
function difficultyOf(en, words) {
  let d = 3;
  if (words >= 12) d = 4;
  if (words >= 17) d = 5;
  if (words <= 8) d = 2;
  const lower = en.toLowerCase();
  if (/\b(because|although|however|whereas|which|while|unless|since|instead)\b/.test(lower)) d += 1;
  if (/\b(there (is|are)|in this (photo|picture)|i can see)\b/.test(lower)) d -= 1;
  return Math.max(1, Math.min(5, d));
}

/** focus：句中的实义词（供弱音素/弱词加权），最多 6 个。 */
function focusOf(en) {
  const seen = new Set();
  const out = [];
  for (const raw of en.toLowerCase().match(/[a-z']+/g) || []) {
    const w = raw.replace(/'/g, "");
    if (w.length < 4 || STOP.has(w) || seen.has(w)) continue;
    seen.add(w);
    out.push(w);
    if (out.length >= 6) break;
  }
  return out;
}

const packs = [];
const shadow = [];
const scenes = [];

const seen = new Set();
curriculum.scenes.forEach((s, idx) => {
  const sid = String(s.id || "");
  if (!/^s\d{2}$/.test(sid)) errors.push(`场景 id 非法：${sid}`);
  if (seen.has(sid)) errors.push(`场景 id 重复：${sid}`);
  seen.add(sid);
  if (![1, 2, 3].includes(s.part)) errors.push(`${sid} part 非法`);
  if (!s.title || !s.cn) errors.push(`${sid} 缺 title/cn`);
  if (!Array.isArray(s.openers) || !s.openers.length) errors.push(`${sid} 缺 openers`);

  const pack = { id: sid, name: String(s.cn || s.title), part: s.part, ids: [], order: idx + 1 };
  packs.push(pack);

  const shadowIds = [];
  (s.shadow || []).forEach((it, i) => {
    const en = String(it.en || "").trim();
    const cn = String(it.cn || "").trim();
    const tip = String(it.tip || "").trim();
    const id = `${sid}-${i + 1}`;
    if (!en || !cn) { errors.push(`${id} 缺 en/cn`); return; }
    if (!SENT_END.test(en)) errors.push(`${id} 不是完整句：${en}`);
    const words = wordCount(en);
    if (words < 8) errors.push(`${id} 句子过短：${en}`);
    const difficulty = Number.isInteger(it.difficulty) ? it.difficulty : difficultyOf(en, words);
    if (difficulty < 1 || difficulty > 5) errors.push(`${id} difficulty 应为 1-5`);
    shadow.push({
      id, pack: sid, packName: pack.name, part: s.part, en, cn, tip,
      difficulty,
      words,
      focus: Array.isArray(it.focus) ? it.focus.map(String) : focusOf(en),
      source: String(it.source || "v4-curriculum"),
      active: it.active !== false,
    });
    shadowIds.push(id);
    pack.ids.push(id);
  });
  if (shadowIds.length !== 3) errors.push(`${sid} 跟读句应为 3 条，实际 ${shadowIds.length}`);

  const make = (s.make || []).map((m, i) => {
    const out = {
      id: `${sid}-m${i + 1}`,
      prompt_cn: String(m.prompt_cn || "").trim(),
      answer: String(m.answer || "").trim(),
      pattern: String(m.pattern || "").trim(),
    };
    if (!out.prompt_cn || !out.answer) errors.push(`${out.id} 缺 prompt_cn/answer`);
    if (!SENT_END.test(out.answer)) errors.push(`${out.id} 标准答案不是完整句`);
    return out;
  });
  if (make.length !== 2) errors.push(`${sid} 造句题应为 2 道，实际 ${make.length}`);

  scenes.push({
    id: sid,
    part: s.part,
    title: pack.name,
    cn: s.cn,
    level: "B1+",
    focus: s.focus || "",
    openers: (s.openers || []).map((x) => String(x)),
    sourceRefs: (s.sourceRefs || []).map((x) => String(x)),
    source: "v4-curriculum",
    shadowIds,
    make,
  });
});

if (scenes.length !== 45) errors.push(`场景应为 45 个，实际 ${scenes.length}`);

// ---------- 造句句型库（保留原始 78 句） ----------
const patternGroups = patterns.groups.map((g) => ({
  id: g.id, part: g.part, name: g.name, cn: g.cn,
  items: g.items.map((it, i) => ({ id: `${g.id}-${i + 1}`, en: it.en, cn: it.cn || "" })),
}));

// ---------- 校验 ----------
const shadowIds = new Set(shadow.map((x) => x.id));
if (shadowIds.size !== shadow.length) errors.push("shadow id 有重复");
for (const p of packs) for (const id of p.ids) if (!shadowIds.has(id)) errors.push(`pack ${p.id} 引用不存在的 shadow ${id}`);
if (p85.items.length !== 85) errors.push(`part1_85=${p85.items.length} ≠ 85`);
if (p130.items.length !== 131) errors.push(`part1_130=${p130.items.length} ≠ 131`);
if (zhen2.items.length !== 89) errors.push(`zhen2=${zhen2.items.length} ≠ 89`);
if (zhen34.items.length !== 55) errors.push(`zhen34=${zhen34.items.length} ≠ 55`);

const out = {
  meta: {
    built: new Date().toISOString().slice(0, 10),
    schema: 5,
    sources: {
      curriculum: "curriculum_v4.json（45 场景，跟读 B1+ 完整句 + 造句题）",
      part1: p85.source, essays: p130.source, patterns: patterns.source,
      rubric: rubric.source, zhen2: zhen2.source, zhen34: zhen34.source, demos: demos.source,
    },
  },
  packs, shadow, free, scenes, plan,
  part1bank: p85.items.map((it) => ({ no: it.no, q: it.q, cn: it.cn, ans: it.ans })),
  categories: p85.categories,
  essays: p130.items.map((it) => ({ no: String(it.no), q: it.q, ans: it.ans })),
  patterns: patternGroups,
  rubric: { global: rubric.global, dims: rubric.dims, note: rubric.note },
  zhen2: zhen2.items,
  zhen34: zhen34.items,
};

console.log(`校验: ${errors.length ? errors.join("\n") : "0 问题"}`);
console.log(
  `统计: scenes=${scenes.length}(P1:${scenes.filter((s) => s.part === 1).length}/P2:${scenes.filter((s) => s.part === 2).length}/P3:${scenes.filter((s) => s.part === 3).length}) ` +
  `packs=${packs.length} shadow=${shadow.length} make=${scenes.reduce((a, s) => a + s.make.length, 0)} ` +
  `patterns=${patternGroups.reduce((a, g) => a + g.items.length, 0)}句/${patternGroups.length}组 free=${free.length}`
);
if (dry) { console.log("(dry run, 未写入)"); process.exit(errors.length ? 1 : 0); }
if (errors.length) process.exit(1);
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out));
console.log(`写入 ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)}KB)`);
