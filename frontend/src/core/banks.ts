/** 词库数据加载：静态产物 /data/banks.json（tools/build_data.py 生成）。 */
import type { PlanWord, WordBanks } from "./plan";

export type WordGroups = Record<string, Array<{ key: string; name: string; audio?: string }>>;

/** 每个词库属于哪个考试、显示名、考哪些维度 */
export interface BankMeta {
  exam: string;
  name: string;
  short: string;
  dims: string[];
  desc?: string;
}

/** 考试级别（KET / PET / 未来的 FCE、初中英语） */
export interface ExamMeta {
  id: string;
  name: string;
  desc?: string;
  soon?: boolean;
}

const PET_BANKS = ["bimo", "gaopin", "guding", "tongyi"];
const KET_BANKS = ["kword", "kcore", "kphrase", "kconfuse", "ksyn"];

export const ALL_BANK_KEYS = [...PET_BANKS, ...KET_BANKS];

export const EMPTY_BANKS: WordBanks = Object.fromEntries(ALL_BANK_KEYS.map((k) => [k, []]));

export const DEFAULT_EXAMS: ExamMeta[] = [
  { id: "pet", name: "PET" },
  { id: "ket", name: "KET" },
];

export interface LoadedBanks {
  banks: WordBanks;
  groups: WordGroups;
  bankMeta: Record<string, BankMeta>;
  exams: ExamMeta[];
}

/** 取某个级别下的词库 id（保持 banks.json 里的顺序） */
export function bankKeysOf(meta: Record<string, BankMeta>, exam: string): string[] {
  return Object.keys(meta).filter((k) => meta[k].exam === exam);
}

/** 该级别下「有内容」的词库 id */
export function availableBankKeys(
  banks: WordBanks,
  meta: Record<string, BankMeta>,
  exam: string,
): string[] {
  return bankKeysOf(meta, exam).filter((k) => (banks[k] ?? []).length > 0);
}

export async function loadBanks(): Promise<LoadedBanks> {
  try {
    const res = await fetch("/data/banks.json");
    if (!res.ok) return { banks: EMPTY_BANKS, groups: {}, bankMeta: {}, exams: DEFAULT_EXAMS };
    const json = await res.json();
    const banks: WordBanks = { ...EMPTY_BANKS, ...(json.banks ?? {}) };
    const bankMeta: Record<string, BankMeta> = json.bankMeta ?? {};
    // 老数据没有 bankMeta 时兜底：全部当 PET
    if (!Object.keys(bankMeta).length) {
      for (const k of PET_BANKS) bankMeta[k] = { exam: "pet", name: k, short: k, dims: ["m2w", "w2m", "spell"] };
    }
    return {
      banks,
      groups: json.groups ?? {},
      bankMeta,
      exams: json.exams?.length ? json.exams : DEFAULT_EXAMS,
    };
  } catch {
    return { banks: EMPTY_BANKS, groups: {}, bankMeta: {}, exams: DEFAULT_EXAMS };
  }
}

export type { PlanWord };
