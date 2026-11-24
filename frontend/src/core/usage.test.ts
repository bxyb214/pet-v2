import { describe, expect, it } from "vitest";
import { fmtChars, fmtMilli, fmtMinutes, localMonth } from "./usage";

describe("usage formatting", () => {
  it("formats milli yuan", () => {
    expect(fmtMilli(0)).toBe("0.00 元");
    expect(fmtMilli(1234)).toBe("1.23 元");
  });

  it("formats seconds and minutes", () => {
    expect(fmtMinutes(0)).toBe("0 分");
    expect(fmtMinutes(45)).toBe("45 秒");
    expect(fmtMinutes(120)).toBe("2 分");
    expect(fmtMinutes(-5)).toBe("0 分");
  });

  it("formats TTS chars", () => {
    expect(fmtChars(0)).toBe("0");
    expect(fmtChars(9999)).toBe("9999");
    expect(fmtChars(12000)).toBe("1.2 万");
  });

  it("formats local month with zero padding", () => {
    expect(localMonth(new Date(2026, 0, 15).getTime())).toBe("2026-01");
    expect(localMonth(new Date(2026, 10, 24).getTime())).toBe("2026-11");
  });
});
