import { describe, expect, it } from "vitest";
import { AUTO_IMPROVE_MIN_WORDS, createImproveGuard, shouldAutoImprove, wordCount } from "./improve";

describe("wordCount", () => {
  it("按空白分词", () => {
    expect(wordCount("  I  like   apples ")).toBe(3);
    expect(wordCount("")).toBe(0);
  });
});

describe("shouldAutoImprove", () => {
  it("少于 4 个词不自动调用", () => {
    expect(AUTO_IMPROVE_MIN_WORDS).toBe(4);
    expect(shouldAutoImprove("yes")).toBe(false);
    expect(shouldAutoImprove("I like it")).toBe(false);
  });

  it("4 个词及以上自动调用", () => {
    expect(shouldAutoImprove("I like red apples")).toBe(true);
    expect(shouldAutoImprove("  I   like red apples  ")).toBe(true);
  });
});

describe("createImproveGuard", () => {
  it("同一句只放行一次（忽略大小写与首尾空白）", () => {
    const g = createImproveGuard();
    expect(g.take("I like it")).toBe(true);
    expect(g.take("  i like IT ")).toBe(false);
    expect(g.has("I LIKE IT")).toBe(true);
  });

  it("空串不放行，不同句子互不影响", () => {
    const g = createImproveGuard();
    expect(g.take("   ")).toBe(false);
    expect(g.take("one")).toBe(true);
    expect(g.take("two")).toBe(true);
  });
});
