/**
 * 学习数据 store：本地持久化 + SyncEngine 接线。
 *
 * 持久化键按用户隔离：`pet_sync_v2::<用户名>`。
 * 早先是一个全局单键，换账号登录时会把上一个人的数据 merge 进来并推到自己名下
 * （admin 看到 felix 的 30 天计划就是这么来的），所以必须一人一份。
 */
import { defineStore } from "pinia";
import { api } from "../core/api";
import type { SyncData } from "../core/merge";
import { createSyncEngine, EMPTY_SYNC_DATA, type SyncEngine } from "../core/sync";

const LS_PREFIX = "pet_sync_v2::";
/** 旧版全局键：无法判断归属，只在首次见到时归档，不自动继承 */
const LS_LEGACY = "pet_sync_v2";
const LS_LEGACY_ARCHIVED = "pet_sync_v2::__legacy__";

interface Persisted {
  rev: number;
  data: SyncData;
}

function keyOf(user: string): string {
  return LS_PREFIX + user;
}

/** 老键（不分用户）不能猜归属，改名归档后不再读取 */
function archiveLegacyKey(): void {
  const legacy = localStorage.getItem(LS_LEGACY);
  if (!legacy) return;
  if (!localStorage.getItem(LS_LEGACY_ARCHIVED)) {
    localStorage.setItem(LS_LEGACY_ARCHIVED, legacy);
  }
  localStorage.removeItem(LS_LEGACY);
}

function loadPersisted(user: string): Persisted {
  if (!user) return { rev: 0, data: structuredClone(EMPTY_SYNC_DATA) };
  try {
    const raw = localStorage.getItem(keyOf(user));
    if (raw) return JSON.parse(raw) as Persisted;
  } catch {
    /* 损坏则丢弃 */
  }
  return { rev: 0, data: structuredClone(EMPTY_SYNC_DATA) };
}

function savePersisted(user: string, p: Persisted): void {
  if (!user) return; // 没有归属就不落盘，避免写到别人的键上
  localStorage.setItem(keyOf(user), JSON.stringify(p));
}

/** 同一时刻只允许一次连接（restore 与 login 可能并发） */
let inflight: Promise<void> | null = null;

export const useLearningStore = defineStore("learning", {
  state: () => ({
    /** 本地快照归属的用户名；空串表示尚未登录，此时不读写本地 */
    owner: "",
    data: structuredClone(EMPTY_SYNC_DATA) as SyncData,
    rev: 0,
    status: "idle" as "idle" | "synced" | "offline" | "error",
    localOnly: localStorage.getItem("pet_local_only") === "true",
    engine: null as SyncEngine | null,
  }),
  getters: {
    dueMistakes(state): string[] {
      const today = new Date().toISOString().slice(0, 10);
      return state.data.mistakes
        .filter((m) => m.dims.length > 0 && m.due_at && m.due_at <= today)
        .map((m) => m.word_id);
    },
  },
  actions: {
    _persist(): void {
      savePersisted(this.owner, { rev: this.rev, data: this.data });
    },
    /**
     * 登录/刷新恢复后调用：切到该用户自己的本地快照，建立引擎并首次 pull 合并。
     * 幂等 + 并发安全（restore 与 login 可能同时触发）。
     */
    async connect(username: string): Promise<void> {
      if (this.localOnly || !username) return;
      if (this.engine && this.owner === username) return;
      if (inflight) return inflight;
      inflight = this._doConnect(username).finally(() => {
        inflight = null;
      });
      return inflight;
    },
    /** 只切换本地快照（不建引擎），登录前与单测都用它 */
    hydrate(username: string): void {
      if (this.owner && this.owner !== username) this._persist(); // 换人前先落盘上一位
      archiveLegacyKey();
      this.owner = username;
      const persisted = loadPersisted(username);
      this.rev = persisted.rev;
      this.data = persisted.data;
    },
    async _doConnect(username: string): Promise<void> {
      this.hydrate(username);

      this.engine?.stopPolling();
      this.engine?.reset();
      this.engine = createSyncEngine({
        pull: () => api<{ rev: number; data: SyncData }>("/sync/pull"),
        push: (rev, data) =>
          api<{ rev: number; data: SyncData }>("/sync/push", {
            method: "POST",
            body: JSON.stringify({ rev, data }),
          }),
        getLocalData: () => structuredClone(toRawData(this.data)),
        saveRev: (rev) => {
          this.rev = rev;
          this._persist();
        },
        onMerged: (data) => {
          this.data = data;
          this._persist();
        },
        onStatus: (s) => {
          this.status = s;
        },
      });
      await this.engine.init();
      this.engine.startPolling();
    },
    /** 登出：落盘本人快照、停引擎、清内存，避免下一个账号读到别人的数据 */
    disconnect(): void {
      if (this.owner) this._persist();
      this.engine?.stopPolling();
      this.engine?.reset();
      this.engine = null;
      this.owner = "";
      this.rev = 0;
      this.data = structuredClone(EMPTY_SYNC_DATA);
      this.status = "idle";
    },
    /** 任何本地数据修改后调用 */
    markDirty(): void {
      this._persist();
      this.engine?.markDirty();
    },
    /** 记录掌握维度（V5） */
    recordMastery(wordId: string, dims: string[]): void {
      const found = this.data.mastery.find((m) => m.word_id === wordId);
      if (found) {
        found.mastered_dims = [...new Set([...found.mastered_dims, ...dims])];
      } else {
        this.data.mastery.push({ word_id: wordId, mastered_dims: [...new Set(dims)] });
      }
      this.markDirty();
    },
    /** 答错：全维度重欠 + 回 1 天间隔（V6 记忆曲线） */
    recordWrong(wordId: string, allDims: string[]): void {
      const today = new Date().toISOString().slice(0, 10);
      const found = this.data.mistakes.find((m) => m.word_id === wordId);
      if (found) {
        found.dims = [...allDims];
        found.stage = 0;
        found.due_at = today;
        found.repeats = 0;
      } else {
        this.data.mistakes.push({
          word_id: wordId,
          dims: [...allDims],
          stage: 0,
          due_at: today,
          repeats: 0,
        });
      }
      // 答错则该维度掌握收回
      const mastery = this.data.mastery.find((m) => m.word_id === wordId);
      if (mastery) mastery.mastered_dims = mastery.mastered_dims.filter((d) => !allDims.includes(d));
      this.markDirty();
    },
    /** 答对一个维度：划掉；若全部间隔走完 → 毕业移出（V6） */
    recordRight(wordId: string, dim: string): void {
      const found = this.data.mistakes.find((m) => m.word_id === wordId);
      if (!found) return;
      found.dims = found.dims.filter((d) => d !== dim);
      if (found.dims.length === 0) {
        this.data.mistakes = this.data.mistakes.filter((m) => m.word_id !== wordId);
        this.recordMastery(wordId, [dim]);
      }
      this.markDirty();
    },
    /** 阅读进度记录（R6：key=read:book:test:part，seen 存完成日期并集，idx 取大） */
    recordProgress(key: string): void {
      const today = new Date().toISOString().slice(0, 10);
      const found = this.data.progress.find((p) => p.key === key);
      if (found) {
        if (!found.seen.includes(today)) found.seen.push(today);
        found.idx = Math.max(found.idx, 1);
      } else {
        this.data.progress.push({ key, seen: [today], idx: 1 });
      }
      this.markDirty();
    },
    /** 精读续学进度（R7：idx=已学到的句子下标，0-based；seen 记最后学习日期） */
    setStudyIdx(key: string, idx: number): void {
      const today = new Date().toISOString().slice(0, 10);
      const found = this.data.progress.find((p) => p.key === key);
      if (found) {
        found.idx = Math.max(found.idx, idx);
        if (!found.seen.includes(today)) found.seen.push(today);
      } else {
        this.data.progress.push({ key, seen: [today], idx });
      }
      this.markDirty();
    },
    progressOf(key: string): { idx: number; seen: string[] } | null {
      const found = this.data.progress.find((p) => p.key === key);
      return found ? { idx: found.idx, seen: found.seen } : null;
    },
    /** 阅读计划（R9）：独立于词汇计划 */
    setReadingPlan(length: number, books: string[] = []): void {
      this.data.plan.reading_length = length;
      this.data.plan.reading_days_done = []; // 新建/改计划重置打卡
      // 空数组 = 全部教材（兼容老数据），有值则按选择切分
      this.data.plan.reading_books = [...new Set(books)].sort();
      this.data.plan.reading_updated_at = Date.now();
      this.markDirty();
    },
    deleteReadingPlan(): void {
      this.data.plan.reading_length = 0;
      this.data.plan.reading_days_done = [];
      this.data.plan.reading_books = [];
      this.data.plan.reading_updated_at = Date.now();
      this.markDirty();
    },
    markReadingDayDone(day: number): void {
      const key = String(day);
      if (!this.data.plan.reading_days_done.includes(key)) {
        this.data.plan.reading_days_done.push(key);
        this.data.plan.reading_days_done.sort((a, b) => Number(a) - Number(b));
        this.markDirty();
      }
    },
    /** 自定义精读句（R10）：sid 业务键去重 */
    addCustomSentence(item: import("../core/merge").CustomSentenceItem): void {
      if (!this.data.custom_sentences.some((s) => s.sid === item.sid)) {
        this.data.custom_sentences.push(item);
        this.markDirty();
      }
    },
    removeCustomSentence(sid: string): void {
      this.data.custom_sentences = this.data.custom_sentences.filter((s) => s.sid !== sid);
      this.markDirty();
    },
    /** 计划完成标记（P3 并集） */
    markPlanDayDone(day: number): void {
      const key = String(day);
      if (!this.data.plan.days_done.includes(key)) {
        this.data.plan.days_done.push(key);
        this.data.plan.days_done.sort((a, b) => Number(a) - Number(b));
        this.markDirty();
      }
    },
    /** 计划生成（P1：新建/改天数重置打卡；时间戳让新计划覆盖服务端旧计划） */
    setPlan(length: number): void {
      this.data.plan.length = length;
      this.data.plan.days_done = [];
      this.data.plan.plan_updated_at = Date.now();
      this.markDirty();
    },
    /** 只删词汇计划，保留阅读计划 */
    deletePlan(): void {
      this.data.plan.length = 0;
      this.data.plan.days_done = [];
      this.data.plan.plan_updated_at = Date.now();
      this.markDirty();
    },
  },
});

/** 响应式对象 → 纯数据（structuredClone 需要） */
function toRawData(data: SyncData): SyncData {
  return JSON.parse(JSON.stringify(data)) as SyncData;
}
