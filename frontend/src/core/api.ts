/** 统一 API 客户端：业务组件禁止裸 fetch。 */

const BASE = "/api/v1";

interface ApiError extends Error {
  status?: number;
  /** 409 冲突等场景下服务端返回的 detail（可能是对象，如 {rev, data}） */
  detail?: unknown;
}

let accessToken: string | null = localStorage.getItem("pet_access") ?? "";
let unauthorizedHandler: (() => void) | null = null;
let unauthorizedFired = false;

export function setToken(token: string | null): void {
  accessToken = token;
  if (token) localStorage.setItem("pet_access", token);
  else localStorage.removeItem("pet_access");
}

export function getToken(): string | null {
  // 多标签页 / 手动清除 localStorage 时，内存值可能过期，守卫以存储为准
  const stored = localStorage.getItem("pet_access");
  if (stored !== accessToken) accessToken = stored;
  return accessToken;
}

/** 由 main.ts 注册：任一接口 401 时清会话并回登录页。 */
export function setUnauthorizedHandler(fn: (() => void) | null): void {
  unauthorizedHandler = fn;
}

/** 仅测试用：重置 401 去重锁。 */
export function resetUnauthorizedForTest(): void {
  unauthorizedFired = false;
}

function fireUnauthorized(): void {
  if (unauthorizedFired) return;
  unauthorizedFired = true;
  setToken(null);
  unauthorizedHandler?.();
  window.setTimeout(() => {
    unauthorizedFired = false;
  }, 0);
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(BASE + path, { ...options, headers });
  if (!res.ok) {
    let detail: unknown;
    let message = `请求失败 (${res.status})`;
    try {
      const body = await res.json();
      detail = body?.detail;
      if (typeof body?.detail === "string") message = body.detail;
      // 额度/开通类错误：detail 为对象（{code, message}）
      else if (detail && typeof (detail as { message?: unknown }).message === "string") {
        message = (detail as { message: string }).message;
      }
    } catch {
      /* 保留默认消息 */
    }
    // 登录/刷新失败由表单自己提示；其余 401 一律视为会话失效
    if (res.status === 401 && path !== "/auth/login" && path !== "/auth/refresh") {
      fireUnauthorized();
    }
    const err = new Error(message) as ApiError;
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return (await res.json()) as T;
}

/**
 * 带鉴权下载文件（如 AI 用量 CSV）：后端返回附件时使用。
 */
export async function downloadFile(path: string, filename: string): Promise<void> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(BASE + path, { headers });
  if (!res.ok) throw new Error(`下载失败 (${res.status})`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export type ProbeResult = {
  status: number;
  ok: boolean;
  contentType: string;
  contentLength: number;
  contentRange: string;
  body: string;
};

/**
 * 调试用：探测多媒体 URL 的响应头（如本地 TTS 的 wav）。
 * 用 Range 只取前 2 字节，避免把整段音频读进内存；404 时带回响应体方便看错误。
 */
export async function probeFile(url: string, timeoutMs = 15000): Promise<ProbeResult> {
  const ctl = new AbortController();
  const timer = window.setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const res = await fetch(url, { headers: { Range: "bytes=0-1" }, signal: ctl.signal });
    let body = "";
    if (!res.ok) {
      try {
        body = (await res.text()).slice(0, 200);
      } catch {
        /* 不是文本：忽略 */
      }
    }
    return {
      status: res.status,
      ok: res.ok,
      contentType: res.headers.get("Content-Type") ?? "",
      contentLength: Number(res.headers.get("Content-Length") ?? 0),
      contentRange: res.headers.get("Content-Range") ?? "",
      body,
    };
  } finally {
    window.clearTimeout(timer);
  }
}

/**
 * 页面关闭/切走时的补报：keepalive fetch（可带 Authorization），
 * sendBeacon 无法设置鉴权头，因此不用它。仍统一走 api.ts，组件不裸 fetch。
 */
export function apiBeacon(path: string, body: unknown): void {
  try {
    const headers = new Headers({ "Content-Type": "application/json" });
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    void fetch(BASE + path, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      keepalive: true,
    }).catch(() => undefined);
  } catch {
    /* 页面正在关闭，忽略 */
  }
}
