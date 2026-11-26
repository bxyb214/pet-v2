/**
 * 测验生成（V2–V4）纯逻辑。
 * 朗读规则红线：w2m（看词选义）答题前有发音；spell/m2w 答题前不放。
 */
import type { PlanWord } from "./plan";
import { mulberry32, shuffleWith } from "./shuffle";

/** 兼容既有引用：计划测试用稳定种子 */
export { seedFrom } from "./shuffle";

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

/**
 * 计划测试：每个词按该库要求的题型各出一题。
 * 学习按词库原顺序翻卡；测试把当天词确定性乱序后轮流出题，
 * 同一个词的多个题型被拆开，不会「一个词连着考」。
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
  // 先按种子打乱词序，再给每个词排好各题型；出题时每次挑「剩余最多且与上一题不同词」的一组
  const queues = shuffleWith(words, rand).map((word) => ({
    id: word.id,
    qs: dims.map((dim) => makeQuestion(bank, word, dim, rand)),
  }));
  const total = queues.reduce((s, q) => s + q.qs.length, 0);
  const out: QuizQuestion[] = [];
  let prev = "";
  for (let n = 0; n < total; n++) {
    let pick = -1;
    for (let i = 0; i < queues.length; i++) {
      const q = queues[i];
      if (!q.qs.length || q.id === prev) continue;
      if (pick < 0 || q.qs.length > queues[pick].qs.length) pick = i;
    }
    // 只剩同一个词（当天只有 1 个词）时才允许连着考
    if (pick < 0) pick = queues.findIndex((q) => q.qs.length > 0);
    const q = queues[pick];
    out.push(q.qs.shift() as QuizQuestion);
    prev = q.id;
  }
  return out;
}

/** 判分：忽略首尾空格，大小写不敏感 */
export function checkAnswer(input: string, answer: string): boolean {
  return input.trim().toLowerCase() === answer.trim().toLowerCase();
}
