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
    expect(s.data.plan).toEqual({ length: 40, days_done: ["1", "3"], reading_length: 0, reading_days_done: [] });
    s.deletePlan();
    expect(s.data.plan).toEqual({ length: 0, days_done: [], reading_length: 0, reading_days_done: [] });
  });

  it("本地持久化：刷新后数据仍在", () => {
    let s = useLearningStore();
    s.recordMastery("w1", ["spell"]);
    // 模拟重新加载
    setActivePinia(createPinia());
    s = useLearningStore();
    expect(s.data.mastery[0]).toEqual({ word_id: "w1", mastered_dims: ["spell"] });
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
