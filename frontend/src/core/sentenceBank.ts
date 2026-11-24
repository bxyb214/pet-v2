/**
 * 跟读句库选句（P0-3 / P2-5）：纯前端、确定性、无 AI 调用。
 *
 * 规则（docs/AI优化与额度方案 §3.2）：
 * 1. 最近 3 次平均分 ≥85 → 目标难度 +1；<60 → −1；范围 1–5。
 * 2. 候选 active 且 |difficulty−target| ≤1；不足时放宽到 ≤2。
 * 3. 未练过优先；最近练过的降权；词数接近 8–15 优先；命中最近读错的词加权；
 *    最后用 hash(userId|date|id) 做稳定抖动。
 */

export type BankSentence = {
  id: string;
  pack: string;
  packName: string;
  part?: number;
  en: string;
  cn: string;
  tip?: string;
  difficulty?: number;
  words?: number;
  focus?: string[];
  source?: string;
  active?: boolean;
};

export type RecentShadow = {
  sentence_id?: string;
  score?: number;
  weak_words?: string[];
  created_at?: string | null;
};

export type PickInput = {
  sentences: BankSentence[];
  /** 最近得分，最新在前 */
  recentScores?: number[];
  /** 最近练过的句子 id，最新在前 */
  recentIds?: string[];
  /** 最近读错的词（小写） */
  weakWords?: string[];
  packId?: string;
  packIds?: string[];
  count?: number;
  userId?: string | number;
  /** YYYY-MM-DD，用于当日稳定 */
  date?: string;
};

export type PickResult = { target: number; items: BankSentence[] };

const DEFAULT_TARGET = 3;
const IDEAL_WORDS = 11;

export function countWords(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

export function normalizeSentence(s: BankSentence): Required<BankSentence> {
  return {
    id: s.id,
    pack: s.pack,
    packName: s.packName,
    part: s.part ?? 0,
    en: s.en,
    cn: s.cn,
    tip: s.tip ?? "",
    difficulty: clampInt(s.difficulty ?? 3, 1, 5),
    words: s.words ?? countWords(s.en),
    focus: s.focus ?? [],
    source: s.source ?? "unknown",
    active: s.active !== false,
  };
}

function clampInt(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, Math.round(n)));
}

/** 最近 3 次平均分 → 目标难度（1–5）。 */
export function targetDifficulty(recentScores: number[] = []): number {
  const scores = recentScores.filter((n) => Number.isFinite(n) && n > 0).slice(0, 3);
  if (!scores.length) return DEFAULT_TARGET;
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  if (avg >= 85) return clampInt(DEFAULT_TARGET + 1, 1, 5);
  if (avg < 60) return clampInt(DEFAULT_TARGET - 1, 1, 5);
  return DEFAULT_TARGET;
}

/** FNV-1a 32 位：稳定、无随机源。返回 [0,1)。 */
export function hashSeed(key: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0) / 4294967296;
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

type RankInput = {
  target: number;
  recency: Map<string, number>;
  weak: Set<string>;
  seed: string;
};

function rank(s: Required<BankSentence>, r: RankInput): number {
  let score = 0;
  // 最近练过：降权；越近降得越多。没练过：优先。
  if (r.recency.has(s.id)) score += 8 + (r.recency.get(s.id) ?? 0);
  else score -= 2;
  // 词数接近 8–15
  score += Math.abs(s.words - IDEAL_WORDS) * 0.6;
  // 命中最近读错的词：加权（最多计 2 个）
  let hits = 0;
  for (const f of s.focus) {
    if (r.weak.has(String(f).toLowerCase())) hits++;
  }
  score -= Math.min(2, hits) * 3;
  // 难度贴合
  const diff = Math.abs(s.difficulty - r.target);
  if (diff === 0) score -= 1.5;
  else if (diff >= 2) score += 2;
  // 稳定抖动，避免每日顺序完全一样
  score += hashSeed(`${r.seed}|${s.id}`) * 2.5;
  return score;
}

function makeRankInput(input: PickInput, target: number): RankInput {
  const recentIds = input.recentIds ?? [];
  return {
    target,
    recency: new Map(recentIds.map((id, i) => [id, i])),
    weak: new Set((input.weakWords ?? []).map((w) => w.toLowerCase())),
    seed: `${input.userId ?? "anon"}|${input.date ?? todayStr()}`,
  };
}

function poolOf(sentences: BankSentence[], input: PickInput): Required<BankSentence>[] {
  const packs = new Set<string>(
    input.packIds ?? (input.packId ? [input.packId] : []),
  );
  return sentences
    .map(normalizeSentence)
    .filter((s) => s.active && (!packs.size || packs.has(s.pack)));
}

/** 计划模式：包内全部句子按难度与个性化排序（不截断）。 */
export function sortSentences(input: PickInput): BankSentence[] {
  const target = targetDifficulty(input.recentScores);
  const r = makeRankInput(input, target);
  return poolOf(input.sentences, input)
    .sort((a, b) => rank(a, r) - rank(b, r) || a.id.localeCompare(b.id));
}

/** 自由模式：跨库选 N 句；先 ±1 难度，不足再放宽到 ±2。 */
export function pickSentences(input: PickInput): PickResult {
  const count = Math.max(1, Math.min(input.count ?? 5, 20));
  const target = targetDifficulty(input.recentScores);
  const r = makeRankInput(input, target);
  const pool = poolOf(input.sentences, input);
  const strict = pool.filter((s) => Math.abs(s.difficulty - target) <= 1);
  const relaxed = pool.filter((s) => Math.abs(s.difficulty - target) <= 2);
  const candidates = strict.length >= count ? strict : relaxed.length ? relaxed : pool;
  const sorted = candidates
    .slice()
    .sort((a, b) => rank(a, r) - rank(b, r) || a.id.localeCompare(b.id));
  return { target, items: sorted.slice(0, count) };
}

/** 从最近记录里汇总读错的词（去重，最多 10 个）。 */
export function weakWordsFromRecent(recent: RecentShadow[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const r of recent) {
    for (const w of r.weak_words ?? []) {
      const key = String(w).toLowerCase();
      if (!key || seen.has(key)) continue;
      seen.add(key);
      out.push(key);
      if (out.length >= 10) return out;
    }
  }
  return out;
}
