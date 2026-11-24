/**
 * 阅读测验续做（本地会话状态）。
 *
 * 只保存「这一轮走到哪」；答题成果（错题本）仍由 learning store 每题即时落盘。
 * 按「用户 + 测验范围」分键，并校验题目指纹，避免教材/错题变化后续错位。
 */
export const READING_SESSION_VERSION = 1;
/** 与单词轮次一致：7 天内回来都能接着做 */
export const READING_SESSION_TTL_MS = 7 * 24 * 60 * 60 * 1000;
const LS_PREFIX = "pet_reading_quiz::";

export interface ReadingQuizSession {
  version: number;
  saved_at: number;
  /** 题目指纹：题干/类型变化时不恢复 */
  sig: string;
  idx: number;
  results: Array<boolean | null>;
  correct_count: number;
  /** 当前题是否已作答（停在反馈态时离开） */
  answered: boolean;
  picked: number;
}

export type ReadingQuizSessionInput = Omit<ReadingQuizSession, "version" | "saved_at">;

export function readingSessionKey(owner: string, scope: string): string {
  return `${LS_PREFIX}${owner || "-"}::${scope}`;
}

/** 读取并校验；签名不一致、过期或数据损坏都返回 null。 */
export function loadReadingSession(
  owner: string,
  scope: string,
  sig: string,
  now = Date.now(),
): ReadingQuizSession | null {
  const key = readingSessionKey(owner, scope);
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const s = JSON.parse(raw) as Partial<ReadingQuizSession>;
    if (s.version !== READING_SESSION_VERSION || typeof s.saved_at !== "number") return null;
    if (now - s.saved_at > READING_SESSION_TTL_MS) {
      localStorage.removeItem(key);
      return null;
    }
    if (s.sig !== sig || !Array.isArray(s.results)) return null;
    const results = s.results.map((v) => (v === true ? true : v === false ? false : null));
    return {
      version: READING_SESSION_VERSION,
      saved_at: s.saved_at,
      sig,
      idx: Math.max(0, Math.floor(Number(s.idx) || 0)),
      results,
      correct_count: Math.max(0, Math.floor(Number(s.correct_count) || 0)),
      answered: s.answered === true,
      picked: Math.floor(Number(s.picked) || -1),
    };
  } catch {
    return null;
  }
}

export function saveReadingSession(owner: string, scope: string, data: ReadingQuizSessionInput): void {
  try {
    localStorage.setItem(
      readingSessionKey(owner, scope),
      JSON.stringify({ version: READING_SESSION_VERSION, saved_at: Date.now(), ...data }),
    );
  } catch {
    /* 隐私模式等无法持久化时，仅本次会话内有效 */
  }
}

export function clearReadingSession(owner: string, scope: string): void {
  try {
    localStorage.removeItem(readingSessionKey(owner, scope));
  } catch {
    /* ignore */
  }
}
