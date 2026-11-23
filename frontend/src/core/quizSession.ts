/**
 * 单词测验轮次续做（本地会话状态）。
 *
 * 只存「这一轮走到哪」这一临时状态，学习成果（mastery / mistakes）仍由
 * learning store 每题落盘并同步。按作用域分键，计划测试同一天每个词库各自续做。
 */
import type { QuizQuestion } from "./quiz";
import type { PlanWord } from "./plan";

export const QUIZ_SESSION_VERSION = 2;
/** 一轮最多几十题，7 天足够跨过「学到一半第二天接着学」 */
export const QUIZ_SESSION_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const LS_PREFIX = "pet_quiz_session::";

export interface QuizSession {
  version: number;
  saved_at: number;
  mode: "plan" | "free";
  plan_day: number;
  /** 开轮时的计划总天数；用于识别计划被删除/改天数 */
  plan_length: number;
  /** 开轮时的计划结构时间戳；计划重建但天数相同时也能识别 */
  plan_updated_at: number;
  bank: string;
  count: number;
  mistake_first: boolean;
  round: QuizQuestion[];
  results: Array<boolean | null>;
  correct_count: number;
  wrong_words: PlanWord[];
}

export type QuizSessionInput = Omit<QuizSession, "version" | "saved_at">;

export interface ResumeContext {
  mode: "plan" | "free";
  planLength: number;
  planUpdatedAt: number;
  /** URL 指定的计划天；未指定为 null */
  planDay: number | null;
  /** URL 指定的词库；未指定为空串 */
  bank: string;
}

/** 计划测试：同一天每个词库一份会话 */
export function planScope(user: string, planUpdatedAt: number, day: number, bank: string): string {
  return `plan:${user}:${planUpdatedAt}:${day}:${bank}`;
}

/** 自由测验：每个用户一份 */
export function freeScope(user: string): string {
  return `free:${user}`;
}

export function quizSessionKey(scope: string): string {
  return LS_PREFIX + scope;
}

/**
 * 清理本用户不再需要的会话：过期轮次、旧计划代际（时间戳不同）的轮次。
 * 在进入学习/测试页时调用一次，避免长期使用后 localStorage 堆积。
 */
export function pruneQuizSessions(user: string, planUpdatedAt: number, now = Date.now()): void {
  if (!user) return;
  let keys: string[] = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(LS_PREFIX)) keys.push(k);
    }
  } catch {
    return;
  }
  const planPrefix = `plan:${user}:`;
  const keepPlan = `plan:${user}:${planUpdatedAt}:`;
  const free = freeScope(user);
  for (const key of keys) {
    const scope = key.slice(LS_PREFIX.length);
    // v1 旧键是裸用户名，已不再读取
    if (scope === user) {
      localStorage.removeItem(key);
      continue;
    }
    const mine = scope.startsWith(planPrefix) || scope === free;
    if (!mine) continue;
    if (!scope.startsWith(keepPlan) && scope !== free) {
      localStorage.removeItem(key); // 旧计划代际
      continue;
    }
    const raw = localStorage.getItem(key);
    if (!raw) continue;
    try {
      const at = (JSON.parse(raw) as { saved_at?: unknown }).saved_at;
      if (typeof at === "number" && now - at > QUIZ_SESSION_TTL_MS) localStorage.removeItem(key);
    } catch {
      localStorage.removeItem(key);
    }
  }
}

export function saveQuizSession(scope: string, data: QuizSessionInput, now = Date.now()): void {
  if (!scope) return;
  try {
    const payload: QuizSession = {
      version: QUIZ_SESSION_VERSION,
      saved_at: now,
      ...data,
    };
    localStorage.setItem(quizSessionKey(scope), JSON.stringify(payload));
  } catch {
    /* 私密模式/配额不足：续做降级，不影响答题 */
  }
}

export function clearQuizSession(scope: string): void {
  if (!scope) return;
  try {
    localStorage.removeItem(quizSessionKey(scope));
  } catch {
    /* ignore */
  }
}

/** 读取并校验；任何不合法的轮次都清除并返回 null，由调用方正常开局。 */
export function loadQuizSession(scope: string, now = Date.now()): QuizSession | null {
  if (!scope) return null;
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(quizSessionKey(scope));
  } catch {
    return null;
  }
  if (!raw) return null;

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    clearQuizSession(scope);
    return null;
  }

  const s = parsed as Partial<QuizSession>;
  const fresh = typeof s.saved_at === "number" && s.saved_at >= 0 && now - s.saved_at <= QUIZ_SESSION_TTL_MS;
  const planFieldsOk =
    s.mode === "free" ||
    (s.mode === "plan" &&
      typeof s.plan_day === "number" &&
      s.plan_day >= 1 &&
      typeof s.plan_length === "number" &&
      s.plan_length >= 1);
  const valid =
    s.version === QUIZ_SESSION_VERSION &&
    (s.mode === "plan" || s.mode === "free") &&
    fresh &&
    planFieldsOk &&
    Array.isArray(s.round) &&
    s.round.length > 0 &&
    Array.isArray(s.results) &&
    s.results.length === s.round.length &&
    typeof s.correct_count === "number" &&
    Array.isArray(s.wrong_words) &&
    typeof s.plan_day === "number" &&
    typeof s.plan_length === "number" &&
    typeof s.plan_updated_at === "number" &&
    typeof s.bank === "string" &&
    typeof s.count === "number" &&
    typeof s.mistake_first === "boolean";

  if (!valid) {
    clearQuizSession(scope);
    return null;
  }
  return s as QuizSession;
}

/** 复用的轮次必须与当前入口上下文一致，避免把用户拉回过期题组。 */
export function sessionMatches(s: QuizSession, ctx: ResumeContext): boolean {
  if (s.mode !== ctx.mode) return false;
  if (ctx.mode === "plan") {
    if (s.plan_length !== ctx.planLength) return false;
    if (s.plan_updated_at !== ctx.planUpdatedAt) return false;
    if (ctx.planDay !== null && ctx.planDay !== s.plan_day) return false;
    if (ctx.bank && s.bank !== ctx.bank) return false;
    return true;
  }
  if (ctx.bank && s.bank !== ctx.bank) return false;
  return true;
}

/** 第一道未答题下标；全部答完返回 -1。 */
export function firstUnanswered(results: Array<boolean | null>): number {
  return results.findIndex((r) => r === null);
}

/** 恢复落点：第一道未答题；全部答完则停在结算页。 */
export function resumePosition(s: Pick<QuizSession, "round" | "results">): {
  index: number;
  finished: boolean;
} {
  const idx = firstUnanswered(s.results);
  return idx === -1
    ? { index: Math.max(0, s.round.length - 1), finished: true }
    : { index: idx, finished: false };
}
