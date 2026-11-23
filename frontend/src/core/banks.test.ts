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
});
