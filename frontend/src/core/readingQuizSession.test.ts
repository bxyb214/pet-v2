import { beforeEach, describe, expect, it } from "vitest";
import {
  clearReadingSession,
  loadReadingSession,
  readingSessionKey,
  READING_SESSION_TTL_MS,
  saveReadingSession,
} from "./readingQuizSession";

const OWNER = "felix";
const SCOPE = "read:t2:3:all";
const SIG = "s1:meaning|s2:blank";

function save(partial: Partial<Parameters<typeof saveReadingSession>[2]> = {}) {
  saveReadingSession(OWNER, SCOPE, {
    sig: SIG,
    idx: 2,
    results: [true, false, null],
    correct_count: 1,
    answered: false,
    picked: -1,
    ...partial,
  });
}

describe("阅读测验续做", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("同一用户、同一范围、题目未变时恢复", () => {
    save();
    const s = loadReadingSession(OWNER, SCOPE, SIG);
    expect(s?.idx).toBe(2);
    expect(s?.results).toEqual([true, false, null]);
    expect(s?.correct_count).toBe(1);
  });

  it("换用户或换题目指纹不恢复", () => {
    save();
    expect(loadReadingSession("other", SCOPE, SIG)).toBeNull();
    expect(loadReadingSession(OWNER, SCOPE, "different")).toBeNull();
  });

  it("过期后清除", () => {
    save();
    const later = Date.now() + READING_SESSION_TTL_MS + 1;
    expect(loadReadingSession(OWNER, SCOPE, SIG, later)).toBeNull();
    expect(localStorage.getItem(readingSessionKey(OWNER, SCOPE))).toBeNull();
  });

  it("损坏数据返回 null 且不抛错", () => {
    localStorage.setItem(readingSessionKey(OWNER, SCOPE), "{not json");
    expect(loadReadingSession(OWNER, SCOPE, SIG)).toBeNull();
  });

  it("保留反馈态（已答未下一题）", () => {
    save({ answered: true, picked: 1 });
    const s = loadReadingSession(OWNER, SCOPE, SIG);
    expect(s?.answered).toBe(true);
    expect(s?.picked).toBe(1);
  });

  it("可以清除", () => {
    save();
    clearReadingSession(OWNER, SCOPE);
    expect(loadReadingSession(OWNER, SCOPE, SIG)).toBeNull();
  });
});
