/**
 * 计划切分（F-1）：四库按天切分，任意天数，不重不漏（V1/P1）。
 * 沿用现站语义推广：每库按 ceil(库长/N) 配额顺序切片，末天吸收余量。
 */
/** 词库 id（bimo/gaopin/guding/tongyi/kword/kcore/kphrase/kconfuse/ksyn…），可扩展 */
export type BankKey = string;

export interface PlanWord {
  id: string;
  en: string;
  cn: string;
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
  const perBank: Record<BankKey, PlanWord[][]> = {};
  for (const key of order) {
    const quota = Math.ceil(banks[key].length / days);
    perBank[key] = chunk(banks[key], quota);
  }
  const out: PlanDay[] = [];
  for (let d = 1; d <= days; d++) {
    const dayBanks: Record<BankKey, PlanWord[]> = {};
    let total = 0;
    for (const key of order) {
      const slice = perBank[key][d - 1] ?? [];
      dayBanks[key] = slice;
      total += slice.length;
    }
    out.push({ day: d, banks: dayBanks, total });
  }
  return out;
}

/** 不变量校验：各库拼回 = 原库且无重复（生成计划后前端自检） */
export function validatePlan(banks: WordBanks, plan: PlanDay[]): boolean {
  for (const key of Object.keys(banks)) {
    if (!banks[key].length) continue;
    const original = banks[key].map((w) => w.id);
    const rebuilt = plan.flatMap((d) => d.banks[key] ?? []).map((w) => w.id);
    if (original.length !== rebuilt.length) return false;
    if (new Set(rebuilt).size !== rebuilt.length) return false;
    for (let i = 0; i < original.length; i++) {
      if (original[i] !== rebuilt[i]) return false;
    }
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
