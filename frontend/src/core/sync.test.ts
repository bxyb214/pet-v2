import { describe, expect, it, vi } from "vitest";
import { createSyncEngine, type SyncDeps } from "./sync";
import type { SyncData } from "./merge";

const base: SyncData = { mastery: [], mistakes: [], progress: [], plan: { length: 0, days_done: [], reading_length: 0, reading_days_done: [] }, custom_words: [], custom_sentences: [] };

function fakeTimers() {
  const callbacks: Array<{ fn: () => void; ms: number }> = [];
  return {
    callbacks,
    setTimeout: (fn: () => void, ms: number) => {
      callbacks.push({ fn, ms });
      return callbacks.length;
    },
    clearTimeout: () => {},
    setInterval: () => 0,
    clearInterval: () => {},
  };
}

function makeDeps(overrides: Partial<SyncDeps> = {}) {
  let local: SyncData = structuredClone(base);
  const saved: number[] = [];
  const statuses: string[] = [];
  const deps: SyncDeps = {
    pull: vi.fn(async () => ({ rev: 1, data: structuredClone(base) })),
    push: vi.fn(async (rev: number, data: SyncData) => ({ rev: rev + 1, data })),
    getLocalData: () => structuredClone(local),
    saveRev: (r: number) => saved.push(r),
    onMerged: (d: SyncData) => (local = d),
    onStatus: (s) => statuses.push(s),
    timers: fakeTimers() as unknown as SyncDeps["timers"],
    ...overrides,
  };
  return { deps, getLocal: () => local, saved, statuses };
}

describe("sync engine", () => {
  it("init: pull 后合并并保存 rev", async () => {
    const remote: SyncData = {
      mastery: [{ word_id: "w1", mastered_dims: ["spell"] }],
      mistakes: [],
      progress: [],
      plan: { length: 30, days_done: ["1"], reading_length: 0, reading_days_done: [] },
      custom_words: [], custom_sentences: [],
    };
    const local: SyncData = {
      mastery: [{ word_id: "w1", mastered_dims: ["w2m"] }],
      mistakes: [],
      progress: [],
      plan: { length: 0, days_done: ["2"], reading_length: 0, reading_days_done: [] },
      custom_words: [], custom_sentences: [],
    };
    const { deps, getLocal } = makeDeps({
      pull: async () => ({ rev: 5, data: remote }),
      getLocalData: () => local,
    });
    const engine = createSyncEngine(deps);
    await engine.init();
    expect(engine.rev).toBe(5);
    expect(getLocal().mastery[0].mastered_dims).toEqual(["spell", "w2m"]);
    expect(getLocal().plan.days_done).toEqual(["1", "2"]);
  });

  it("markDirty 防抖：多次调用只推一次", async () => {
    const push = vi.fn(async (rev: number, d: SyncData) => ({ rev: rev + 1, data: d }));
    const timers = fakeTimers();
    const { deps } = makeDeps({ push, pushDelayMs: 1200, timers: timers as unknown as SyncDeps["timers"] });
    const engine = createSyncEngine(deps);
    engine.markDirty();
    engine.markDirty();
    engine.markDirty();
    const queued = timers.callbacks.filter((c) => c.ms === 1200);
    expect(queued.length).toBe(3);
    // 清掉前两个（模拟 clearTimeout 已移除引用），只执行最后一个
    await queued[queued.length - 1].fn();
    expect(push).toHaveBeenCalledTimes(1);
  });

  it("push 成功：rev 前进并保存", async () => {
    const push = vi.fn(async (rev: number, d: SyncData) => ({ rev: 7, data: d }));
    const { deps, saved, statuses } = makeDeps({ push });
    const engine = createSyncEngine(deps);
    engine.markDirty();
    await engine.flushPush();
    expect(engine.rev).toBe(7);
    expect(saved).toContain(7);
    expect(statuses).toContain("synced");
  });

  it("409 冲突：合并后用服务端 rev 重试成功", async () => {
    const serverData: SyncData = {
      mastery: [{ word_id: "w1", mastered_dims: ["spell"] }],
      mistakes: [],
      progress: [],
      plan: { length: 30, days_done: ["1"], reading_length: 0, reading_days_done: [] },
      custom_words: [], custom_sentences: [],
    };
    let call = 0;
    const push = vi.fn(async (rev: number, d: SyncData) => {
      call += 1;
      if (call === 1) {
        const err = new Error("rev 冲突") as { status?: number; detail?: unknown };
        err.status = 409;
        err.detail = { rev: 9, data: serverData };
        throw err;
      }
      return { rev: 10, data: d };
    });
    const local: SyncData = {
      mastery: [{ word_id: "w1", mastered_dims: ["w2m"] }],
      mistakes: [],
      progress: [],
      plan: { length: 0, days_done: ["2"], reading_length: 0, reading_days_done: [] },
      custom_words: [], custom_sentences: [],
    };
    const { deps, getLocal, statuses } = makeDeps({ push, getLocalData: () => local });
    const engine = createSyncEngine(deps);
    await engine.flushPush();
    expect(push).toHaveBeenCalledTimes(2);
    expect(push.mock.calls[1][0]).toBe(9); // 用服务端 rev 重试
    expect(getLocal().plan.days_done).toEqual(["1", "2"]);
    expect(getLocal().mastery[0].mastered_dims).toEqual(["spell", "w2m"]);
    expect(statuses).toContain("synced");
  });

  it("网络失败：状态 offline，本地不丢", async () => {
    const push = vi.fn(async () => {
      throw new Error("network");
    });
    const { deps, statuses } = makeDeps({ push });
    const engine = createSyncEngine(deps);
    await engine.flushPush();
    expect(statuses).toContain("offline");
    expect(engine.rev).toBe(0);
  });
});
