/** 会后复盘（§5.5）：类型 + 评分记账规则（与后端 grade 阈值一致）。 */

export type ReviewItem = {
  id: number;
  log_id: number;
  child_said: string;
  improved_en: string;
  improved_cn: string;
  focus: string;
  dims: string[];
  stage: number;
  due_at: string;
  repeats: number;
  done: boolean;
};

export type GradePlan = {
  /** 本次可划掉的维度（≥85 才划） */
  dims_ok: string[];
  /** advance = 前进到下个间隔；retry = 今天再练；reset = 回第 1 阶段 */
  next: "advance" | "retry" | "reset";
  /** 给孩子的中文反馈 */
  tip: string;
};

export const PASS = 85;
export const MIN = 60;

/** 按 SOE 得分决定本次要划掉的维度与下一步（纯函数，便于单测）。 */
export function gradePlan(score: number, dims: string[]): GradePlan {
  if (score >= PASS) {
    return { dims_ok: [...dims], next: "advance", tip: "很棒！这句过关了" };
  }
  if (score >= MIN) {
    return { dims_ok: [], next: "retry", tip: "听得懂，再顺一点就过关（85 分）" };
  }
  return { dims_ok: [], next: "reset", tip: "慢一点，先听示范再读一遍" };
}

/** 维度标签中文化：grammar:past-tense → 语法·past-tense。 */
export function dimLabel(dim: string): string {
  const [kind, ...rest] = dim.split(":");
  const body = rest.join(":");
  const kindCn: Record<string, string> = { grammar: "语法", vocab: "词汇", phrase: "句型" };
  const k = kindCn[kind] ?? "表达";
  return body ? `${k}·${body}` : k;
}

export function focusLabel(focus: string): string {
  return { grammar: "语法", vocab: "词汇", phrase: "句型" }[focus] ?? "表达";
}

/** 记忆曲线间隔（与后端一致），用于展示"几天后再见"。 */
export const INTERVALS = [1, 2, 4, 7, 15];

export function nextGapLabel(stage: number): string {
  const d = INTERVALS[Math.min(stage + 1, INTERVALS.length - 1)];
  return `${d} 天后再练`;
}
