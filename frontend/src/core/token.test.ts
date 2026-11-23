import { describe, expect, it } from "vitest";
import { isTokenExpired } from "./token";

function jwt(payload: Record<string, unknown>): string {
  const body = btoa(JSON.stringify(payload)).replace(/=+$/, "");
  return `header.${body}.signature`;
}

describe("isTokenExpired", () => {
  it("accepts a token whose exp is in the future", () => {
    const now = 1_700_000_000_000;
    expect(isTokenExpired(jwt({ exp: now / 1000 + 60 }), now)).toBe(false);
  });

  it("rejects a token whose exp has passed", () => {
    const now = 1_700_000_000_000;
    expect(isTokenExpired(jwt({ exp: now / 1000 - 1 }), now)).toBe(true);
  });

  it("rejects malformed or expiry-less tokens", () => {
    expect(isTokenExpired("not-a-jwt")).toBe(true);
    expect(isTokenExpired(jwt({ sub: "1" }))).toBe(true);
  });
});
