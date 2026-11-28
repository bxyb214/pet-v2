/**
 * 单词量评测（纯逻辑）：从 KET / PET 词库分层抽样，按「看词选义」估算覆盖率与达标情况。
 * 只做抽样识别，不写学习/掌握度；结果存本地 localStorage，不进同步通道。
 */
import type { WordBanks } from "./plan";
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

/** 每个级别抽多少题（两级合计 24 题） */
export const PER_EXAM = 12;
/** 达到 / 接近 该级别的覆盖率门槛 */
export const PASS_RATE = 0.8;
export const NEAR_RATE = 0.6;

export const VERDICT_LABEL: Record<Verdict, string> = {
  reached: "达到",
  near: "接近",
  below: "未达到",
};

export interface VocabItem {
  id: string;
  en: string;
  cn: string;
  exam: ExamId;
  bank: string;
}

export interface VocabQuestion {
  item: VocabItem;
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

interface Pool {
  exam: ExamId;
  bank: string;
  words: VocabItem[];
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

/** 某级别按词库分层的候选池：跳过空字段与跨库重复英文（先出现的词库保留） */
export function examPools(banks: WordBanks, exam: ExamId): Pool[] {
  const seen = new Set<string>();
  return EXAM_BANKS[exam].map((bank) => {
    const words: VocabItem[] = [];
    for (const w of banks[bank] ?? []) {
      const en = clean(w.en);
      const cn = clean(w.cn);
      if (!en || !cn) continue;
      const key = norm(en);
      if (seen.has(key)) continue;
      seen.add(key);
      words.push({ id: w.id, en, cn, exam, bank });
    }
    return { exam, bank, words };
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

function sampleExam(
  banks: WordBanks,
  exam: ExamId,
  quota: number,
  rand: () => number,
): VocabItem[] {
  const pools = examPools(banks, exam);
  const counts = allocateQuota(pools.map((p) => p.words.length), quota);
  return pools.flatMap((p, i) => shuffleWith(p.words, rand).slice(0, counts[i]));
}

/** 同一词库优先做干扰项，不够再从同级别其他词库补；选项按中文去重 */
function makeQuestion(item: VocabItem, banks: WordBanks, rand: () => number): VocabQuestion {
  const collect = (bank: string): string[] =>
    (banks[bank] ?? [])
      .map((w) => ({ en: clean(w.en), cn: clean(w.cn) }))
      .filter((w) => w.cn && w.en && norm(w.en) !== norm(item.en))
      .map((w) => w.cn);
  const candidates = uniqueBy(
    [...collect(item.bank), ...EXAM_BANKS[item.exam].flatMap(collect)],
    (cn) => cn,
  ).filter((cn) => cn !== item.cn);
  const distractors = shuffleWith(candidates, rand).slice(0, 3);
  return {
    item,
    options: shuffleWith([item.cn, ...distractors], rand),
    answer: item.cn,
  };
}

/** 生成整套题：KET 12 + PET 12，两级混排 */
export function buildVocabTest(
  banks: WordBanks,
  rand: () => number = Math.random,
): VocabQuestion[] {
  const items = (["ket", "pet"] as ExamId[]).flatMap((exam) =>
    sampleExam(banks, exam, PER_EXAM, rand),
  );
  return shuffleWith(items.map((it) => makeQuestion(it, banks, rand)), rand);
}

/** 判分：chosen 与 questions 等长，null 表示跳过（记错） */
export function scoreVocabTest(
  questions: VocabQuestion[],
  chosen: Array<string | null>,
  banks: WordBanks,
): VocabResult {
  const scoreExam = (exam: ExamId): ExamScore => {
    const rows = questions
      .map((q, i) => ({ q, i }))
      .filter(({ q }) => q.item.exam === exam);
    const total = rows.length;
    const correct = rows.filter(({ q, i }) => chosen[i] === q.answer).length;
    const accuracy = total ? correct / total : 0;
    const pools = examPools(banks, exam);
    const bankTotal = pools.reduce((s, p) => s + p.words.length, 0);
    const weak = pools
      .map((p) => {
        const qs = rows.filter(({ q }) => q.item.bank === p.bank);
        const ok = qs.filter(({ q, i }) => chosen[i] === q.answer).length;
        return { bank: p.bank, label: BANK_SHORT[p.bank] ?? p.bank, correct: ok, total: qs.length };
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

const STORE_PREFIX = "pet_vocab_test_v1";

export function vocabResultKey(owner: string): string {
  return `${STORE_PREFIX}:${owner || "guest"}`;
}

export function loadVocabResult(owner: string): VocabResult | null {
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
  try {
    localStorage.setItem(vocabResultKey(owner), JSON.stringify(result));
  } catch {
    /* 隐私模式 / 存储已满：评测照常，只是不记上次结果 */
  }
}
