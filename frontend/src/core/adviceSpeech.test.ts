import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({ api: vi.fn() }));

import { adviceBusy, adviceText, readAdvice, stopAdvice } from "./adviceSpeech";
import { api } from "./api";
import { setTtsConfig, TTS_OFF } from "./ttsConfig";

const mockedApi = vi.mocked(api);

type FakeUtterance = { text: string; lang: string; rate: number; pitch: number; voice: unknown };

function installSpeech(): { spoken: FakeUtterance[]; synth: Record<string, unknown> } {
  const spoken: FakeUtterance[] = [];
  const synth = {
    speak: vi.fn((u: FakeUtterance) => spoken.push(u)),
    cancel: vi.fn(),
    getVoices: () => [],
    addEventListener: vi.fn(),
    speaking: false,
    pending: false,
  };
  Object.defineProperty(window, "speechSynthesis", { configurable: true, value: synth });
  vi.stubGlobal(
    "SpeechSynthesisUtterance",
    class {
      text: string;
      lang = "";
      rate = 1;
      pitch = 1;
      voice: unknown = null;
      constructor(text: string) {
        this.text = text;
      }
    },
  );
  return { spoken, synth };
}

function installAudio(): string[] {
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
      return Promise.resolve();
    }
    pause(): void { /* noop */ }
    setAttribute(): void { /* noop */ }
    removeAttribute(): void { this._src = ""; }
    load(): void { /* noop */ }
  }
  vi.stubGlobal("Audio", FakeAudio);
  return urls;
}

const TIPS = ["漏读了 really，跟着示范逐词读完整", "重音再清晰一点"];

beforeEach(() => {
  stopAdvice();
  setTtsConfig(null);
  mockedApi.mockReset();
});

afterEach(() => {
  stopAdvice();
  setTtsConfig(null);
  vi.unstubAllGlobals();
  Reflect.deleteProperty(window, "speechSynthesis");
});

describe("adviceText", () => {
  it("用句号连接并补结尾", () => {
    expect(adviceText(TIPS)).toBe("漏读了 really，跟着示范逐词读完整。重音再清晰一点。");
  });

  it("过滤空串且不重复句号", () => {
    expect(adviceText(["  ", "再慢一点。", ""])).toBe("再慢一点。");
    expect(adviceText([])).toBe("");
  });
});

describe("readAdvice", () => {
  it("本地启用时 POST 中文原文并播放返回 URL", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    const urls = installAudio();
    installSpeech();
    mockedApi.mockResolvedValueOnce({ url: "/api/v1/speak/tts/file/zh.wav" } as never);

    await readAdvice(TIPS);

    expect(urls).toEqual(["/api/v1/speak/tts/file/zh.wav"]);
    const [path, init] = mockedApi.mock.calls[0];
    expect(path).toBe("/speak/tts/local");
    const body = JSON.parse(String((init as RequestInit).body)) as { text: string };
    // 中文原文不被 englishOnly 截断
    expect(body.text).toBe(adviceText(TIPS));
  });

  it("本地未启用时用浏览器中文朗读", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: false });
    const { spoken } = installSpeech();

    await readAdvice(TIPS);

    expect(mockedApi).not.toHaveBeenCalled();
    expect(spoken).toHaveLength(1);
    expect(spoken[0].text).toBe(adviceText(TIPS));
    expect(spoken[0].lang).toBe("zh-CN");
  });

  it("本地接口失败时回退浏览器中文", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    installAudio();
    const { spoken } = installSpeech();
    mockedApi.mockRejectedValueOnce(new Error("503"));

    await readAdvice(TIPS);

    expect(spoken).toHaveLength(1);
    expect(spoken[0].lang).toBe("zh-CN");
  });

  it("没有建议时不发声也不请求", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    const { spoken } = installSpeech();

    await readAdvice(["   "]);

    expect(spoken).toHaveLength(0);
    expect(mockedApi).not.toHaveBeenCalled();
  });

  it("播放期间 adviceBusy 为 true，读完或手动停止后复位", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: false });
    const { spoken } = installSpeech();

    await readAdvice(TIPS);
    expect(adviceBusy.value).toBe(true);
    (spoken[0] as FakeUtterance & { onend?: () => void }).onend?.();
    expect(adviceBusy.value).toBe(false);

    await readAdvice(TIPS);
    expect(adviceBusy.value).toBe(true);
    stopAdvice();
    expect(adviceBusy.value).toBe(false);
  });
});
