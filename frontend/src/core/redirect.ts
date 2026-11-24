/**
 * 登录 / 注册成功后的回跳地址：只接受站内绝对路径。
 * - 必须以单个 "/" 开头，拒绝 "//host"、"https://..." 等站外地址；
 * - 回到登录/注册页会造成循环，直接忽略；
 * - 任何非字符串都回退到 fallback。
 */
export function safeRedirect(raw: unknown, fallback = "/"): string {
  if (typeof raw !== "string" || !raw) return fallback;
  if (!raw.startsWith("/") || raw.startsWith("//")) return fallback;
  // 兼容部分浏览器把 "/\host" 当成协议相对地址
  if (raw.startsWith("/\\")) return fallback;
  if (raw === "/login" || raw.startsWith("/login?") || raw === "/register" || raw.startsWith("/register?")) {
    return fallback;
  }
  return raw;
}
