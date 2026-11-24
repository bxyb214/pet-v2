import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearMediaToken, mediaToken } from "./mediaToken";

const now = () => Math.floor(Date.now() / 1000);

function stubToken(token: string, expiresAt: number) {
  const fn = vi.fn(async (_url: string, _init?: RequestInit) => ({
    ok: true,
    status: 200,
    json: async () => ({ token, expires_at: expiresAt }),
  }));
  vi.stubGlobal("fetch", fn);
  return fn;
}

describe("媒体令牌", () => {
  beforeEach(() => {
    clearMediaToken();
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("未过期时复用内存令牌，不重复请求", async () => {
    const fetchMock = stubToken("t1", now() + 3600);
    expect(await mediaToken()).toBe("t1");
    expect(await mediaToken()).toBe("t1");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/media/token");
  });

  it("临近过期（<5 分钟）会重新换取", async () => {
    const fetchMock = stubToken("t1", now() + 60);
    expect(await mediaToken()).toBe("t1");
    fetchMock.mockImplementationOnce(async (_url: string, _init?: RequestInit) => ({
      ok: true, status: 200, json: async () => ({ token: "t2", expires_at: now() + 3600 }),
    }));
    expect(await mediaToken()).toBe("t2");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("退出登录清除缓存后再取会重新请求", async () => {
    const fetchMock = stubToken("t1", now() + 3600);
    await mediaToken();
    clearMediaToken();
    await mediaToken();
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("并发调用只发一次请求", async () => {
    const fetchMock = stubToken("t1", now() + 3600);
    const [a, b] = await Promise.all([mediaToken(), mediaToken()]);
    expect([a, b]).toEqual(["t1", "t1"]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
