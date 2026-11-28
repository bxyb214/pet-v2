import { describe, expect, it } from "vitest";
import { englishModulesFor, moduleAvailable } from "../core/examContent";
import { router } from "../router";
import { modulesForSubject } from "./navModules";

describe("各级别已上线的英语板块", () => {
  it("PET 四个一级板块（语法在阅读页签下）", () => {
    expect(englishModulesFor("pet")).toEqual(["words", "reading", "listening", "speak"]);
  });

  it("KET 已上线单词、阅读（语法在阅读下）、听力与口语", () => {
    expect(englishModulesFor("ket")).toEqual(["words", "reading", "listening", "speak"]);
    expect(moduleAvailable("ket", "reading")).toBe(true);
    expect(moduleAvailable("ket", "words")).toBe(true);
    expect(moduleAvailable("ket", "listening")).toBe(true);
    expect(moduleAvailable("ket", "speak")).toBe(true);
  });

  it("FCE / 初中英语还没有内容", () => {
    expect(englishModulesFor("fce")).toEqual([]);
    expect(englishModulesFor("junior")).toEqual([]);
  });

  it("导航按级别过滤，语法不单列，数学不受影响", () => {
    expect(modulesForSubject("english", "pet").map((m) => m.key))
      .toEqual(["words", "reading", "listening", "speak"]);
    expect(modulesForSubject("english", "ket").map((m) => m.key))
      .toEqual(["words", "reading", "listening", "speak"]);
    expect(modulesForSubject("math", "ket").map((m) => m.key)).toEqual(["books", "progress"]);
  });

  it("没有 module 的页面不拦截", () => {
    expect(moduleAvailable("ket", undefined)).toBe(true);
    expect(moduleAvailable("ket", "")).toBe(true);
  });
});

describe("语法挂在阅读下", () => {
  it("语法页属于阅读板块，并出现在阅读页签里", () => {
    const meta = router.resolve("/english/grammar").meta;
    expect(meta.module).toBe("reading");
    expect(meta.tabs?.map((t) => t.to)).toContain("/english/grammar");
  });

  it("阅读其他页签仍齐全", () => {
    const meta = router.resolve("/english/reading/home").meta;
    expect(meta.tabs?.map((t) => t.label)).toEqual(["教材", "语法", "计划", "错题"]);
  });
});
