/** 口语数据加载（speak.json）+ 90 天计划视图纯函数。 */

export type ShadowItem = { id: string; pack: string; packName: string; en: string; cn: string; tip: string };
export type SpeakPack = { id: string; name: string; part: number; ids: string[]; order: number };
export type FreeItem = { id: string; pack: string; en: string; cn: string };
export type Scene = { id: string; part: number; title: string; cn: string; level: string; focus: string; openers: string[] };
/** 教材里的 90 天原始任务 */
export type SpeakSourceDay = {
  d: number; phase: number; pack: string; title: string; goal: string;
  focus: string; shadow: string[]; scene: string;
};
export type SpeakPlan = {
  title: string;
  phases: { name: string; desc: string; from: number; to: number }[];
  days?: SpeakSourceDay[];
};

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

export type DayCheck = {
  day: number;
  shadow_done: boolean;
  make_done: boolean;
  talk_done: boolean;
  score: number;
};

/** 打卡完成 = 跟读 + 造句 + 对话三项都做了 */
export function dayDone(d: DayCheck | undefined): boolean {
  return !!d && d.shadow_done && d.make_done && d.talk_done;
}

/** 用户计划里的一天（可合并多个原始天） */
export type PlanDayView = {
  day: number;
  sourceDays: number[];
  from: number;
  to: number;
  title: string;
  goal: string;
  focus: string;
  shadowIds: string[];
  scene: string;
  sceneTitle: string;
  sceneIds: string[];
  sceneTitles: string[];
  phase: number;
};

/**
 * 按用户选择的天数切分 90 天计划。
 *
 * 注意：`speak.json` 的 `plan.days[].shadow/scene` 是旧版编号（sh001 / c101），
 * 与当前 v3 的 `shadow[].id`（tp85-xx）和 `scenes[].id`（sc1-x）对不上。
 * 因此每日内容改为按天数比例从 `packs` / `scenes` 中取，保证一定能加载到素材。
 */
export function splitSpeakPlan(data: SpeakData | null | undefined, length: number): PlanDayView[] {
  if (!data) return [];
  const source = data.plan.days ?? [];
  const total = source.length || 90;
  const n = Math.max(1, Math.min(Math.floor(length) || total, total));
  const packs = [...(data.packs ?? [])].sort((a, b) => a.order - b.order);
  const scenes = data.scenes ?? [];
  const base = Math.floor(total / n);
  const rem = total % n;
  const out: PlanDayView[] = [];
  let cursor = 0;
  for (let i = 0; i < n; i++) {
    const size = base + (i < rem ? 1 : 0);
    const group = source.slice(cursor, cursor + size);
    cursor += size;
    const sourceDays = group.map((g) => g.d);
    const from = sourceDays[0] ?? i + 1;
    const to = sourceDays[sourceDays.length - 1] ?? from;

    const pStart = Math.floor(((from - 1) * packs.length) / total);
    const pEnd = Math.max(pStart + 1, Math.floor((to * packs.length) / total));
    const packGroup = packs.slice(pStart, Math.min(pEnd, packs.length));
    const shadowIds = packGroup.flatMap((p) => p.ids);

    const sStart = Math.floor(((from - 1) * scenes.length) / total);
    const sEnd = Math.max(sStart + 1, Math.floor((to * scenes.length) / total));
    const sceneGroup = scenes.slice(sStart, Math.min(sEnd, scenes.length));
    const sceneIds = sceneGroup.map((s) => s.id);
    const sceneTitles = sceneGroup.map((s) => s.title);
    const sceneLabel =
      sceneTitles.length > 2
        ? `${sceneTitles.slice(0, 2).join("、")} 等 ${sceneTitles.length} 个场景`
        : sceneTitles.join("、") || "今日话题";

    const legacy = group[0];
    out.push({
      day: i + 1,
      sourceDays,
      from,
      to,
      title:
        packGroup.length > 0
          ? packGroup.map((p) => p.name).join(" / ")
          : legacy?.title ?? `第 ${i + 1} 天`,
      goal: `跟读 ${shadowIds.length} 句 → 和 AI 聊「${sceneLabel}」`,
      focus: sceneGroup[0]?.focus || legacy?.focus || "",
      shadowIds,
      scene: sceneIds[0] ?? "",
      sceneTitle: sceneTitles[0] ?? "今日话题",
      sceneIds,
      sceneTitles,
      phase: legacy?.phase ?? (from <= 30 ? 0 : from <= 55 ? 1 : from <= 75 ? 2 : 3),
    });
  }
  return out;
}

/** 计划日完成 = 它包含的所有原始天都完成 */
export function planDayDone(pd: PlanDayView, checks: Record<number, DayCheck>): boolean {
  return pd.sourceDays.length > 0 && pd.sourceDays.every((d) => dayDone(checks[d]));
}

/** 原始天范围文案：第 3 天 / 第 3–5 天 */
export function sourceRangeText(pd: PlanDayView): string {
  return pd.from === pd.to ? `第 ${pd.from} 天` : `第 ${pd.from}–${pd.to} 天`;
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

