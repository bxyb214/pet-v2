/**
 * 首页聚合（纯逻辑）：今日计划进度、口语打卡、数学进度、继续目标。
 * 只读现有数据，不新增同步字段；组件负责取数，本模块只做计算。
 */
import {
  availableBooks, courseProgress, nextLesson, statusOf,
  type MathBook, type RecLookup,
} from "./math";
import { dayDone, type DayCheck } from "./speak";

export type PlanProgress = {
  hasPlan: boolean;
  /** 当前学习日：第一个未完成的天；全部完成时为最后一天 */
  day: number;
  totalDays: number;
  doneDays: number;
  todayDone: boolean;
  /** 完成比例 0–100 */
  percent: number;
};

function daySet(daysDone: Array<string | number>): Set<number> {
  const out = new Set<number>();
  for (const d of daysDone) {
    const n = Number(d);
    if (Number.isInteger(n) && n >= 1) out.add(n);
  }
  return out;
}

export function planProgress(length: number, daysDone: Array<string | number>): PlanProgress {
  const totalDays = Math.max(0, Math.floor(Number(length) || 0));
  if (!totalDays) {
    return { hasPlan: false, day: 0, totalDays: 0, doneDays: 0, todayDone: false, percent: 0 };
  }
  const done = daySet(daysDone);
  let day = totalDays;
  for (let d = 1; d <= totalDays; d++) {
    if (!done.has(d)) { day = d; break; }
  }
  const doneDays = [...done].filter((d) => d <= totalDays).length;
  return {
    hasPlan: true,
    day,
    totalDays,
    doneDays,
    todayDone: done.has(day),
    percent: Math.round((doneDays / totalDays) * 100),
  };
}

/** 口语打卡按「原始天」记录；计划天一一对应，首个未完成天即当前天 */
export function speakProgress(length: number, checks: DayCheck[]): PlanProgress {
  const byDay = new Map<number, DayCheck>();
  for (const c of checks) if (Number.isInteger(c.day)) byDay.set(c.day, c);
  const total = Math.max(0, Math.floor(Number(length) || 0));
  const done: number[] = [];
  for (let d = 1; d <= total; d++) {
    if (dayDone(byDay.get(d))) done.push(d);
  }
  return planProgress(total, done);
}

export type ProgressCount = { done: number; total: number };

/** 只统计已创建的计划，避免把「没计划」当成未完成拖低进度 */
export function overallProgress(items: Array<{ exists: boolean; done: boolean }>): ProgressCount {
  const active = items.filter((t) => t.exists);
  return { done: active.filter((t) => t.done).length, total: active.length };
}

/** 「继续」目标：按传入顺序取第一个已创建且未完成的任务 */
export function pickContinue(
  items: Array<{ exists: boolean; done: boolean; route: string }>,
  fallback: string,
): string {
  return items.find((t) => t.exists && !t.done)?.route ?? fallback;
}

export function greetingOf(hour: number): string {
  if (hour < 5) return "晚上好";
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

/** 口语按「跟读 → 造句 → 对话」推进：落到当天第一个没做的环节 */
export function nextSpeakRoute(day: number, checks: DayCheck[]): string {
  const c = checks.find((x) => x.day === day);
  if (c?.shadow_done && !c.make_done) return `/english/speak/make?day=${day}`;
  if (c?.shadow_done && c.make_done && !c.talk_done) return `/english/speak/talk?day=${day}`;
  return `/english/speak/shadow?day=${day}`;
}

export type MathSummary = {
  hasBooks: boolean;
  gradeName: string;
  /** 「第 12 节」；没有可继续的课节时为空 */
  lessonLabel: string;
  /** 可直接续播的课程地址；没有时回课程首页 */
  route: string;
  done: number;
  total: number;
  watching: number;
  /** 「三年级 / 四年级已上线 / 五年级即将上线」 */
  grades: string;
  detail: string;
};

/** 数学：优先正在学的课节，其次第一节没学完的；统计只算已上线教材 */
export function summarizeMath(books: MathBook[], recOf: RecLookup): MathSummary {
  const avail = availableBooks(books);
  const stat = courseProgress(books, recOf);
  const soon = books.filter((b) => b.comingSoon).map((b) => `${b.gradeName}即将上线`);
  let current: { book: MathBook; lessonId: string; no: string } | null = null;

  for (const book of avail) {
    const lesson = book.lessons.find((l) => statusOf(recOf(l.id)) === "watching");
    if (lesson) {
      current = { book, lessonId: lesson.id, no: lesson.no };
      break;
    }
  }
  if (!current && avail.length) {
    const book = avail[0];
    const lesson = nextLesson(book.lessons, recOf);
    if (lesson) current = { book, lessonId: lesson.id, no: lesson.no };
  }

  const grades = [...avail.map((b) => b.gradeName), ...soon].join(" / ");
  return {
    hasBooks: avail.length > 0,
    gradeName: current?.book.gradeName ?? avail[0]?.gradeName ?? "",
    lessonLabel: current ? `第 ${current.no} 节` : "",
    route: current
      ? `/math/books/${encodeURIComponent(current.book.id)}/${encodeURIComponent(current.lessonId)}`
      : "/math",
    done: stat.done,
    total: stat.total,
    watching: stat.watching,
    grades,
    detail: stat.total ? `已学完 ${stat.done} 节 · 正在学 ${stat.watching} 节` : "还没有开始",
  };
}
