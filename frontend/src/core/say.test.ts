import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({ api: vi.fn() }));

import { api } from "./api";
import {
  audioPending, beginAudioPending, englishOnly, playWordAudio, say, splitExample, stopSpeaking,
} from "./say";
import { setTtsConfig, TTS_OFF } from "./ttsConfig";

const mockedApi = vi.mocked(api);

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

function installAudio(reject: boolean | ((url: string) => boolean) = false): string[] {
  const urls: string[] = [];
  class FakeAudio {
    onended: (() => void) | null = null;
    onerror: (() => void) | null = null;
    preload = "";
    private _src = "";
    constructor(url?: string) {
      if (url) this.src = url;
    }
    get src(): string {
      return this._src;
    }
    set src(v: string) {
      this._src = v;
      if (v && !v.startsWith("data:")) urls.push(v);
    }
    play(): Promise<void> {
      const fail = typeof reject === "function" ? reject(this._src) : reject;
      return fail ? Promise.reject(new Error("no audio")) : Promise.resolve();
    }
    pause(): void { /* noop */ }
    setAttribute(): void { /* noop */ }
    removeAttribute(): void { this._src = ""; }
    load(): void { /* noop */ }
  }
  vi.stubGlobal("Audio", FakeAudio);
  return urls;
}

beforeEach(() => {
  setTtsConfig(null);
  installSpeech();
  mockedApi.mockReset();
  mockedApi.mockRejectedValue(new Error("offline"));
});

afterEach(() => {
  setTtsConfig(null);
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  Reflect.deleteProperty(window, "speechSynthesis");
});

describe("playWordAudio", () => {
  it("同步调用 speak（iOS 只在用户手势调用栈内允许发声）", () => {
    let calledAfterReturn = false;
    playWordAudio("accommodation");
    calledAfterReturn = true;

    // 返回前已经发声：若改成先请求音频再异步回退，这里会失败
    expect(spoken.map((u) => u.text)).toEqual(["accommodation"]);
    expect(calledAfterReturn).toBe(true);
  });

  it("本地 TTS 未启用时不请求静态音频", () => {
    const audioSpy = vi.fn();
    vi.stubGlobal("Audio", audioSpy);

    playWordAudio("accommodation");

    expect(audioSpy).not.toHaveBeenCalled();
    expect(spoken).toHaveLength(1);
  });

  it("本地 TTS 启用时同步播放确定性 URL，不调浏览器朗读", () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    const urls = installAudio();

    playWordAudio("hello");

    expect(urls).toEqual(["/api/v1/speak/tts/local?text=hello&v=piper1"]);
    expect(spoken).toHaveLength(0);
  });

  it("本地播放失败时回退浏览器朗读", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    installAudio(true);

    playWordAudio("hello");

    await vi.waitFor(() => {
      expect(spoken.map((u) => u.text)).toEqual(["hello"]);
    });
  });

  it("iOS 缓存未命中时先合成再补播，不依赖 404 的 error 事件", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    vi.spyOn(window.navigator, "userAgent", "get").mockReturnValue(
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
    );
    vi.spyOn(window.navigator, "platform", "get").mockReturnValue("iPhone");
    const urls = installAudio((url) => !url.includes("/file/abc.wav"));
    mockedApi.mockResolvedValueOnce({
      url: "/api/v1/speak/tts/file/abc.wav",
    } as never);

    playWordAudio("hello");

    await vi.waitFor(() => {
      expect(urls).toContain("/api/v1/speak/tts/file/abc.wav");
    });
    expect(spoken).toHaveLength(0);
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

describe("audioPending", () => {
  it("等待超过 300ms 才显示转圈，结束后立即消失", async () => {
    const done = beginAudioPending("Hello!");
    expect(audioPending("hello")).toBe(false);
    await new Promise((resolve) => setTimeout(resolve, 340));
    expect(audioPending("  HELLO!  ")).toBe(true);
    done();
    expect(audioPending("hello")).toBe(false);
  });

  it("快速命中缓存时不闪转圈", async () => {
    const done = beginAudioPending("hello");
    done();
    await new Promise((resolve) => setTimeout(resolve, 340));
    expect(audioPending("hello")).toBe(false);
  });

  it("不同文本互不影响", async () => {
    const done = beginAudioPending("hello");
    await new Promise((resolve) => setTimeout(resolve, 340));
    expect(audioPending("hello")).toBe(true);
    expect(audioPending("world")).toBe(false);
    done();
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
