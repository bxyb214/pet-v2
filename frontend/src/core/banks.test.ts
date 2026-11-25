import { describe, expect, it } from "vitest";
import { splitTermMeaning } from "./banks";

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
