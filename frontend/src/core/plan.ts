/**
 * 计划切分（F-1）：每种词库各自平均分到各天，任意天数，不重不漏（V1/P1）。
 * 对每个词库，第 d 天取 [floor(d*L/N), floor((d+1)*L/N))：
 * 各天条数最多差 1，余量均匀散布；只要 L >= N，每天都有该词库的词。
 * 每天切片后再按「库 + 天 + 天数 + 区间」确定性乱序：
 * 学习翻卡与计划测试不再按词库原始顺序出词，且各页面拿到的顺序一致。
 */
import { deterministicShuffle, seedFrom } from "./shuffle";

/** 词库 id（bimo/gaopin/guding/tongyi/kword/kcore/kphrase/kconfuse/ksyn…），可扩展 */
export type BankKey = string;

export interface PlanWord {
  id: string;
  en: string;
  cn: string;
  /** 同义替换库：alt 为纯英文同义短语，alt_cn 为其中文释义 */
  alt?: string;
  alt_cn?: string;
  /** banks.json 附加字段（phonetic/pos/example/audio 等） */
  [k: string]: unknown;
}

export type WordBanks = Record<BankKey, PlanWord[]>;

export interface PlanDay {
  day: number; // 1-based
  /** 每库当天的词；键即词库 id（PET 四库 / KET 五库都走这一套） */
  banks: Record<BankKey, PlanWord[]>;
  total: number;
}

function chunk<T>(arr: T[], size: number): T[][] {
  if (size <= 0) return arr.length ? [arr] : [];
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

export function splitPlan(banks: WordBanks, days: number, keys?: BankKey[]): PlanDay[] {
  if (!Number.isInteger(days) || days <= 0) throw new Error("天数必须为正整数");
  const order = (keys ?? Object.keys(banks)).filter((k) => (banks[k] ?? []).length > 0);

  const out: PlanDay[] = Array.from({ length: days }, (_, i) => ({
    day: i + 1,
    banks: {},
    total: 0,
  }));

  for (const key of order) {
    const words = banks[key] ?? [];
    for (let d = 0; d < days; d++) {
      // 均匀散布余量：各天条数差 ≤1，且每天尽量都有该库
      const start = Math.floor((d * words.length) / days);
      const end = Math.floor(((d + 1) * words.length) / days);
      // 只打乱当天词序，不跨天搬词：计划词集与每天词数保持原切分
      const slice = deterministicShuffle(
        words.slice(start, end),
        seedFrom(key, d + 1, days, start, end),
      );
      out[d].banks[key] = slice;
      out[d].total += slice.length;
    }
  }
  return out;
}

/** 不变量校验：各库拼回 = 原库（集合一致、无重复）；每天词集仍与原切分区一致；每库每天条数差 ≤1。 */
export function validatePlan(banks: WordBanks, plan: PlanDay[], keys?: BankKey[]): boolean {
  const order = (keys ?? Object.keys(banks)).filter((k) => (banks[k] ?? []).length > 0);
  for (const key of order) {
    const original = banks[key].map((w) => w.id);
    const originalSet = new Set(original);
    if (originalSet.size !== original.length) return false;
    const rebuilt = plan.flatMap((d) => d.banks[key] ?? []).map((w) => w.id);
    if (original.length !== rebuilt.length) return false;
    if (new Set(rebuilt).size !== rebuilt.length) return false;
    if (!rebuilt.every((id) => originalSet.has(id))) return false;
    // 乱序只允许发生在当天切片内：每天词集必须与切分区间一致
    for (let d = 0; d < plan.length; d++) {
      const start = Math.floor((d * original.length) / plan.length);
      const end = Math.floor(((d + 1) * original.length) / plan.length);
      const expected = new Set(original.slice(start, end));
      const actual = (plan[d].banks[key] ?? []).map((w) => w.id);
      if (actual.length !== expected.size) return false;
      if (!actual.every((id) => expected.has(id))) return false;
    }
    const counts = plan.map((d) => (d.banks[key] ?? []).length);
    if (counts.length && Math.max(...counts) - Math.min(...counts) > 1) return false;
  }
  return true;
}

/** 阅读计划（R9）：单位是 Part，按顺序 ceil(parts/N) 切分，末天吸收余量。 */
export interface ReadingPartRef {
  book: string;
  testNo: number;
  part: number;
}

export interface ReadingPlanDay {
  day: number; // 1-based
  parts: ReadingPartRef[];
}

export function partKey(p: ReadingPartRef): string {
  return `${p.book}:${p.testNo}:${p.part}`;
}

/**
 * 计划覆盖的 Part 序列。
 * bookIds 有值：先按选择顺序排教材，再按 tests 顺序排套与 Part；
 * bookIds 为空：按 tests 顺序走全部教材（兼容未选教材的老计划）。
 */
export function readingParts(
  tests: { no: number; book?: string; parts: { part: number }[] }[],
  bookIds?: string[],
): ReadingPartRef[] {
  const bookOf = (t: { book?: string }): string => t.book || "t2";
  const order = bookIds && bookIds.length ? bookIds : [...new Set(tests.map(bookOf))];
  const out: ReadingPartRef[] = [];
  for (const book of order) {
    for (const t of tests) {
      if (bookOf(t) !== book) continue;
      for (const p of t.parts) out.push({ book, testNo: t.no, part: p.part });
    }
  }
  return out;
}

export function buildReadingPlan(parts: ReadingPartRef[], days: number): ReadingPlanDay[] {
  if (!Number.isInteger(days) || days <= 0) throw new Error("天数必须为正整数");
  const quota = Math.ceil(parts.length / days);
  return chunk(parts, quota).map((chunks, i) => ({ day: i + 1, parts: chunks }));
}

/** 反查 PartKey 属于第几天（1-based；不在计划中返回 0） */
export function readingDayOf(plan: ReadingPlanDay[], key: string): number {
  for (const d of plan) {
    if (d.parts.some((p) => partKey(p) === key)) return d.day;
  }
  return 0;
}

export function validateReadingPlan(parts: ReadingPartRef[], plan: ReadingPlanDay[]): boolean {
  const original = parts.map(partKey);
  const rebuilt = plan.flatMap((d) => d.parts.map(partKey));
  if (original.length !== rebuilt.length) return false;
  if (new Set(rebuilt).size !== rebuilt.length) return false;
  for (let i = 0; i < original.length; i++) {
    if (original[i] !== rebuilt[i]) return false;
  }
  return true;
}
