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
