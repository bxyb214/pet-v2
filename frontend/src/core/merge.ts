/**
 * 同步合并语义（与服务端 app/services/merge.py 保持同语义，红线）。
 * 原则：合并 = 保留「欠得多/进度多」的状态，绝不覆盖丢失。
 */

type MasteryItem = { word_id: string; mastered_dims: string[] };
type MistakeItem = { word_id: string; dims: string[]; stage: number; due_at: string; repeats: number };
type ProgressItem = { key: string; seen: string[]; idx: number };
type PlanData = { length: number; days_done: string[]; reading_length: number; reading_days_done: string[] };
type CustomWordItem = {
  id: number;
  word: string;
  pos: string;
  definition: string;
  example_en: string;
  example_cn: string;
};
type CustomSentenceItem = {
  sid: string;
  book: string;
  test_no: number;
  part: number;
  en: string;
  cn: string;
  key: string;
  note: string;
};
export type SyncData = {
  mastery: MasteryItem[];
  mistakes: MistakeItem[];
  progress: ProgressItem[];
  plan: PlanData;
  custom_words: CustomWordItem[];
  custom_sentences: CustomSentenceItem[];
};
export type { MasteryItem, MistakeItem, ProgressItem, PlanData, CustomWordItem, CustomSentenceItem };

export const EMPTY_PLAN: PlanData = { length: 0, days_done: [], reading_length: 0, reading_days_done: [] };

function splitDims(v: string[] | string | undefined): string[] {
  if (Array.isArray(v)) return v.filter(Boolean);
  return (v ?? "").split(",").filter(Boolean);
}

function toSeen(v: unknown): string[] {
  return Array.isArray(v) ? v.map(String) : [];
}

export function mergeMastery(server: MasteryItem[], client: MasteryItem[]): MasteryItem[] {
  const byId = new Map<string, Set<string>>();
  for (const r of [...server, ...client]) {
    const set = byId.get(r.word_id) ?? new Set<string>();
    splitDims(r.mastered_dims).forEach((d) => set.add(d));
    byId.set(r.word_id, set);
  }
  return [...byId.entries()]
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([word_id, dims]) => ({ word_id, mastered_dims: [...dims].sort() }));
}

function mergeOneMistake(a: MistakeItem, b: MistakeItem): MistakeItem {
  const dims = [...new Set([...a.dims, ...b.dims])].sort();
  const fallbackDue = "9999-99-99";
  return {
    word_id: a.word_id,
    dims,
    stage: Math.min(a.stage, b.stage),
    due_at: [a.due_at || fallbackDue, b.due_at || fallbackDue].sort()[0],
    repeats: Math.min(a.repeats, b.repeats),
  };
}

export function mergeMistakes(server: MistakeItem[], client: MistakeItem[]): MistakeItem[] {
  const srv = new Map(server.map((r) => [r.word_id, r]));
  const out = new Map<string, MistakeItem>();
  for (const r of client) {
    const s = srv.get(r.word_id);
    out.set(r.word_id, s ? mergeOneMistake(s, r) : { ...r });
  }
  for (const r of server) if (!out.has(r.word_id)) out.set(r.word_id, { ...r });
  return [...out.values()].sort((a, b) => (a.word_id < b.word_id ? -1 : 1));
}

export function mergeProgress(server: ProgressItem[], client: ProgressItem[]): ProgressItem[] {
  const byKey = new Map<string, { seen: Set<string>; idx: number }>();
  for (const r of [...server, ...client]) {
    const cur = byKey.get(r.key) ?? { seen: new Set<string>(), idx: 0 };
    toSeen(r.seen).forEach((s) => cur.seen.add(s));
    cur.idx = Math.max(cur.idx, r.idx);
    byKey.set(r.key, cur);
  }
  return [...byKey.entries()]
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([key, v]) => ({ key, seen: [...v.seen].sort(), idx: v.idx }));
}

export function mergePlan(server: PlanData | undefined, client: PlanData | undefined): PlanData {
  const srv = server ?? EMPTY_PLAN;
  const cli = client ?? EMPTY_PLAN;
  const days = [...new Set([...toSeen(srv.days_done), ...toSeen(cli.days_done)])];
  const rdays = [...new Set([...toSeen(srv.reading_days_done), ...toSeen(cli.reading_days_done)])];
  return {
    length: cli.length || srv.length || 0,
    days_done: days.sort((a, b) => Number(a) - Number(b)),
    reading_length: cli.reading_length || srv.reading_length || 0,
    reading_days_done: rdays.sort((a, b) => Number(a) - Number(b)),
  };
}

export function mergeCustomWords(server: CustomWordItem[], client: CustomWordItem[]): CustomWordItem[] {
  /** 按 word 小写为业务键取并集；同词双侧内容不同 → 服务端优先。 */
  const byWord = new Map<string, CustomWordItem>();
  for (const r of client) byWord.set(r.word.toLowerCase(), { ...r });
  for (const r of server) byWord.set(r.word.toLowerCase(), { ...r });
  return [...byWord.values()].sort((a, b) => (a.word.toLowerCase() < b.word.toLowerCase() ? -1 : 1));
}

export function mergeCustomSentences(server: CustomSentenceItem[], client: CustomSentenceItem[]): CustomSentenceItem[] {
  /** 按 sid 业务键取并集；冲突服务端优先（与 custom_words 一致）。 */
  const bySid = new Map<string, CustomSentenceItem>();
  for (const r of client) bySid.set(r.sid, { ...r });
  for (const r of server) bySid.set(r.sid, { ...r });
  return [...bySid.values()].sort((a, b) => (a.sid < b.sid ? -1 : 1));
}

export function mergeSyncData(server: SyncData, client: Partial<SyncData>): SyncData {
  return {
    mastery: mergeMastery(server.mastery ?? [], client.mastery ?? []),
    mistakes: mergeMistakes(server.mistakes ?? [], client.mistakes ?? []),
    progress: mergeProgress(server.progress ?? [], client.progress ?? []),
    plan: mergePlan(server.plan, client.plan),
    custom_words: mergeCustomWords(server.custom_words ?? [], client.custom_words ?? []),
    custom_sentences: mergeCustomSentences(server.custom_sentences ?? [], client.custom_sentences ?? []),
  };
}
