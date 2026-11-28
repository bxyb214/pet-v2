import type { Component } from "vue";
import {
  BookOutline, CalculatorOutline, HeadsetOutline,
  LanguageOutline, LibraryOutline, MicOutline, PlayCircleOutline,
  ReaderOutline, StatsChartOutline,
} from "@vicons/ionicons5";
import { englishModulesFor } from "../core/examContent";

/** 侧栏 / 手机底栏共用的导航定义（唯一来源） */

export type Module = {
  key: "words" | "reading" | "grammar" | "listening" | "speak" | "books" | "progress";
  name: string;
  icon: Component;
  first: string;
};

export type Subject = {
  key: "english" | "chinese" | "math";
  name: string;
  icon: Component;
  desc: string;
  first: string;
  /** 侧栏配色的短类名（CSS 用 .en/.cn/.ma） */
  cls: string;
};

export const SUBJECTS: Subject[] = [
  { key: "english", name: "英语", icon: LanguageOutline, desc: "", first: "/english/words/browse", cls: "en" },
  { key: "chinese", name: "语文", icon: BookOutline, desc: "筹备中", first: "/chinese", cls: "cn" },
  { key: "math", name: "数学", icon: CalculatorOutline, desc: "三、四年级已上线", first: "/math", cls: "ma" },
];

export const EN_MODULES: Module[] = [
  { key: "words", name: "单词", icon: ReaderOutline, first: "/english/words/browse" },
  { key: "reading", name: "阅读", icon: LibraryOutline, first: "/english/reading/home" },
  { key: "listening", name: "听力", icon: HeadsetOutline, first: "/english/listening/home" },
  { key: "speak", name: "口语", icon: MicOutline, first: "/english/speak" },
];

export const MATH_MODULES: Module[] = [
  { key: "books", name: "一课通关", icon: PlayCircleOutline, first: "/math" },
  { key: "progress", name: "学习进度", icon: StatsChartOutline, first: "/math/progress" },
];

/** 手机底栏 / 侧栏：按当前路由学科取二级板块；无板块（首页 / 语文）返回空数组。
 *  英语按级别过滤：KET 已开放单词/阅读/听力，没内容的板块不展示。 */
export function modulesForSubject(subject?: string, exam = "pet"): Module[] {
  if (subject === "english") {
    const allowed = new Set<string>(englishModulesFor(exam));
    return EN_MODULES.filter((m) => allowed.has(m.key));
  }
  if (subject === "math") return MATH_MODULES;
  return [];
}
