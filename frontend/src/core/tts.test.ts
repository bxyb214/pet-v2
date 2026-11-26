import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", () => ({ api: vi.fn() }));

import { api } from "./api";
import { audioPending } from "./say";
import { playShadowDemo, playTts } from "./tts";
import { setTtsConfig, TTS_OFF } from "./ttsConfig";

const mockedApi = vi.mocked(api);

function installSpeech(): string[] {
  const spoken: string[] = [];
  const synth = {
    speak: vi.fn((u: { text: string }) => spoken.push(u.text)),
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
  return spoken;
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

beforeEach(() => {
  setTtsConfig(null);
  mockedApi.mockReset();
});

afterEach(() => {
  setTtsConfig(null);
  vi.unstubAllGlobals();
  Reflect.deleteProperty(window, "speechSynthesis");
});

describe("playTts", () => {
  it("本地启用时走 POST 合成并播放返回 URL", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    const urls = installAudio();
    mockedApi.mockResolvedValueOnce({
      url: "/api/v1/speak/tts/file/abc.wav",
      mime: "audio/wav",
      cached: false,
      chars: 5,
    } as never);

    const source = await playTts("hello");

    expect(source).toBe("local");
    expect(urls).toEqual(["/api/v1/speak/tts/file/abc.wav"]);
    expect(mockedApi).toHaveBeenCalledWith(
      "/speak/tts/local",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("本地未启用时回退浏览器朗读", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: false });
    const spoken = installSpeech();

    const source = await playTts("hello");

    expect(source).toBe("browser");
    expect(spoken).toEqual(["hello"]);
    expect(mockedApi).not.toHaveBeenCalled();
  });

  it("合成等待超过 300ms 时 audioPending 为 true，播放后清除", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    installAudio();
    let resolveApi!: (v: unknown) => void;
    mockedApi.mockReturnValueOnce(new Promise((resolve) => { resolveApi = resolve; }) as never);

    const pending = playTts("hello");
    await new Promise((resolve) => setTimeout(resolve, 340));
    expect(audioPending("hello")).toBe(true);

    resolveApi({ url: "/api/v1/speak/tts/file/abc.wav" });
    await pending;
    expect(audioPending("hello")).toBe(false);
  });
});

describe("playShadowDemo", () => {
  it("优先调 Qwen 示范接口并播放缓存 URL", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    const urls = installAudio();
    mockedApi.mockResolvedValueOnce({
      url: "/api/v1/speak/tts/file/demo.wav",
      mime: "audio/wav",
      cached: true,
      chars: 18,
      provider: "qwen",
    } as never);

    const source = await playShadowDemo("I went to the park.");

    expect(source).toBe("qwen");
    expect(urls).toEqual(["/api/v1/speak/tts/file/demo.wav"]);
    expect(mockedApi).toHaveBeenCalledTimes(1);
    expect(mockedApi).toHaveBeenCalledWith(
      "/speak/tts/demo",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("Qwen 失败时回退本地 TTS", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: true });
    installAudio();
    mockedApi
      .mockRejectedValueOnce(new Error("403"))
      .mockResolvedValueOnce({
        url: "/api/v1/speak/tts/file/local.wav",
        mime: "audio/wav",
        cached: false,
        chars: 18,
      } as never);

    const source = await playShadowDemo("I went to the park.");

    expect(source).toBe("local");
    expect(mockedApi).toHaveBeenLastCalledWith(
      "/speak/tts/local",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("Qwen 与本地都不可用时回退浏览器", async () => {
    setTtsConfig({ ...TTS_OFF, enabled: false });
    const spoken = installSpeech();
    mockedApi.mockRejectedValueOnce(new Error("503"));

    const source = await playShadowDemo("hello");

    expect(source).toBe("browser");
    expect(spoken).toEqual(["hello"]);
  });
});
