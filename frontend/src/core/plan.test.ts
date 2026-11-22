import { describe, expect, it } from "vitest";
import { splitPlan, validatePlan, buildReadingPlan, validateReadingPlan, readingDayOf, type WordBanks } from "./plan";

function makeBank(prefix: string, n: number) {
  return Array.from({ length: n }, (_, i) => ({ id: `${prefix}-${i + 1}`, en: `word${i}`, cn: `词${i}` }));
}

const banks: WordBanks = {
  bimo: makeBank("b", 23),
  gaopin: makeBank("g", 16),
  guding: makeBank("f", 8),
  tongyi: makeBank("t", 10),
};

describe("splitPlan", () => {
  it("30 天切分：第 1 天 23+16+8+10 → 4 天后必默空", () => {
    const plan = splitPlan(banks, 30);
    expect(plan.length).toBe(30);
    expect(plan[0].bimo.length).toBe(1); // ceil(23/30)=1
    expect(plan[0].gaopin.length).toBe(1);
    expect(plan[0].guding.length).toBe(1);
    expect(plan[0].tongyi.length).toBe(1);
    expect(plan[0].total).toBe(4);
    // 必默 23 词每天 1 个覆盖前 23 天，第 24 天起为空
    expect(plan[22].bimo.length).toBe(1);
    expect(plan[23].bimo.length).toBe(0);
  });

  it("10 天切分：末天吸收余量", () => {
    const plan = splitPlan(banks, 10);
    // 必默 ceil(23/10)=3 → 7 天×3 + 末块 2 → 第 8 天 2 个，第 9 天起 0
    const flat = plan.flatMap((d) => d.bimo).map((w) => w.id);
    expect(flat.length).toBe(23);
    expect(plan[7].bimo.length).toBe(2);
    expect(plan[8].bimo.length).toBe(0);
  });

  it("任意天数（45）不抛错且总天数正确", () => {
    const plan = splitPlan(banks, 45);
    expect(plan.length).toBe(45);
  });

  it("非法天数抛错", () => {
    expect(() => splitPlan(banks, 0)).toThrow();
    expect(() => splitPlan(banks, -3)).toThrow();
    expect(() => splitPlan(banks, 2.5)).toThrow();
  });
});

describe("validatePlan 不变量（不重不漏、顺序不变）", () => {
  it("30/45 天均通过", () => {
    expect(validatePlan(banks, splitPlan(banks, 30))).toBe(true);
    expect(validatePlan(banks, splitPlan(banks, 45))).toBe(true);
    expect(validatePlan(banks, splitPlan(banks, 3))).toBe(true);
  });

  it("篡改后校验失败", () => {
    const plan = splitPlan(banks, 3);
    plan[0].bimo.pop();
    expect(validatePlan(banks, plan)).toBe(false);
  });
});

describe("阅读计划（R9）", () => {
  const parts = Array.from({ length: 36 }, (_, i) => ({ book: "t2", testNo: Math.floor(i / 6) + 1, part: (i % 6) + 1 }));

  it("buildReadingPlan：Part 级切分不重不漏", () => {
    const plan = buildReadingPlan(parts, 12);
    expect(plan.length).toBe(12);
    expect(plan.every((d) => d.parts.length === 3)).toBe(true);
    expect(validateReadingPlan(parts, plan)).toBe(true);
  });

  it("余量吸收：末天配额少", () => {
    const plan = buildReadingPlan(parts.slice(0, 10), 3); // ceil(10/3)=4 → [4,4,2]
    expect(plan.map((d) => d.parts.length)).toEqual([4, 4, 2]);
    expect(validateReadingPlan(parts.slice(0, 10), plan)).toBe(true);
  });

  it("readingDayOf 反查所属天", () => {
    const plan = buildReadingPlan(parts.slice(0, 10), 3);
    expect(readingDayOf(plan, "t2:1:4")).toBe(1); // [0..3]
    expect(readingDayOf(plan, "t2:2:4")).toBe(3); // [8..9]
    expect(readingDayOf(plan, "t2:9:9")).toBe(0);
  });
});
