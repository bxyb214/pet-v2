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
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = "en-GB";
    u.rate = rate;
    u.pitch = 1;
    const v = pickVoice();
    if (v) u.voice = v;
    window.speechSynthesis.speak(u);
  } catch {
    /* 静默失败，不打断学习 */
  }
}

export function stopSpeaking(): void {
  if (ttsSupported()) window.speechSynthesis.cancel();
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
