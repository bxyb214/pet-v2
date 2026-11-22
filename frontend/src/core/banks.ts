/** 词库数据加载：静态产物 /data/banks.json（tools/build_data.py 生成）。 */
import type { WordBanks } from "./plan";

export type WordGroups = Record<string, Array<{ key: string; name: string; audio: string }>>;

export const EMPTY_BANKS: WordBanks = { bimo: [], gaopin: [], guding: [], tongyi: [] };

export interface LoadedBanks {
  banks: WordBanks;
  groups: WordGroups;
}

export async function loadBanks(): Promise<LoadedBanks> {
  try {
    const res = await fetch("/data/banks.json");
    if (!res.ok) return { banks: EMPTY_BANKS, groups: {} };
    const json = await res.json();
    return {
      banks: { ...EMPTY_BANKS, ...(json.banks ?? {}) },
      groups: json.groups ?? {},
    };
  } catch {
    return { banks: EMPTY_BANKS, groups: {} };
  }
}
