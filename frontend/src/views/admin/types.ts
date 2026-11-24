/** 管理后台共用类型。 */

export type TestResult = { ok: boolean; detail: string; dev?: boolean };

export type LlmCfg = { api_key: string; base_url: string; model: string };

export type QwenCfg = {
  base: string;
  workspace: string;
  api_key: string;
  model: string;
  fallback_model: string;
  voice: string;
  shadow_model: string;
  voice_shadow: string;
  vad: string;
  mcp: boolean;
  tts_model: string;
  tts_voice: string;
};

export type SoeCfg = {
  appid: string;
  secret_id: string;
  secret_key: string;
  engine: string;
  coeff: number;
};

export type CacheStats = { files: number; bytes: number; max_mb: number };
