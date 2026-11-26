import { beforeEach, describe, expect, it } from "vitest";
import { cachedTtsConfig, setTtsConfig, TTS_OFF, ttsUrl } from "./ttsConfig";

beforeEach(() => setTtsConfig(null));

describe("ttsConfig", () => {
  it("默认未加载时视为关闭", () => {
    expect(cachedTtsConfig()).toBeNull();
  });

  it("保存后按配置生成确定性 URL", () => {
    setTtsConfig({ ...TTS_OFF, enabled: true, cache_version: "v2" });
    expect(cachedTtsConfig()?.enabled).toBe(true);
    expect(ttsUrl("hello world")).toBe(
      "/api/v1/speak/tts/local?text=hello+world&v=v2",
    );
  });

  it("缺字段的旧缓存会补默认值", () => {
    setTtsConfig({ enabled: true } as never);
    expect(cachedTtsConfig()).toMatchObject({
      enabled: true,
      voice: "en_GB-alan-medium",
      path: "/api/v1/speak/tts/local",
    });
  });
});
