import { describe, expect, it } from "vitest";
import {
  DONE_FLAG, formatTime, groupsOf, isDone, lessonKey, nextLesson,
  seriesProgress, statusOf, videoUrl, type MathLesson, type VideoRec,
} from "./math";

const L = (id: string, no: string, group = "枚举法"): MathLesson => ({
  id, no, title: `课 ${no}`, tag: "拓展B", group, file: `${no} 标题(一)(拓展B).mp4`, size: 1,
});

describe("数学课程：地址与键", () => {
  it("中文、空格、括号按段编码", () => {
    const url = videoUrl("grade_3", "40 枚举法(一)(拓展B).mp4");
    expect(url).toBe(
      "/media/math/grade_3/40%20%E6%9E%9A%E4%B8%BE%E6%B3%95(%E4%B8%80)(%E6%8B%93%E5%B1%95B).mp4",
    );
  });

  it("媒体目录也编码，保留层级", () => {
    expect(videoUrl("a/b", "x y.mp4")).toBe("/media/math/a/b/x%20y.mp4");
  });

  it("进度键带统一前缀", () => {
    expect(lessonKey("g3-43.1")).toBe("math:v:g3-43.1");
  });
});

describe("数学课程：状态", () => {
  it("无记录 = 未开始", () => {
    expect(statusOf(null)).toBe("todo");
    expect(statusOf({ idx: 0, seen: [] })).toBe("todo");
  });

  it("有秒数但没学完 = 学习中", () => {
    expect(statusOf({ idx: 42, seen: [] })).toBe("watching");
    expect(isDone({ idx: 42, seen: [] })).toBe(false);
  });

  it("seen 含 done = 学完（即使 idx 很小）", () => {
    expect(statusOf({ idx: 0, seen: [DONE_FLAG] })).toBe("done");
    expect(isDone({ idx: 0, seen: [DONE_FLAG] })).toBe(true);
  });
});

describe("数学课程：汇总", () => {
  const lessons = [L("a", "40"), L("b", "41"), L("c", "42"), L("d", "43")];
  const recs: Record<string, VideoRec> = {
    a: { idx: 600, seen: [DONE_FLAG] },
    b: { idx: 90, seen: [] },
    c: { idx: 0, seen: [] },
  };
  const recOf = (id: string) => recs[id] ?? null;

  it("统计 done / watching / todo 与百分比", () => {
    expect(seriesProgress(lessons, recOf)).toEqual({
      total: 4, done: 1, watching: 1, todo: 2, percent: 25,
    });
  });

  it("空清单不除以零", () => {
    expect(seriesProgress([], recOf)).toEqual({
      total: 0, done: 0, watching: 0, todo: 0, percent: 0,
    });
  });

  it("下一课 = 第一节没学完的", () => {
    expect(nextLesson(lessons, recOf)?.id).toBe("b");
    const allDone = (id: string) => ({ idx: 1, seen: [DONE_FLAG] });
    expect(nextLesson(lessons, allDone)).toBeNull();
  });

  it("按出现顺序分组，不重排", () => {
    const gs = groupsOf([L("a", "40", "B组"), L("b", "41", "A组"), L("c", "42", "B组")]);
    expect(gs.map((g) => g.name)).toEqual(["B组", "A组"]);
    expect(gs[0].lessons.map((l) => l.id)).toEqual(["a", "c"]);
  });
});

describe("数学课程：时间", () => {
  it("不足 1 小时用 m:ss", () => {
    expect(formatTime(0)).toBe("0:00");
    expect(formatTime(65)).toBe("1:05");
    expect(formatTime(754)).toBe("12:34");
  });

  it("超过 1 小时用 h:mm:ss", () => {
    expect(formatTime(3723)).toBe("1:02:03");
  });

  it("非法值归零", () => {
    expect(formatTime(Number.NaN)).toBe("0:00");
    expect(formatTime(-5)).toBe("0:00");
  });
});
