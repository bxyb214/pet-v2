import { describe, expect, it } from "vitest";
import {
  activeSentenceIdx,
  gradePart,
  isFillCorrect,
  mistakeKey,
  progressKey,
  type LItem,
  type LPart,
} from "./listening";

function part(kind: LPart["kind"], items: LItem[]): LPart {
  return {
    part: 1, qRange: "", label: "", kind,
    audio: "/audio/listen/t1-p1.mp3", duration: 500,
    transcript: "", sentences: [], items,
  };
}

describe("isFillCorrect", () => {
  it("大小写不敏感", () => {
    expect(isFillCorrect("RainForest", "rainforest")).toBe(true);
  });
  it("首尾空格与连续空白归一", () => {
    expect(isFillCorrect("  football   club ", "football club")).toBe(true);
    expect(isFillCorrect("footballclub", "football club")).toBe(false);
  });
});

describe("gradePart", () => {
  const items: LItem[] = [
    { no: 1, stem: "s1", answer: 0, img: null, options: ["a", "b", "c"], t0: 1 },
    { no: 2, stem: "s2", answer: 2, img: null, options: ["x", "y", "z"], t0: 2 },
    { no: 3, stem: "s3", answer: "rainforest", img: null, options: null, t0: 3 },
  ];

  it("choice 判分", () => {
    const g = gradePart(part("choice", items.slice(0, 2)), { 1: 0, 2: 1 });
    expect(g).toEqual({ right: 1, total: 2, wrongNos: [2] });
  });

  it("fill 判分归一化", () => {
    const g = gradePart(part("fill", [items[2]]), { 3: " Rainforest " });
    expect(g.right).toBe(1);
    expect(g.wrongNos).toEqual([]);
  });

  it("未作答算错", () => {
    const g = gradePart(part("choice", items.slice(0, 2)), {});
    expect(g).toEqual({ right: 0, total: 2, wrongNos: [1, 2] });
  });
});

describe("业务键", () => {
  it("mistakeKey / progressKey 格式", () => {
    expect(mistakeKey("t1", 2, 8)).toBe("listen:t1:p2:q8");
    expect(progressKey("t1", 2, 3)).toBe("listen:t1:2:3");
  });
});

describe("activeSentenceIdx", () => {
  const sents = [
    { t0: 0, t1: 2, text: "a", no: null },
    { t0: 2, t1: null, text: "b", no: null },
    { t0: 5, t1: null, text: "c", no: null },
  ];
  it("句区间内命中", () => {
    expect(activeSentenceIdx(sents, 1)).toBe(0);
    expect(activeSentenceIdx(sents, 3)).toBe(1);
    expect(activeSentenceIdx(sents, 5)).toBe(2);
  });
  it("t1 缺省用下一句 t0 补", () => {
    expect(activeSentenceIdx(sents, 4.9)).toBe(1);
    expect(activeSentenceIdx(sents, 5.1)).toBe(2);
  });
  it("尾部余量高亮最后一句", () => {
    expect(activeSentenceIdx(sents, 999)).toBe(2);
  });
  it("空数组返回 -1", () => {
    expect(activeSentenceIdx([], 1)).toBe(-1);
  });
});
