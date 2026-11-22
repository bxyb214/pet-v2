/** SOE 结果解析测试（腾讯智聆口语评测新版返回的类 Python dict 文本）。 */
import { describe, expect, it } from "vitest";
import { parseSoeResult } from "./soe";

describe("parseSoeResult", () => {
  it("正常解析 SuggestedScore 与逐词准确度", () => {
    const raw =
      "SuggestedScore:87.4 PronAccuracy:82.1 PronFluency:0.9 PronCompletion:1.0 " +
      "Words:[{PronAccuracy:91.2 PronFluency:0.98 Word:hello Tag:0 PhoneInfo:[]}" +
      "{PronAccuracy:45.0 PronFluency:0.8 Word:world Tag:0 PhoneInfo:[]}]";
    const r = parseSoeResult(raw);
    expect(r.score).toBe(87);
    expect(r.words).toEqual([
      { w: "hello", ok: true },
      { w: "world", ok: false },
    ]);
  });

  it("整句分无效时回退 PronAccuracy / 逐词最高分", () => {
    const a = parseSoeResult("SuggestedScore:-0.36 PronAccuracy:72 Words:[]");
    expect(a.score).toBe(72);
    const b = parseSoeResult("SuggestedScore:-1 PronAccuracy:-1 Words:[{PronAccuracy:55 Word:apple}]");
    expect(b.score).toBe(55);
  });

  it("无有效分数时得 0 且不崩溃", () => {
    const r = parseSoeResult("SuggestedScore:-1 PronAccuracy:-1 Words:[]");
    expect(r.score).toBe(0);
    expect(r.words).toEqual([]);
    expect(parseSoeResult("").score).toBe(0);
  });
});
