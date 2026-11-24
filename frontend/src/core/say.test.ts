import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { englishOnly, playWordAudio, say, splitExample, stopSpeaking } from "./say";

type FakeUtterance = { text: string; lang: string; rate: number; pitch: number; voice: unknown };

let spoken: FakeUtterance[] = [];
let cancel: ReturnType<typeof vi.fn>;

class FakeSpeechSynthesisUtterance implements FakeUtterance {
  text: string;
  lang = "";
  rate = 1;
  pitch = 1;
  voice: unknown = null;
  constructor(text: string) {
    this.text = text;
  }
}

function installSpeech(): void {
  spoken = [];
  cancel = vi.fn();
  const synth = {
    speak: vi.fn((u: FakeUtterance) => spoken.push(u)),
    cancel,
    getVoices: () => [],
    addEventListener: vi.fn(),
    speaking: false,
    pending: false,
  };
  Object.defineProperty(window, "speechSynthesis", { configurable: true, value: synth });
  vi.stubGlobal("SpeechSynthesisUtterance", FakeSpeechSynthesisUtterance);
}

describe("playWordAudio", () => {
  beforeEach(installSpeech);
  afterEach(() => {
    vi.unstubAllGlobals();
    Reflect.deleteProperty(window, "speechSynthesis");
  });

  it("同步调用 speak（iOS 只在用户手势调用栈内允许发声）", () => {
    let calledAfterReturn = false;
    playWordAudio("accommodation");
    calledAfterReturn = true;

    // 返回前已经发声：若改成先请求音频再异步回退，这里会失败
    expect(spoken.map((u) => u.text)).toEqual(["accommodation"]);
    expect(calledAfterReturn).toBe(true);
  });

  it("完全不走静态音频请求（/media/audio 从未托管，iPad 上会先失败）", () => {
    const audioSpy = vi.fn();
    vi.stubGlobal("Audio", audioSpy);

    playWordAudio("accommodation");

    expect(audioSpy).not.toHaveBeenCalled();
    expect(spoken).toHaveLength(1);
  });

  it("中文混排只读英文部分", () => {
    playWordAudio("apple 苹果");
    expect(spoken[0].text).toBe("apple");
  });

  it("空单词不发声，也不报错", () => {
    playWordAudio("   ");
    expect(spoken).toHaveLength(0);
  });
});

describe("say / stopSpeaking", () => {
  beforeEach(installSpeech);
  afterEach(() => {
    vi.unstubAllGlobals();
    Reflect.deleteProperty(window, "speechSynthesis");
  });

  it("空闲时直接发声，不先 cancel（规避 iOS 吞掉语音）", () => {
    say("hello");
    expect(cancel).not.toHaveBeenCalled();
    expect(spoken[0]).toMatchObject({ text: "hello", lang: "en-GB" });
  });

  it("上一次还没读完时先取消再读新内容", () => {
    (window.speechSynthesis as unknown as { speaking: boolean }).speaking = true;
    say("world");
    expect(cancel).toHaveBeenCalled();
    expect(spoken.map((u) => u.text)).toEqual(["world"]);
  });

  it("没有 speechSynthesis 时静默返回", () => {
    Reflect.deleteProperty(window, "speechSynthesis");
    expect(() => say("hello")).not.toThrow();
    expect(() => stopSpeaking()).not.toThrow();
  });
});

describe("englishOnly / splitExample", () => {
  it("englishOnly 截断到第一个汉字", () => {
    expect(englishOnly("Good morning 早上好")).toBe("Good morning");
    expect(englishOnly("plain english")).toBe("plain english");
  });

  it("splitExample 兼容混排与独立中文", () => {
    expect(splitExample("I have a pet, 我有一只宠物")).toEqual({
      en: "I have a pet",
      cn: "我有一只宠物",
    });
    expect(splitExample("I have a pet", "我有一只宠物")).toEqual({
      en: "I have a pet",
      cn: "我有一只宠物",
    });
  });
});
