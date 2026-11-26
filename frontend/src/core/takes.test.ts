import { describe, expect, it } from "vitest";
import {
  bestTake, filterMyTakes, pcmToWav, pruneTakes, takeStorageKey, type Take,
} from "./takes";

function take(id: string, at: number, score: number): Take {
  return {
    id,
    key: "u|s:p",
    promptKey: "s:p",
    at,
    score,
    transcript: id,
    mime: "audio/webm",
    blob: new Blob(),
  };
}

describe("pruneTakes", () => {
  it("不足三条时全部保留，按时间倒序", () => {
    const rows = [take("a", 1, 60), take("b", 2, 70)];
    expect(pruneTakes(rows).map((t) => t.id)).toEqual(["b", "a"]);
  });

  it("默认保留最近三条", () => {
    const rows = [take("a", 1, 60), take("b", 2, 61), take("c", 3, 62), take("d", 4, 63)];
    expect(pruneTakes(rows).map((t) => t.id)).toEqual(["d", "c", "b"]);
  });

  it("最高分不在最近三条时额外保留（最多四条）", () => {
    const rows = [
      take("old-best", 1, 95),
      take("b", 2, 60),
      take("c", 3, 61),
      take("d", 4, 62),
    ];
    expect(pruneTakes(rows).map((t) => t.id)).toEqual(["d", "c", "b", "old-best"]);
  });

  it("最高分已在最近三条内时不重复", () => {
    const rows = [take("a", 1, 50), take("b", 2, 60), take("c", 3, 90), take("d", 4, 70)];
    expect(pruneTakes(rows).map((t) => t.id)).toEqual(["d", "c", "b"]);
  });

  it("全部没有分数时只保留最近三条", () => {
    const rows = [take("a", 1, 0), take("b", 2, 0), take("c", 3, 0), take("d", 4, 0)];
    expect(pruneTakes(rows).map((t) => t.id)).toEqual(["d", "c", "b"]);
  });
});

describe("bestTake", () => {
  it("取分数最高；同分取较新的一条", () => {
    const rows = [take("a", 5, 80), take("b", 9, 80), take("c", 1, 90)];
    expect(bestTake(rows)?.id).toBe("c");
    expect(bestTake([take("x", 1, 80), take("y", 2, 80)])?.id).toBe("y");
  });

  it("没有有效分数时返回 null", () => {
    expect(bestTake([take("a", 1, 0)])).toBeNull();
    expect(bestTake([])).toBeNull();
  });
});

describe("takeStorageKey", () => {
  it("按用户与题目隔离，未登录归 guest", () => {
    expect(takeStorageKey("amy", "c101:p1")).toBe("amy|c101:p1");
    expect(takeStorageKey("", "c101:p1")).toBe("guest|c101:p1");
  });
});

describe("filterMyTakes", () => {
  it("只保留当前账号，按时间倒序", () => {
    const rows = [
      { ...take("a", 1, 60), key: "amy|s:p" },
      { ...take("b", 3, 80), key: "amy|s:q" },
      { ...take("c", 2, 70), key: "ab|s:p" },
      { ...take("d", 4, 90), key: "guest|s:p" },
    ];
    expect(filterMyTakes(rows, "amy").map((t) => t.id)).toEqual(["b", "a"]);
  });

  it("未登录只看 guest，不串到用户名以 guest 开头的账号", () => {
    const rows = [
      { ...take("a", 1, 60), key: "guest|s:p" },
      { ...take("b", 2, 70), key: "guestie|s:p" },
    ];
    expect(filterMyTakes(rows, "").map((t) => t.id)).toEqual(["a"]);
  });
});

describe("pcmToWav", () => {
  it("输出 16k 单声道 16bit WAV 头与采样数据", async () => {
    const pcm = new Int16Array([0, 1000, -1000, 32767, -32768]);
    const blob = pcmToWav(pcm);
    expect(blob.type).toBe("audio/wav");
    const view = new DataView(await blob.arrayBuffer());
    expect(String.fromCharCode(...new Uint8Array(view.buffer, 0, 4))).toBe("RIFF");
    expect(String.fromCharCode(...new Uint8Array(view.buffer, 8, 4))).toBe("WAVE");
    expect(String.fromCharCode(...new Uint8Array(view.buffer, 36, 4))).toBe("data");
    expect(view.getUint16(22, true)).toBe(1); // 单声道
    expect(view.getUint32(24, true)).toBe(16000);
    expect(view.getUint16(34, true)).toBe(16);
    expect(view.getUint32(40, true)).toBe(pcm.length * 2);
    expect(view.byteLength).toBe(44 + pcm.length * 2);
    expect(view.getInt16(44 + 2 * 2, true)).toBe(-1000);
  });
});
