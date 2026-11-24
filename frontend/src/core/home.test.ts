import { describe, expect, it } from "vitest";
import {
  greetingOf, nextSpeakRoute, overallProgress, pickContinue, planProgress, speakProgress, summarizeMath,
} from "./home";
import type { MathBook, VideoRec } from "./math";
import type { DayCheck } from "./speak";

const check = (day: number, done: boolean): DayCheck => ({
  day,
  shadow_done: done,
  make_done: done,
  talk_done: done,
  score: done ? 90 : 0,
});

describe("planProgress", () => {
  it("没有计划", () => {
    expect(planProgress(0, [])).toEqual({
      hasPlan: false, day: 0, totalDays: 0, doneDays: 0, todayDone: false, percent: 0,
    });
  });

  it("取第一个未完成的天，并统计已完成天数", () => {
    const p = planProgress(5, ["1", "3"]);
    expect(p.day).toBe(2);
    expect(p.doneDays).toBe(2);
    expect(p.todayDone).toBe(false);
    expect(p.percent).toBe(40);
  });

  it("全部完成时停在最后一天", () => {
    const p = planProgress(3, ["1", "2", "3"]);
    expect(p.day).toBe(3);
    expect(p.todayDone).toBe(true);
    expect(p.percent).toBe(100);
  });

  it("忽略越界和非法天数", () => {
    const p = planProgress(2, ["0", "2", "9", "x"]);
    expect(p.day).toBe(1);
    expect(p.doneDays).toBe(1);
  });
});

describe("speakProgress", () => {
  it("口语打卡三项都完成才算当天完成", () => {
    const p = speakProgress(3, [check(1, true), check(2, false)]);
    expect(p.day).toBe(2);
    expect(p.doneDays).toBe(1);
    expect(p.todayDone).toBe(false);
  });

  it("没有打卡从第 1 天开始", () => {
    expect(speakProgress(30, []).day).toBe(1);
  });

  it("没有计划时返回空进度", () => {
    expect(speakProgress(0, [check(1, true)]).hasPlan).toBe(false);
  });
});

describe("overallProgress / pickContinue", () => {
  it("只统计已创建的计划", () => {
    const p = overallProgress([
      { exists: true, done: true },
      { exists: true, done: false },
      { exists: false, done: false },
    ]);
    expect(p).toEqual({ done: 1, total: 2 });
  });

  it("继续目标按顺序取第一个未完成项", () => {
    const items = [
      { exists: true, done: true, route: "/a" },
      { exists: false, done: false, route: "/b" },
      { exists: true, done: false, route: "/c" },
    ];
    expect(pickContinue(items, "/fallback")).toBe("/c");
  });

  it("全部完成或没有计划时回退", () => {
    expect(pickContinue([{ exists: true, done: true, route: "/a" }], "/fallback")).toBe("/fallback");
    expect(pickContinue([], "/fallback")).toBe("/fallback");
  });
});

describe("nextSpeakRoute", () => {
  it("按跟读 → 造句 → 对话找到第一个未完成环节", () => {
    expect(nextSpeakRoute(2, [])).toBe("/english/speak/shadow?day=2");
    expect(nextSpeakRoute(2, [check(2, false)])).toBe("/english/speak/shadow?day=2");
    const shadowDone: DayCheck = { day: 2, shadow_done: true, make_done: false, talk_done: false, score: 80 };
    expect(nextSpeakRoute(2, [shadowDone])).toBe("/english/speak/make?day=2");
    const makeDone: DayCheck = { day: 2, shadow_done: true, make_done: true, talk_done: false, score: 80 };
    expect(nextSpeakRoute(2, [makeDone])).toBe("/english/speak/talk?day=2");
  });
});

describe("greetingOf", () => {
  it("按小时切换问候", () => {
    expect(greetingOf(4)).toBe("晚上好");
    expect(greetingOf(9)).toBe("早上好");
    expect(greetingOf(15)).toBe("下午好");
    expect(greetingOf(21)).toBe("晚上好");
  });
});

describe("summarizeMath", () => {
  const lessons = [
    { id: "a", no: "1", title: "A", tag: "", group: "g", file: "a.mp4", size: 1 },
    { id: "b", no: "2", title: "B", tag: "", group: "g", file: "b.mp4", size: 1 },
  ];
  const books: MathBook[] = [
    { id: "g3", grade: 3, gradeName: "三年级", mediaDir: "g3", lessons },
    { id: "g5", grade: 5, gradeName: "五年级", mediaDir: "g5", lessons: [], comingSoon: true },
  ];
  const recOf = (id: string): VideoRec | null => {
    if (id === "a") return { idx: 30, seen: [] }; // 正在学
    if (id === "b") return { idx: 0, seen: ["done"] };
    return null;
  };

  it("优先正在学的课节，统计只算已上线教材", () => {
    const s = summarizeMath(books, recOf);
    expect(s.gradeName).toBe("三年级");
    expect(s.lessonLabel).toBe("第 1 节");
    expect(s.route).toBe("/math/books/g3/a");
    expect(s.done).toBe(1);
    expect(s.total).toBe(2);
    expect(s.watching).toBe(1);
    expect(s.grades).toBe("三年级 / 五年级即将上线");
    expect(s.detail).toBe("已学完 1 节 · 正在学 1 节");
  });

  it("没学过时指向第一节未完成课", () => {
    const s = summarizeMath(books, () => null);
    expect(s.lessonLabel).toBe("第 1 节");
    expect(s.route).toBe("/math/books/g3/a");
    expect(s.done).toBe(0);
  });

  it("全部学完时回课程首页", () => {
    const allDone = (): VideoRec => ({ idx: 100, seen: ["done"] });
    const s = summarizeMath(books, allDone);
    expect(s.lessonLabel).toBe("");
    expect(s.route).toBe("/math");
    expect(s.done).toBe(2);
  });
});
