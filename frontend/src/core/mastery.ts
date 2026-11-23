/**
 * 单词掌握度：把 mastery / mistakes 折算成「已掌握 / 学习中 / 未学习」。
 *
 * mastered_dims 是并集；某词只有覆盖该词库要求的全部维度才算「已掌握」。
 * 必考维度与计划测试一致：必默三型；高频/固搭/同义两型；KET 两型。
 */
import { testDimsForBank } from "./quiz";

export type MasteryBucket = "mastered" | "learning" | "unlearned";

/** 该词库要求掌握的维度（与计划测试的题型规则一致） */
export function requiredDimsForBank(key: string, metaDims?: string[] | null): string[] {
  return testDimsForBank(key, metaDims ?? undefined);
}

export function bucketOf(
  masteredDims: string[] | undefined,
  mistakeDims: string[] | undefined,
  required: string[],
): MasteryBucket {
  const have = new Set(masteredDims ?? []);
  const owes = (mistakeDims?.length ?? 0) > 0;
  // 还有错题欠账（哪怕只是额外维度）就不算已掌握，避免「已掌握但仍在错题本」
  if (!owes && required.length && required.every((d) => have.has(d))) return "mastered";
  if ((masteredDims?.length ?? 0) > 0 || owes) return "learning";
  return "unlearned";
}

export function masteryPct(masteredDims: string[] | undefined, required: string[]): number {
  if (!required.length) return 0;
  const have = new Set(masteredDims ?? []);
  return Math.round((required.filter((d) => have.has(d)).length / required.length) * 100);
}

export interface MasteryStats {
  total: number;
  mastered: number;
  learning: number;
  unlearned: number;
  masteredPct: number;
  learningPct: number;
  unlearnedPct: number;
}

export function masteryStats(
  words: Array<{ id: string }>,
  mastery: Array<{ word_id: string; mastered_dims: string[] }>,
  mistakes: Array<{ word_id: string; dims: string[] }>,
  required: string[],
): MasteryStats {
  const masteryMap = new Map(mastery.map((m) => [m.word_id, m.mastered_dims]));
  const mistakeMap = new Map(mistakes.map((m) => [m.word_id, m.dims]));
  let mastered = 0;
  let learning = 0;
  let unlearned = 0;
  for (const w of words) {
    const bucket = bucketOf(masteryMap.get(w.id), mistakeMap.get(w.id), required);
    if (bucket === "mastered") mastered += 1;
    else if (bucket === "learning") learning += 1;
    else unlearned += 1;
  }
  const total = words.length;
  // 保留一位小数：1/712 显示 0.1% 而不是 0%
  const pct = (n: number): number => (total ? Math.round((n / total) * 1000) / 10 : 0);
  const masteredPct = pct(mastered);
  const learningPct = Math.min(pct(learning), Math.round((100 - masteredPct) * 10) / 10);
  return {
    total,
    mastered,
    learning,
    unlearned,
    masteredPct,
    learningPct,
    unlearnedPct: total ? Math.round((100 - masteredPct - learningPct) * 10) / 10 : 0,
  };
}
