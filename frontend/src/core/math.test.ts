import { describe, expect, it } from "vitest";
import {
  availableBooks, bookProgress, courseProgress, DONE_FLAG, findBook, firstBook, formatTime,
  groupsOf, isDone, lessonKey, nextLesson, statusOf, videoUrl,
  type MathBook, type MathLesson, type VideoRec,
} from "./math";

const L = (id: string, no: string, group = "枚举法"): MathLesson => ({
  id, no, title: `课 ${no}`, tag: "拓展B", group, file: `${no} 标题(一)(拓展B).mp4`, size: 1,
});

const B = (id: string, grade: number, lessons: MathLesson[], comingSoon = false): MathBook => ({
  id, grade, gradeName: `${grade}年级`, mediaDir: `grade_${grade}`, lessons, comingSoon,
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

  it("拿到媒体令牌后拼 mt 参数（AirPlay 由接收端取流也要能鉴权）", () => {
    expect(videoUrl("grade_4", "01 大数的读写.mp4", "a.b-c_d")).toBe(
      "/media/math/grade_4/01%20%E5%A4%A7%E6%95%B0%E7%9A%84%E8%AF%BB%E5%86%99.mp4?mt=a.b-c_d",
    );
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

describe("数学课程：教材与汇总", () => {
  const g3 = B("yongle-g3", 3, [L("a", "40"), L("b", "41"), L("c", "42"), L("d", "43")]);
  const g4 = B("yongle-g4", 4, [], true);
  const g5 = B("yongle-g5", 5, []);
  const recs: Record<string, VideoRec> = {
    a: { idx: 600, seen: [DONE_FLAG] },
    b: { idx: 90, seen: [] },
    c: { idx: 0, seen: [] },
  };
  const recOf = (id: string) => recs[id] ?? null;

  it("一本教材的 done / watching / todo 与百分比", () => {
    expect(bookProgress(g3, recOf)).toEqual({
      total: 4, done: 1, watching: 1, todo: 2, percent: 25,
    });
  });

  it("空教材不除以零", () => {
    expect(bookProgress(g5, recOf)).toEqual({
      total: 0, done: 0, watching: 0, todo: 0, percent: 0,
    });
  });

  it("课程总进度只统计已上线教材（未上线的空教材不计）", () => {
    expect(courseProgress([g3, g4, g5], recOf)).toEqual({
      total: 4, done: 1, watching: 1, todo: 2, percent: 25,
    });
  });

  it("availableBooks / firstBook 过滤未上线与空教材", () => {
    expect(availableBooks([g4, g3, g5]).map((b) => b.id)).toEqual(["yongle-g3"]);
    expect(firstBook([g4, g5, g3])?.id).toBe("yongle-g3");
    expect(firstBook([g4, g5])).toBeNull();
  });

  it("findBook 按 id 查找", () => {
    expect(findBook([g3, g4], "yongle-g4")?.grade).toBe(4);
    expect(findBook([g3], "nope")).toBeNull();
  });

  it("下一课 = 第一节没学完的", () => {
    expect(nextLesson(g3.lessons, recOf)?.id).toBe("b");
    const allDone = () => ({ idx: 1, seen: [DONE_FLAG] });
    expect(nextLesson(g3.lessons, allDone)).toBeNull();
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
