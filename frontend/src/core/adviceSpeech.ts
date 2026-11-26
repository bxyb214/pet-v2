/** SOE 改进建议朗读（中文）：本地 Piper 中文音色优先，浏览器 zh-CN 兜底。
 *
 * 建议文本由 `core/soe.ts` 的 `soeTips()` 生成，全部是中文（夹英文单词），
 * 不能走 `say()`/`playTts()`（那两个会截到第一个汉字）。
 */
import { ref } from "vue";
import { api } from "./api";
import { beginAudioPending, playAudioUrl, stopSpeaking, unlockAudio } from "./say";
import { loadTtsConfig } from "./ttsConfig";

type TtsOut = { url: string };

let seq = 0;
let zhVoice: SpeechSynthesisVoice | null = null;
let busyTimer: ReturnType<typeof setTimeout> | null = null;

/** 建议是否正在朗读；页面用它切换「朗读建议 / 停止朗读」。 */
export const adviceBusy = ref(false);

function setBusy(on: boolean): void {
  adviceBusy.value = on;
  if (busyTimer) {
    clearTimeout(busyTimer);
    busyTimer = null;
  }
  if (on) {
    // 自动播放被拦截/浏览器不派发 end 事件时，避免按钮一直停在「停止」
    busyTimer = setTimeout(() => {
      adviceBusy.value = false;
      busyTimer = null;
    }, 30000);
  }
}

function supported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

function pickZhVoice(): SpeechSynthesisVoice | null {
  if (zhVoice) return zhVoice;
  const list = window.speechSynthesis?.getVoices?.() ?? [];
  zhVoice =
    list.find((v) => /^zh[-_]CN/i.test(v.lang)) ??
    list.find((v) => /^zh/i.test(v.lang)) ??
    null;
  return zhVoice;
}

if (typeof window !== "undefined" && window.speechSynthesis) {
  window.speechSynthesis.addEventListener?.("voiceschanged", () => {
    zhVoice = null;
    pickZhVoice();
  });
}

/** 多条建议合成一段：句号连接、去掉重复结尾。 */
export function adviceText(tips: string[]): string {
  const parts = tips.map((t) => (t || "").trim()).filter(Boolean);
  if (!parts.length) return "";
  return parts.join("。").replace(/。+$/, "") + "。";
}

/** 浏览器中文朗读；没有中文音色时静默失败。`onDone` 在读完/出错时回调。 */
export function browserSayZh(text: string, onDone?: () => void): void {
  if (!supported() || !text) return;
  try {
    const synth = window.speechSynthesis;
    if (synth.speaking || synth.pending) synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = "zh-CN";
    u.rate = 1;
    u.pitch = 1;
    const v = pickZhVoice();
    if (v) u.voice = v;
    const finish = (): void => onDone?.();
    u.onend = finish;
    u.onerror = finish;
    synth.speak(u);
  } catch {
    /* 静默失败，不打断学习 */
  }
}

/** 停止当前建议/示范朗读。 */
export function stopAdvice(): void {
  seq += 1;
  setBusy(false);
  stopSpeaking();
}

/**
 * 读一遍改进建议：本地中文 TTS → 浏览器 zh-CN 兜底。
 * `fallback: false` 时只用本地 TTS（造句页 AI 反馈要求，失败就不出声）。
 * `onDone` 在正常读完时回调；被停止/被新朗读取代时不回调。
 * 每次评分调用一次；再次调用会取消上一段。
 */
export async function readAdvice(
  tips: string[],
  opts: { fallback?: boolean; onDone?: () => void } = {},
): Promise<void> {
  const text = adviceText(tips);
  if (!text) return;
  const fallback = opts.fallback !== false;
  const my = ++seq;
  setBusy(true);
  stopSpeaking();
  unlockAudio();
  const done = beginAudioPending(text);
  const end = (): void => {
    if (my !== seq) return;
    setBusy(false);
    opts.onDone?.();
  };
  try {
    try {
      const cfg = await loadTtsConfig();
      if (my !== seq) return;
      if (cfg.enabled && text.length <= cfg.max_chars) {
        const out = await api<TtsOut>("/speak/tts/local", {
          method: "POST",
          body: JSON.stringify({ text }),
        });
        if (my !== seq) return;
        if (await playAudioUrl(out.url, "", end)) return;
      }
    } catch {
      /* 本地未启用/失败：按需走浏览器中文兜底 */
    }
    if (my !== seq) return;
    if (!fallback) {
      end();
      return;
    }
    browserSayZh(text, end);
  } finally {
    done();
  }
}
