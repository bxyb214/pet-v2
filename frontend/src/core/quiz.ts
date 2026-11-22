/**
 * 测验生成（V2–V4）纯逻辑。
 * 朗读规则红线：w2m（看词选义）答题前有发音；spell/m2w 答题前不放。
 */
import type { PlanWord } from "./plan";

export type QuizDim = "spell" | "w2m" | "m2w";

export const ALL_DIMS: QuizDim[] = ["w2m", "m2w", "spell"];

export const DIM_LABEL: Record<QuizDim, string> = {
  spell: "拼写",
  w2m: "看词选义",
  m2w: "看义选词",
};

export interface QuizQuestion {
  word: PlanWord;
  dim: QuizDim;
  /** 选择题选项（spell 为空，输入作答） */
  options: string[];
  answer: string;
}

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function makeQuestion(bank: PlanWord[], word: PlanWord, dim: QuizDim): QuizQuestion {
  if (dim === "spell") {
    return { word, dim, options: [], answer: word.en };
  }
  const distractors = shuffle(bank.filter((w) => w.id !== word.id))
    .slice(0, 3)
    .map((w) => (dim === "w2m" ? w.cn : w.en));
  const answer = dim === "w2m" ? word.cn : word.en;
  const options = shuffle([answer, ...distractors]);
  return { word, dim, options, answer };
}

export function makeRound(
  bank: PlanWord[],
  count: number,
  dims: QuizDim[],
  picked?: PlanWord[],
): QuizQuestion[] {
  if (bank.length < 4) throw new Error("词库太少，无法生成选择题");
  const pool = picked ?? shuffle(bank).slice(0, Math.min(count, bank.length));
  return pool.map((word) => makeQuestion(bank, word, dims[Math.floor(Math.random() * dims.length)]));
}

/** 判分：忽略首尾空格，大小写不敏感 */
export function checkAnswer(input: string, answer: string): boolean {
  return input.trim().toLowerCase() === answer.trim().toLowerCase();
}
