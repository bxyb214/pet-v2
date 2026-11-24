import { describe, expect, it } from "vitest";
import {
  budgetBanner,
  fmtMilliYuan,
  paidBlocked,
  paidClickHint,
  paidLockText,
  type AiStatus,
} from "./aiStatus";

function st(over: Partial<AiStatus> = {}): AiStatus {
  return {
    ai_enabled: true,
    speak_enabled: true,
    daily: { used_milli: 0, budget_milli: 500, ratio: 0, stage: 0, reset_at: "" },
    monthly: { used_milli: 0, budget_milli: 10000, ratio: 0, stage: 0, reset_at: "" },
    remaining_milli: 500,
    max_session_sec: 600,
    blocked: false,
    reason: "",
    message: "",
    alert_stage: 0,
    ...over,
  };
}

describe("paidBlocked", () => {
  it("未开通或已拦截时锁定；未知状态不锁", () => {
    expect(paidBlocked(null)).toBe(false);
    expect(paidBlocked(st())).toBe(false);
    expect(paidBlocked(st({ ai_enabled: false }))).toBe(true);
    expect(paidBlocked(st({ blocked: true, reason: "daily_exhausted" }))).toBe(true);
  });
});

describe("budgetBanner", () => {
  it("未开通不弹横幅", () => {
    expect(budgetBanner(null)).toBeNull();
    expect(budgetBanner(st({ ai_enabled: false }))).toBeNull();
  });

  it("80% 黄色、100% 红色", () => {
    expect(budgetBanner(st({ daily: { ...st().daily, stage: 1 } }))).toEqual({
      tone: "warn",
      text: "AI 额度已用 80%，用完将暂停付费功能。",
    });
    expect(budgetBanner(st({ daily: { ...st().daily, stage: 2 } }))).toEqual({
      tone: "danger",
      text: "今日 AI 额度已用完，免费功能仍可用。",
    });
  });

  it("月额度用尽取月文案", () => {
    expect(budgetBanner(st({ monthly: { ...st().monthly, stage: 2 } }))?.text).toBe(
      "本月 AI 额度已用完，免费功能仍可用。",
    );
  });
});

describe("paidLockText", () => {
  it("区分未开通与额度用尽", () => {
    expect(paidLockText(st())).toBe("");
    expect(paidLockText(st({ ai_enabled: false }))).toContain("需要找小淏开通");
    expect(paidLockText(st({ blocked: true, message: "今日 AI 额度已用完" }))).toBe("今日 AI 额度已用完");
    expect(paidLockText(st({ blocked: true }))).toBe("AI 额度已用完，免费功能仍可用。");
  });
});

describe("paidClickHint", () => {
  it("未开通时给完整费用与免费功能提示", () => {
    expect(paidClickHint(st({ ai_enabled: false }))).toBe(
      "此功能调用外部 AI 接口，有费用，需要找小淏开通。免费功能：题库浏览、浏览器朗读、看标准答案。",
    );
  });

  it("额度用尽沿用服务端原因；可用时为空", () => {
    expect(paidClickHint(st())).toBe("");
    expect(paidClickHint(st({ blocked: true, message: "今日 AI 额度已用完" }))).toBe("今日 AI 额度已用完");
    expect(paidClickHint(st({ blocked: true }))).toBe("AI 额度已用完，免费功能仍可用。");
    expect(paidClickHint(null)).toBe("");
  });
});

describe("fmtMilliYuan", () => {
  it("0.001 元为单位转元", () => {
    expect(fmtMilliYuan(1234)).toBe("1.23 元");
    expect(fmtMilliYuan(0)).toBe("0.00 元");
  });
});
