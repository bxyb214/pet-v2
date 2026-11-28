import { describe, expect, it } from "vitest";
import { ALL_BANK_KEYS, availableBankKeys, bankShortLabel, splitTermMeaning, type BankMeta } from "./banks";
import type { WordBanks } from "./plan";

describe("splitTermMeaning（同义替换库中英混排）", () => {
  it("按首个中文字符拆出英文与中文", () => {
    expect(splitTermMeaning("a DVD you can keep 你可以拥有的 DVD")).toEqual({
      en: "a DVD you can keep",
      cn: "你可以拥有的 DVD",
    });
  });

  it("纯英文返回英文、中文为空", () => {
    expect(splitTermMeaning("look after")).toEqual({ en: "look after", cn: "" });
  });

  it("空值安全", () => {
    expect(splitTermMeaning("")).toEqual({ en: "", cn: "" });
  });

  it("中文量词前的数字归到中文：10 米高…", () => {
    expect(splitTermMeaning("10-metre cliff with climbing classes 10 米高悬崖的攀岩课程"))
      .toEqual({ en: "10-metre cliff with climbing classes", cn: "10 米高悬崖的攀岩课程" });
  });

  it("中文里重复出现同一数字时，数字留在英文", () => {
    expect(splitTermMeaning("members aged 12-18 年龄在 12-18 岁的人"))
      .toEqual({ en: "members aged 12-18", cn: "年龄在 12-18 岁的人" });
    expect(splitTermMeaning("must be over 15 必须 15 岁以上"))
      .toEqual({ en: "must be over 15", cn: "必须 15 岁以上" });
  });
});

describe("KET 四库与旧词库兼容", () => {
  const meta: Record<string, BankMeta> = {
    kword: { exam: "ket", name: "必默词", short: "必默", dims: ["m2w", "w2m", "spell"] },
    kcore: { exam: "ket", name: "高频词", short: "高频", dims: ["m2w", "w2m"] },
    kphrase: { exam: "ket", name: "固定搭配", short: "固搭", dims: ["m2w", "w2m"] },
    ksyn: { exam: "ket", name: "同义替换", short: "同义", dims: ["m2w", "w2m"] },
  };
  const banks: WordBanks = {
    kword: [{ id: "kw0", en: "camera", cn: "照相机" }],
    kcore: [{ id: "kc0", en: "achieve", cn: "实现" }],
    kphrase: [],
    ksyn: [],
  };

  it("只返回当前级别有内容的词库，顺序来自 bankMeta", () => {
    expect(availableBankKeys(banks, meta, "ket")).toEqual(["kword", "kcore"]);
  });

  it("不含已合并的 kconfuse", () => {
    expect(ALL_BANK_KEYS).not.toContain("kconfuse");
  });

  it("历史生词的 kconfuse 显示为必默", () => {
    expect(bankShortLabel("kconfuse")).toBe("必默");
    expect(bankShortLabel("kword", meta)).toBe("必默");
    expect(bankShortLabel("unknown")).toBe("unknown");
  });
});
