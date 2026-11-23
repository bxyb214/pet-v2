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

/** 与线上 PET 词库同量级，用于验证「每种类型平均分到各天」 */
const petBanks: WordBanks = {
  bimo: makeBank("b", 712),
  gaopin: makeBank("g", 414),
  guding: makeBank("f", 254),
  tongyi: makeBank("t", 300),
};

describe("splitPlan（每种词库各自平均分到各天）", () => {
  it("30 天：每天四库都有词；第 24 天 24+14+9+10=57", () => {
    const plan = splitPlan(petBanks, 30);
    expect(plan.length).toBe(30);
    expect(
      plan.every((d) => ["bimo", "gaopin", "guding", "tongyi"].every((k) => d.banks[k].length > 0)),
    ).toBe(true);
    const d24 = plan[23];
    expect(d24.banks.bimo).toHaveLength(24);
    expect(d24.banks.gaopin).toHaveLength(14);
    expect(d24.banks.guding).toHaveLength(9);
    expect(d24.banks.tongyi).toHaveLength(10);
    expect(d24.total).toBe(57);
  });

  it("每库每天条数差 ≤1；库内顺序不变、不重不漏", () => {
    const plan = splitPlan(petBanks, 30);
    for (const key of Object.keys(petBanks)) {
      const counts = plan.map((d) => d.banks[key].length);
      expect(Math.max(...counts) - Math.min(...counts)).toBeLessThanOrEqual(1);
      const flat = plan.flatMap((d) => d.banks[key]).map((w) => w.id);
      expect(flat).toEqual(petBanks[key].map((w) => w.id));
    }
    expect(validatePlan(petBanks, plan)).toBe(true);
  });

  it("180 天：每个词库每天仍有词（PET 最小库 254 > 180）", () => {
    const plan = splitPlan(petBanks, 180);
    expect(plan).toHaveLength(180);
    expect(plan.every((d) => Object.values(d.banks).every((ws) => ws.length > 0))).toBe(true);
    expect(validatePlan(petBanks, plan)).toBe(true);
  });

  it("小库/天数更多时允许某些天为 0，但仍均匀且不重不漏", () => {
    const small: WordBanks = { bimo: makeBank("b", 5), tongyi: makeBank("t", 3) };
    const plan = splitPlan(small, 10);
    expect(plan).toHaveLength(10);
    expect(plan.reduce((s, d) => s + d.total, 0)).toBe(8);
    expect(validatePlan(small, plan)).toBe(true);
    for (const key of Object.keys(small)) {
      const counts = plan.map((d) => d.banks[key].length);
      expect(Math.max(...counts) - Math.min(...counts)).toBeLessThanOrEqual(1);
    }
  });

  it("库间都参与：第 1 天包含所有有词的词库", () => {
    const plan = splitPlan(banks, 3);
    expect(Object.keys(plan[0].banks).length).toBe(4);
    expect(plan[0].total).toBeGreaterThan(0);
  });

  it("非法天数抛错", () => {
    expect(() => splitPlan(banks, 0)).toThrow();
    expect(() => splitPlan(banks, -3)).toThrow();
    expect(() => splitPlan(banks, 2.5)).toThrow();
  });
});

describe("validatePlan 不变量（不重不漏、顺序不变、每库均匀）", () => {
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

  it("只校验参与切分的库：别的级别词库非空也不影响（回归）", () => {
    const mixed = { ...banks, kword: makeBank("k", 100) };
    const keys = ["bimo", "gaopin", "guding", "tongyi"];
    const plan = splitPlan(mixed, 30, keys);
    expect(validatePlan(mixed, plan, keys)).toBe(true);
    // 不传 keys 会把 kword 也当成本计划的一部分，旧实现正是这样误报
    expect(validatePlan(mixed, plan)).toBe(false);
  });

  it("每库每天条数差 >1 时校验失败（防止退回全局平分）", () => {
    const plan = splitPlan(petBanks, 30);
    const extra = petBanks.bimo[0];
    plan[0].banks.bimo.push(extra);
    plan[29].banks.bimo.pop();
    expect(validatePlan(petBanks, plan)).toBe(false);
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
