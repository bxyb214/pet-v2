import { describe, expect, it } from "vitest";
import {
  buildQuizItems, grammarIndex, itemForDim, sentenceDims,
  withCustomSentences, customSid,
  type ReadingData, type RSentence, type RTest,
} from "./reading";
import type { CustomSentenceItem } from "./merge";

function s(id: string, en: string, cn: string, key: string, quiz: string[], gq: RSentence["gq"] = []): RSentence {
  return {
    id, en, cn, key, quiz,
    point: "", note: "", tense: "",
    parse: [{ r: "主", t: "x" }, { r: "谓", t: "y" }, { r: "宾", t: "z" }],
    gram: [{ c: 1, g: "g", d: "d" }],
    gq,
  };
}

const sMaker = s; // 别名，避免与局部变量冲突
const pool = [
  s("a", "Alpha beta gamma.", "甲句", "Alpha", ["meaning", "blank"]),
  s("b", "Delta epsilon zeta.", "乙句", "Delta", ["meaning", "blank"]),
  s("c", "Eta theta iota.", "丙句", "Eta", ["meaning", "blank"]),
  s("d", "Kappa lambda mu.", "丁句", "Kappa", ["meaning", "blank"]),
];

// 确定性随机源（恒 0 → 洗牌退化，保证可断言）
const rnd = () => 0;

describe("buildQuizItems", () => {
  it("三题型都生成且选项恰好 4 个、恰 1 正确", () => {
    const withGq = s("g", "Alpha beta gamma.", "甲句", "Alpha", ["meaning", "blank", "grammar"],
      [{ stem: "选时态", opts: ["A", "B", "C", "D"], a: 2, why: "w", c: 29 }]);
    const items = buildQuizItems([withGq], pool, 100, rnd);
    const types = items.map((i) => i.type);
    expect(types).toContain("meaning");
    expect(types).toContain("blank");
    expect(types).toContain("grammar");
    for (const it of items) {
      expect(it.options.length).toBe(4);
      expect(it.options.filter((o) => o.correct).length).toBe(1);
    }
    const g = items.find((i) => i.type === "grammar")!;
    expect(g.prompt).toBe("选时态");
  });

  it("blank 题 prompt 挖掉 key", () => {
    const items = buildQuizItems([pool[0]], pool, 100, rnd);
    const blank = items.find((i) => i.type === "blank")!;
    expect(blank.prompt).not.toContain("Alpha");
    expect(blank.prompt).toContain("______");
    expect(blank.options.some((o) => o.label === "Alpha" && o.correct)).toBe(true);
  });

  it("干扰项不会是本题答案", () => {
    const items = buildQuizItems([pool[1]], pool, 100, rnd);
    for (const it of items) {
      const correctLabels = it.options.filter((o) => o.correct).map((o) => o.label);
      for (const o of it.options) {
        if (!o.correct) expect(correctLabels).not.toContain(o.label);
      }
    }
  });

  it("cap 截断且打乱", () => {
    const items = buildQuizItems(pool, pool, 6, rnd);
    expect(items.length).toBe(6);
  });

  it("干扰池不足 3 时跳过对应题型", () => {
    const items = buildQuizItems([pool[0]], pool.slice(0, 2), 100, rnd); // 干扰池只有 1 句
    expect(items.filter((i) => i.type === "meaning").length).toBe(0);
    expect(items.filter((i) => i.type === "blank").length).toBe(0);
  });
});

describe("grammarIndex", () => {
  it("按考点编号聚合 gq", () => {
    const t = {
      no: 1, book: "t2", title: "T",
      parts: [{
        part: 1, kind: "", focus: "",
        sentences: [
          s("x", "One.", "一", "One", ["grammar"], [{ stem: "q1", opts: ["1", "2", "3", "4"], a: 0, why: "", c: 29 }]),
          s("y", "Two.", "二", "Two", ["grammar"], [{ stem: "q2", opts: ["1", "2", "3", "4"], a: 1, why: "", c: 29 }]),
        ],
      }],
    };
    const idx = grammarIndex([t]);
    expect(idx[29].length).toBe(2);
    expect(idx[29][0].prompt).toBe("q1");
  });
});

describe("R8 错题维度", () => {
  it("sentenceDims 按 quiz 配置生成", () => {
    const sent = sMaker("d1", "Hello world today.", "你好世界", "world", ["meaning", "blank"],
      [{ stem: "q", opts: ["1", "2", "3", "4"], a: 0, why: "", c: 29 }]);
    expect(sentenceDims(sent)).toEqual(["meaning", "blank", "grammar:g0"]);
  });

  it("itemForDim 按维度重建题目", () => {
    const sent = sMaker("d1", "Hello world today.", "你好世界", "world", ["meaning", "blank"]);
    const blank = itemForDim(sent, "blank", pool, rnd)!;
    expect(blank.type).toBe("blank");
    expect(blank.options.length).toBe(4);
    const meaning = itemForDim(sent, "meaning", pool, rnd)!;
    expect(meaning.type).toBe("meaning");
    expect(itemForDim(sent, "grammar:g0", pool, rnd)).toBeNull();
  });
});

describe("R10 自定义句", () => {
  const data: ReadingData = {
    grammar: { book: "", days: [] },
    books: [{ id: "t2", name: "T2", desc: "" }],
    tests: [
      {
        no: 1, book: "t2", title: "Test 1",
        parts: [{ part: 1, kind: "", focus: "", sentences: [pool[0]] }],
      },
    ],
    meta: { sentences: 1, gq: 0, points_covered: 1, built: "2026-01-01" },
  };
  const custom: CustomSentenceItem[] = [
    { sid: "t2:1:1:my sentence", book: "t2", test_no: 1, part: 1, en: "My sentence here.", cn: "我的句子", key: "sentence", note: "" },
    { sid: "t2:1:2:other", book: "t2", test_no: 1, part: 2, en: "Other.", cn: "", key: "", note: "" },
  ];

  it("注入对应 part，原数据不被修改", () => {
    const merged = withCustomSentences(data, custom);
    const p1 = merged.tests[0].parts[0];
    expect(p1.sentences.length).toBe(2);
    expect(p1.sentences[1].id).toBe("t2:1:1:my sentence");
    expect(p1.sentences[1].quiz).toEqual(["meaning", "blank"]);
    expect(data.tests[0].parts[0].sentences.length).toBe(1); // 原 cache 不变
    // part 2 无原数据中的 part → 不新增 part，忽略
    expect(merged.tests[0].parts.length).toBe(1);
  });

  it("customSid 规范化空格与大小写", () => {
    expect(customSid("t2", 1, 1, "  My   Sentence ")).toBe("t2:1:1:my sentence");
  });
});
