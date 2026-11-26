/**
 * 造句录音（本机 IndexedDB）：每道题保留最近 3 条 + 该题最高分那条。
 * 录音只存在本设备、不上传服务器；IndexedDB 不可用（隐私模式等）时静默降级为空。
 */

export type Take = {
  id: string;
  /** 归属键：`用户名|场景:题目`，用于按人按题查询 */
  key: string;
  promptKey: string;
  /** 毫秒时间戳 */
  at: number;
  /** 0–100；0 表示这次没拿到分 */
  score: number;
  transcript: string;
  mime: string;
  blob: Blob;
};

export const KEEP_LATEST = 3;

/** 最近 N 条 + 最高分那条（不重复），按时间倒序 */
export function pruneTakes(takes: Take[], keepLatest = KEEP_LATEST): Take[] {
  const sorted = [...takes].sort((a, b) => b.at - a.at);
  const keep = new Map<string, Take>();
  for (const t of sorted.slice(0, Math.max(1, keepLatest))) keep.set(t.id, t);
  const best = bestTake(sorted);
  if (best) keep.set(best.id, best);
  return [...keep.values()].sort((a, b) => b.at - a.at);
}

/** 最高分那条；同分取较新的一条；没有分数时返回 null */
export function bestTake(takes: Take[]): Take | null {
  let best: Take | null = null;
  for (const t of takes) {
    if (t.score <= 0) continue;
    if (!best || t.score > best.score || (t.score === best.score && t.at > best.at)) best = t;
  }
  return best;
}

export function takeStorageKey(username: string, promptKey: string): string {
  return `${username || "guest"}|${promptKey}`;
}

export function newTakeId(at = Date.now()): string {
  return `${at}-${Math.random().toString(36).slice(2, 8)}`;
}

/** 16 kHz 单声道 Int16 PCM → WAV Blob（跟读的本地录音回放用） */
export function pcmToWav(pcm: Int16Array, sampleRate = 16000): Blob {
  const dataBytes = pcm.length * 2;
  const bytes = new Uint8Array(44 + dataBytes);
  const view = new DataView(bytes.buffer);
  const ascii = (offset: number, text: string): void => {
    for (let i = 0; i < text.length; i++) view.setUint8(offset + i, text.charCodeAt(i));
  };
  ascii(0, "RIFF");
  view.setUint32(4, 36 + dataBytes, true);
  ascii(8, "WAVE");
  ascii(12, "fmt ");
  view.setUint32(16, 16, true); // fmt 块大小
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // 单声道
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); // 每秒字节数
  view.setUint16(32, 2, true); // 采样对齐
  view.setUint16(34, 16, true); // 位深
  ascii(36, "data");
  view.setUint32(40, dataBytes, true);
  for (let i = 0; i < pcm.length; i++) view.setInt16(44 + i * 2, pcm[i], true);
  return new Blob([bytes], { type: "audio/wav" });
}

const DB_NAME = "pet_speak_takes";
const STORE = "takes";
const VERSION = 1;

let dbPromise: Promise<IDBDatabase | null> | null = null;

function openDb(): Promise<IDBDatabase | null> {
  if (typeof indexedDB === "undefined") return Promise.resolve(null);
  if (!dbPromise) {
    dbPromise = new Promise<IDBDatabase | null>((resolve) => {
      try {
        const req = indexedDB.open(DB_NAME, VERSION);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains(STORE)) {
            db.createObjectStore(STORE, { keyPath: "id" }).createIndex("key", "key");
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
        req.onblocked = () => resolve(null);
      } catch {
        resolve(null);
      }
    });
  }
  return dbPromise;
}

function readAll(db: IDBDatabase, key: string): Promise<Take[]> {
  return new Promise((resolve) => {
    try {
      const req = db.transaction(STORE, "readonly").objectStore(STORE).index("key").getAll(key);
      req.onsuccess = () => resolve((req.result as Take[]).sort((a, b) => b.at - a.at));
      req.onerror = () => resolve([]);
    } catch {
      resolve([]);
    }
  });
}

/** 某道题已保留的录音（按时间倒序） */
export async function listTakes(key: string): Promise<Take[]> {
  const db = await openDb();
  if (!db) return [];
  return pruneTakes(await readAll(db, key));
}

/** 新增一条并落库，返回该题保留后的列表 */
export async function addTake(take: Take): Promise<Take[]> {
  const db = await openDb();
  if (!db) return [take];
  const existing = await readAll(db, take.key);
  const kept = pruneTakes([...existing, take]);
  const drop = existing.filter((t) => !kept.some((k) => k.id === t.id)).map((t) => t.id);
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE, "readwrite");
      const store = tx.objectStore(STORE);
      store.put(take);
      for (const id of drop) store.delete(id);
      tx.oncomplete = () => resolve(kept);
      tx.onerror = () => resolve(kept);
      tx.onabort = () => resolve(kept);
    } catch {
      resolve(kept);
    }
  });
}
