import { describe, expect, it } from "vitest";
import {
  countWords,
  normalizeSentence,
  pickSentences,
  sortSentences,
  targetDifficulty,
  weakWordsFromRecent,
  type BankSentence,
} from "./sentenceBank";

const BASE = { pack: "p1", packName: "P1" };

function s(id: string, en: string, difficulty = 3, extra: Partial<BankSentence> = {}): BankSentence {
  return { ...BASE, id, en, cn: "", difficulty, ...extra };
}

const INPUT = { userId: "u1", date: "2026-11-24" };

describe("targetDifficulty", () => {
  it("没有记录时默认 3", () => {
    expect(targetDifficulty([])).toBe(3);
    expect(targetDifficulty([0, Number.NaN, -1])).toBe(3);
  });

  it("最近 3 次平均 ≥85 升到 4，<60 降到 2", () => {
    expect(targetDifficulty([90, 88, 85])).toBe(4);
    expect(targetDifficulty([55, 58, 50])).toBe(2);
    expect(targetDifficulty([70, 75, 80])).toBe(3);
  });

  it("只看最新 3 次", () => {
    expect(targetDifficulty([95, 95, 95, 10])).toBe(4);
  });
});

describe("normalizeSentence", () => {
  it("补齐默认值：难度夹在 1–5、词数按英文统计、默认启用", () => {
    const n = normalizeSentence({ ...BASE, id: "a", en: "I like apples .", cn: "" });
    expect(n.difficulty).toBe(3);
    expect(n.words).toBe(4);
    expect(n.active).toBe(true);
    expect(n.source).toBe("unknown");
    expect(normalizeSentence({ ...n, difficulty: 9 }).difficulty).toBe(5);
  });

  it("countWords 忽略多余空白", () => {
    expect(countWords("  one   two  ")).toBe(2);
  });
});

describe("pickSentences", () => {
  it("优先选难度 ±1 的句子", () => {
    const pool = [
      s("easy", "a b c d e f g h i j k", 1),
      s("fit", "a b c d e f g h i j k", 3),
      s("hard", "a b c d e f g h i j k", 5),
    ];
    const out = pickSentences({ ...INPUT, sentences: pool, count: 1 });
    expect(out.target).toBe(3);
    expect(out.items.map((x) => x.id)).toEqual(["fit"]);
  });

  it("±1 不足时放宽到 ±2", () => {
    const pool = [s("d1", "a b c", 1), s("d5", "a b c", 5)];
    const out = pickSentences({ ...INPUT, sentences: pool, count: 1 });
    expect(out.items).toHaveLength(1);
    expect([1, 5]).toContain(out.items[0].difficulty);
  });

  it("跳过 active=false，并限定 pack", () => {
    const pool = [
      s("off", "a b c", 3, { active: false }),
      s("other", "a b c", 3, { pack: "p2" }),
      s("ok", "a b c", 3),
    ];
    const out = pickSentences({ ...INPUT, sentences: pool, packId: "p1", count: 5 });
    expect(out.items.map((x) => x.id)).toEqual(["ok"]);
  });

  it("最近练过的降权，优先没练过的", () => {
    const pool = [s("a", "a b c d e f g h i j k", 3), s("b", "a b c d e f g h i j k", 3)];
    const first = pickSentences({ ...INPUT, sentences: pool, count: 1 });
    const other = first.items[0].id === "a" ? "b" : "a";
    const out = pickSentences({ ...INPUT, sentences: pool, recentIds: [first.items[0].id], count: 1 });
    expect(out.items[0].id).toBe(other);
  });

  it("命中最近读错的词会加权", () => {
    const pool = [
      s("plain", "a b c d e f g h i j k", 3),
      s("weak", "a b c d e f g h i j k", 3, { focus: ["th"] }),
    ];
    const out = pickSentences({ ...INPUT, sentences: pool, weakWords: ["th"], count: 1 });
    expect(out.items[0].id).toBe("weak");
  });

  it("同样输入结果稳定", () => {
    const pool = Array.from({ length: 20 }, (_, i) => s(`s${i}`, "a b c d e f g h i j k", 2 + (i % 3)));
    const a = pickSentences({ ...INPUT, sentences: pool, count: 5 }).items.map((x) => x.id);
    const b = pickSentences({ ...INPUT, sentences: pool, count: 5 }).items.map((x) => x.id);
    expect(a).toEqual(b);
  });
});

describe("sortSentences", () => {
  it("计划模式返回包内全部句子，不截断", () => {
    const pool = [
      s("a", "a b c d e f g h i j k", 2),
      s("b", "a b c d e f g h i j k", 4),
      s("c", "a b c d e f g h i j k", 3),
    ];
    const out = sortSentences({ ...INPUT, sentences: pool, packIds: ["p1"] });
    expect(out.map((x) => x.id).sort()).toEqual(["a", "b", "c"]);
  });
});

describe("weakWordsFromRecent", () => {
  it("去重、转小写、最多 10 个", () => {
    const recent = [
      { weak_words: ["This", "that"] },
      { weak_words: ["this", "three"] },
      { weak_words: Array.from({ length: 12 }, (_, i) => `w${i}`) },
    ];
    const out = weakWordsFromRecent(recent);
    expect(out.slice(0, 3)).toEqual(["this", "that", "three"]);
    expect(out).toHaveLength(10);
  });
});
