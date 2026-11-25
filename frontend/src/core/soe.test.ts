/** SOE 结果解析测试（腾讯智聆口语评测新版返回的类 Python dict 文本）。 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SoeEval, parseSoeResult, soeTips, trimSilence } from "./soe";
import { cancelMic, micActive, resetMicForTest, stopMic } from "./micPresence";
import { resetDevModeForTest } from "./devMode";

describe("parseSoeResult", () => {
  it("正常解析综合分、三项子分与逐词准确度", () => {
    const raw =
      "SuggestedScore:87.4 PronAccuracy:82.1 PronFluency:0.9 PronCompletion:1.0 " +
      "Words:[{PronAccuracy:91.2 PronFluency:0.98 Word:hello Tag:0 PhoneInfo:[]}" +
      "{PronAccuracy:45.0 PronFluency:0.8 Word:world Tag:0 PhoneInfo:[]}]";
    const r = parseSoeResult(raw);
    expect(r.score).toBe(87);
    expect(r.accuracy).toBe(82);
    expect(r.fluency).toBe(90);
    expect(r.completion).toBe(100);
    expect(r.words).toEqual([
      { w: "hello", ok: true, acc: 91, tag: 0 },
      { w: "world", ok: false, acc: 45, tag: 0 },
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

  it("新版返回结构化对象也能解析", () => {
    const r = parseSoeResult({
      SuggestedScore: 97.64,
      PronAccuracy: 97.64,
      PronFluency: 88.5,
      PronCompletion: 100,
      Words: [
        { Word: "the", PronAccuracy: 97.4, ReferenceWord: "the_0" },
        { Word: "lazy", PronAccuracy: 45, MatchTag: 3 },
      ],
    });
    expect(r.score).toBe(98);
    expect(r.accuracy).toBe(98);
    expect(r.fluency).toBe(89);
    expect(r.completion).toBe(100);
    expect(r.words).toEqual([
      { w: "the", ok: true, acc: 97 },
      { w: "lazy", ok: false, acc: 45, tag: 3 },
    ]);
  });

  it("漏读词（准确度为 -1）保留为未读对，而不是被丢掉", () => {
    const r = parseSoeResult({
      SuggestedScore: 60,
      Words: [{ Word: "really", PronAccuracy: -1, MatchTag: 2 }],
    });
    expect(r.words).toEqual([{ w: "really", ok: false, tag: 2 }]);
  });

  it("只返回 Sentences 时回落到第一句解析", () => {
    const r = parseSoeResult({
      Sentences: [{
        SuggestedScore: 81,
        PronAccuracy: 80,
        PronFluency: 0.75,
        Words: [{ Word: "hello", PronAccuracy: 88 }],
      }],
    });
    expect(r.score).toBe(81);
    expect(r.accuracy).toBe(80);
    expect(r.fluency).toBe(75);
    expect(r.words).toEqual([{ w: "hello", ok: true, acc: 88 }]);
  });
});

describe("soeTips", () => {
  const base = { accuracy: 90, fluency: 90, completion: 100, words: [] };

  it("按漏读/增读/替换和三项分数给出改进提示", () => {
    const tips = soeTips({
      score: 55,
      accuracy: 60,
      fluency: 50,
      completion: 70,
      words: [
        { w: "really", ok: false, tag: 2 },
        { w: "uh", ok: false, tag: 1 },
        { w: "world", ok: false, acc: 40, tag: 3 },
      ],
    });
    const text = tips.join("\n");
    expect(text).toContain("漏读了 really");
    expect(text).toContain("多读了 uh");
    expect(text).toContain("读成了别的词：world");
    expect(text).toContain("流利度 50 分");
    expect(text).toContain("完整度 70 分");
    expect(tips.length).toBeLessThanOrEqual(4);
  });

  it("读得好时给鼓励，不硬凑问题", () => {
    const tips = soeTips({ ...base, score: 92, words: [{ w: "hello", ok: true, acc: 95 }] });
    expect(tips).toEqual(["读得很棒！可以再用正常语速读一遍，保持连读。"]);
  });
});

describe("trimSilence", () => {
  const tone = (samples: number): Int16Array => {
    const a = new Int16Array(samples);
    for (let i = 0; i < samples; i++) a[i] = Math.round(8000 * Math.sin((2 * Math.PI * 440 * i) / 16000));
    return a;
  };

  it("裁掉首尾静音并保留余量", () => {
    const raw = new Int16Array(16000 * 3);
    raw.set(tone(16000), 16000); // 中间 1 秒有声，前后各 1 秒静音
    const out = trimSilence(raw);
    expect(out.length).toBeLessThan(raw.length);
    expect(out.length).toBeGreaterThan(16000); // 语音保留 + 两侧 300ms
  });

  it("全静音时原样返回", () => {
    const raw = new Int16Array(16000);
    expect(trimSilence(raw)).toBe(raw);
  });
});

describe("SoeEval：关闭麦克风（开发环境模拟）", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    resetMicForTest();
    resetDevModeForTest();
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ dev_mode: true }) })));
  });
  afterEach(() => {
    resetMicForTest();
    resetDevModeForTest();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  function makeEval(
    onResult: ReturnType<typeof vi.fn>,
    onStopped: ReturnType<typeof vi.fn>,
    onMicClosed: ReturnType<typeof vi.fn>,
    onStatus: (s: string) => void = () => {},
  ) {
    return new SoeEval({
      refText: "hello world",
      onStatus,
      onResult,
      onError: () => {},
      onMicClosed,
      onStopped,
    });
  }

  it("读过之后关闭麦克风，自动评分并给出结果", async () => {
    const onResult = vi.fn();
    const onStopped = vi.fn();
    const onMicClosed = vi.fn();
    const ev = makeEval(onResult, onStopped, onMicClosed);
    await ev.start();
    vi.advanceTimersByTime(1000); // 累计开口时长
    stopMic();
    expect(onMicClosed).toHaveBeenCalledTimes(1);
    expect(micActive.value).toBe(false);
    vi.advanceTimersByTime(600);
    expect(onResult).toHaveBeenCalledTimes(1);
    expect(onResult.mock.calls[0][0].score).toBe(100);
    expect(onStopped).toHaveBeenCalledTimes(1);
  });

  it("还没开口就点提交，只提示继续朗读，不结束会话", async () => {
    const onResult = vi.fn();
    const onStopped = vi.fn();
    const onMicClosed = vi.fn();
    const onStatus = vi.fn();
    const ev = makeEval(onResult, onStopped, onMicClosed, onStatus);
    await ev.start();
    stopMic();
    expect(onStatus).toHaveBeenCalledWith(expect.stringContaining("还没听到声音"));
    expect(onMicClosed).not.toHaveBeenCalled();
    expect(micActive.value).toBe(true);
    vi.advanceTimersByTime(600);
    expect(onResult).not.toHaveBeenCalled();
    ev.stop();
    expect(onStopped).toHaveBeenCalledTimes(1);
  });

  it("数字人「取消」：放弃本次录音，不评分", async () => {
    const onResult = vi.fn();
    const onStopped = vi.fn();
    const onStatus = vi.fn();
    const ev = makeEval(onResult, onStopped, vi.fn(), onStatus);
    await ev.start();
    vi.advanceTimersByTime(1000);
    expect(micActive.value).toBe(true);
    cancelMic();
    expect(onResult).not.toHaveBeenCalled();
    expect(micActive.value).toBe(false);
    expect(onStatus).toHaveBeenCalledWith(expect.stringContaining("已取消"));
    expect(onStopped).toHaveBeenCalledTimes(1);
    vi.advanceTimersByTime(1000);
    expect(onResult).not.toHaveBeenCalled();
  });

  it("点了提交后再关闭麦克风，已发出的评分结果仍然返回", async () => {
    const onResult = vi.fn();
    const onStopped = vi.fn();
    const ev = makeEval(onResult, onStopped, vi.fn());
    await ev.start();
    vi.advanceTimersByTime(1000);
    ev.submit();
    expect(micActive.value).toBe(false);
    stopMic();
    vi.advanceTimersByTime(600);
    expect(onResult).toHaveBeenCalledTimes(1);
    expect(onStopped).toHaveBeenCalledTimes(1);
  });

  it("提交后进入 busy，拿到结果后复位（页面据此隐藏按钮）", async () => {
    const onBusy = vi.fn();
    const ev = new SoeEval({
      refText: "hello world",
      onStatus: () => {},
      onResult: vi.fn(),
      onError: () => {},
      onBusy,
    });
    await ev.start();
    vi.advanceTimersByTime(1000);
    ev.submit();
    expect(onBusy).toHaveBeenLastCalledWith(true);
    vi.advanceTimersByTime(600);
    expect(onBusy).toHaveBeenLastCalledWith(false);
  });
});

describe("SoeEval：评测消息", () => {
  it("结构化 result + final=1：回调结果，不抛异常也不等到超时", () => {
    const onResult = vi.fn();
    const onError = vi.fn();
    const ev = new SoeEval({
      refText: "the lazy dog",
      onStatus: () => {},
      onResult,
      onError,
    });
    const ws: { onmessage?: (ev: MessageEvent) => void } = {};
    (ev as unknown as { bindWs: (w: unknown) => void }).bindWs(ws);
    ws.onmessage?.({
      data: JSON.stringify({
        code: 0,
        final: 1,
        message: "abc_8",
        result: { SuggestedScore: 90.2, Words: [{ Word: "the", PronAccuracy: 95 }] },
      }),
    } as MessageEvent);
    expect(onError).not.toHaveBeenCalled();
    expect(onResult).toHaveBeenCalledWith({
      score: 90,
      accuracy: null,
      fluency: null,
      completion: null,
      words: [{ w: "the", ok: true, acc: 95 }],
    });
  });
});
