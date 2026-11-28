import { describe, expect, it } from "vitest";
import raw from "../../public/data/ket/speak.json";
import { speakUrl, type SpeakData } from "./speak";

const data = raw as unknown as SpeakData;

describe("KET speak.json", () => {
  it("45 个场景，Part 1/2 分别为 25/20", () => {
    expect(data.scenes).toHaveLength(45);
    const count = (p: number) => data.scenes.filter((s) => s.part === p).length;
    expect([count(1), count(2)]).toEqual([25, 20]);
  });

  it("每个场景 3 条跟读句、2 道造句题", () => {
    for (const s of data.scenes) {
      expect(s.shadowIds, s.id).toHaveLength(3);
      expect(s.make, s.id).toHaveLength(2);
      expect(s.openers.length, s.id).toBeGreaterThan(0);
    }
  });

  it("跟读句是完整句子，重读词都在句子里", () => {
    for (const s of data.shadow) {
      expect(s.en, s.id).toMatch(/[.?!]$/);
      expect(s.cn.length, s.id).toBeGreaterThan(0);
      for (const w of s.focus ?? []) {
        expect(s.en.toLowerCase(), `${s.id}: ${w}`).toContain(w.toLowerCase());
      }
    }
  });

  it("45 天计划与场景一一对应", () => {
    expect(data.plan.days ?? []).toHaveLength(45);
    expect(data.plan.phases.map((p) => p.to)).toEqual([25, 45]);
    for (const d of data.plan.days ?? []) {
      expect(data.scenes.some((s) => s.id === d.scene), `day ${d.d}`).toBe(true);
    }
  });

  it("按级别取数据地址", () => {
    expect(speakUrl("pet")).toBe("/data/speak.json");
    expect(speakUrl("ket")).toBe("/data/ket/speak.json");
    expect(speakUrl()).toBe("/data/speak.json");
  });
});
