/** 听力板块核心：加载 / 判分 / 错题键（纯函数，便于测试）。 */

export type LSentence = { t0: number; t1: number | null; text: string; no: number | null };

export type LItem = {
  no: number;
  stem: string;
  /** choice: 0-2 下标；picture: 0-2；fill: 答案字符串 */
  answer: number | string;
  img: string | null;
  options: string[] | null;
  t0: number;
};

export type LPart = {
  part: number;
  qRange: string;
  label: string;
  kind: "picture" | "choice" | "fill";
  audio: string;
  duration: number;
  transcript: string;
  sentences: LSentence[];
  items: LItem[];
};

export type LTest = {
  no: number;
  book: string;
  title: string;
  duration: number;
  parts: LPart[];
};

export type ListeningBook = { id: string; name: string; desc: string };

export type ListeningData = {
  books: ListeningBook[];
  tests: LTest[];
  meta: { tests: number; parts: number; items: number; items_by_kind: Record<string, number>; sentences: number; built: string };
};

const caches = new Map<string, ListeningData>();
const loadings = new Map<string, Promise<ListeningData>>();

/** 各级别数据路径：PET 沿用旧文件，KET 用单独目录。 */
export function listeningUrl(exam = "pet"): string {
  return exam === "ket" ? "/data/ket/listening.json" : "/data/listening.json";
}

export function loadListening(exam = "pet"): Promise<ListeningData> {
  const hit = caches.get(exam);
  if (hit) return Promise.resolve(hit);
  let pending = loadings.get(exam);
  if (!pending) {
    pending = fetch(listeningUrl(exam), { cache: "no-cache" })
      .then(async (res) => {
        if (!res.ok) throw new Error("听力数据加载失败");
        const data = (await res.json()) as ListeningData;
        caches.set(exam, data);
        return data;
      })
      .finally(() => {
        loadings.delete(exam);
      });
    loadings.set(exam, pending);
  }
  return pending;
}

/** fill 判分：trim + 小写 + 连续空白归一为单空格 */
export function isFillCorrect(input: string, answer: string): boolean {
  const norm = (s: string) => s.trim().toLowerCase().replace(/\s+/g, " ");
  return norm(input) === norm(answer);
}

export type GradeResult = { right: number; total: number; wrongNos: number[] };

/** 判分一个 Part：answers 以 item.no 为键 */
export function gradePart(part: LPart, answers: Record<number, string | number>): GradeResult {
  let right = 0;
  const wrongNos: number[] = [];
  for (const it of part.items) {
    const a = answers[it.no];
    let ok = false;
    if (part.kind === "fill") {
      ok = typeof a === "string" && isFillCorrect(a, String(it.answer));
    } else {
      ok = typeof a === "number" && a === it.answer;
    }
    if (ok) right++;
    else wrongNos.push(it.no);
  }
  return { right, total: part.items.length, wrongNos };
}

/** 错题本业务键：listen:t1:p2:q8（book 字段本身已是 "t1" 前缀） */
export function mistakeKey(book: string, partNo: number, itemNo: number): string {
  return `listen:${book}:p${partNo}:q${itemNo}`;
}

/** 进度 key：listen:t1:2:1（book:testNo:part） */
export function progressKey(book: string, testNo: number, partNo: number): string {
  return `listen:${book}:${testNo}:${partNo}`;
}

/** 音频跳转辅助：给定时刻，找当前应高亮的字幕句下标（二分，句区间 [t0, t1||next.t0)） */
export function activeSentenceIdx(sentences: LSentence[], t: number): number {
  if (!sentences.length) return -1;
  let lo = 0;
  let hi = sentences.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const s = sentences[mid];
    const next = sentences[mid + 1];
    const end = s.t1 ?? (next ? next.t0 : Infinity);
    if (t < s.t0) hi = mid - 1;
    else if (t >= end) lo = mid + 1;
    else return mid;
  }
  // 超出最后一句结束时间也高亮最后一句（音频尾部余量）
  const last = sentences[sentences.length - 1];
  if (t >= last.t0) ans = sentences.length - 1;
  return ans;
}
