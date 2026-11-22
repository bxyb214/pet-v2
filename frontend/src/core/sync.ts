/**
 * 同步引擎：本地数据 + 服务端 pull/push，防抖推送 + 静默拉取 + 409 合并重试。
 * 依赖全部注入，便于测试与 Pinia store 解耦。
 */
import { mergeSyncData, type SyncData } from "./merge";

export interface PullResp {
  rev: number;
  data: SyncData;
}

export interface SyncDeps {
  /** 服务端交互（默认实现走 core/api.ts，测试注入 mock） */
  pull(): Promise<PullResp>;
  push(rev: number, data: SyncData): Promise<PullResp>;
  /** 当前内存中的本地数据 */
  getLocalData(): SyncData;
  /** rev 变化后持久化 */
  saveRev(rev: number): void;
  /** 合并结果写回本地（pull 后 / 409 合并后） */
  onMerged(data: SyncData): void;
  onStatus?(status: "synced" | "offline" | "error"): void;
  /** 定时器注入（默认 window，测试注入 fake） */
  timers?: {
    setTimeout(fn: () => void, ms: number): unknown;
    clearTimeout(handle: unknown): void;
    setInterval(fn: () => void, ms: number): unknown;
    clearInterval(handle: unknown): void;
  };
  pushDelayMs?: number; // 默认 1200
  pullIntervalMs?: number; // 默认 45000
  maxRetries?: number; // 409 重试上限，默认 3
}

const EMPTY: SyncData = {
  mastery: [],
  mistakes: [],
  progress: [],
  plan: { length: 0, days_done: [], reading_length: 0, reading_days_done: [], reading_books: [] },
  custom_words: [],
  custom_sentences: [],
};

export function createSyncEngine(deps: SyncDeps) {
  const t = deps.timers ?? {
    setTimeout: (fn, ms) => window.setTimeout(fn, ms),
    clearTimeout: (h) => window.clearTimeout(h as number),
    setInterval: (fn, ms) => window.setInterval(fn, ms),
    clearInterval: (h) => window.clearInterval(h as number),
  };
  const pushDelay = deps.pushDelayMs ?? 1200;
  const pullInterval = deps.pullIntervalMs ?? 45000;
  const maxRetries = deps.maxRetries ?? 3;

  let rev = 0;
  let pushTimer: unknown = null;
  let pullTimer: unknown = null;
  let retries = 0;
  let pushing = false;
  let pending = false;

  async function doPush(): Promise<void> {
    if (pushing) {
      pending = true;
      return;
    }
    pushing = true;
    try {
      const resp = await deps.push(rev, deps.getLocalData());
      rev = resp.rev;
      deps.saveRev(rev);
      retries = 0;
      deps.onStatus?.("synced");
    } catch (e) {
      const err = e as { status?: number; detail?: { rev?: number; data?: SyncData } };
      if (err.status === 409 && err.detail?.data) {
        // 合并服务端最新 + 本地，用服务端 rev 重试
        const merged = mergeSyncData(err.detail.data, deps.getLocalData());
        rev = err.detail.rev ?? rev;
        deps.saveRev(rev);
        deps.onMerged(merged);
        retries += 1;
        if (retries <= maxRetries) {
          pushing = false;
          await doPush();
          return;
        }
        deps.onStatus?.("error");
      } else {
        deps.onStatus?.("offline"); // 网络失败：保留本地，不重置
      }
    } finally {
      pushing = false;
      if (pending) {
        pending = false;
        t.setTimeout(() => void doPush(), 0);
      }
    }
  }

  async function pullAndMerge(): Promise<void> {
    try {
      const resp = await deps.pull();
      const merged = mergeSyncData(resp.data, deps.getLocalData());
      rev = resp.rev;
      deps.saveRev(rev);
      deps.onMerged(merged);
      deps.onStatus?.("synced");
    } catch {
      deps.onStatus?.("offline");
    }
  }

  return {
    get rev() {
      return rev;
    },
    /** 登录后初始化：以服务端为准拉一次并合并本地 */
    async init(): Promise<void> {
      await pullAndMerge();
    },
    /** 本地数据变更后调用：防抖推送 */
    markDirty(): void {
      t.clearTimeout(pushTimer);
      pushTimer = t.setTimeout(() => void doPush(), pushDelay);
    },
    /** 定时静默拉取 */
    startPolling(): void {
      if (pullTimer) return;
      pullTimer = t.setInterval(() => void pullAndMerge(), pullInterval);
    },
    stopPolling(): void {
      t.clearInterval(pullTimer);
      pullTimer = null;
    },
    /** 供测试/手动触发 */
    flushPush: doPush,
    pullNow: pullAndMerge,
    reset(): void {
      rev = 0;
      retries = 0;
      t.clearTimeout(pushTimer);
      t.clearInterval(pullTimer);
      pushTimer = null;
      pullTimer = null;
    },
  };
}

export type SyncEngine = ReturnType<typeof createSyncEngine>;

export { EMPTY as EMPTY_SYNC_DATA };
