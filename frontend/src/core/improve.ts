/** 对话中即时优化（P1-3）：少于 4 个词不自动调用，改由用户点「帮我改」。 */

export function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

/** 自动请求 improve 的最小词数（方案 §2.3 P1-3：≥4–5 个词）。 */
export const AUTO_IMPROVE_MIN_WORDS = 4;

export function shouldAutoImprove(text: string): boolean {
  return wordCount(text) >= AUTO_IMPROVE_MIN_WORDS;
}

/** 同一句只请求一次，避免轮次重复/并发叠加。 */
export function createImproveGuard() {
  const seen = new Set<string>();
  return {
    take(text: string): boolean {
      const key = text.trim().toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    },
    has(text: string): boolean {
      return seen.has(text.trim().toLowerCase());
    },
  };
}
