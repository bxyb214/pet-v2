/** 口语数据加载（speak.json）+ 90 天计划视图纯函数。 */

export type ShadowItem = { id: string; pack: string; packName: string; en: string; cn: string; tip: string };
export type SpeakPack = { id: string; name: string; part: number; ids: string[]; order: number };
export type FreeItem = { id: string; pack: string; en: string; cn: string };
export type Scene = { id: string; part: number; title: string; cn: string; level: string; focus: string; openers: string[] };
export type SpeakPlan = { title: string; phases: { name: string; desc: string; from: number; to: number }[] };

// 教材数据（speak.json schema v3 新增，来自 PET 官方口语教辅）
export type PatternGroup = { id: string; part: number; name: string; cn: string; items: { id: string; en: string; cn: string }[] };
export type RubricDim = { key: string; name: string; cn: string; levels: { level: number; desc: string }[] };
export type Part1BankItem = { no: number; q: string; cn: string; ans: string };
export type EssayItem = { no: string; q: string; ans: string };

export type SpeakData = {
  meta: Record<string, unknown>;
  packs: SpeakPack[];
  shadow: ShadowItem[];
  free: FreeItem[];
  scenes: Scene[];
  plan: SpeakPlan;
  patterns?: PatternGroup[];
  rubric?: { global: { level: number; desc: string }[]; dims: RubricDim[]; note: string };
  part1bank?: Part1BankItem[];
  categories?: { cn: string; en: string; from: number; to: number }[];
  essays?: EssayItem[];
  zhen2?: { no: number; title: string; page: number }[];
  zhen34?: { no: number; title: string; page: number }[];
};

let cache: SpeakData | null = null;

export async function loadSpeak(): Promise<SpeakData> {
  if (cache) return cache;
  const res = await fetch("/data/speak.json");
  if (!res.ok) throw new Error("口语数据加载失败");
  cache = (await res.json()) as SpeakData;
  return cache;
}

/** 90 天计划的某一天该做什么（来自阶段表） */
export function phaseOfDay(plan: SpeakPlan, day: number): SpeakPlan["phases"][number] | null {
  return plan.phases.find((p) => day >= p.from && day <= p.to) ?? null;
}

export type DayCheck = { day: number; shadow_done: boolean; talk_done: boolean; score: number };

/** 打卡完成 = 跟读 + 对话都做了（与旧站语义一致） */
export function dayDone(d: DayCheck | undefined): boolean {
  return !!d && d.shadow_done && d.talk_done;
}

/** shadow JSON 回复容错解析 */
export function parseShadowReply(text: string): { transcript: string; score: number; words: { w: string; ok: boolean }[]; tips: string[]; say: string } | null {
  try {
    let clean = text.trim();
    if (clean.startsWith("```json")) clean = clean.slice(7);
    if (clean.startsWith("```")) clean = clean.slice(3);
    if (clean.endsWith("```")) clean = clean.slice(0, -3);
    clean = clean.trim();
    const s = clean.indexOf("{");
    const e = clean.lastIndexOf("}");
    if (s < 0 || e <= s) return null;
    const j = JSON.parse(clean.slice(s, e + 1));
    return {
      transcript: String(j.transcript ?? ""),
      score: Number(j.score ?? 0) || 0,
      words: Array.isArray(j.words) ? j.words : [],
      tips: Array.isArray(j.tips) ? j.tips.map(String) : [],
      say: String(j.say ?? ""),
    };
  } catch {
    return null;
  }
}

