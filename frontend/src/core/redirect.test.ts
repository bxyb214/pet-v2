import { describe, expect, it } from "vitest";
import { safeRedirect } from "./redirect";

describe("safeRedirect", () => {
  it("保留站内路径与查询参数", () => {
    expect(safeRedirect("/english/reading/study/1/1")).toBe("/english/reading/study/1/1");
    expect(safeRedirect("/english/words/study?day=3")).toBe("/english/words/study?day=3");
  });

  it("拒绝站外地址", () => {
    expect(safeRedirect("https://evil.example/x")).toBe("/");
    expect(safeRedirect("//evil.example/x")).toBe("/");
    expect(safeRedirect("/\\evil.example/x")).toBe("/");
  });

  it("空值与非字符串回退", () => {
    expect(safeRedirect(undefined)).toBe("/");
    expect(safeRedirect("")).toBe("/");
    expect(safeRedirect(["/english"])).toBe("/");
  });

  it("不回到登录或注册页", () => {
    expect(safeRedirect("/login")).toBe("/");
    expect(safeRedirect("/login?redirect=%2Fenglish")).toBe("/");
    expect(safeRedirect("/register")).toBe("/");
  });

  it("允许自定义 fallback", () => {
    expect(safeRedirect(undefined, "/english/words/browse")).toBe("/english/words/browse");
  });
});
