#!/usr/bin/env node
/**
 * speak-v3 数据构建：PET 官方口语教辅 → frontend/public/data/speak.json
 *
 * 数据源（data-src/speak/）：
 *   part1_85.json   85 题 Part1 问答（题目+译文+参考答案）+ 17 分类   [脚本解析自文本层]
 *   part1_130.json  131 条话题范文                                    [脚本解析自文本层]
 *   patterns.json   四部分句型库（造句模块核心）
 *   rubric.json     剑桥评分标准（四维 1-5 分档）
 *   toc_zhen2.json  89 个真题图片描述场景（24-26 考场原题）
 *   toc_zhen34.json 55 个真题讨论话题（24-26 考场原题）
 *   demos.json      Part2 描述示范 / Part3 讨论对话示范（对照翻译）
 * 旧数据保留：free（300 句）/ plan（90 天计划）从旧站 speak-data.js 迁移。
 *
 * 用法：node tools/build_speak_v3.js [--dry]
 */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC_DIR = path.join(ROOT, "data-src", "speak");
const LEGACY = path.join(ROOT, "..", "PET", "js", "speak-data.js");
const OUT = path.join(ROOT, "frontend", "public", "data", "speak.json");
const dry = process.argv.includes("--dry");

const read = (f) => JSON.parse(fs.readFileSync(path.join(SRC_DIR, f), "utf8"));
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

// ---------- 跟读句库 shadow / packs（全部来自教材） ----------
const shadow = [];
const packs = [];

function addPack(id, name, part, order) {
  const p = { id, name, part, ids: [], order };
  packs.push(p);
  return p;
}
function addShadow(pack, id, en, cn, tip, part) {
  if (!en || !en.trim()) { errors.push(`shadow ${id} 缺 en`); return; }
  shadow.push({ id, pack, packName: packs.find((p) => p.id === pack).name, part, en: en.trim(), cn: cn || "", tip: tip || "" });
  packs.find((p) => p.id === pack).ids.push(id);
}

// Part1 高频问答：按 17 分类拆包
for (const cat of p85.categories) {
  const packId = `p1-${cat.from}-${cat.to}`;
  addPack(packId, `Part1 ${cat.en}`, 1, cat.from);
  for (const it of p85.items) {
    if (it.no < cat.from || it.no > cat.to) continue;
    const q = it.q && it.q.trim() ? it.q.trim() : `Question ${it.no}`;
    addShadow(packId, `tp85-${it.no}`, it.ans, "", `Q: ${q}｜${it.cn}`, 1);
  }
}
// Part2 描述示范（逐句跟读）
addPack("p2-demo", "Part2 Photo Demos", 2, 200);
for (const demo of demos.photo) {
  demo.items.forEach((it, i) => addShadow("p2-demo", `${demo.id}-${i + 1}`, it.en, it.cn, demo.title, 2));
}
// Part3 讨论示范（逐轮跟读，带角色）
addPack("p3-demo", "Part3 Talk Demo", 3, 300);
demos.talk[0].items.forEach((it, i) => addShadow("p3-demo", `tp3-${i + 1}`, it.en, it.cn, `Role ${it.role}`, 3));

// ---------- 造句 patterns ----------
const patternGroups = patterns.groups.map((g) => ({
  id: g.id, part: g.part, name: g.name, cn: g.cn,
  items: g.items.map((it, i) => ({ id: `${g.id}-${i + 1}`, en: it.en, cn: it.cn || "" })),
}));

// ---------- 实时对话 scenes ----------
const scenes = [];
// Part1：17 分类场景，openers 取该类前两题
for (const cat of p85.categories) {
  const qs = p85.items.filter((it) => it.no >= cat.from && it.no <= cat.to).slice(0, 2).map((it) => it.q);
  scenes.push({
    id: `sc1-${cat.from}-${cat.to}`, part: 1,
    title: cat.en, cn: cat.cn, level: "B1",
    focus: "完整句回答 + 原因/举例扩展（2-3 句）",
    openers: qs,
    source: "215话题",
  });
}
// Part2：89 真题图片场景
for (const it of zhen2.items) {
  scenes.push({
    id: `sc2-z${it.no}`, part: 2,
    title: it.title, cn: `真题第 ${it.no} 题`, level: "B1",
    focus: "四步法：整体描述 → 人物 → 场景 → 合理猜测",
    openers: [`Now, please describe the picture: ${it.title}.`, "大约描述 1 分钟，用现在进行时讲动作。"],
    source: "zhen2",
  });
}
// Part3(+4)：55 真题讨论话题
for (const it of zhen34.items) {
  scenes.push({
    id: `sc3-z${it.no}`, part: 3,
    title: it.title, cn: `真题第 ${it.no} 题`, level: "B1",
    focus: "五步讨论：观点 → 理由 → 例子 → 反问搭档 → 达成一致",
    openers: [it.title], source: "zhen34",
  });
}

// ---------- 校验 ----------
const shadowIds = new Set(shadow.map((s) => s.id));
if (shadowIds.size !== shadow.length) errors.push("shadow id 有重复");
for (const p of packs) for (const id of p.ids) if (!shadowIds.has(id)) errors.push(`pack ${p.id} 引用不存在的 shadow ${id}`);
const catNos = p85.categories.flatMap((c) => [c.from, c.to]);
if (catNos[0] !== 1 || catNos[catNos.length - 1] !== 85) errors.push("分类边界异常");
if (zhen2.items.length !== 89) errors.push(`zhen2=${zhen2.items.length} ≠ 89`);
if (zhen34.items.length !== 55) errors.push(`zhen34=${zhen34.items.length} ≠ 55`);
if (p85.items.length !== 85) errors.push(`part1_85=${p85.items.length} ≠ 85`);
if (p130.items.length !== 131) errors.push(`part1_130=${p130.items.length} ≠ 131`);
for (const s of scenes) if (!s.title) errors.push(`scene ${s.id} 缺 title`);
for (const g of patternGroups) for (const it of g.items) if (!it.en) errors.push(`pattern ${it.id} 缺 en`);

const out = {
  meta: {
    built: new Date().toISOString().slice(0, 10),
    schema: 3,
    sources: {
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
  `统计: shadow=${shadow.length} packs=${packs.length} scenes=${scenes.length}(P1:${scenes.filter((s) => s.part === 1).length}/P2:${scenes.filter((s) => s.part === 2).length}/P3:${scenes.filter((s) => s.part === 3).length}) patterns=${patternGroups.reduce((a, g) => a + g.items.length, 0)}句/${patternGroups.length}组 bank=85+131 rubric=4维 zhen=89图+55题 free=${free.length}`
);
if (dry) { console.log("(dry run, 未写入)"); process.exit(errors.length ? 1 : 0); }
if (errors.length) process.exit(1);
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out));
console.log(`写入 ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)}KB)`);
