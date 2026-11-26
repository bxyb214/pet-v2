/** 本地 TTS 配置：启动时从后端拉取，localStorage 缓存 10 分钟。 */
import { api } from "./api";

export type TtsConfig = {
  enabled: boolean;
  engine: string;
  voice: string;
  /** 中英音色；后端按文本是否含汉字自动选择 */
  voices?: { en: string; zh: string };
  speed: number;
  cache_version: string;
  max_chars: number;
  path: string;
};

export const TTS_OFF: TtsConfig = {
  enabled: false,
  engine: "piper",
  voice: "en_GB-alan-medium",
  voices: { en: "en_GB-alan-medium", zh: "zh_CN-huayan-medium" },
  speed: 0.95,
  cache_version: "piper1",
  max_chars: 300,
  path: "/api/v1/speak/tts/local",
};

const KEY = "pet_tts_cfg_v1";
const TTL = 10 * 60 * 1000;

type Stored = { cfg: TtsConfig; at: number };

function readStored(): Stored | null {
  try {
    if (typeof localStorage === "undefined") return null;
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const d = JSON.parse(raw) as Partial<Stored> | null;
    if (!d || !d.cfg || typeof d.at !== "number") return null;
    return { cfg: { ...TTS_OFF, ...d.cfg }, at: d.at };
  } catch {
    return null;
  }
}

const initial = readStored();
let cache: TtsConfig | null = initial?.cfg ?? null;
let cacheAt = initial?.at ?? 0;

export function cachedTtsConfig(): TtsConfig | null {
  return cache;
}

export function localTtsEnabled(): boolean {
  return !!cache?.enabled;
}

/** 测试或登出时覆盖缓存（传 null 恢复未加载状态）。 */
export function setTtsConfig(cfg: TtsConfig | null): void {
  cache = cfg ? { ...TTS_OFF, ...cfg } : null;
  cacheAt = cfg ? Date.now() : 0;
  try {
    if (typeof localStorage === "undefined") return;
    if (cache) localStorage.setItem(KEY, JSON.stringify({ cfg: cache, at: cacheAt }));
    else localStorage.removeItem(KEY);
  } catch {
    /* 隐私模式 / 配额不足：只影响下次首屏，不影响本次 */
  }
}

export async function loadTtsConfig(force = false): Promise<TtsConfig> {
  if (cache && !force && Date.now() - cacheAt < TTL) return cache;
  try {
    const cfg = await api<TtsConfig>("/speak/tts/config");
    setTtsConfig(cfg);
    return cache ?? { ...TTS_OFF, ...cfg };
  } catch {
    return cache ?? TTS_OFF;
  }
}

/** 确定性 GET URL：同一文本/版本永远同一地址，浏览器可长期缓存，iOS 可同步起播。 */
export function ttsUrl(text: string, cfg: TtsConfig | null = cache): string {
  const c = cfg ?? TTS_OFF;
  const q = new URLSearchParams({ text, v: c.cache_version });
  return `${c.path}?${q.toString()}`;
}
