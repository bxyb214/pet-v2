/**
 * 确定性乱序工具（计划切词 / 测验选项共用）。
 * 同一组种子永远得到同一序列，保证刷新、换页面、续做不跳词。
 */

/** 稳定种子：同一组输入（计划时间戳/天/词库等）永远得到同一序列 */
export function seedFrom(...parts: Array<string | number>): number {
  let h = 2166136261 >>> 0;
  for (const part of parts) {
    const s = String(part);
    for (let i = 0; i < s.length; i++) {
      h ^= s.charCodeAt(i);
      h = Math.imul(h, 16777619) >>> 0;
    }
    h ^= 0x9e3779b9;
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h >>> 0;
}

/** 32 位 PRNG：与种子配合，保证序列可复现 */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Fisher–Yates 洗牌（不修改入参） */
export function shuffleWith<T>(arr: T[], rand: () => number): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** 按种子确定性乱序：同种子 + 同数组 → 同结果 */
export function deterministicShuffle<T>(arr: T[], seed: number): T[] {
  return shuffleWith(arr, mulberry32(seed));
}
