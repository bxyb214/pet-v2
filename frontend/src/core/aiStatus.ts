/** 付费 AI 状态：额度横幅、锁定态与降级文案（P0-1 / P2-4）。 */
import { api } from "./api";

export type BudgetPeriod = {
  used_milli: number;
  budget_milli: number;
  ratio: number;
  stage: number;
  reset_at: string;
};

export type AiStatus = {
  ai_enabled: boolean;
  speak_enabled: boolean;
  daily: BudgetPeriod;
  monthly: BudgetPeriod;
  remaining_milli: number;
  max_session_sec: number;
  blocked: boolean;
  reason: "" | "not_enabled" | "daily_exhausted" | "monthly_exhausted";
  message: string;
  alert_stage: number;
};

let cache: AiStatus | null = null;

export function cachedAiStatus(): AiStatus | null {
  return cache;
}

/** 退出登录时清掉，避免下一个账号沿用上一个账号的额度状态。 */
export function clearAiStatus(): void {
  cache = null;
}

export async function loadAiStatus(force = false): Promise<AiStatus | null> {
  if (cache && !force) return cache;
  try {
    cache = await api<AiStatus>("/speak/ai_status");
    return cache;
  } catch {
    return cache;
  }
}

/** 是否应锁定付费按钮：未开通或额度用尽。 */
export function paidBlocked(st: AiStatus | null | undefined): boolean {
  if (!st) return false;
  return !st.ai_enabled || st.blocked;
}

/** 顶部横幅：80% 黄色、100% 红色；未开通只锁按钮不弹横幅。 */
export function budgetBanner(st: AiStatus | null | undefined): { tone: "warn" | "danger"; text: string } | null {
  if (!st || !st.ai_enabled) return null;
  if (st.daily.stage >= 2 || st.monthly.stage >= 2) {
    const which = st.daily.stage >= 2 ? "今日" : "本月";
    return { tone: "danger", text: `${which} AI 额度已用完，免费功能仍可用。` };
  }
  if (st.daily.stage === 1 || st.monthly.stage === 1) {
    return { tone: "warn", text: "AI 额度已用 80%，用完将暂停付费功能。" };
  }
  return null;
}

/** 锁定态文案：区分「没开通」与「额度用完」。 */
export function paidLockText(st: AiStatus | null | undefined): string {
  if (!st) return "";
  if (!st.ai_enabled) return "此功能调用外部 AI 接口，有费用，需要找小淏开通。";
  if (st.blocked) return st.message || "AI 额度已用完，免费功能仍可用。";
  return "";
}

export function fmtMilliYuan(milli: number): string {
  return (milli / 1000).toFixed(2) + " 元";
}
