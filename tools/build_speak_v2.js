#!/usr/bin/env node
/** speak-v2 数据迁移：PET/js/speak-data.js → frontend/public/data/speak.json [--dry] */
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "..", "PET", "js", "speak-data.js");
const OUT = path.join(ROOT, "frontend", "public", "data", "speak.json");
const dry = process.argv.includes("--dry");

const window = {};
new Function("window", fs.readFileSync(SRC, "utf8"))(window);
const S = window.PET_SPEAK;

const errors = [];
// shadow: id/pack/packName/topic/en/cn/tip
const shadow = (S.shadow || []).map((s) => ({
  id: s.id, pack: s.pack, packName: s.packName || s.topic || "", en: s.en, cn: s.cn || "", tip: s.tip || "",
}));
const packs = (S.packs || []).map((p) => ({
  id: p.id, name: p.name, part: p.part || 0, ids: p.ids || [], order: p.order || 0,
}));
const free = (S.free || []).map((f) => ({ id: f.id, pack: f.pack, en: f.en, cn: f.cn || "" }));
const scenes = (S.scenes || []).map((c) => ({
  id: c.id, part: c.part || 0, title: c.title, cn: c.cn || "", level: c.level || "",
  focus: c.focus || "", openers: c.openers || [],
}));
const plan = S.plan || { title: "90 天 PET 口语计划", phases: [] };

// 校验
const shadowIds = new Set(shadow.map((s) => s.id));
if (shadow.length !== 305) errors.push(`shadow=${shadow.length} ≠ 305`);
if (packs.length !== 60) errors.push(`packs=${packs.length} ≠ 60`);
if (free.length !== 300) errors.push(`free=${free.length} ≠ 300`);
if (scenes.length !== 54) errors.push(`scenes=${scenes.length} ≠ 54`);
for (const p of packs) {
  for (const id of p.ids) if (!shadowIds.has(id)) errors.push(`pack ${p.id} 引用不存在的 shadow ${id}`);
}
for (const s of shadow) if (!s.en) errors.push(`shadow ${s.id} 缺 en`);
for (const c of scenes) if (!c.title) errors.push(`scene ${c.id} 缺 title`);

const out = {
  meta: S.meta || { built: new Date().toISOString().slice(0, 10) },
  packs, shadow, free, scenes, plan,
};
console.log(`校验: ${errors.length ? errors.join("\n") : "0 问题"}`);
console.log(`统计: shadow=${shadow.length} packs=${packs.length} free=${free.length} scenes=${scenes.length} days=${(plan.phases || []).reduce((a, p) => a + (p.to - p.from + 1), 0)}`);
if (dry) { console.log("(dry run, 未写入)"); process.exit(errors.length ? 1 : 0); }
if (errors.length) process.exit(1);
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out));
console.log(`写入 ${OUT} (${(fs.statSync(OUT).size / 1024).toFixed(0)}KB)`);
