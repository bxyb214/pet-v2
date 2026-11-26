/** 单词/例句朗读：本地 TTS 优先，浏览器 speechSynthesis 兜底。 */
import { ref } from "vue";
import { api } from "./api";
import { cachedTtsConfig, loadTtsConfig, ttsUrl } from "./ttsConfig";

let cached: SpeechSynthesisVoice | null = null;

function pickVoice(): SpeechSynthesisVoice | null {
  if (cached) return cached;
  const list = window.speechSynthesis?.getVoices?.() ?? [];
  cached =
    list.find((v) => /en[-_]GB/i.test(v.lang)) ??
    list.find((v) => /^en/i.test(v.lang)) ??
    null;
  return cached;
}

if (typeof window !== "undefined" && window.speechSynthesis) {
  // 语音列表异步加载，加载完刷新缓存
  window.speechSynthesis.addEventListener?.("voiceschanged", () => {
    cached = null;
    pickVoice();
  });
}

export function ttsSupported(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/** 浏览器朗读；本地 TTS 失败时的兜底，不对外导出。 */
function browserSay(clean: string, rate: number): void {
  if (!ttsSupported()) return;
  try {
    const synth = window.speechSynthesis;
    // iOS Safari 上「cancel() 后立即 speak()」偶发被吞；空闲时不要多调一次 cancel
    if (synth.speaking || synth.pending) synth.cancel();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = "en-GB";
    u.rate = rate;
    u.pitch = 1;
    const v = pickVoice();
    if (v) u.voice = v;
    synth.speak(u);
  } catch {
    /* 静默失败，不打断学习 */
  }
}

/** 服务端 TTS 回放：同一时间只保留一条，避免连点叠音 */
let currentAudio: HTMLAudioElement | null = null;

/** 0.05s 静音 WAV：iOS Safari 只在手势栈内允许起播，用它解锁共享 audio 元素。 */
const SILENT_WAV =
  "data:audio/wav;base64,UklGRmQGAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YUAGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";

let sharedAudio: HTMLAudioElement | null = null;
let audioUnlocked = false;

/** 全站共用一个 audio 元素：iOS 的解锁状态是按元素记的。 */
function audioEl(): HTMLAudioElement | null {
  if (typeof Audio === "undefined") return null;
  if (sharedAudio && !(sharedAudio instanceof Audio)) {
    sharedAudio = null;
    audioUnlocked = false;
  }
  if (!sharedAudio) {
    sharedAudio = new Audio();
    sharedAudio.preload = "auto";
    sharedAudio.setAttribute("playsinline", "");
    sharedAudio.setAttribute("webkit-playsinline", "");
    // 部分 iOS 版本要求音频元素挂在 DOM 里才稳定解锁；测试里的假 Audio 不是节点，跳过。
    try {
      if (sharedAudio.nodeType === 1 && document.body && !sharedAudio.isConnected) {
        sharedAudio.style.display = "none";
        document.body.appendChild(sharedAudio);
      }
    } catch {
      /* 非浏览器节点：忽略 */
    }
  }
  return sharedAudio;
}

/**
 * iOS Safari 的自动播放限制：在触摸/按键回调里先播一小段静音，
 * 之后 `await` 后端合成再 `play()` 才不会被 NotAllowedError 拦截。
 */
export function unlockAudio(): void {
  if (audioUnlocked) return;
  const el = audioEl();
  if (!el) return;
  try {
    el.src = SILENT_WAV;
    const p = el.play();
    audioUnlocked = true;
    if (p && typeof p.catch === "function") {
      p.catch((e: unknown) => {
        // 仅“未被手势允许”时重置；AbortError 是随后真正播放把静音顶掉，不算失败。
        if ((e as DOMException | undefined)?.name === "NotAllowedError") audioUnlocked = false;
      });
    }
  } catch {
    audioUnlocked = false;
  }
}

if (typeof window !== "undefined") {
  window.addEventListener("pointerdown", unlockAudio, { capture: true, passive: true });
  window.addEventListener("touchstart", unlockAudio, { capture: true, passive: true });
  window.addEventListener("keydown", unlockAudio, { capture: true });
}

export function stopAudioUrl(): void {
  const el = currentAudio;
  currentAudio = null;
  if (el) {
    try { el.pause(); } catch { /* noop */ }
    el.onended = null;
    el.onerror = null;
  }
}

/**
 * 手势内同步起播确定性 GET URL；返回 play() 是否成功。
 * iOS 对 404 音频有时不触发 error，因此带超时，失败后由调用方合成并补播。
 */
function playAudioSync(url: string, timeoutMs = 1500): Promise<boolean> {
  const el = audioEl();
  if (!url || !el) return Promise.resolve(false);
  stopAudioUrl();
  el.src = url;
  currentAudio = el;
  return new Promise<boolean>((resolve) => {
    let done = false;
    const finish = (ok: boolean): void => {
      if (done) return;
      done = true;
      window.clearTimeout(timer);
      if (!ok) {
        try { el.pause(); } catch { /* noop */ }
        if (currentAudio === el) currentAudio = null;
      }
      resolve(ok);
    };
    const timer = window.setTimeout(() => finish(false), timeoutMs);
    el.onended = () => { if (currentAudio === el) currentAudio = null; };
    el.onerror = () => finish(false);
    try {
      const p = el.play();
      if (p && typeof p.then === "function") p.then(() => finish(true)).catch(() => finish(false));
      else finish(true);
    } catch {
      finish(false);
    }
  });
}

/** 最近一次本地朗读尝试：iOS 调试面板用。 */
export type LocalAttempt = {
  text: string;
  url: string;
  status: "playing" | "miss" | "error" | "fallback";
  error?: string;
  at: number;
};

let lastAttempt: LocalAttempt | null = null;
let saySeq = 0;

export function lastLocalAttempt(): LocalAttempt | null {
  return lastAttempt;
}

function recordAttempt(a: Omit<LocalAttempt, "at">): void {
  lastAttempt = { ...a, at: Date.now() };
}

/*
 * 合成等待状态：未命中缓存时播放按钮显示转圈。
 * 计数支持「Qwen 失败 → 本地合成」这类嵌套；延迟 300ms 才对外可见，
 * 避免缓存命中时闪一下。
 */
const pendingCounts = ref<Record<string, number>>({});
const pendingVisible = ref<Record<string, boolean>>({});
const pendingTimers = new Map<string, ReturnType<typeof setTimeout>>();

function audioKey(text: string): string {
  const raw = String(text ?? "");
  return (englishOnly(raw) || raw).trim().toLowerCase();
}

/** 组件用：该文本当前是否在等合成。 */
export function audioPending(text: string): boolean {
  const key = audioKey(text);
  return !!key && !!pendingVisible.value[key];
}

/** 开始一次可能等待的播放；返回值必须在结束（成功/失败/回退）时调用。 */
export function beginAudioPending(text: string): () => void {
  const key = audioKey(text);
  if (!key) return () => { /* 空文本无需等待 */ };
  pendingCounts.value = { ...pendingCounts.value, [key]: (pendingCounts.value[key] ?? 0) + 1 };
  if (!pendingTimers.has(key)) {
    pendingTimers.set(key, setTimeout(() => {
      pendingTimers.delete(key);
      if ((pendingCounts.value[key] ?? 0) > 0) {
        pendingVisible.value = { ...pendingVisible.value, [key]: true };
      }
    }, 300));
  }
  let ended = false;
  return () => {
    if (ended) return;
    ended = true;
    const next = { ...pendingCounts.value };
    const n = (next[key] ?? 1) - 1;
    if (n > 0) {
      next[key] = n;
    } else {
      delete next[key];
      const timer = pendingTimers.get(key);
      if (timer) {
        clearTimeout(timer);
        pendingTimers.delete(key);
      }
      if (pendingVisible.value[key]) {
        const vis = { ...pendingVisible.value };
        delete vis[key];
        pendingVisible.value = vis;
      }
    }
    pendingCounts.value = next;
  };
}

/** 本地 TTS 最多等 5s：期间播放按钮转圈，超时后回退浏览器发声。 */
export const LOCAL_TTS_WAIT_MS = 5000;

/**
 * 给等待加超时：超时或失败都返回 undefined。
 * 原 Promise 不取消——服务端合成会继续并写入缓存，下次点击直接命中。
 */
export function raceTimeout<T>(p: Promise<T>, ms: number): Promise<T | undefined> {
  return new Promise<T | undefined>((resolve) => {
    let done = false;
    const timer = window.setTimeout(() => {
      if (done) return;
      done = true;
      resolve(undefined);
    }, ms);
    p.then(
      (v) => {
        if (done) return;
        done = true;
        window.clearTimeout(timer);
        resolve(v);
      },
      () => {
        if (done) return;
        done = true;
        window.clearTimeout(timer);
        resolve(undefined);
      },
    );
  });
}

/**
 * 本地优先：手势内先同步播缓存 URL；未命中再 POST 合成并补播。
 * 合成最多等 5s（按钮转圈），超时/失败回退浏览器朗读。
 * iOS 对 404 音频不一定触发 error，缓存播放本身也带超时。
 */
async function playLocal(text: string, cfg: NonNullable<ReturnType<typeof cachedTtsConfig>>, rate: number, my: number): Promise<void> {
  const done = beginAudioPending(text);
  const started = Date.now();
  try {
    const url = ttsUrl(text, cfg);
    const ok = await playAudioSync(url);
    if (my !== saySeq) return;
    if (ok) {
      recordAttempt({ text, url, status: "playing" });
      return;
    }

    recordAttempt({ text, url, status: "miss" });
    const synth = (async (): Promise<boolean> => {
      try {
        const out = await api<{ url: string }>("/speak/tts/local", {
          method: "POST",
          body: JSON.stringify({ text }),
        });
        if (my !== saySeq) return false;
        const played = await playAudioUrl(out.url, "");
        if (played) recordAttempt({ text, url: out.url, status: "playing" });
        else recordAttempt({ text, url: out.url, status: "error", error: "audio play failed" });
        return played;
      } catch (e) {
        recordAttempt({ text, url, status: "error", error: (e as Error).message });
        return false;
      }
    })();
    const remain = Math.max(0, LOCAL_TTS_WAIT_MS - (Date.now() - started));
    const played = await raceTimeout(synth, remain);
    if (my !== saySeq) return;
    if (played) return;

    // 超时/失败：浏览器兜底；作废本次本地尝试，迟到的合成结果不再补播
    saySeq += 1;
    recordAttempt({ text, url, status: "fallback" });
    browserSay(text, rate);
  } finally {
    done();
  }
}

/** 朗读英文；text 里若混入中文会自动截止到第一个汉字 */
export function say(text: string, rate = 0.9): void {
  const clean = englishOnly(text);
  if (!clean) return;
  const my = ++saySeq;
  const cfg = cachedTtsConfig();
  if (cfg?.enabled && clean.length <= cfg.max_chars) {
    unlockAudio();
    void playLocal(clean, cfg, rate, my);
    return;
  }
  if (!cfg) void loadTtsConfig();
  browserSay(clean, rate);
}

export function stopSpeaking(): void {
  saySeq += 1;
  stopAudioUrl();
  if (ttsSupported()) window.speechSynthesis.cancel();
}

/**
 * 直接浏览器朗读：本地 TTS 刚超时/失败时用，避免再等一轮本地合成。
 */
export function sayWithBrowser(text: string, rate = 0.9): void {
  const clean = englishOnly(text);
  if (!clean) return;
  saySeq += 1;
  browserSay(clean, rate);
}

/**
 * 朗读单词：本地 TTS 优先，点击手势内先同步尝试缓存 URL；
 * 未命中时合成后补播，仍失败才回退浏览器朗读。
 */
export function playWordAudio(word: string): void {
  say(word);
}

/**
 * 播放服务端 TTS 返回的 URL；失败时回退浏览器朗读（付费接口/网络失败）。
 * 返回是否由服务端音频播放成功；`onEnd` 在自然播完/出错时回调（手动 stop 不回调）。
 */
export async function playAudioUrl(
  url: string,
  fallbackText = "",
  onEnd?: () => void,
): Promise<boolean> {
  const fallback = (): void => {
    const clean = englishOnly(fallbackText);
    if (clean) browserSay(clean, 0.9);
  };
  const el = audioEl();
  if (!url || !el) {
    fallback();
    return false;
  }
  stopAudioUrl();
  el.src = url;
  currentAudio = el;
  const done = (): void => {
    if (currentAudio === el) currentAudio = null;
    onEnd?.();
  };
  el.onended = done;
  el.onerror = done;
  try {
    await el.play();
    audioUnlocked = true;
    return true;
  } catch {
    if (currentAudio === el) currentAudio = null;
    fallback();
    return false;
  }
}

/** 只保留英文部分（词库数据里 example 常把中英混在一个字段） */
export function englishOnly(s: string): string {
  const i = s.search(/[一-鿿]/);
  return (i >= 0 ? s.slice(0, i) : s).trim();
}

/** 拆分「英文例句 + 中文翻译」：兼容 example 混排 与 example_cn 独立两种来源 */
export function splitExample(example: string, exampleCn = ""): { en: string; cn: string } {
  if (!example) return { en: "", cn: exampleCn };
  const i = example.search(/[一-鿿]/);
  if (i < 0) return { en: example.trim(), cn: exampleCn };
  return {
    en: example.slice(0, i).trim().replace(/[,;，；]$/, ""),
    cn: existingCn(example.slice(i).trim()) || exampleCn,
  };
}

function existingCn(s: string): string {
  return s.trim();
}
