import { describe, expect, it, beforeEach } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useLearningStore } from "./learning";

beforeEach(() => {
  localStorage.clear();
  setActivePinia(createPinia());
});

describe("learning store（无网络，纯本地逻辑）", () => {
  it("recordWrong：全维度重欠 + stage 回 0 + 掌握收回", () => {
    const s = useLearningStore();
    s.recordMastery("w1", ["spell"]);
    s.recordWrong("w1", ["spell", "w2m"]);
    expect(s.data.mistakes[0]).toMatchObject({ word_id: "w1", dims: ["spell", "w2m"], stage: 0, repeats: 0 });
    expect(s.data.mastery[0].mastered_dims).toEqual([]);
  });

  it("recordRight：划单维，dims 空自动移出并记掌握（红线不变量）", () => {
    const s = useLearningStore();
    s.recordWrong("w1", ["w2m", "spell"]);
    s.recordRight("w1", "w2m");
    expect(s.data.mistakes[0].dims).toEqual(["spell"]);
    s.recordRight("w1", "spell");
    expect(s.data.mistakes.length).toBe(0); // dims 空 → 移出错题本
    expect(s.data.mastery[0].mastered_dims).toContain("spell");
  });

  it("markPlanDayDone 并集 + deletePlan 清空", () => {
    const s = useLearningStore();
    s.setPlan(40);
    s.markPlanDayDone(3);
    s.markPlanDayDone(1);
    expect(s.data.plan).toMatchObject({
      length: 40, days_done: ["1", "3"], reading_length: 0, reading_days_done: [], reading_books: [],
    });
    expect(s.data.plan.plan_updated_at).toBeGreaterThan(0);
    s.deletePlan();
    expect(s.data.plan).toMatchObject({
      length: 0, days_done: [], reading_length: 0, reading_days_done: [], reading_books: [],
    });
    expect(s.data.plan.plan_updated_at).toBeGreaterThan(0);
  });

  it("deletePlan 只删词汇计划，阅读计划保留", () => {
    const s = useLearningStore();
    s.setReadingPlan(20, ["t1"]);
    s.setPlan(40);
    s.deletePlan();
    expect(s.data.plan.length).toBe(0);
    expect(s.data.plan.reading_length).toBe(20);
    expect(s.data.plan.reading_books).toEqual(["t1"]);
    expect(s.data.plan.reading_updated_at).toBeGreaterThan(0);
  });

  it("本地持久化：同一用户刷新后数据仍在", () => {
    let s = useLearningStore();
    s.hydrate("felix");
    s.recordMastery("w1", ["spell"]);
    // 模拟重新加载
    setActivePinia(createPinia());
    s = useLearningStore();
    s.hydrate("felix");
    expect(s.data.mastery[0]).toEqual({ word_id: "w1", mastered_dims: ["spell"] });
  });

  it("本地快照按用户隔离：换账号读不到上一个人的数据（admin 曾看到 felix 计划）", () => {
    let s = useLearningStore();
    s.hydrate("felix");
    s.setPlan(30);
    s.markPlanDayDone(1);
    s.recordMastery("w1", ["spell"]);

    setActivePinia(createPinia());
    s = useLearningStore();
    s.hydrate("admin");
    expect(s.data.plan.length).toBe(0);
    expect(s.data.mastery).toHaveLength(0);

    // 换回 felix 仍能看到自己的
    setActivePinia(createPinia());
    s = useLearningStore();
    s.hydrate("felix");
    expect(s.data.plan.length).toBe(30);
    expect(s.data.plan.days_done).toEqual(["1"]);
  });

  it("recordVideoProgress：idx 取大、seen 并集且学完不可撤销", () => {
    const s = useLearningStore();
    s.recordVideoProgress("math:v:g3-40", 30);
    expect(s.progressOf("math:v:g3-40")).toEqual({ idx: 30, seen: [] });
    s.recordVideoProgress("math:v:g3-40", 20); // 回看不倒退
    expect(s.progressOf("math:v:g3-40")?.idx).toBe(30);
    s.recordVideoProgress("math:v:g3-40", 31, true);
    expect(s.progressOf("math:v:g3-40")).toEqual({ idx: 31, seen: ["done"] });
    s.recordVideoProgress("math:v:g3-40", 5); // 学完后重看不会清除 done
    expect(s.progressOf("math:v:g3-40")).toEqual({ idx: 31, seen: ["done"] });
  });

  it("dueMistakes：到期错题筛选", () => {
    const s = useLearningStore();
    s.data.mistakes.push(
      { word_id: "a", dims: ["spell"], stage: 0, due_at: "2026-01-01", repeats: 0 },
      { word_id: "b", dims: ["spell"], stage: 1, due_at: "2099-12-31", repeats: 1 },
    );
    expect(s.dueMistakes).toEqual(["a"]);
  });
});
