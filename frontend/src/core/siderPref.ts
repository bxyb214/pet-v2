/**
 * 侧栏折叠偏好（纯逻辑）：
 * - 用户没手动切换过 → 按窗口宽度决定默认（<1280 收起成图标条）
 * - 手动切换过后 → 记住用户选择（localStorage 由组件读写）
 */
export const SIDER_AUTO_WIDTH = 1280;
export type SiderPref = "open" | "closed" | null;

export function parseSiderPref(raw: string | null | undefined): SiderPref {
  return raw === "open" || raw === "closed" ? raw : null;
}

export function isSiderCollapsed(width: number, pref: SiderPref): boolean {
  if (pref === "open") return false;
  if (pref === "closed") return true;
  return width < SIDER_AUTO_WIDTH;
}
