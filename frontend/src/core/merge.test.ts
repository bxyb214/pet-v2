import { describe, expect, it } from "vitest";
import {
  mergeMastery,
  mergeMistakes,
  mergeProgress,
  mergePlan,
  mergeSyncData,
  mergeCustomWords,
  mergeCustomSentences,
} from "./merge";

describe("mergeMastery 并集", () => {
  it("dims 并集 + 单侧保留", () => {
    const out = mergeMastery(
      [{ word_id: "w1", mastered_dims: ["spell"] }],
      [
        { word_id: "w1", mastered_dims: ["w2m"] },
        { word_id: "w2", mastered_dims: [] },
      ],
    );
    expect(Object.fromEntries(out.map((r) => [r.word_id, r.mastered_dims]))).toEqual({
      w1: ["spell", "w2m"],
      w2: [],
    });
  });
});

describe("mergeMistakes 取欠得多", () => {
  it("dims 并集、stage 取小、due 取早、repeats 取小", () => {
    const out = mergeMistakes(
      [{ word_id: "w1", dims: ["spell"], stage: 3, due_at: "2026-12-01", repeats: 2 }],
      [{ word_id: "w1", dims: ["w2m"], stage: 1, due_at: "2026-11-25", repeats: 0 }],
    );
    expect(out[0]).toEqual({
      word_id: "w1",
      dims: ["spell", "w2m"],
      stage: 1,
      due_at: "2026-11-25",
      repeats: 0,
    });
  });

  it("单侧直接保留", () => {
    const out = mergeMistakes(
      [{ word_id: "w1", dims: ["spell"], stage: 2, due_at: "2026-12-01", repeats: 1 }],
      [{ word_id: "w2", dims: [], stage: 0, due_at: "", repeats: 0 }],
    );
    expect(new Set(out.map((r) => r.word_id))).toEqual(new Set(["w1", "w2"]));
  });
});

describe("mergeProgress", () => {
  it("seen 并集 + idx 取大", () => {
    const out = mergeProgress(
      [{ key: "r101", seen: ["q1", "q2"], idx: 3 }],
      [{ key: "r101", seen: ["q2", "q3"], idx: 5 }],
    );
    expect(out[0].seen).toEqual(["q1", "q2", "q3"]);
    expect(out[0].idx).toBe(5);
  });
});

describe("mergePlan", () => {
  it("days_done 并集", () => {
    expect(
      mergePlan(
        { length: 30, days_done: ["1", "2"], reading_length: 0, reading_days_done: [] },
        { length: 30, days_done: ["2", "3"], reading_length: 0, reading_days_done: [] },
      ),
    ).toEqual({
      length: 30,
      days_done: ["1", "2", "3"],
      reading_length: 0,
      reading_days_done: [],
    });
  });

  it("阅读计划独立合并：days 并集 + length 取非 0", () => {
    expect(
      mergePlan(
        { length: 30, days_done: [], reading_length: 20, reading_days_done: ["1"] },
        { length: 0, days_done: [], reading_length: 0, reading_days_done: ["2"] },
      ),
    ).toEqual({
      length: 30,
      days_done: [],
      reading_length: 20,
      reading_days_done: ["1", "2"],
    });
  });
});

describe("mergeCustomSentences", () => {
  it("按 sid 去重并集，冲突服务端优先", () => {
    const out = mergeCustomSentences(
      [{ sid: "a", book: "t2", test_no: 1, part: 1, en: "Server side.", cn: "服务端", key: "", note: "" }],
      [
        { sid: "a", book: "t2", test_no: 1, part: 1, en: "Client side.", cn: "客户端", key: "", note: "" },
        { sid: "b", book: "t2", test_no: 1, part: 2, en: "Only client.", cn: "", key: "", note: "" },
      ],
    );
    expect(out.length).toBe(2);
    expect(out[0].sid).toBe("a");
    expect(out[0].en).toBe("Server side.");
    expect(out[1].sid).toBe("b");
  });
});

describe("mergeCustomWords", () => {
  it("按 word 小写并集，服务端优先", () => {
    const out = mergeCustomWords(
      [{ id: 1, word: "Shadow", pos: "n.", definition: "服务端修正版", example_en: "", example_cn: "" }],
      [
        { id: 9, word: "shadow", pos: "n.", definition: "客户端旧版", example_en: "", example_cn: "" },
        { id: 10, word: "apple", pos: "n.", definition: "苹果", example_en: "", example_cn: "" },
      ],
    );
    expect(out.map((w) => w.word.toLowerCase())).toEqual(["apple", "shadow"]);
    const byWord = Object.fromEntries(out.map((w) => [w.word.toLowerCase(), w]));
    expect(byWord.shadow.definition).toBe("服务端修正版");
    expect(byWord.apple.definition).toBe("苹果");
  });
});

describe("mergeSyncData 入口", () => {
  it("五类数据合并（含 custom_words）", () => {
    const out = mergeSyncData(
      { mastery: [], mistakes: [], progress: [], plan: { length: 0, days_done: [], reading_length: 0, reading_days_done: [] }, custom_words: [], custom_sentences: [] },
      {
        mastery: [{ word_id: "w1", mastered_dims: ["spell"] }],
        mistakes: [{ word_id: "w9", dims: ["w2m"], stage: 0, due_at: "", repeats: 0 }],
        progress: [{ key: "k", seen: [], idx: 0 }],
        plan: { length: 40, days_done: ["1"], reading_length: 0, reading_days_done: [] },
        custom_words: [{ id: 0, word: "apple", pos: "n.", definition: "苹果", example_en: "", example_cn: "" }],
      },
    );
    expect(out.mastery[0].word_id).toBe("w1");
    expect(out.mistakes[0].word_id).toBe("w9");
    expect(out.plan.length).toBe(40);
    expect(out.custom_words[0].word).toBe("apple");
  });
});
