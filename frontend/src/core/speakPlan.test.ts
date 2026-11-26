import { describe, expect, it } from "vitest";
import {
  planDayDone, planDayScenes, resolvePlanDay, sourceRangeText, splitSpeakPlan,
  type DayCheck, type SpeakData, type SpeakPlan, type SpeakSourceDay,
} from "./speak";

function makeData(): SpeakData {
  const sourceDays: SpeakSourceDay[] = Array.from({ length: 90 }, (_, i) => ({
    d: i + 1,
    phase: i < 30 ? 0 : i < 55 ? 1 : i < 75 ? 2 : 3,
    pack: `legacy-${i + 1}`,
    title: `旧话题 ${i + 1}`,
    goal: "旧目标",
    focus: "旧 focus",
    shadow: [`sh${String(i + 1).padStart(3, "0")}`], // 旧编号，故意与 v3 不一致
    scene: `c${100 + i}`,
  }));
  const plan: SpeakPlan = { title: "90 天", phases: [], days: sourceDays };
  const packs = Array.from({ length: 19 }, (_, i) => ({
    id: `p${i + 1}`, name: `Pack ${i + 1}`, part: i < 17 ? 1 : i === 17 ? 2 : 3,
    ids: Array.from({ length: 5 }, (_, j) => `tp-${i + 1}-${j + 1}`), order: i + 1,
  }));
  const scenes = Array.from({ length: 161 }, (_, i) => ({
    id: `sc${i + 1}`, part: 1, title: `Scene ${i + 1}`, cn: "", level: "", focus: `focus ${i + 1}`, openers: [],
  }));
  return { meta: {}, packs, shadow: [], free: [], scenes, plan };
}

function coverage(data: SpeakData, length: number): number[] {
  return splitSpeakPlan(data, length).flatMap((d) => d.sourceDays);
}

describe("splitSpeakPlan", () => {
  it("30 天：每天合并 3 个原始天，不重不漏", () => {
    const data = makeData();
    const out = splitSpeakPlan(data, 30);
    expect(out).toHaveLength(30);
    expect(out[0].sourceDays).toEqual([1, 2, 3]);
    expect(out[29].sourceDays).toEqual([88, 89, 90]);
    expect(coverage(data, 30)).toEqual(Array.from({ length: 90 }, (_, i) => i + 1));
  });

  it("内容从 v3 packs/scenes 取，不用旧的 sh/c 编号", () => {
    const data = makeData();
    const out = splitSpeakPlan(data, 90);
    const allIds = new Set(data.packs.flatMap((p) => p.ids));
    expect(out[0].shadowIds.length).toBeGreaterThan(0);
    expect(out[0].shadowIds.every((id) => allIds.has(id))).toBe(true);
    expect(out.every((d) => d.shadowIds.length > 0)).toBe(true);
    expect(out.every((d) => !d.shadowIds.some((id) => id.startsWith("sh")))).toBe(true);
    expect(out[0].scene.startsWith("sc")).toBe(true);
    expect(out[0].sceneTitle.startsWith("Scene")).toBe(true);
    expect(out[0].sceneIds.length).toBeGreaterThan(0);
    expect(out[0].sceneIds.every((id) => id.startsWith("sc"))).toBe(true);
    expect(out[0].sceneTitles.length).toBe(out[0].sceneIds.length);
    expect(out[0].sceneTitles.every((t) => t.startsWith("Scene"))).toBe(true);
  });

  it("90 天：每天一个原始天、一个 pack", () => {
    const out = splitSpeakPlan(makeData(), 90);
    expect(out).toHaveLength(90);
    expect(out[0].sourceDays).toEqual([1]);
    expect(out[89].sourceDays).toEqual([90]);
    expect(out[0].title).toBe("Pack 1");
    expect(out[89].title).toBe("Pack 19");
  });

  it("7 天：余数分给前几天，仍覆盖 1–90", () => {
    const data = makeData();
    const out = splitSpeakPlan(data, 7);
    expect(out).toHaveLength(7);
    expect(out.map((d) => d.sourceDays.length)).toEqual([13, 13, 13, 13, 13, 13, 12]);
    expect(coverage(data, 7)).toEqual(Array.from({ length: 90 }, (_, i) => i + 1));
  });

  it("length<=0 时按源天数；超过源天数时封顶", () => {
    expect(splitSpeakPlan(makeData(), 0)).toHaveLength(90);
    expect(splitSpeakPlan(makeData(), 200)).toHaveLength(90);
  });

  it("缺数据时返回空数组", () => {
    expect(splitSpeakPlan(null, 30)).toEqual([]);
  });
});

describe("planDayDone / sourceRangeText", () => {
  const checks: Record<number, DayCheck> = {
    1: { day: 1, shadow_done: true, make_done: true, talk_done: true, score: 90 },
    2: { day: 2, shadow_done: true, make_done: true, talk_done: false, score: 80 },
    3: { day: 3, shadow_done: true, make_done: true, talk_done: true, score: 80 },
  };

  it("合并日需要组内所有原始天完成", () => {
    const pd = splitSpeakPlan(makeData(), 30)[0];
    expect(planDayDone(pd, checks)).toBe(false); // 第 2 天缺 talk
    checks[2].talk_done = true;
    expect(planDayDone(pd, checks)).toBe(true);
  });

  it("范围文案", () => {
    expect(sourceRangeText(splitSpeakPlan(makeData(), 30)[0])).toBe("第 1–3 天");
    expect(sourceRangeText(splitSpeakPlan(makeData(), 90)[0])).toBe("第 1 天");
  });
});

describe("resolvePlanDay / planDayScenes", () => {
  const days = splitSpeakPlan(makeData(), 30);

  it("优先使用路由里的有效 day", () => {
    expect(resolvePlanDay(days, {}, 3)?.day).toBe(3);
  });

  it("没有 day 时取第一个未完成日，全部完成则回第 1 天", () => {
    const checks: Record<number, DayCheck> = {};
    // 30 天计划的第 1 天合并原始天 1–3，必须全部完成才算完成
    for (const d of days[0].sourceDays) {
      checks[d] = { day: d, shadow_done: true, make_done: true, talk_done: true, score: 90 };
    }
    expect(resolvePlanDay(days, checks)?.day).toBe(2);
    const allDone: Record<number, DayCheck> = {};
    for (const pd of days) {
      for (const d of pd.sourceDays) {
        allDone[d] = { day: d, shadow_done: true, make_done: true, talk_done: true, score: 90 };
      }
    }
    expect(resolvePlanDay(days, allDone)?.day).toBe(1);
  });

  it("day 越界时回退到未完成日；空计划返回 null", () => {
    expect(resolvePlanDay(days, {}, 999)?.day).toBe(1);
    expect(resolvePlanDay([], {}, 1)).toBeNull();
  });

  it("按计划顺序取当天场景，自动跳过缺失 id", () => {
    const data = makeData();
    const pd = days[0];
    const scenes = planDayScenes(data, pd);
    expect(scenes.map((s) => s.id)).toEqual(pd.sceneIds);
    const missing = { ...pd, sceneIds: ["sc1", "nope", "sc2"], sceneTitles: ["Scene 1", "?", "Scene 2"] };
    expect(planDayScenes(data, missing).map((s) => s.id)).toEqual(["sc1", "sc2"]);
    expect(planDayScenes(null, pd)).toEqual([]);
    expect(planDayScenes(data, null)).toEqual([]);
  });
});
