import { describe, expect, it } from "vitest";
import { devShadowResult, parseDevTarget } from "./devSpeak";

describe("devSpeak", () => {
  it("extracts the target sentence from shadow instructions", () => {
    const instructions =
      'You are a pronunciation checker.\nTarget sentence for shadowing: "I like playing football."\nDay 1 of the plan.';
    expect(parseDevTarget(instructions)).toBe("I like playing football.");
  });

  it("returns a perfect shadow result with every target word marked ok", () => {
    const result = devShadowResult('Target sentence for shadowing: "My name is Chen."');
    expect(result.score).toBe(100);
    expect(result.transcript).toBe("My name is Chen.");
    expect(result.words.every((w) => w.ok)).toBe(true);
    expect(result.words.map((w) => w.w)).toEqual(["My", "name", "is", "Chen"]);
  });

  it("falls back to a readable sentence when no target is present", () => {
    expect(parseDevTarget("no target here")).toBe("I like learning English.");
  });
});
