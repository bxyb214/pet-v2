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

export type LocalTtsCfg = {
  enabled: boolean;
  engine: string;
  voice: string;
  voice_zh: string;
  speed: number;
  sidecar: string;
  max_chars: number;
  cache_version: string;
  rate_per_min: number;
};

export type CacheStats = { files: number; bytes: number; max_mb: number };

/** 「用户与额度」账号卡的数据：额度单位均为 0.001 元。 */
export type AdminUserRow = {
  id: number;
  username: string;
  display_name: string;
  is_admin: boolean;
  created_at: string | null;
  ai_enabled: boolean;
  unlimited: boolean;
  ai_credit_milli: number | null;
  credit_custom: boolean;
  default_credit_milli: number;
  credit_used_milli: number;
  credit_budget_milli: number;
  remaining_milli: number;
  alert_stage: number;
};
