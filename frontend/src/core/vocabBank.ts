/**
 * 单词评测题库加载：/data/vocab-test.json（tools/build_vocab_test.py 生成）。
 * 题库缺失或格式不对时返回 null，由页面回退到 banks.json + fromWordBanks。
 */
import type { WordBanks } from "./plan";
import {
  BANK_SHORT, EXAM_BANKS,
  type ExamId, type VocabBank, type VocabBankPool, type VocabBankWord,
} from "./vocabTest";

interface RawWord {
  id?: unknown;
  en?: unknown;
  cn?: unknown;
  hits?: unknown;
}

interface RawPool {
  key?: unknown;
  name?: unknown;
  words?: unknown;
}

const norm = (s: string): string => s.replace(/\s+/g, " ").trim().toLowerCase();

function poolsOf(raw: unknown, exam: ExamId): VocabBankPool[] {
  if (!Array.isArray(raw)) return [];
  const seen = new Set<string>();
  const out: VocabBankPool[] = [];
  for (const item of raw as RawPool[]) {
    if (!item || typeof item !== "object") continue;
    const key = String(item.key ?? "").trim();
    const name = String(item.name ?? "").trim();
    if (!key || !Array.isArray(item.words)) continue;
    const words: VocabBankWord[] = [];
    for (const rawWord of item.words as RawWord[]) {
      if (!rawWord || typeof rawWord !== "object") continue;
      const id = String(rawWord.id ?? "").trim();
      const en = String(rawWord.en ?? "").trim();
      const cn = String(rawWord.cn ?? "").trim();
      if (!id || !en || !cn) continue;
      const k = norm(en);
      if (seen.has(k)) continue;
      seen.add(k);
      const hits = Number(rawWord.hits);
      words.push({ id, en, cn, hits: Number.isFinite(hits) && hits > 0 ? Math.round(hits) : 0, exam, bank: key });
    }
    if (words.length) out.push({ key, name: name || BANK_SHORT[key] || key, exam, words });
  }
  return out;
}

/** 读取静态题库；不存在/404/格式不对都返回 null（页面走兜底） */
export async function loadVocabBank(): Promise<VocabBank | null> {
  try {
    const res = await fetch("/data/vocab-test.json", { cache: "no-cache" });
    if (!res.ok) return null;
    const data = (await res.json()) as { exams?: Record<string, { banks?: unknown }> };
    const ket = poolsOf(data?.exams?.ket?.banks, "ket");
    const pet = poolsOf(data?.exams?.pet?.banks, "pet");
    if (!ket.length || !pet.length) return null;
    return { ket, pet };
  } catch {
    return null;
  }
}

/** 从 banks.json 构造无真题标签的题库（fresh clone / 忘记跑构建时的兜底） */
export function fromWordBanks(
  banks: WordBanks,
  meta?: Record<string, { short?: string }>,
): VocabBank {
  const build = (exam: ExamId): VocabBankPool[] => {
    const seen = new Set<string>();
    const pools: VocabBankPool[] = [];
    for (const key of EXAM_BANKS[exam]) {
      const words: VocabBankWord[] = [];
      for (const w of banks[key] ?? []) {
        const en = String(w.en ?? "").trim();
        const cn = String(w.cn ?? "").trim();
        if (!en || !cn) continue;
        const k = norm(en);
        if (seen.has(k)) continue;
        seen.add(k);
        words.push({
          id: String(w.id ?? `${key}-${k}`),
          en,
          cn,
          hits: 0,
          exam,
          bank: key,
        });
      }
      if (words.length) {
        pools.push({ key, name: meta?.[key]?.short || BANK_SHORT[key] || key, exam, words });
      }
    }
    return pools;
  };
  return { ket: build("ket"), pet: build("pet") };
}
