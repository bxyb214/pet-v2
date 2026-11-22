/**
 * 学习数据 store：本地持久化 + SyncEngine 接线。
 * 持久化键 pet_sync_v2（单活跃用户，登出清空 rev 基线）。
 */
import { defineStore } from "pinia";
import { api } from "../core/api";
import type { SyncData } from "../core/merge";
import { createSyncEngine, EMPTY_SYNC_DATA, type SyncEngine } from "../core/sync";

const LS_KEY = "pet_sync_v2";

interface Persisted {
  rev: number;
  data: SyncData;
}

function loadPersisted(): Persisted {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) return JSON.parse(raw) as Persisted;
  } catch {
    /* 损坏则丢弃 */
  }
  return { rev: 0, data: structuredClone(EMPTY_SYNC_DATA) };
}

function savePersisted(p: Persisted): void {
  localStorage.setItem(LS_KEY, JSON.stringify(p));
}

export const useLearningStore = defineStore("learning", {
  state: () => {
    const p = loadPersisted();
    return {
      data: p.data,
      rev: p.rev,
      status: "idle" as "idle" | "synced" | "offline" | "error",
      localOnly: localStorage.getItem("pet_local_only") === "true",
      engine: null as SyncEngine | null,
    };
  },
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
      savePersisted({ rev: this.rev, data: this.data });
    },
    /** 登录成功后调用：建立引擎并做首次 pull 合并 */
    async connect(): Promise<void> {
      if (this.localOnly) return;
      const persisted = loadPersisted();
      this.rev = persisted.rev;
      this.data = persisted.data;
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
    /** 登出：停轮询、清基线 */
    disconnect(): void {
      this.engine?.stopPolling();
      this.engine?.reset();
      this.engine = null;
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
    setReadingPlan(length: number): void {
      this.data.plan.reading_length = length;
      this.markDirty();
    },
    deleteReadingPlan(): void {
      this.data.plan.reading_length = 0;
      this.data.plan.reading_days_done = [];
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
    markPlanDayDone(day: number): void {      const key = String(day);
      if (!this.data.plan.days_done.includes(key)) {
        this.data.plan.days_done.push(key);
        this.data.plan.days_done.sort((a, b) => Number(a) - Number(b));
        this.markDirty();
      }
    },
    /** 计划生成/删除（P1：可删除重新生成） */
    setPlan(length: number): void {
      this.data.plan.length = length;
      this.markDirty();
    },
    deletePlan(): void {
      this.data.plan = { length: 0, days_done: [], reading_length: 0, reading_days_done: [] };
      this.markDirty();
    },
  },
});

/** 响应式对象 → 纯数据（structuredClone 需要） */
function toRawData(data: SyncData): SyncData {
  return JSON.parse(JSON.stringify(data)) as SyncData;
}
