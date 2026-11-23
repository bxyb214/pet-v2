import { describe, expect, it } from "vitest";
import { dayDone, parseShadowReply, phaseOfDay, type SpeakPlan } from "./speak";

describe("phaseOfDay", () => {
  const plan: SpeakPlan = {
    title: "90 天",
    phases: [
      { name: "Part 1", desc: "第 1–30 天", from: 1, to: 30 },
      { name: "Part 2", desc: "第 31–55 天", from: 31, to: 55 },
    ],
  };
  it("按天命中阶段", () => {
    expect(phaseOfDay(plan, 1)?.name).toBe("Part 1");
    expect(phaseOfDay(plan, 40)?.name).toBe("Part 2");
    expect(phaseOfDay(plan, 60)).toBeNull();
  });
});

describe("dayDone", () => {
  it("跟读+造句+对话都完成才算", () => {
    expect(dayDone({ day: 1, shadow_done: true, make_done: true, talk_done: true, score: 80 })).toBe(true);
    expect(dayDone({ day: 1, shadow_done: true, make_done: true, talk_done: false, score: 0 })).toBe(false);
    expect(dayDone(undefined)).toBe(false);
  });
});

describe("parseShadowReply", () => {
  it("纯 JSON 解析", () => {
    const r = parseShadowReply('{"transcript":"hello","score":88,"words":[{"w":"hello","ok":true}],"tips":["注意重音"],"say":"Good!"}');
    expect(r?.score).toBe(88);
    expect(r?.tips).toEqual(["注意重音"]);
  });
  it("容忍 markdown 围栏", () => {
    const r = parseShadowReply('```json\n{"transcript":"","score":0,"words":[],"tips":["大声点"],"say":""}\n```');
    expect(r?.score).toBe(0);
  });
  it("垃圾输入返回 null", () => {
    expect(parseShadowReply("sorry I don't understand")).toBeNull();
  });
});

describe("phaseOfDay", () => {
  const plan: SpeakPlan = {
    title: "90 天",
    phases: [
      { name: "Part 1", desc: "第 1–30 天", from: 1, to: 30 },
      { name: "Part 2", desc: "第 31–55 天", from: 31, to: 55 },
    ],
  };
  it("按天命中阶段", () => {
    expect(phaseOfDay(plan, 1)?.name).toBe("Part 1");
    expect(phaseOfDay(plan, 40)?.name).toBe("Part 2");
    expect(phaseOfDay(plan, 60)).toBeNull();
  });
});

describe("dayDone", () => {
  it("跟读+造句+对话都完成才算", () => {
    expect(dayDone({ day: 1, shadow_done: true, make_done: true, talk_done: true, score: 80 })).toBe(true);
    expect(dayDone({ day: 1, shadow_done: true, make_done: true, talk_done: false, score: 0 })).toBe(false);
    expect(dayDone(undefined)).toBe(false);
  });
});

describe("parseShadowReply", () => {
  it("纯 JSON 解析", () => {
    const r = parseShadowReply('{"transcript":"hello","score":88,"words":[{"w":"hello","ok":true}],"tips":["注意重音"],"say":"Good!"}');
    expect(r?.score).toBe(88);
    expect(r?.tips).toEqual(["注意重音"]);
  });
  it("容忍 markdown 围栏", () => {
    const r = parseShadowReply('```json\n{"transcript":"","score":0,"words":[],"tips":["大声点"],"say":""}\n```');
    expect(r?.score).toBe(0);
  });
  it("垃圾输入返回 null", () => {
    expect(parseShadowReply("sorry I don't understand")).toBeNull();
  });
});
