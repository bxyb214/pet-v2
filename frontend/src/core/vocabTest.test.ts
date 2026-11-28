import { describe, expect, it, beforeEach } from "vitest";
import {
  allocateQuota, buildVocabTest, examPools, loadVocabResult, saveVocabResult,
  scoreVocabTest, PER_EXAM, type VocabQuestion,
} from "./vocabTest";
import type { WordBanks } from "./plan";

function bank(prefix: string, n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: `${prefix}${i}`,
    en: `${prefix} word ${i}`,
    cn: `${prefix}释义${i}`,
  }));
}

function makeBanks(): WordBanks {
  return {
    kword: bank("kw", 30),
    kcore: bank("kc", 20),
    kphrase: bank("kp", 15),
    ksyn: [{ id: "ks0", en: "on foot", cn: "走路", alt: "walk", alt_cn: "走路" }],
    bimo: bank("b", 40),
    gaopin: bank("g", 25),
    guding: bank("d", 15),
    tongyi: [{ id: "t0", en: "a DVD", cn: "DVD", alt: "something to keep" }],
  };
}

const seeded = (seed: number) => {
  let a = seed;
  return () => {
    a = (a * 1664525 + 1013904223) >>> 0;
    return a / 4294967296;
  };
};

describe("examPools", () => {
  it("只取本级别三类词库，跳过同义库与空字段", () => {
    const pools = examPools(makeBanks(), "ket");
    expect(pools.map((p) => p.bank)).toEqual(["kword", "kcore", "kphrase"]);
    expect(pools.flatMap((p) => p.words).some((w) => w.id === "ks0")).toBe(false);
    expect(pools.flatMap((p) => p.words)).toHaveLength(65);
  });

  it("跨词库相同英文只保留先出现的词库", () => {
    const banks = makeBanks();
    banks.kcore = [{ id: "dup", en: "kw word 0", cn: "重复" }, ...bank("kc", 5)];
    const pools = examPools(banks, "ket");
    expect(pools[0].words.some((w) => w.id === "kw0")).toBe(true);
    expect(pools[1].words.some((w) => w.id === "dup")).toBe(false);
  });
});

describe("allocateQuota", () => {
  it("名额用满、每库至少 2 题", () => {
    const q = allocateQuota([100, 50, 20], PER_EXAM);
    expect(q.reduce((a, b) => a + b, 0)).toBe(PER_EXAM);
    expect(q.every((n) => n >= 2)).toBe(true);
  });

  it("小词库先取满，不超总数", () => {
    const q = allocateQuota([1, 2, 100], 10);
    expect(q[0]).toBe(1);
    expect(q[1]).toBe(2);
    expect(q.reduce((a, b) => a + b, 0)).toBe(10);
  });
});

describe("buildVocabTest", () => {
  const questions = buildVocabTest(makeBanks(), seeded(7));

  it("KET / PET 各 12 题，共 24 题", () => {
    expect(questions).toHaveLength(PER_EXAM * 2);
    expect(questions.filter((q) => q.item.exam === "ket")).toHaveLength(PER_EXAM);
    expect(questions.filter((q) => q.item.exam === "pet")).toHaveLength(PER_EXAM);
  });

  it("同一词条不重复出题", () => {
    expect(new Set(questions.map((q) => q.item.id)).size).toBe(questions.length);
  });

  it("每题 4 个互不相同的中文选项，且含正确答案", () => {
    for (const q of questions) {
      expect(q.options).toHaveLength(4);
      expect(new Set(q.options).size).toBe(4);
      expect(q.options).toContain(q.answer);
      expect(q.answer).toBe(q.item.cn);
    }
  });
});

describe("scoreVocabTest", () => {
  const banks = makeBanks();
  const questions = buildVocabTest(banks, seeded(11));
  const answerAll = (ok: (q: VocabQuestion) => boolean): string[] =>
    questions.map((q) => (ok(q) ? q.answer : "错误选项"));

  it("全对：KET / PET 都达到，级别为 PET", () => {
    const r = scoreVocabTest(questions, answerAll(() => true), banks);
    expect(r.ket.correct).toBe(PER_EXAM);
    expect(r.ket.verdict).toBe("reached");
    expect(r.pet.verdict).toBe("reached");
    expect(r.level).toBe("pet");
    expect(r.ket.estimated).toBe(r.ket.bankTotal);
    expect(r.estimated).toBe(r.pet.estimated);
  });

  it("只答对 KET：级别为 KET，PET 未达到", () => {
    const r = scoreVocabTest(questions, answerAll((q) => q.item.exam === "ket"), banks);
    expect(r.level).toBe("ket");
    expect(r.ket.verdict).toBe("reached");
    expect(r.pet.verdict).toBe("below");
    expect(r.estimated).toBe(r.ket.estimated);
  });

  it("跳过按答错计，薄弱词库正确率 < 60% 时列出", () => {
    const r = scoreVocabTest(questions, questions.map(() => null), banks);
    expect(r.ket.correct).toBe(0);
    expect(r.ket.verdict).toBe("below");
    expect(r.level).toBe("below");
    expect(r.pet.weak.map((w) => w.bank).sort()).toEqual(["bimo", "gaopin", "guding"]);
  });
});

describe("评测结果本地存取", () => {
  beforeEach(() => localStorage.clear());

  it("按账号隔离存取", () => {
    const banks = makeBanks();
    const questions = buildVocabTest(banks, seeded(3));
    const result = scoreVocabTest(questions, questions.map((q) => q.answer), banks);
    saveVocabResult("kid", result);
    expect(loadVocabResult("kid")?.level).toBe("pet");
    expect(loadVocabResult("other")).toBeNull();
  });

  it("坏数据返回 null，不抛错", () => {
    localStorage.setItem("pet_vocab_test_v1:kid", "{not json");
    expect(loadVocabResult("kid")).toBeNull();
  });
});
