/** 各级别已上线（有内容）的英语板块；语法是「阅读」下的页签，不单列。 */
export type EnglishModule = "words" | "reading" | "listening" | "speak";

/** 新增级别内容后在这里放开；页面/导航/首页都读这一份。 */
export const EXAM_ENGLISH_MODULES: Record<string, EnglishModule[]> = {
  pet: ["words", "reading", "listening", "speak"],
  ket: ["words", "reading", "listening", "speak"],
  fce: [],
  junior: [],
};

export function englishModulesFor(exam: string): EnglishModule[] {
  return EXAM_ENGLISH_MODULES[exam] ?? [];
}

/** 没有 module 的页面（首页、设置等）不拦截；只有明确属于某板块的页面才判断。 */
export function moduleAvailable(exam: string, module?: string): boolean {
  if (!module) return true;
  return (englishModulesFor(exam) as string[]).includes(module);
}
