/** 统一 API 客户端：业务组件禁止裸 fetch。 */

const BASE = "/api/v1";

interface ApiError extends Error {
  status?: number;
  /** 409 冲突等场景下服务端返回的 detail（可能是对象，如 {rev, data}） */
  detail?: unknown;
}

let accessToken: string | null = localStorage.getItem("pet_access") ?? "";

export function setToken(token: string | null): void {
  accessToken = token;
  if (token) localStorage.setItem("pet_access", token);
  else localStorage.removeItem("pet_access");
}

export function getToken(): string | null {
  return accessToken;
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
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
    const err = new Error(message) as ApiError;
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return (await res.json()) as T;
}
