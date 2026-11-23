import { describe, expect, it } from "vitest";
import raw from "../../public/data/speak.json";
import type { SpeakData } from "./speak";

const data = raw as unknown as SpeakData;

describe("speak.json v4 场景语料", () => {
  it("45 个场景，Part 分布 14/16/15", () => {
    expect(data.scenes).toHaveLength(45);
    const count = (p: number) => data.scenes.filter((s) => s.part === p).length;
    expect([count(1), count(2), count(3)]).toEqual([14, 16, 15]);
  });

  it("每个场景 3 条跟读句、2 道造句题，且与 pack 一一对应", () => {
    for (const s of data.scenes) {
      expect(s.shadowIds, s.id).toHaveLength(3);
      expect(s.make, s.id).toHaveLength(2);
      const pack = data.packs.find((p) => p.id === s.id);
      expect(pack, `pack ${s.id}`).toBeTruthy();
      expect(pack!.ids).toEqual(s.shadowIds);
    }
  });

  it("跟读句都是完整句子（≥8 词，以 . ? ! 结尾）", () => {
    for (const s of data.shadow) {
      expect(s.en.split(/\s+/).length, s.id).toBeGreaterThanOrEqual(8);
      expect(s.en, s.id).toMatch(/[.?!]$/);
      expect(s.cn.length, s.id).toBeGreaterThan(0);
    }
  });

  it("造句题有中文提示与完整英文标准答案", () => {
    for (const scene of data.scenes) {
      for (const m of scene.make ?? []) {
        expect(m.prompt_cn.length, m.id).toBeGreaterThan(0);
        expect(m.answer, m.id).toMatch(/[.?!]$/);
      }
    }
  });

  it("场景 id 不重复，shadow id 不重复", () => {
    expect(new Set(data.scenes.map((s) => s.id)).size).toBe(45);
    expect(new Set(data.shadow.map((s) => s.id)).size).toBe(data.shadow.length);
  });
});
