/** 数学「李永乐一课通关」：课程序列 → 分年级教材 → 课时（纯逻辑，无组件依赖）。 */

export type MathLesson = {
  id: string;
  /** 课号（字符串，可能带小数：40 / 43.1） */
  no: string;
  title: string;
  /** 难度/类型标签：校内A / 拓展B / 浅奥C / 讲座 / 回放 */
  tag: string;
  group: string;
  /** NAS 上的真实文件名（保留中文与括号，不重命名用户媒体） */
  file: string;
  size: number;
};

/** 一本教材 = 一个年级的课程包 */
export type MathBook = {
  id: string;
  grade: number;
  gradeName: string;
  mediaDir: string;
  lessons: MathLesson[];
  /** 还没上传视频的年级：显示「即将上线」，不可进入 */
  comingSoon?: boolean;
};

export type MathCourse = { id: string; title: string; desc?: string };
export type MathData = { version: number; course: MathCourse; books: MathBook[] };

/** progress 记录（见 core/merge.ts ProgressItem 的业务子集） */
export type VideoRec = { idx: number; seen: string[] };
export type RecLookup = (lessonId: string) => VideoRec | null;
export type LessonStatus = "done" | "watching" | "todo";

export const MATH_KEY_PREFIX = "math:v:";
export const DONE_FLAG = "done";
export const MEDIA_BASE = "/media/math";
/** 用户要求的三档倍速 */
export const SPEEDS = [1, 1.25, 1.5] as const;

export function lessonKey(id: string): string {
  return MATH_KEY_PREFIX + id;
}

/** 逐段编码：中文、空格转义，保留 / 层级 */
export function encodePath(p: string): string {
  return p.split("/").map(encodeURIComponent).join("/");
}

export function videoUrl(mediaDir: string, file: string): string {
  return `${MEDIA_BASE}/${encodePath(mediaDir)}/${encodePath(file)}`;
}

export function isDone(rec: VideoRec | null | undefined): boolean {
  return !!rec && rec.seen.includes(DONE_FLAG);
}

export function statusOf(rec: VideoRec | null | undefined): LessonStatus {
  if (isDone(rec)) return "done";
  return (rec?.idx ?? 0) > 0 ? "watching" : "todo";
}

export type ProgressSummary = {
  total: number;
  done: number;
  watching: number;
  todo: number;
  percent: number;
};

function summarize(lessons: MathLesson[], recOf: RecLookup): ProgressSummary {
  let done = 0;
  let watching = 0;
  for (const l of lessons) {
    const s = statusOf(recOf(l.id));
    if (s === "done") done += 1;
    else if (s === "watching") watching += 1;
  }
  const total = lessons.length;
  return {
    total,
    done,
    watching,
    todo: total - done - watching,
    percent: total ? Math.round((done / total) * 100) : 0,
  };
}

/** 一本教材的进度 */
export function bookProgress(book: MathBook, recOf: RecLookup): ProgressSummary {
  return summarize(book.lessons, recOf);
}

/** 已上线教材合计（首页大卡用） */
export function courseProgress(books: MathBook[], recOf: RecLookup): ProgressSummary {
  return summarize(books.filter((b) => !b.comingSoon).flatMap((b) => b.lessons), recOf);
}

/** 只有已上传内容、可进入的教材 */
export function availableBooks(books: MathBook[]): MathBook[] {
  return books.filter((b) => !b.comingSoon && b.lessons.length > 0);
}

export function findBook(books: MathBook[], id: string): MathBook | null {
  return books.find((b) => b.id === id) ?? null;
}

/** 默认教材：第一个已上线年级 */
export function firstBook(books: MathBook[]): MathBook | null {
  return availableBooks(books)[0] ?? null;
}

/** 第一节没学完的课；全部学完返回 null */
export function nextLesson(lessons: MathLesson[], recOf: RecLookup): MathLesson | null {
  return lessons.find((l) => !isDone(recOf(l.id))) ?? null;
}

export type LessonGroup = { name: string; lessons: MathLesson[] };

/** 按清单出现顺序分组（组序稳定，不在前端重排） */
export function groupsOf(lessons: MathLesson[]): LessonGroup[] {
  const out: LessonGroup[] = [];
  const at = new Map<string, LessonGroup>();
  for (const l of lessons) {
    let g = at.get(l.group);
    if (!g) {
      g = { name: l.group, lessons: [] };
      at.set(l.group, g);
      out.push(g);
    }
    g.lessons.push(l);
  }
  return out;
}

/** 12:34；超过 1 小时用 1:02:03 */
export function formatTime(seconds: number): string {
  const s = Math.max(0, Math.floor(Number.isFinite(seconds) ? seconds : 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return `${h ? h + ":" : ""}${mm}:${String(r).padStart(2, "0")}`;
}

let cache: MathData | null = null;

export async function loadMath(): Promise<MathData> {
  if (cache) return cache;
  const res = await fetch("/data/math.json");
  if (!res.ok) throw new Error("数学课程数据加载失败");
  cache = (await res.json()) as MathData;
  return cache;
}
