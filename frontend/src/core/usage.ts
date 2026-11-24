/** 用户端 AI 计费统计：类型、请求与展示格式化（M4）。 */
import { api } from "./api";
import type { AiStatus } from "./aiStatus";

export type UsageMetrics = {
  rt_seconds: number;
  rt_ai_seconds: number;
  soe_calls: number;
  llm_in_tok: number;
  llm_out_tok: number;
  llm_tok: number;
  tts_calls: number;
  tts_chars: number;
  tts_cache_hits: number;
  est_cost_milli: number;
};

export type UsageTotals = UsageMetrics & { active_days: number };
export type UsageDay = UsageMetrics & { day: string };

export type MyUsage = {
  month: string;
  status: AiStatus;
  totals: {
    today: UsageTotals;
    week: UsageTotals;
    month: UsageTotals;
    year: UsageTotals;
  };
  days: UsageDay[];
};

export async function loadMyUsage(month?: string): Promise<MyUsage> {
  const q = month ? `?month=${encodeURIComponent(month)}` : "";
  return api<MyUsage>(`/usage/me${q}`);
}

export function fmtMilli(milli: number): string {
  return (milli / 1000).toFixed(2) + " 元";
}

export function fmtMinutes(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s === 0) return "0 分";
  if (s < 60) return `${s} 秒`;
  return `${Math.round(s / 60)} 分`;
}

export function fmtChars(chars: number): string {
  const n = Math.max(0, Math.round(chars));
  return n >= 10000 ? `${(n / 10000).toFixed(1)} 万` : String(n);
}

/** 本地月份 YYYY-MM（月份选择器用；记账与展示口径仍以服务端北京时间为准）。 */
export function localMonth(ts: number): string {
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
