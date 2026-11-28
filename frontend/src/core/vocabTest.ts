/**
 * 单词量评测（纯逻辑）：从 KET/PET 题库分层抽样，按「看词选义」估算覆盖率与达标情况。
 * 题库由 tools/build_vocab_test.py 生成（真题词带 hits 标签）；题库缺失时用 banks.json 兜底。
 * 只做抽样识别，不写学习/掌握度；结果存本地 localStorage，不进同步通道。
 */
import { shuffleWith } from "./shuffle";

export type ExamId = "ket" | "pet";
export type Verdict = "reached" | "near" | "below";

/** 参与评测的词库（同义替换是改写对照，不计入词汇量） */
export const EXAM_BANKS: Record<ExamId, string[]> = {
  ket: ["kword", "kcore", "kphrase"],
  pet: ["bimo", "gaopin", "guding"],
};

export const BANK_SHORT: Record<string, string> = {
  kword: "必默", kcore: "高频", kphrase: "固搭",
  bimo: "必默", gaopin: "高频", guding: "固搭",
};

/** 每个级别抽多少题（两级合计 50 题） */
export const PER_EXAM = 25;
/** 每个词库内优先从真题词抽的比例 */
export const EXAM_SHARE = 0.6;
/** 达到 / 接近 该级别的覆盖率门槛 */
export const PASS_RATE = 0.8;
export const NEAR_RATE = 0.6;

export const VERDICT_LABEL: Record<Verdict, string> = {
  reached: "达到",
  near: "接近",
  below: "未达到",
};

/** 题库中的词条：hits 为在对应级别真题原文中的出现次数（0 表示未命中） */
export interface VocabBankWord {
  id: string;
  en: string;
  cn: string;
  hits: number;
  exam: ExamId;
  bank: string;
}

export interface VocabBankPool {
  key: string;
  name: string;
  exam: ExamId;
  words: VocabBankWord[];
}

export interface VocabBank {
  ket: VocabBankPool[];
  pet: VocabBankPool[];
}

export interface VocabQuestion {
  item: VocabBankWord;
  /** 4 个中文释义（含正确答案） */
  options: string[];
  answer: string;
}

export interface BankScore {
  bank: string;
  label: string;
  correct: number;
  total: number;
}

export interface ExamScore {
  exam: ExamId;
  correct: number;
  total: number;
  /** 0–1 */
  accuracy: number;
  /** 本平台词库里估算认识的词条数 */
  estimated: number;
  /** 本级别参与评测的不重复词条数 */
  bankTotal: number;
  verdict: Verdict;
  /** 正确率 < 60% 的词库 */
  weak: BankScore[];
  /** 真题词（hits > 0）答题统计；旧结果可能没有该字段 */
  tagged?: { correct: number; total: number };
}

export interface VocabResult {
  at: number;
  ket: ExamScore;
  pet: ExamScore;
  /** 达到的最高级别；都没达到为 below */
  level: ExamId | "below";
  /** 识别词汇量估算（展示用，取所达级别的估算） */
  estimated: number;
}

const clean = (v: unknown): string => String(v ?? "").trim();
const norm = (s: string): string => s.replace(/\s+/g, " ").trim().toLowerCase();

function verdictOf(accuracy: number): Verdict {
  if (accuracy >= PASS_RATE) return "reached";
  if (accuracy >= NEAR_RATE) return "near";
  return "below";
}

function uniqueBy<T>(arr: T[], key: (v: T) => string): T[] {
  const seen = new Set<string>();
  return arr.filter((v) => {
    const k = key(v);
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

/** 每库先保底 2 题，剩余名额按词库大小用最大余数法分配 */
export function allocateQuota(sizes: number[], quota: number, minEach = 2): number[] {
  const n = sizes.length;
  const out = sizes.map(() => 0);
  let left = quota;
  for (let i = 0; i < n; i++) {
    const take = Math.min(minEach, sizes[i], left);
    out[i] = take;
    left -= take;
  }
  if (left <= 0) return out;
  const room = sizes.map((s, i) => Math.max(0, s - out[i]));
  const total = room.reduce((a, b) => a + b, 0);
  if (!total) return out;
  const exact = room.map((r) => (left * r) / total);
  const add = exact.map(Math.floor);
  let rest = left - add.reduce((a, b) => a + b, 0);
  const order = exact
    .map((v, i) => ({ i, frac: v - Math.floor(v), room: room[i] }))
    .sort((a, b) => b.frac - a.frac || b.room - a.room);
  for (const o of order) {
    if (rest <= 0) break;
    if (out[o.i] + add[o.i] < sizes[o.i]) {
      add[o.i] += 1;
      rest -= 1;
    }
  }
  for (let i = 0; i < n; i++) out[i] += add[i];
  return out;
}

/** 一个词库内：先抽目标数量的真题词，余下从未标注词补，不够再用剩余真题词补 */
function pickWords(
  words: VocabBankWord[],
  quota: number,
  rand: () => number,
  used: Set<string>,
): VocabBankWord[] {
  if (quota <= 0) return [];
  const available = words.filter((w) => !used.has(norm(w.en)));
  const tagged = shuffleWith(available.filter((w) => w.hits > 0), rand);
  const tagQuota = Math.min(tagged.length, Math.round(quota * EXAM_SHARE));
  const picked = tagged.slice(0, tagQuota);
  const pickedIds = new Set(picked.map((w) => w.id));
  const rest = shuffleWith(available.filter((w) => w.hits <= 0), rand).slice(0, quota - picked.length);
  picked.push(...rest);
  if (picked.length < quota) {
    const left = tagged.filter((w) => !pickedIds.has(w.id));
    picked.push(...left.slice(0, quota - picked.length));
  }
  for (const w of picked) used.add(norm(w.en));
  return picked;
}

function sampleExam(
  bank: VocabBank,
  exam: ExamId,
  quota: number,
  rand: () => number,
  used: Set<string>,
): VocabBankWord[] {
  const pools = bank[exam] ?? [];
  const counts = allocateQuota(pools.map((p) => p.words.length), quota);
  const picked = pools.flatMap((p, i) => pickWords(p.words, counts[i], rand, used));
  if (picked.length < quota) {
    // 跨级别去重导致某库凑不满时，从本级别剩余词补足
    const ids = new Set(picked.map((w) => w.id));
    const extra = shuffleWith(
      pools.flatMap((p) => p.words).filter((w) => !ids.has(w.id) && !used.has(norm(w.en))),
      rand,
    );
    const add = extra.slice(0, quota - picked.length);
    for (const w of add) used.add(norm(w.en));
    picked.push(...add);
  }
  return picked;
}

/** 同一词库优先做干扰项，不够再从同级别其他词库补；选项按中文去重 */
function makeQuestion(item: VocabBankWord, bank: VocabBank, rand: () => number): VocabQuestion {
  const pools = bank[item.exam] ?? [];
  const collect = (pool: VocabBankPool): string[] =>
    pool.words
      .filter((w) => w.cn && w.en && norm(w.en) !== norm(item.en))
      .map((w) => w.cn);
  const own = pools.find((p) => p.key === item.bank);
  const candidates = uniqueBy(
    [...(own ? collect(own) : []), ...pools.flatMap(collect)],
    (cn) => cn,
  ).filter((cn) => cn !== item.cn);
  const distractors = shuffleWith(candidates, rand).slice(0, 3);
  return {
    item,
    options: shuffleWith([item.cn, ...distractors], rand),
    answer: item.cn,
  };
}

/** 生成整套题：KET 25 + PET 25，两级混排；同一英文词全局只出现一次 */
export function buildVocabTest(bank: VocabBank, rand: () => number = Math.random): VocabQuestion[] {
  const used = new Set<string>();
  const items = (["ket", "pet"] as ExamId[]).flatMap((exam) =>
    sampleExam(bank, exam, PER_EXAM, rand, used),
  );
  return shuffleWith(items.map((it) => makeQuestion(it, bank, rand)), rand);
}

/** 判分：chosen 与 questions 等长，null 表示跳过（记错） */
export function scoreVocabTest(
  questions: VocabQuestion[],
  chosen: Array<string | null>,
  bank: VocabBank,
): VocabResult {
  const scoreExam = (exam: ExamId): ExamScore => {
    const rows = questions
      .map((q, i) => ({ q, i }))
      .filter(({ q }) => q.item.exam === exam);
    const total = rows.length;
    const correct = rows.filter(({ q, i }) => chosen[i] === q.answer).length;
    const accuracy = total ? correct / total : 0;
    const pools = bank[exam] ?? [];
    const bankTotal = pools.reduce((s, p) => s + p.words.length, 0);
    const taggedRows = rows.filter(({ q }) => q.item.hits > 0);
    const weak = pools
      .map((p) => {
        const qs = rows.filter(({ q }) => q.item.bank === p.key);
        const ok = qs.filter(({ q, i }) => chosen[i] === q.answer).length;
        return { bank: p.key, label: p.name || BANK_SHORT[p.key] || p.key, correct: ok, total: qs.length };
      })
      .filter((b) => b.total > 0 && b.correct / b.total < NEAR_RATE);
    return {
      exam,
      correct,
      total,
      accuracy,
      estimated: Math.round(bankTotal * accuracy),
      bankTotal,
      verdict: verdictOf(accuracy),
      weak,
      tagged: {
        correct: taggedRows.filter(({ q, i }) => chosen[i] === q.answer).length,
        total: taggedRows.length,
      },
    };
  };

  const ket = scoreExam("ket");
  const pet = scoreExam("pet");
  const level: VocabResult["level"] =
    pet.verdict === "reached" ? "pet" : ket.verdict === "reached" ? "ket" : "below";
  return {
    at: Date.now(),
    ket,
    pet,
    level,
    estimated: level === "pet" ? pet.estimated : ket.estimated,
  };
}

/* ---------- 本地结果（不进同步通道） ---------- */

/** 2026-11-28 题库版：存储键升到 v2，旧的 24 题结果一律清理 */
const STORE_PREFIX = "pet_vocab_test_v2";
const LEGACY_PREFIX = "pet_vocab_test_v1:";

function clearLegacyResults(): void {
  try {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(LEGACY_PREFIX)) keys.push(k);
    }
    for (const k of keys) localStorage.removeItem(k);
  } catch {
    /* 隐私模式：忽略 */
  }
}

export function vocabResultKey(owner: string): string {
  return `${STORE_PREFIX}:${owner || "guest"}`;
}

export function loadVocabResult(owner: string): VocabResult | null {
  clearLegacyResults();
  try {
    const raw = localStorage.getItem(vocabResultKey(owner));
    if (!raw) return null;
    const data = JSON.parse(raw) as Partial<VocabResult>;
    if (!data || typeof data.at !== "number" || !data.ket || !data.pet) return null;
    return data as VocabResult;
  } catch {
    return null;
  }
}

export function saveVocabResult(owner: string, result: VocabResult): void {
  clearLegacyResults();
  try {
    localStorage.setItem(vocabResultKey(owner), JSON.stringify(result));
  } catch {
    /* 隐私模式 / 存储已满：评测照常，只是不记上次结果 */
  }
}
