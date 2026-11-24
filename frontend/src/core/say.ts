/** 单词/例句朗读：浏览器原生 speechSynthesis（零依赖、零费用，旧站同方案） */
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

/** 朗读英文；text 里若混入中文会自动截止到第一个汉字 */
export function say(text: string, rate = 0.9): void {
  if (!ttsSupported()) return;
  const clean = englishOnly(text);
  if (!clean) return;
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

export function stopSpeaking(): void {
  if (ttsSupported()) window.speechSynthesis.cancel();
}

/**
 * 朗读单词：直接用浏览器内置语音，且必须在点击事件里同步调用。
 *
 * 不再先尝试 `/media/audio/<audio>`：该目录本站从未托管（旧站的 mp3 是「整组音频」，
 * 词库里每个词拿到的都是整组文件名），请求会命中 nginx 的 index.html 回退，
 * 播放失败后再异步调 say()。桌面 Chrome 允许异步朗读，iOS Safari 只允许在
 * 用户手势的同步调用栈里发声——异步回退会被静默丢弃，表现为 iPad 按播放没声音。
 */
export function playWordAudio(word: string): void {
  say(word);
}

/**
 * 播放服务端 TTS 返回的 URL；失败时回退浏览器朗读（免费降级 / 网络失败）。
 * 返回是否由服务端音频播放成功。
 */
export async function playAudioUrl(url: string, fallbackText = ""): Promise<boolean> {
  if (!url || typeof Audio === "undefined") {
    if (fallbackText) say(fallbackText);
    return false;
  }
  try {
    const el = new Audio(url);
    await el.play();
    return true;
  } catch {
    if (fallbackText) say(fallbackText);
    return false;
  }
}

/** 只保留英文部分（词库数据里 example 常把中英混在一个字段） */
export function englishOnly(s: string): string {
  const i = s.search(/[\u4e00-\u9fff]/);
  return (i >= 0 ? s.slice(0, i) : s).trim();
}

/** 拆分「英文例句 + 中文翻译」：兼容 example 混排 与 example_cn 独立两种来源 */
export function splitExample(example: string, exampleCn = ""): { en: string; cn: string } {
  if (!example) return { en: "", cn: exampleCn };
  const i = example.search(/[\u4e00-\u9fff]/);
  if (i < 0) return { en: example.trim(), cn: exampleCn };
  return {
    en: example.slice(0, i).trim().replace(/[,;，；]$/, ""),
    cn: existingCn(example.slice(i).trim()) || exampleCn,
  };
}

function existingCn(s: string): string {
  return s.trim();
}
