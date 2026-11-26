import { beforeEach, describe, expect, it } from "vitest";
import {
  QUIZ_SESSION_TTL_MS,
  QUIZ_SESSION_VERSION,
  clearQuizSession,
  firstUnanswered,
  freeScope,
  loadQuizSession,
  planDayAllDone,
  planScope,
  pruneQuizSessions,
  quizSessionKey,
  resumePosition,
  saveQuizSession,
  sessionMatches,
  type QuizSession,
  type QuizSessionInput,
} from "./quizSession";
import type { QuizQuestion } from "./quiz";

function question(id: string): QuizQuestion {
  return {
    word: { id, en: `word ${id}`, cn: `词义 ${id}` },
    dim: "w2m",
    options: [`词义 ${id}`, "其他 1", "其他 2", "其他 3"],
    answer: `词义 ${id}`,
  };
}

function input(overrides: Partial<QuizSessionInput> = {}): QuizSessionInput {
  return {
    mode: "plan",
    plan_day: 1,
    plan_length: 30,
    plan_updated_at: 100,
    bank: "bimo",
    count: 10,
    mistake_first: true,
    round: [question("w1"), question("w2")],
    results: [true, null],
    correct_count: 1,
    wrong_words: [],
    ...overrides,
  };
}

const PLAN_SCOPE = planScope("felix", 100, 1, "bimo");

beforeEach(() => {
  localStorage.clear();
});

describe("quizSession 作用域存取", () => {
  it("保存后可按作用域读回，轮次/结果/错词完整保留", () => {
    saveQuizSession(PLAN_SCOPE, input({ wrong_words: [{ id: "w9", en: "nine", cn: "九" }] }));
    const s = loadQuizSession(PLAN_SCOPE);
    expect(s).not.toBeNull();
    expect(s!.version).toBe(QUIZ_SESSION_VERSION);
    expect(s!.round.map((q) => q.word.id)).toEqual(["w1", "w2"]);
    expect(s!.results).toEqual([true, null]);
    expect(s!.correct_count).toBe(1);
    expect(s!.wrong_words[0]).toMatchObject({ id: "w9" });
    expect(quizSessionKey(PLAN_SCOPE)).toContain("pet_quiz_session::plan:felix:100:1:bimo");
  });

  it("同一天不同词库 / 不同天 / 不同用户互不覆盖", () => {
    saveQuizSession(PLAN_SCOPE, input());
    saveQuizSession(planScope("felix", 100, 1, "gaopin"), input({ bank: "gaopin", results: [null, null] }));
    saveQuizSession(planScope("felix", 100, 2, "bimo"), input({ plan_day: 2 }));
    saveQuizSession(planScope("admin", 100, 1, "bimo"), input());

    expect(loadQuizSession(PLAN_SCOPE)!.bank).toBe("bimo");
    expect(loadQuizSession(planScope("felix", 100, 1, "gaopin"))!.bank).toBe("gaopin");
    expect(loadQuizSession(planScope("felix", 100, 2, "bimo"))!.plan_day).toBe(2);
    expect(loadQuizSession(planScope("admin", 100, 1, "bimo"))).not.toBeNull();
    expect(loadQuizSession(planScope("nobody", 100, 1, "bimo"))).toBeNull();
  });

  it("自由测验使用独立作用域", () => {
    saveQuizSession(freeScope("felix"), input({ mode: "free", plan_day: 0, plan_length: 0, plan_updated_at: 0 }));
    expect(loadQuizSession(freeScope("felix"))!.mode).toBe("free");
    expect(loadQuizSession(PLAN_SCOPE)).toBeNull();
  });

  it("超过 7 天自动失效并清除", () => {
    saveQuizSession(PLAN_SCOPE, input(), 1_000);
    expect(loadQuizSession(PLAN_SCOPE, 1_000 + QUIZ_SESSION_TTL_MS)).not.toBeNull();
    expect(loadQuizSession(PLAN_SCOPE, 1_001 + QUIZ_SESSION_TTL_MS)).toBeNull();
    expect(localStorage.getItem(quizSessionKey(PLAN_SCOPE))).toBeNull();
  });

  it("损坏 JSON / 版本不符 / results 长度不符 → 丢弃", () => {
    localStorage.setItem(quizSessionKey(PLAN_SCOPE), "{not json");
    expect(loadQuizSession(PLAN_SCOPE)).toBeNull();

    saveQuizSession(PLAN_SCOPE, input());
    const raw = JSON.parse(localStorage.getItem(quizSessionKey(PLAN_SCOPE))!) as QuizSession;
    localStorage.setItem(quizSessionKey(PLAN_SCOPE), JSON.stringify({ ...raw, version: 99 }));
    expect(loadQuizSession(PLAN_SCOPE)).toBeNull();

    saveQuizSession(PLAN_SCOPE, input());
    localStorage.setItem(
      quizSessionKey(PLAN_SCOPE),
      JSON.stringify({ ...payload(), results: [true] }),
    );
    expect(loadQuizSession(PLAN_SCOPE)).toBeNull();
  });

  it("空作用域不写盘；clear 删除对应键", () => {
    saveQuizSession("", input());
    expect(localStorage.length).toBe(0);
    saveQuizSession(PLAN_SCOPE, input());
    clearQuizSession(PLAN_SCOPE);
    expect(loadQuizSession(PLAN_SCOPE)).toBeNull();
  });

  it("prune 清理过期与旧计划代际，保留当前计划/自由/其他用户", () => {
    const now = 10_000_000;
    saveQuizSession(planScope("felix", 100, 1, "bimo"), input(), now);
    saveQuizSession(planScope("felix", 100, 1, "gaopin"), input({ bank: "gaopin" }), now);
    saveQuizSession(
      freeScope("felix"),
      input({ mode: "free", plan_day: 0, plan_length: 0, plan_updated_at: 0 }),
      now,
    );
    saveQuizSession(planScope("felix", 50, 1, "bimo"), input(), now); // 旧计划代际
    saveQuizSession(planScope("admin", 100, 1, "bimo"), input(), now); // 其他用户
    localStorage.setItem("pet_quiz_session::felix", "{}"); // v1 旧键
    saveQuizSession(
      planScope("felix", 100, 2, "bimo"),
      input({ plan_day: 2 }),
      now - QUIZ_SESSION_TTL_MS - 1,
    ); // 已过期

    pruneQuizSessions("felix", 100, now);

    expect(loadQuizSession(planScope("felix", 100, 1, "bimo"), now)).not.toBeNull();
    expect(loadQuizSession(planScope("felix", 100, 1, "gaopin"), now)).not.toBeNull();
    expect(loadQuizSession(freeScope("felix"), now)).not.toBeNull();
    expect(loadQuizSession(planScope("felix", 50, 1, "bimo"), now)).toBeNull();
    expect(loadQuizSession(planScope("felix", 100, 2, "bimo"), now)).toBeNull();
    expect(loadQuizSession(planScope("admin", 100, 1, "bimo"), now)).not.toBeNull();
    expect(localStorage.getItem("pet_quiz_session::felix")).toBeNull();
  });
});

describe("sessionMatches", () => {
  const saved = {
    ...input(),
    version: QUIZ_SESSION_VERSION,
    saved_at: Date.now(),
  } as QuizSession;

  it("计划模式：计划天数/结构时间戳/指定日/词库一致才恢复", () => {
    expect(
      sessionMatches(saved, {
        mode: "plan", planLength: 30, planUpdatedAt: 100, planDay: null, bank: "",
      }),
    ).toBe(true);
    expect(
      sessionMatches(saved, {
        mode: "plan", planLength: 30, planUpdatedAt: 100, planDay: 1, bank: "bimo",
      }),
    ).toBe(true);
    expect(
      sessionMatches(saved, {
        mode: "plan", planLength: 20, planUpdatedAt: 100, planDay: null, bank: "",
      }),
    ).toBe(false);
    expect(
      sessionMatches(saved, {
        mode: "plan", planLength: 30, planUpdatedAt: 200, planDay: null, bank: "",
      }),
    ).toBe(false);
    expect(
      sessionMatches(saved, {
        mode: "plan", planLength: 30, planUpdatedAt: 100, planDay: 2, bank: "",
      }),
    ).toBe(false);
    expect(
      sessionMatches(saved, {
        mode: "plan", planLength: 30, planUpdatedAt: 100, planDay: null, bank: "gaopin",
      }),
    ).toBe(false);
  });

  it("自由模式：带词库时须一致，不带词库恢复原轮", () => {
    const free = { ...saved, mode: "free" as const, bank: "bimo" };
    expect(
      sessionMatches(free, { mode: "free", planLength: 0, planUpdatedAt: 0, planDay: null, bank: "" }),
    ).toBe(true);
    expect(
      sessionMatches(free, { mode: "free", planLength: 0, planUpdatedAt: 0, planDay: null, bank: "bimo" }),
    ).toBe(true);
    expect(
      sessionMatches(free, { mode: "free", planLength: 0, planUpdatedAt: 0, planDay: null, bank: "tongyi" }),
    ).toBe(false);
  });

  it("模式不同不恢复", () => {
    expect(
      sessionMatches(saved, { mode: "free", planLength: 30, planUpdatedAt: 100, planDay: null, bank: "" }),
    ).toBe(false);
  });
});

describe("planDayAllDone（当天各库是否都测完）", () => {
  const states = {
    bimo: { finished: true },
    gaopin: { finished: true },
    guding: { finished: false },
  };

  it("所有有词的库都完成才为 true", () => {
    expect(planDayAllDone(states, ["bimo", "gaopin"])).toBe(true);
    expect(planDayAllDone(states, ["bimo", "gaopin", "guding"])).toBe(false);
  });

  it("空词库/缺状态不算完成；当天没有任何库时不为 true", () => {
    expect(planDayAllDone(states, [])).toBe(false);
    expect(planDayAllDone(states, ["bimo", "tongyi"])).toBe(false);
    expect(planDayAllDone({}, ["bimo"])).toBe(false);
  });
});

describe("firstUnanswered / resumePosition", () => {  it("定位第一道未答题；全部答完返回 -1", () => {
    expect(firstUnanswered([true, false, null, null])).toBe(2);
    expect(firstUnanswered([true, false])).toBe(-1);
    expect(firstUnanswered([])).toBe(-1);
  });

  it("停在第一道未答题；全部答完停在结算页", () => {
    expect(resumePosition({ round: [question("w1"), question("w2")], results: [true, null] }))
      .toEqual({ index: 1, finished: false });
    expect(resumePosition({ round: [question("w1"), question("w2")], results: [true, false] }))
      .toEqual({ index: 1, finished: true });
  });
});

/** 与 saveQuizSession 写入的形状一致，便于构造非法变体 */
function payload(): QuizSession {
  return {
    version: QUIZ_SESSION_VERSION,
    saved_at: Date.now(),
    ...input(),
  };
}
