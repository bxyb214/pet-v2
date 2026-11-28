import { describe, expect, it, beforeEach } from "vitest";
import {
  allocateQuota, buildVocabTest, loadVocabResult, saveVocabResult,
  scoreVocabTest, vocabResultKey, EXAM_SHARE, PER_EXAM,
  type ExamId, type VocabBank, type VocabBankPool, type VocabQuestion,
} from "./vocabTest";
import { fromWordBanks } from "./vocabBank";
import type { WordBanks } from "./plan";

function makePool(exam: ExamId, key: string, n: number, tagged = 0): VocabBankPool {
  return {
    key,
    name: key,
    exam,
    words: Array.from({ length: n }, (_, i) => ({
      id: `${exam}-${key}-${i}`,
      en: `${exam} ${key} word ${i}`,
      cn: `${exam}${key}释义${i}`,
      hits: i < tagged ? 3 : 0,
      exam,
      bank: key,
    })),
  };
}

function makeBank(): VocabBank {
  return {
    ket: [
      makePool("ket", "kword", 30, 18),
      makePool("ket", "kcore", 20, 12),
      makePool("ket", "kphrase", 15, 9),
    ],
    pet: [
      makePool("pet", "bimo", 40, 24),
      makePool("pet", "gaopin", 25, 15),
      makePool("pet", "guding", 15, 9),
    ],
  };
}

/** 旧版 banks.json 形状，用于兜底转换测试 */
function makeBanks(): WordBanks {
  const bank = (prefix: string, n: number) =>
    Array.from({ length: n }, (_, i) => ({
      id: `${prefix}${i}`,
      en: `${prefix} word ${i}`,
      cn: `${prefix}释义${i}`,
    }));
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

const quotaOf = (bank: VocabBank, exam: ExamId): number[] =>
  allocateQuota(bank[exam].map((p) => p.words.length), PER_EXAM);

const expectedTagged = (bank: VocabBank, exam: ExamId): number[] => {
  const quotas = quotaOf(bank, exam);
  return bank[exam].map((p, i) =>
    Math.min(p.words.filter((w) => w.hits > 0).length, Math.round(quotas[i] * EXAM_SHARE)),
  );
};

describe("allocateQuota", () => {
  it("真实词库规模：KET [16,5,4]、PET [11,8,6]", () => {
    expect(allocateQuota([855, 182, 144], PER_EXAM)).toEqual([16, 5, 4]);
    expect(allocateQuota([661, 409, 252], PER_EXAM)).toEqual([11, 8, 6]);
  });

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
  const bank = makeBank();
  const questions = buildVocabTest(bank, seeded(7));

  it("KET / PET 各 25 题，共 50 题", () => {
    expect(questions).toHaveLength(PER_EXAM * 2);
    expect(questions.filter((q) => q.item.exam === "ket")).toHaveLength(PER_EXAM);
    expect(questions.filter((q) => q.item.exam === "pet")).toHaveLength(PER_EXAM);
  });

  it("同一词条、同一英文不重复出题", () => {
    expect(new Set(questions.map((q) => q.item.id)).size).toBe(questions.length);
    expect(new Set(questions.map((q) => q.item.en.toLowerCase())).size).toBe(questions.length);
  });

  it("每库题量与真题词数量符合配额", () => {
    for (const exam of ["ket", "pet"] as ExamId[]) {
      const quotas = quotaOf(bank, exam);
      const tagged = expectedTagged(bank, exam);
      bank[exam].forEach((pool, i) => {
        const qs = questions.filter((q) => q.item.exam === exam && q.item.bank === pool.key);
        expect(qs).toHaveLength(quotas[i]);
        expect(qs.filter((q) => q.item.hits > 0)).toHaveLength(tagged[i]);
      });
    }
  });

  it("每题 4 个互不相同的中文选项，且含正确答案", () => {
    for (const q of questions) {
      expect(q.options).toHaveLength(4);
      expect(new Set(q.options).size).toBe(4);
      expect(q.options).toContain(q.answer);
      expect(q.answer).toBe(q.item.cn);
    }
  });

  it("真题词不足时用普通词补足，总题数不变", () => {
    const sparse = makeBank();
    sparse.ket.forEach((pool) => pool.words.forEach((w) => { w.hits = 0; }));
    sparse.ket[0].words[0].hits = 5;
    const qs = buildVocabTest(sparse, seeded(9));
    expect(qs).toHaveLength(PER_EXAM * 2);
    expect(qs.filter((q) => q.item.exam === "ket" && q.item.hits > 0)).toHaveLength(1);
  });

  it("跨级别重复英文被跳过，仍能凑满 50 题", () => {
    const dup = makeBank();
    dup.pet[0].words[0].en = dup.ket[0].words[0].en;
    const qs = buildVocabTest(dup, seeded(11));
    expect(qs).toHaveLength(PER_EXAM * 2);
    expect(new Set(qs.map((q) => q.item.en.toLowerCase())).size).toBe(qs.length);
  });
});

describe("scoreVocabTest", () => {
  const bank = makeBank();
  const questions = buildVocabTest(bank, seeded(13));
  const answerAll = (ok: (q: VocabQuestion) => boolean): string[] =>
    questions.map((q) => (ok(q) ? q.answer : "错误选项"));

  it("全对：KET / PET 都达到，级别为 PET", () => {
    const r = scoreVocabTest(questions, answerAll(() => true), bank);
    expect(r.ket.correct).toBe(PER_EXAM);
    expect(r.ket.verdict).toBe("reached");
    expect(r.pet.verdict).toBe("reached");
    expect(r.level).toBe("pet");
    expect(r.ket.estimated).toBe(r.ket.bankTotal);
    expect(r.estimated).toBe(r.pet.estimated);
  });

  it("只答对 KET：级别为 KET，PET 未达到", () => {
    const r = scoreVocabTest(questions, answerAll((q) => q.item.exam === "ket"), bank);
    expect(r.level).toBe("ket");
    expect(r.ket.verdict).toBe("reached");
    expect(r.pet.verdict).toBe("below");
    expect(r.estimated).toBe(r.ket.estimated);
  });

  it("跳过按答错计，薄弱词库正确率 < 60% 时列出", () => {
    const r = scoreVocabTest(questions, questions.map(() => null), bank);
    expect(r.ket.correct).toBe(0);
    expect(r.ket.verdict).toBe("below");
    expect(r.level).toBe("below");
    expect(r.pet.weak.map((w) => w.bank).sort()).toEqual(["bimo", "gaopin", "guding"]);
  });

  it("统计真题词答对情况", () => {
    const r = scoreVocabTest(questions, answerAll((q) => q.item.hits > 0), bank);
    for (const exam of ["ket", "pet"] as ExamId[]) {
      const rows = questions.filter((q) => q.item.exam === exam && q.item.hits > 0);
      expect(r[exam].tagged?.total).toBe(rows.length);
      expect(r[exam].tagged?.correct).toBe(rows.length);
    }
  });
});

describe("fromWordBanks 兜底", () => {
  it("只取三库、跳过同义库与空字段、跨库重复只保留先出现的库", () => {
    const banks = makeBanks();
    banks.kcore = [{ id: "dup", en: "kw word 0", cn: "重复" }, ...banks.kcore];
    const bank = fromWordBanks(banks);
    expect(bank.ket.map((p) => p.key)).toEqual(["kword", "kcore", "kphrase"]);
    expect(bank.pet.map((p) => p.key)).toEqual(["bimo", "gaopin", "guding"]);
    expect(bank.ket.flatMap((p) => p.words).some((w) => w.id === "ks0")).toBe(false);
    expect(bank.ket.flatMap((p) => p.words).some((w) => w.id === "dup")).toBe(false);
    expect(bank.ket.flatMap((p) => p.words).every((w) => w.hits === 0)).toBe(true);
    expect(bank.ket[0].name).toBe("必默");
  });
});

describe("评测结果本地存取", () => {
  beforeEach(() => localStorage.clear());

  it("按账号隔离存取", () => {
    const bank = makeBank();
    const questions = buildVocabTest(bank, seeded(3));
    const result = scoreVocabTest(questions, questions.map((q) => q.answer), bank);
    saveVocabResult("kid", result);
    expect(loadVocabResult("kid")?.level).toBe("pet");
    expect(loadVocabResult("kid")?.ket.tagged?.total).toBeGreaterThan(0);
    expect(loadVocabResult("other")).toBeNull();
  });

  it("旧版 24 题结果被清理，不再展示", () => {
    const legacy = {
      at: 1,
      ket: { exam: "ket", correct: 10, total: 12, accuracy: 0.83, estimated: 900, bankTotal: 1100, verdict: "reached", weak: [] },
      pet: { exam: "pet", correct: 5, total: 12, accuracy: 0.42, estimated: 500, bankTotal: 1200, verdict: "below", weak: [] },
      level: "ket",
      estimated: 900,
    };
    localStorage.setItem("pet_vocab_test_v1:kid", JSON.stringify(legacy));
    localStorage.setItem("pet_vocab_test_v1:other", "{}");
    expect(loadVocabResult("kid")).toBeNull();
    expect(localStorage.getItem("pet_vocab_test_v1:kid")).toBeNull();
    expect(localStorage.getItem("pet_vocab_test_v1:other")).toBeNull();
    expect(vocabResultKey("kid")).toBe("pet_vocab_test_v2:kid");
  });

  it("坏数据返回 null，不抛错", () => {
    localStorage.setItem(vocabResultKey("kid"), "{not json");
    expect(loadVocabResult("kid")).toBeNull();
  });
});
