import { describe, expect, it } from "vitest";
import { dimLabel, focusLabel, gradePlan, nextGapLabel } from "./review";

describe("gradePlan", () => {
  const dims = ["grammar:past-tense", "vocab:weekend"];

  it("85 分以上划掉全部维度并前进", () => {
    const p = gradePlan(90, dims);
    expect(p.dims_ok).toEqual(dims);
    expect(p.next).toBe("advance");
  });

  it("60~84 分不划维度，今天再练", () => {
    const p = gradePlan(72, dims);
    expect(p.dims_ok).toEqual([]);
    expect(p.next).toBe("retry");
  });

  it("60 分以下回第 1 阶段", () => {
    const p = gradePlan(40, dims);
    expect(p.next).toBe("reset");
  });

  it("边界 85 / 60", () => {
    expect(gradePlan(85, dims).next).toBe("advance");
    expect(gradePlan(84, dims).next).toBe("retry");
    expect(gradePlan(60, dims).next).toBe("retry");
    expect(gradePlan(59, dims).next).toBe("reset");
  });
});

describe("labels", () => {
  it("维度中文化", () => {
    expect(dimLabel("grammar:past-tense")).toBe("语法·past-tense");
    expect(dimLabel("vocab")).toBe("词汇");
    expect(dimLabel("whatever:x")).toBe("表达·x");
  });

  it("focus 中文化", () => {
    expect(focusLabel("phrase")).toBe("句型");
    expect(focusLabel("other")).toBe("表达");
  });

  it("间隔标签", () => {
    expect(nextGapLabel(0)).toBe("2 天后再练");
    expect(nextGapLabel(3)).toBe("15 天后再练");
    expect(nextGapLabel(99)).toBe("15 天后再练");
  });
});
