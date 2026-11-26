/** 付费 AI 状态：一次性总额度、横幅、锁定态与降级文案（P0-1 / P2-4）。 */
import { api } from "./api";

export type AiCredit = {
  used_milli: number;
  budget_milli: number;
  ratio: number;
  stage: number;
};

export type AiStatus = {
  ai_enabled: boolean;
  speak_enabled: boolean;
  /** 管理员账号：不受总额度拦截，但仍展示用量 */
  unlimited: boolean;
  credit: AiCredit;
  remaining_milli: number;
  max_session_sec: number;
  blocked: boolean;
  reason: "" | "not_enabled" | "credit_exhausted";
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

/** 顶部横幅：80% 黄色、100% 红色；未开通与管理员不限额度不弹。 */
export function budgetBanner(st: AiStatus | null | undefined): { tone: "warn" | "danger"; text: string } | null {
  if (!st || !st.ai_enabled || st.unlimited) return null;
  if (st.credit.stage >= 2) {
    return { tone: "danger", text: "AI 总额度已用完，免费功能仍可用。" };
  }
  if (st.credit.stage === 1) {
    return { tone: "warn", text: "AI 总额度已用 80%，用完将暂停付费功能。" };
  }
  return null;
}

/** 没有 AI 权限时的唯一提示：只在点击置灰按钮时出现，不再整页展示。 */
export const AI_PERMISSION_REQUIRED = "此功能需要 AI 权限，请联系小淏开通。";

/** 锁定态文案：区分「没权限」与「额度用完」。 */
export function paidLockText(st: AiStatus | null | undefined): string {
  if (!st) return "";
  if (!st.ai_enabled) return AI_PERMISSION_REQUIRED;
  if (st.blocked) return st.message || "AI 总额度已用完，免费功能仍可用。";
  return "";
}

/** 点击置灰的付费按钮时展示：没权限给开通提示，额度用尽给服务端原因。 */
export function paidClickHint(st: AiStatus | null | undefined): string {
  if (!st) return "";
  if (!st.ai_enabled) return AI_PERMISSION_REQUIRED;
  if (st.blocked) return st.message || "AI 总额度已用完，免费功能仍可用。";
  return "";
}

export function fmtMilliYuan(milli: number): string {
  return (milli / 1000).toFixed(2) + " 元";
}
