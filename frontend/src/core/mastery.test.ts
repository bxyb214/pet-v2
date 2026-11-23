import { describe, expect, it } from "vitest";
import {
  bucketOf,
  masteryPct,
  masteryStats,
  requiredDimsForBank,
} from "./mastery";

const DIMS = ["w2m", "m2w", "spell"];

describe("requiredDimsForBank", () => {
  it("与计划测试题型规则一致：必默三型、其他 PET 库两型、KET 两型", () => {
    expect(requiredDimsForBank("bimo")).toEqual(["spell", "w2m", "m2w"]);
    expect(requiredDimsForBank("gaopin")).toEqual(["w2m", "m2w"]);
    expect(requiredDimsForBank("kword", ["m2w", "w2m"])).toEqual(["m2w", "w2m"]);
    expect(requiredDimsForBank("unknown")).toEqual(DIMS);
  });
});

describe("bucketOf", () => {
  it("覆盖全部要求维度才算已掌握", () => {
    expect(bucketOf(["w2m", "m2w", "spell"], [], DIMS)).toBe("mastered");
    expect(bucketOf(["w2m", "m2w", "spell"], [], ["m2w", "w2m"])).toBe("mastered");
    expect(bucketOf(["w2m", "m2w"], [], DIMS)).toBe("learning");
  });

  it("有部分掌握或错题欠账算学习中；都没有算未学习", () => {
    expect(bucketOf(["w2m"], [], DIMS)).toBe("learning");
    expect(bucketOf([], ["spell", "w2m"], DIMS)).toBe("learning");
    expect(bucketOf([], [], DIMS)).toBe("unlearned");
    expect(bucketOf(undefined, undefined, DIMS)).toBe("unlearned");
  });

  it("必考维度已掌握但仍有错题欠账 → 学习中（不会带着错题显示已掌握）", () => {
    expect(bucketOf(["w2m", "m2w"], ["spell"], ["w2m", "m2w"])).toBe("learning");
  });
});

describe("masteryPct", () => {
  it("按该词库要求维度计算百分比", () => {
    expect(masteryPct(["w2m", "m2w"], DIMS)).toBe(67);
    expect(masteryPct(["w2m", "m2w"], ["m2w", "w2m"])).toBe(100);
    expect(masteryPct(["spell"], ["m2w", "w2m"])).toBe(0);
    expect(masteryPct([], DIMS)).toBe(0);
  });
});

describe("masteryStats", () => {
  const words = [{ id: "a" }, { id: "b" }, { id: "c" }, { id: "d" }];
  const mastery = [
    { word_id: "a", mastered_dims: DIMS },
    { word_id: "b", mastered_dims: ["w2m"] },
  ];
  const mistakes = [{ word_id: "c", dims: ["w2m"] }];

  it("三类计数与比例（百分比合计 100）", () => {
    const s = masteryStats(words, mastery, mistakes, DIMS);
    expect(s).toMatchObject({ total: 4, mastered: 1, learning: 2, unlearned: 1 });
    expect(s.masteredPct + s.learningPct + s.unlearnedPct).toBeCloseTo(100);
    expect(s).toMatchObject({ masteredPct: 25, learningPct: 50, unlearnedPct: 25 });
  });

  it("词库要求两型时，两维全掌握即已掌握", () => {
    const twoDim = [
      { word_id: "a", mastered_dims: DIMS },
      { word_id: "b", mastered_dims: ["w2m", "m2w"] },
    ];
    const s = masteryStats(words, twoDim, mistakes, ["w2m", "m2w"]);
    expect(s.mastered).toBe(2); // a + b
    expect(s.learning).toBe(1); // c
    expect(s.unlearned).toBe(1); // d
  });

  it("空词库不除零", () => {
    expect(masteryStats([], mastery, mistakes, DIMS)).toMatchObject({
      total: 0, mastered: 0, learning: 0, unlearned: 0,
      masteredPct: 0, learningPct: 0, unlearnedPct: 0,
    });
  });
});
