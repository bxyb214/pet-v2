import { afterEach, describe, expect, it, vi } from "vitest";
import {
  api,
  getToken,
  resetUnauthorizedForTest,
  setToken,
  setUnauthorizedHandler,
} from "./api";

function unauthorized(): Response {
  return {
    ok: false,
    status: 401,
    json: async () => ({ detail: "未登录" }),
  } as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
  setUnauthorizedHandler(null);
  resetUnauthorizedForTest();
  setToken(null);
  localStorage.clear();
});

describe("api 401 handling", () => {
  it("clears the token and notifies once for a protected endpoint", async () => {
    setToken("stale");
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    vi.stubGlobal("fetch", vi.fn(async () => unauthorized()));

    await expect(api("/words/custom")).rejects.toMatchObject({ status: 401 });
    expect(handler).toHaveBeenCalledTimes(1);
    expect(getToken()).toBeNull();
  });

  it("lets the login form show its own error without redirecting", async () => {
    setToken("old");
    const handler = vi.fn();
    setUnauthorizedHandler(handler);
    vi.stubGlobal("fetch", vi.fn(async () => unauthorized()));

    await expect(api("/auth/login", { method: "POST" })).rejects.toMatchObject({ status: 401 });
    expect(handler).not.toHaveBeenCalled();
    expect(getToken()).toBe("old");
  });
});
