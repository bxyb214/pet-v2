/** 阅读板块数据与测验构建（reading-v2）。 */

export interface GramRef { c: number; g: string; d: string }
export interface ParseRef { r: string; t: string }
export interface GQ { stem: string; opts: string[]; a: number; why: string; c: number }
export interface RSentence {
  id: string; en: string; cn: string; key: string;
  quiz: string[]; point: string; note: string; tense: string;
  parse: ParseRef[]; gram: GramRef[]; gq: GQ[]; cs?: number[];
}
export interface RPart { part: number; kind: string; focus: string; sentences: RSentence[] }
export interface RTest { no: number; book: string; title: string; note?: string; parts: RPart[] }
export interface RBook { id: string; name: string; desc: string }
export interface RGrammar {
  book: string;
  days: { day: number; name: string; points: { c: number; name: string }[] }[];
  /** 语法书例句（只用于语法专项出题，不出现在阅读列表） */
  examples?: RSentence[];
}
export interface ReadingData {
  grammar: RGrammar; books: RBook[]; tests: RTest[];
  meta: { sentences: number; gq: number; points_covered: number; built: string };
}

export type QuizType = "meaning" | "blank" | "grammar";
export interface QuizItem {
  type: QuizType;
  s: RSentence;
  q?: GQ;               // grammar 题才有
  prompt: string;
  options: { label: string; correct: boolean }[];
}

const caches = new Map<string, ReadingData>();
const loadings = new Map<string, Promise<ReadingData>>();

/** 各级别数据路径：PET 沿用旧文件，KET 用单独目录。 */
export function readingUrl(exam = "pet"): string {
  return exam === "ket" ? "/data/ket/reading.json" : "/data/reading.json";
}

export function loadReading(exam = "pet"): Promise<ReadingData> {
  const hit = caches.get(exam);
  if (hit) return Promise.resolve(hit);
  let pending = loadings.get(exam);
  if (!pending) {
    pending = fetch(readingUrl(exam), { cache: "no-cache" })
      .then((r) => {
        if (!r.ok) throw new Error("阅读数据加载失败");
        return r.json() as Promise<ReadingData>;
      })
      .then((d) => {
        caches.set(exam, d);
        return d;
      })
      .finally(() => {
        loadings.delete(exam);
      });
    loadings.set(exam, pending);
  }
  return pending;
}

export function bookOf(data: ReadingData, test: RTest): RBook | undefined {
  return data.books.find((b) => b.id === (test.book || "t2"));
}

export function testSentences(test: RTest): RSentence[] {
  return test.parts.flatMap((p) => p.sentences);
}

function shuffle<T>(arr: T[], rnd: () => number = Math.random): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rnd() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

/** 三题型构建：meaning 选中文 / blank 选词填空 / grammar 语法选择。干扰项取自全库池，不足 3 跳过该题（旧站同语义）。 */
export function buildQuizItems(
  sentences: RSentence[],
  pool: RSentence[],
  cap = 24,
  rnd: () => number = Math.random,
): QuizItem[] {
  const out: QuizItem[] = [];
  const cnPool = [...new Set(pool.filter((x) => x.cn).map((x) => x.cn))];
  const keyPool = [...new Set(pool.filter((x) => x.key).map((x) => x.key))];
  for (const s of sentences) {
    const types = s.quiz && s.quiz.length ? s.quiz : ["meaning"];
    if (types.includes("meaning")) {
      const dis = shuffle(cnPool.filter((c) => c !== s.cn), rnd).slice(0, 3);
      if (dis.length === 3) {
        out.push({
          type: "meaning", s, prompt: s.en,
          options: shuffle([{ label: s.cn, correct: true }, ...dis.map((c) => ({ label: c, correct: false }))], rnd),
        });
      }
    }
    if (types.includes("blank") && s.key && s.en.includes(s.key)) {
      const dis = shuffle(keyPool.filter((k) => k !== s.key), rnd).slice(0, 3);
      if (dis.length === 3) {
        out.push({
          type: "blank", s, prompt: s.en.replace(s.key, "______"),
          options: shuffle([{ label: s.key, correct: true }, ...dis.map((k) => ({ label: k, correct: false }))], rnd),
        });
      }
    }
    if (types.includes("grammar")) {
      for (const q of s.gq || []) {
        if (!q || !Array.isArray(q.opts) || q.opts.length !== 4) continue;
        out.push({
          type: "grammar", s, q, prompt: q.stem,
          options: q.opts.map((o, i) => ({ label: o, correct: i === q.a })),
        });
      }
    }
  }
  return shuffle(out, rnd).slice(0, cap);
}

/** 考点索引：c → 语法题列表；可选传入语法书例句。 */
export function grammarIndex(tests: RTest[], examples: RSentence[] = []): Record<number, QuizItem[]> {
  const idx: Record<number, QuizItem[]> = {};
  const add = (s: RSentence): void => {
    for (const q of s.gq || []) {
      if (q.c == null) continue;
      (idx[q.c] = idx[q.c] || []).push({
        type: "grammar", s, q, prompt: q.stem,
        options: q.opts.map((o, i) => ({ label: o, correct: i === q.a })),
      });
    }
  };
  for (const t of tests) for (const p of t.parts) for (const s of p.sentences) add(s);
  for (const s of examples) add(s);
  return idx;
}

export function grammarName(data: ReadingData, c: number): { name: string; day: number; dname: string } | undefined {
  for (const d of data.grammar.days) {
    const p = d.points.find((x) => x.c === c);
    if (p) return { name: p.name, day: d.day, dname: d.name };
  }
  return undefined;
}

// ---------- 自定义句（R10）与错题维度（R8） ----------

import type { CustomSentenceItem } from "./merge";

export function customSid(book: string, testNo: number, part: number, en: string): string {
  return `${book}:${testNo}:${part}:${en.toLowerCase().replace(/\s+/g, " ").trim()}`;
}

/** 自定义句 → 精读句结构（无 parse/gram/gq；key 有则可出 blank 题）。 */
function customToSentence(c: CustomSentenceItem): RSentence {
  const quiz: string[] = ["meaning"];
  if (c.key && c.en.includes(c.key)) quiz.push("blank");
  return {
    id: c.sid, en: c.en, cn: c.cn, key: c.key || "",
    quiz, point: "", note: c.note, tense: "",
    parse: [], gram: [], gq: [],
  };
}

/** 把自定义句注入对应 test+part（返回新对象，不改 cache）。 */
export function withCustomSentences(data: ReadingData, custom: CustomSentenceItem[]): ReadingData {
  if (!custom.length) return data;
  const byPart = new Map<string, RSentence[]>();
  for (const c of custom) {
    const k = `${c.book}:${c.test_no}:${c.part}`;
    (byPart.get(k) ?? byPart.set(k, []).get(k)!).push(customToSentence(c));
  }
  return {
    ...data,
    tests: data.tests.map((t) => ({
      ...t,
      parts: t.parts.map((p) => {
        const extra = byPart.get(`${t.book || "t2"}:${t.no}:${p.part}`);
        return extra ? { ...p, sentences: [...p.sentences, ...extra] } : p;
      }),
    })),
  };
}

/** 句子的错题维度：meaning / blank / grammar:g<下标>（按 quiz 配置）。 */
export function sentenceDims(s: RSentence): string[] {
  const dims: string[] = [];
  const types = s.quiz && s.quiz.length ? s.quiz : ["meaning"];
  if (types.includes("meaning")) dims.push("meaning");
  if (types.includes("blank") && s.key && s.en.includes(s.key)) dims.push("blank");
  (s.gq || []).forEach((q, i) => {
    if (q && Array.isArray(q.opts) && q.opts.length === 4) dims.push(`grammar:g${i}`);
  });
  return dims;
}

/** 句子在指定维度下的 quiz item（复习用：只考欠的维度）。 */
export function itemForDim(s: RSentence, dim: string, pool: RSentence[], rnd: () => number = Math.random): QuizItem | null {
  if (dim === "meaning") {
    const dis = shuffle([...new Set(pool.filter((x) => x.id !== s.id && x.cn && x.cn !== s.cn).map((x) => x.cn))], rnd).slice(0, 3);
    if (dis.length < 3) return null;
    return {
      type: "meaning", s, prompt: s.en,
      options: shuffle([{ label: s.cn, correct: true }, ...dis.map((c) => ({ label: c, correct: false }))], rnd),
    };
  }
  if (dim === "blank") {
    if (!s.key || !s.en.includes(s.key)) return null;
    const dis = shuffle([...new Set(pool.filter((x) => x.id !== s.id && x.key && x.key !== s.key).map((x) => x.key))], rnd).slice(0, 3);
    if (dis.length < 3) return null;
    return {
      type: "blank", s, prompt: s.en.replace(s.key, "______"),
      options: shuffle([{ label: s.key, correct: true }, ...dis.map((k) => ({ label: k, correct: false }))], rnd),
    };
  }
  const m = /^grammar:g(\d+)$/.exec(dim);
  if (m) {
    const q = (s.gq || [])[Number(m[1])];
    if (!q || !Array.isArray(q.opts) || q.opts.length !== 4) return null;
    return { type: "grammar", s, q, prompt: q.stem, options: q.opts.map((o, i) => ({ label: o, correct: i === q.a })) };
  }
  return null;
}
