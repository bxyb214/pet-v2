/**
 * 麦克风可用性判断与错误文案。
 * 浏览器只在安全上下文（HTTPS 或 localhost）暴露 navigator.mediaDevices；
 * 用 http://局域网IP 打开时直接提示换地址，而不是笼统说“没有权限”。
 */

/** 地址/浏览器层面不可用的原因；可用时返回空字符串。 */
export function micBlockedReason(): string {
  if (typeof window === "undefined") return "";
  if (!window.isSecureContext) {
    return "当前地址不是 HTTPS（或 localhost），浏览器禁止使用麦克风；请改用 https 地址打开后再练。";
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    return "当前浏览器不支持麦克风采集，请换用新版 Chrome / Safari / Edge。";
  }
  return "";
}

/** 把 getUserMedia 抛出的 DOMException 转成给孩子看的提示。 */
export function micErrorText(e: unknown): string {
  const name = (e as { name?: string } | null)?.name ?? "";
  if (name === "NotAllowedError" || name === "SecurityError") {
    return "麦克风权限被拒绝，请在浏览器地址栏的麦克风图标里允许后重试。";
  }
  if (name === "NotFoundError") return "没有检测到麦克风设备，请接上麦克风后重试。";
  if (name === "NotReadableError") return "麦克风被其他应用占用，关闭占用后重试。";
  return "没有拿到麦克风，请检查浏览器设置后重试。";
}
