/**
 * 句子示范朗读：默认本地 TTS；跟读示范与造句 AI 示范句按权限走 Qwen
 * （`playShadowDemo` / `playModelSentence`）。本地合成最多等 5s。
 */
import { api } from "./api";
import {
  beginAudioPending, englishOnly, LOCAL_TTS_WAIT_MS, playAudioUrl, raceTimeout, sayWithBrowser,
  stopSpeaking, unlockAudio,
} from "./say";
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
 * 只走本地 TTS（不回落浏览器）；返回是否已开始播放。
 * 合成最多等 5s（按钮转圈），超时或失败返回 false 由调用方决定后续。
 */
export async function playLocalTts(text: string): Promise<boolean> {
  const clean = englishOnly(text);
  if (!clean) return false;
  stopSpeaking();
  unlockAudio();
  const cfg = await loadTtsConfig();
  if (!cfg.enabled || clean.length > cfg.max_chars) return false;
  const done = beginAudioPending(clean);
  try {
    const out = await raceTimeout(
      api<TtsOut>("/speak/tts/local", {
        method: "POST",
        body: JSON.stringify({ text: clean }),
      }),
      LOCAL_TTS_WAIT_MS,
    );
    if (!out) return false;
    return await playAudioUrl(out.url, "");
  } catch {
    return false;
  } finally {
    done();
  }
}

/**
 * 先停掉当前朗读，再按「本地 POST 合成 → 浏览器」顺序播放。
 * 本地未启用、超长或 5s 内没就绪时都直接回退浏览器，不再产生云端 TTS 费用。
 */
export async function playTts(text: string): Promise<"local" | "browser"> {
  const clean = englishOnly(text);
  if (!clean) return "browser";
  if (await playLocalTts(clean)) return "local";
  sayWithBrowser(clean);
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

/**
 * 造句页 AI 示范句朗读：有 AI 权限优先 Qwen（磁盘缓存、免费不记账），
 * 没有权限只用本地 Piper；两者失败都按已有链路回退（本地 → 浏览器）。
 */
export async function playModelSentence(
  text: string,
  opts: { qwen?: boolean } = {},
): Promise<DemoEngine> {
  return opts.qwen ? playShadowDemo(text) : playTts(text);
}
