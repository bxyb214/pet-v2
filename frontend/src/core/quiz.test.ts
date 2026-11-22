import { describe, expect, it } from "vitest";
import { makeQuestion, makeRound, checkAnswer, ALL_DIMS, type QuizDim } from "./quiz";
import type { PlanWord } from "./plan";

function makeBank(n: number): PlanWord[] {
  return Array.from({ length: n }, (_, i) => ({ id: `w${i}`, en: `word${i}`, cn: `词义${i}` }));
}

describe("makeQuestion", () => {
  const bank = makeBank(10);
  const word = bank[0];

  it("w2m：题干为英文，选项 4 个含正确中文", () => {
    const q = makeQuestion(bank, word, "w2m");
    expect(q.options.length).toBe(4);
    expect(q.options).toContain(word.cn);
    expect(q.answer).toBe(word.cn);
    expect(new Set(q.options).size).toBe(4);
  });

  it("m2w：题干为中文，选项为英文", () => {
    const q = makeQuestion(bank, word, "m2w");
    expect(q.answer).toBe(word.en);
    expect(q.options).toContain(word.en);
  });

  it("spell：无选项，答案为英文", () => {
    const q = makeQuestion(bank, word, "spell");
    expect(q.options).toEqual([]);
    expect(q.answer).toBe(word.en);
  });
});

describe("makeRound", () => {
  it("按数量生成，dims 随机分布", () => {
    const round = makeRound(makeBank(50), 10, ALL_DIMS);
    expect(round.length).toBe(10);
    expect(new Set(round.map((q) => q.word.id)).size).toBe(10); // 本轮不重复
    const dims = new Set(round.map((q) => q.dim));
    expect(dims.size).toBeGreaterThan(0);
  });

  it("指定 picked（错题优先场景）", () => {
    const bank = makeBank(20);
    const picked = [bank[3], bank[7]];
    const round = makeRound(bank, 2, ["w2m" as QuizDim], picked);
    expect(round.map((q) => q.word.id)).toEqual(["w3", "w7"]);
  });

  it("词库 <4 抛错", () => {
    expect(() => makeRound(makeBank(3), 5, ALL_DIMS)).toThrow();
  });
});

describe("checkAnswer", () => {
  it("忽略大小写与首尾空格", () => {
    expect(checkAnswer(" Apple ", "apple")).toBe(true);
    expect(checkAnswer("Apple", "banana")).toBe(false);
  });
});
