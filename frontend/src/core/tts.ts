/** 句子示范朗读：默认本地 TTS；跟读示范单独走 Qwen（`playShadowDemo`）。 */
import { api } from "./api";
import { englishOnly, beginAudioPending, playAudioUrl, say, stopSpeaking, unlockAudio } from "./say";
import { loadTtsConfig } from "./ttsConfig";

type TtsOut = {
  url: string;
  mime: string;
  cached: boolean;
  chars: number;
  provider?: string;
  ms?: number;
};

export type DemoEngine = "qwen" | "local" | "browser";

/**
 * 先停掉当前朗读，再按「本地 POST 合成 → 浏览器」顺序播放。
 * 本地未启用、超长或失败时都回退浏览器，不再产生云端 TTS 费用。
 */
export async function playTts(text: string): Promise<"local" | "browser"> {
  const clean = englishOnly(text);
  if (!clean) return "browser";
  stopSpeaking();
  unlockAudio();

  const cfg = await loadTtsConfig();
  if (cfg.enabled && clean.length <= cfg.max_chars) {
    const done = beginAudioPending(clean);
    try {
      const out = await api<TtsOut>("/speak/tts/local", {
        method: "POST",
        body: JSON.stringify({ text: clean }),
      });
      if (await playAudioUrl(out.url, "")) return "local";
    } catch {
      /* 继续走浏览器兜底 */
    } finally {
      done();
    }
  }
  say(clean);
  return "browser";
}

/**
 * 跟读「听示范」：Qwen 合成 + 缓存（免费、不记用量）。
 * 失败时按本地 Piper → 浏览器回退，保证未配置 Key 也能听。
 */
export async function playShadowDemo(text: string): Promise<DemoEngine> {
  const clean = englishOnly(text);
  if (!clean) return "browser";
  stopSpeaking();
  unlockAudio();
  const done = beginAudioPending(clean);
  try {
    if (clean.length <= 300) {
      try {
        const out = await api<TtsOut>("/speak/tts/demo", {
          method: "POST",
          body: JSON.stringify({ text: clean }),
        });
        if (await playAudioUrl(out.url, "")) return "qwen";
      } catch {
        /* 未配 Key / 网络失败：继续本地回退 */
      }
    }
    return await playTts(clean);
  } finally {
    done();
  }
}
