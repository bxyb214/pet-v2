/** 管理后台共用格式化：金额单位是 0.001 元（milli），展示统一换成元。 */

export function fmtYuan(milli: number | null | undefined): string {
  return ((milli ?? 0) / 1000).toFixed(2) + " 元";
}

export function fmtYuanShort(milli: number | null | undefined): string {
  return ((milli ?? 0) / 1000).toFixed(2);
}

export function fmtMB(bytes: number | null | undefined): string {
  return ((bytes ?? 0) / 1024 / 1024).toFixed(1) + " MB";
}

export function fmtInt(n: number | null | undefined): string {
  return String(Math.round(n ?? 0));
}

/** 本地日期 YYYY-MM-DD（北京时间，不能用 toISOString 的 UTC 日期）。 */
export function localDay(ts: number): string {
  const d = new Date(ts);
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

/** 本地月份 YYYY-MM。 */
export function localMonth(ts: number): string {
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function ratioPct(used: number, budget: number): number {
  if (budget <= 0) return 100;
  return Math.min(100, Math.round((used / budget) * 100));
}
