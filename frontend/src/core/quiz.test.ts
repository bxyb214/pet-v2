import { describe, expect, it } from "vitest";
import {
  makeQuestion, makeRound, makeTestRound, seedFrom, testDimsForBank,
  checkAnswer, ALL_DIMS, type QuizDim,
} from "./quiz";
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

  it("错题优先也只取题量上限（不会把整库都排进来）", () => {
    const bank = makeBank(50);
    const picked = bank.slice(0, 8);
    const round = makeRound(bank, 3, ["w2m" as QuizDim], picked);
    expect(round.map((q) => q.word.id)).toEqual(["w0", "w1", "w2"]);
  });

  it("词库 <4 抛错", () => {
    expect(() => makeRound(makeBank(3), 5, ALL_DIMS)).toThrow();
  });
});

describe("testDimsForBank（v1 计划测试规则）", () => {
  it("必默三型全考；高频/固搭/同义只考两型（不拼写）", () => {
    expect(testDimsForBank("bimo")).toEqual(["spell", "w2m", "m2w"]);
    for (const k of ["gaopin", "guding", "tongyi"]) {
      expect(testDimsForBank(k)).toEqual(["w2m", "m2w"]);
    }
  });

  it("KET 沿用 bankMeta.dims；异常空配置回退全三型", () => {
    expect(testDimsForBank("kword", ["m2w", "w2m"])).toEqual(["m2w", "w2m"]);
    expect(testDimsForBank("unknown")).toEqual(ALL_DIMS);
  });
});

describe("makeTestRound（计划测试按词出多题）", () => {
  const bank = makeBank(10);
  const words = bank.slice(0, 3);

  it("每个词按题型各出一题：必默 3 题/词，其他 2 题/词", () => {
    const bimo = makeTestRound(bank, words, testDimsForBank("bimo"), 1);
    const high = makeTestRound(bank, words, testDimsForBank("gaopin"), 1);
    expect(bimo.length).toBe(9);
    expect(high.length).toBe(6);
    expect(bimo.map((q) => q.word.id)).toEqual([
      "w0", "w0", "w0", "w1", "w1", "w1", "w2", "w2", "w2",
    ]);
    expect(bimo.map((q) => q.dim)).toEqual([
      "spell", "w2m", "m2w", "spell", "w2m", "m2w", "spell", "w2m", "m2w",
    ]);
    expect(high.map((q) => q.dim)).toEqual(["w2m", "m2w", "w2m", "m2w", "w2m", "m2w"]);
  });

  it("同种子完全一致（题目顺序 + 选项顺序），不同种子选项会变化", () => {
    const a = makeTestRound(bank, words, testDimsForBank("gaopin"), seedFrom(100, 1, "gaopin"));
    const b = makeTestRound(bank, words, testDimsForBank("gaopin"), seedFrom(100, 1, "gaopin"));
    const c = makeTestRound(bank, words, testDimsForBank("gaopin"), seedFrom(200, 1, "gaopin"));
    expect(a).toEqual(b);
    expect(a[0].options).not.toEqual(c[0].options);
  });
});

describe("checkAnswer", () => {
  it("忽略大小写与首尾空格", () => {
    expect(checkAnswer(" Apple ", "apple")).toBe(true);
    expect(checkAnswer("Apple", "banana")).toBe(false);
  });
});
