/**
 * 测验生成（V2–V4）纯逻辑。
 * 朗读规则红线：w2m（看词选义）答题前有发音；spell/m2w 答题前不放。
 */
import type { PlanWord } from "./plan";

export type QuizDim = "spell" | "w2m" | "m2w";

export const ALL_DIMS: QuizDim[] = ["w2m", "m2w", "spell"];

export const DIM_LABEL: Record<QuizDim, string> = {
  spell: "单词填空",
  w2m: "看词选义",
  m2w: "看义选词",
};

/** 同义替换库的两型标签：考短语配对，不考中文释义 */
export const SYN_DIM_LABEL: Record<Exclude<QuizDim, "spell">, string> = {
  w2m: "选同义短语",
  m2w: "看同义选短语",
};

export interface QuizQuestion {
  word: PlanWord;
  dim: QuizDim;
  /** 选择题选项（spell 为空，输入作答） */
  options: string[];
  answer: string;
}

function isDim(v: string): v is QuizDim {
  return v === "spell" || v === "w2m" || v === "m2w";
}

/** 同义替换词（带 alt 字段）：考「原短语 ↔ 同义短语」，不考中文释义 */
export function isSynonymWord(w: PlanWord): boolean {
  const alt = w.alt;
  return typeof alt === "string" && alt.trim().length > 0;
}

/** 字段里的英文部分（同义库字段是「英文 中文」混排，如「walk 走路」→「walk」） */
export function enPart(s: string): string {
  const m = s.match(/^([\s\S]*?)([㐀-鿿][\s\S]*)$/);
  return (m ? m[1] : s).trim();
}

/** 题干文本：同义库 w2m 题干=原短语、m2w 题干=同义短语；普通库沿用 en/cn */
export function stemOf(word: PlanWord, dim: QuizDim): string {
  if (dim === "w2m") return isSynonymWord(word) ? enPart(String(word.en ?? "")) : String(word.en ?? "");
  if (isSynonymWord(word)) return enPart(String(word.alt ?? ""));
  return String(word.cn ?? "");
}

/**
 * 计划测试的每词题型（v1 规则）：
 * 必默三型全考；高频 / 固定搭配 / 同义替换只考两型，不考拼写。
 * KET 各库沿用 bankMeta.dims。
 */
const PET_TEST_DIMS: Record<string, QuizDim[]> = {
  bimo: ["spell", "w2m", "m2w"],
  gaopin: ["w2m", "m2w"],
  guding: ["w2m", "m2w"],
  tongyi: ["w2m", "m2w"],
};

export function testDimsForBank(key: string, metaDims?: string[]): QuizDim[] {
  const fixed = PET_TEST_DIMS[key];
  if (fixed) return [...fixed];
  const dims = (metaDims ?? []).filter(isDim);
  return dims.length ? dims : [...ALL_DIMS];
}

function shuffleWith<T>(arr: T[], rand: () => number): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function makeQuestion(
  bank: PlanWord[],
  word: PlanWord,
  dim: QuizDim,
  rand: () => number = Math.random,
): QuizQuestion {
  if (dim === "spell") {
    return { word, dim, options: [], answer: word.en };
  }
  // 同义替换库：w2m=看原短语选同义短语，m2w=看同义短语选原短语（不考中文）
  if (isSynonymWord(word)) {
    const fromAlt = dim === "m2w"; // 题干给同义短语，选原短语
    const answer = fromAlt ? enPart(String(word.en ?? "")) : enPart(String(word.alt ?? ""));
    const distractors = shuffleWith(
      bank.filter((w) => w.id !== word.id && isSynonymWord(w)),
      rand,
    )
      .slice(0, 3)
      .map((w) => enPart(String(fromAlt ? w.en : w.alt)));
    const options = shuffleWith([answer, ...distractors], rand);
    return { word, dim, options, answer };
  }
  const distractors = shuffleWith(
    bank.filter((w) => w.id !== word.id),
    rand,
  )
    .slice(0, 3)
    .map((w) => (dim === "w2m" ? w.cn : w.en));
  const answer = dim === "w2m" ? word.cn : word.en;
  const options = shuffleWith([answer, ...distractors], rand);
  return { word, dim, options, answer };
}

export function makeRound(
  bank: PlanWord[],
  count: number,
  dims: QuizDim[],
  picked?: PlanWord[],
): QuizQuestion[] {
  if (bank.length < 4) throw new Error("词库太少，无法生成选择题");
  // picked（错题优先）只决定顺序，仍受题量限制
  const pool = (picked ?? shuffleWith(bank, Math.random)).slice(0, Math.min(count, bank.length));
  return pool.map((word) => makeQuestion(bank, word, dims[Math.floor(Math.random() * dims.length)]));
}

/** 稳定种子：同一组输入（计划时间戳/天/词库）永远得到同一序列 */
export function seedFrom(...parts: Array<string | number>): number {
  let h = 2166136261 >>> 0;
  for (const part of parts) {
    const s = String(part);
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
    h ^= 0x9e3779b9;
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * 计划测试：每个词按该库要求的题型各出一题（逐词交错）。
 * 题组只由「库 + 当天词 + 题型 + 种子」决定，刷新/换设备一致。
 */
export function makeTestRound(
  bank: PlanWord[],
  words: PlanWord[],
  dims: QuizDim[],
  seed: number,
): QuizQuestion[] {
  if (bank.length < 4) throw new Error("词库太少，无法生成选择题");
  const rand = mulberry32(seed);
  const out: QuizQuestion[] = [];
  for (const word of words) {
    for (const dim of dims) out.push(makeQuestion(bank, word, dim, rand));
  }
  return out;
}

/** 判分：忽略首尾空格，大小写不敏感 */
export function checkAnswer(input: string, answer: string): boolean {
  return input.trim().toLowerCase() === answer.trim().toLowerCase();
}
