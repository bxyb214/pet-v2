import { describe, expect, it } from "vitest";
import {
  splitPlan, validatePlan, buildReadingPlan, validateReadingPlan, readingDayOf, readingParts,
  type WordBanks,
} from "./plan";

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
    expect(plan[0].banks.bimo.length).toBe(1); // ceil(23/30)=1
    expect(plan[0].banks.gaopin.length).toBe(1);
    expect(plan[0].banks.guding.length).toBe(1);
    expect(plan[0].banks.tongyi.length).toBe(1);
    expect(plan[0].total).toBe(4);
    // 必默 23 词每天 1 个覆盖前 23 天，第 24 天起为空
    expect(plan[22].banks.bimo.length).toBe(1);
    expect(plan[23].banks.bimo.length).toBe(0);
  });

  it("10 天切分：末天吸收余量", () => {
    const plan = splitPlan(banks, 10);
    // 必默 ceil(23/10)=3 → 7 天×3 + 末块 2 → 第 8 天 2 个，第 9 天起 0
    const flat = plan.flatMap((d) => d.banks.bimo).map((w) => w.id);
    expect(flat.length).toBe(23);
    expect(plan[7].banks.bimo.length).toBe(2);
    expect(plan[8].banks.bimo.length).toBe(0);
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
    plan[0].banks.bimo.pop();
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

describe("readingParts（教材选择）", () => {
  const tests = [
    { no: 1, book: "t1", parts: [{ part: 1 }, { part: 2 }] },
    { no: 2, book: "t1", parts: [{ part: 1 }] },
    { no: 1, book: "t2", parts: [{ part: 1 }, { part: 2 }] },
  ];

  it("空选择 = 全部教材，顺序与 tests 一致", () => {
    expect(readingParts(tests)).toEqual([
      { book: "t1", testNo: 1, part: 1 },
      { book: "t1", testNo: 1, part: 2 },
      { book: "t1", testNo: 2, part: 1 },
      { book: "t2", testNo: 1, part: 1 },
      { book: "t2", testNo: 1, part: 2 },
    ]);
    expect(readingParts(tests, [])).toHaveLength(5);
  });

  it("按选择的教材顺序排（t2 在前）", () => {
    expect(readingParts(tests, ["t2", "t1"]).map((p) => p.book)).toEqual([
      "t2", "t2", "t1", "t1", "t1",
    ]);
  });

  it("只选一本教材", () => {
    const only = readingParts(tests, ["t2"]);
    expect(only).toHaveLength(2);
    expect(only.every((p) => p.book === "t2")).toBe(true);
  });

  it("选中的教材一起切分：不重不漏", () => {
    const parts = readingParts(tests, ["t1", "t2"]);
    const plan = buildReadingPlan(parts, 2);
    expect(validateReadingPlan(parts, plan)).toBe(true);
    expect(plan.map((d) => d.parts.length)).toEqual([3, 2]);
  });
});
