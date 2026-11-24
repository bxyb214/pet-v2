import { createRouter, createWebHistory } from "vue-router";
import { getToken } from "../core/api";

/** 面包屑项：纯字符串只展示；带 to 的项可点击回跳 */
export type Crumb = string | { label: string; to: string };

declare module "vue-router" {
  interface RouteMeta {
    /** 所属学科（布局侧边栏高亮） */
    subject?: "english" | "chinese" | "math";
    /** 所属二级板块 */
    module?: "words" | "reading" | "grammar" | "listening" | "speak" | "books" | "progress";
    /** 面包屑 */
    crumbs?: Crumb[];
    /** 三级页签条（内容区顶部） */
    tabs?: { label: string; to: string }[];
    /** 内容宽度档位（默认 960；narrow=720 仅沉浸式作答/对话页） */
    width?: "wide" | "narrow";
    /** ComingSoon / 占位页文案、无面包屑页面的标题 */
    title?: string;
    tags?: string[];
    /** 错题占位页的「去学习」目标 */
    studyTo?: string;
  }
}

// 三级页签配置（集中一处，路由 meta 引用）
const WORD_TABS = [
  { label: "词库", to: "/english/words/browse" },
  { label: "学习", to: "/english/words/study" },
  { label: "计划", to: "/english/words/plan" },
  { label: "错题", to: "/english/words/mistakes" },
];
const READING_TABS = [
  { label: "教材", to: "/english/reading/home" },
  { label: "计划", to: "/english/reading/plan" },
  { label: "错题", to: "/english/reading/mistakes" },
];
const SPEAK_TABS = [
  { label: "计划", to: "/english/speak" },
  { label: "跟读", to: "/english/speak/shadow" },
  { label: "造句", to: "/english/speak/make" },
  { label: "对话", to: "/english/speak/talk" },
  { label: "题库", to: "/english/speak/scenes" },
];
const MATH_TABS = [
  { label: "课程", to: "/math" },
  { label: "学习进度", to: "/math/progress" },
];

export const router = createRouter({
  history: createWebHistory(),
  // 浏览器后退恢复原位置；页签切换、进入新页面一律从顶部开始
  scrollBehavior(_to, _from, savedPosition) {
    return savedPosition ?? { top: 0 };
  },
  routes: [
    { path: "/login", component: () => import("../views/Login.vue"), meta: { title: "登录" } },
    { path: "/register", component: () => import("../views/Register.vue"), meta: { title: "注册" } },

    {
      path: "/",
      component: () => import("../layouts/AppLayout.vue"),
      children: [
        {
          path: "",
          component: () => import("../views/HomePage.vue"),
          meta: { title: "首页" },
        },
        {
          path: "settings",
          component: () => import("../views/SettingsPage.vue"),
          meta: { crumbs: ["设置"], width: "narrow" },
        },
        {
          path: "settings/usage",
          component: () => import("../views/UsagePage.vue"),
          meta: { crumbs: [{ label: "设置", to: "/settings" }, "AI 计费"] },
        },
        // ---------- 英语 · 单词 ----------
        {
          path: "english/words/browse",
          component: () => import("../views/BrowsePage.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", { label: "单词", to: "/english/words/browse" }, "词库"], tabs: WORD_TABS },
        },
        {
          path: "english/words/study",
          component: () => import("../views/QuizPage.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", { label: "单词", to: "/english/words/browse" }, "学习"], tabs: WORD_TABS },
        },
        {
          path: "english/words/study/day",
          component: () => import("../views/PlanStudyPage.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", { label: "单词", to: "/english/words/browse" }, "学习"], tabs: WORD_TABS },
        },
        {
          path: "english/words/plan",
          component: () => import("../views/PlanPage.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", { label: "单词", to: "/english/words/browse" }, "计划"], tabs: WORD_TABS },
        },
        {
          path: "english/words/mistakes",
          component: () => import("../views/WordsMistakes.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", { label: "单词", to: "/english/words/browse" }, "错题"], tabs: WORD_TABS },
        },
        // ---------- 英语 · 阅读 ----------
        {
          path: "english/reading/home",
          component: () => import("../views/ReadingHome.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", { label: "阅读", to: "/english/reading/home" }, "教材"], tabs: READING_TABS },
        },
        {
          path: "english/reading/plan",
          component: () => import("../views/ReadingPlanPage.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", { label: "阅读", to: "/english/reading/home" }, "计划"], tabs: READING_TABS },
        },
        {
          path: "english/reading/study/:testNo/:part",
          component: () => import("../views/ReadingStudy.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", { label: "阅读", to: "/english/reading/home" }, "精读"] },
        },
        {
          path: "english/reading/quiz/:testNo",
          component: () => import("../views/ReadingQuiz.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", { label: "阅读", to: "/english/reading/home" }, "测验"], width: "narrow" },
        },
        {
          path: "english/reading/add",
          component: () => import("../views/AddSentencePage.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", { label: "阅读", to: "/english/reading/home" }, "加句"] },
        },
        {
          path: "english/reading/mistakes",
          component: () => import("../views/ReadingMistakes.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", { label: "阅读", to: "/english/reading/home" }, "错题"], tabs: READING_TABS },
        },
        // ---------- 英语 · 语法 ----------
        {
          path: "english/grammar",
          component: () => import("../views/GrammarHome.vue"),
          meta: { subject: "english", module: "grammar", crumbs: ["英语", "语法"] },
        },
        // ---------- 英语 · 听力 ----------
        {
          path: "english/listening/home",
          component: () => import("../views/ListeningHome.vue"),
          meta: { subject: "english", module: "listening", crumbs: ["英语", { label: "听力", to: "/english/listening/home" }, "教材"] },
        },
        {
          path: "english/listening/part/:testNo/:part",
          component: () => import("../views/ListeningPartPage.vue"),
          meta: { subject: "english", module: "listening", crumbs: ["英语", { label: "听力", to: "/english/listening/home" }, "播放"] },
        },
        // 听力错题本已下线，旧链接回首页
        { path: "english/listening/review", redirect: "/english/listening/home" },
        // ---------- 英语 · 口语 ----------
        {
          path: "english/speak",
          component: () => import("../views/SpeakHome.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", { label: "口语", to: "/english/speak" }, "计划"], tabs: SPEAK_TABS },
        },
        {
          path: "english/speak/shadow",
          component: () => import("../views/SpeakShadow.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", { label: "口语", to: "/english/speak" }, "跟读"], tabs: SPEAK_TABS },
        },
        {
          path: "english/speak/talk",
          component: () => import("../views/SpeakTalk.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", { label: "口语", to: "/english/speak" }, "对话"], tabs: SPEAK_TABS },
        },
        // 复盘已并入自由对话页，旧链接回口语首页
        { path: "english/speak/review", redirect: "/english/speak" },
        {
          path: "english/speak/make",
          component: () => import("../views/SentencePage.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", { label: "口语", to: "/english/speak" }, "造句"], tabs: SPEAK_TABS },
        },
        {
          path: "english/speak/scenes",
          component: () => import("../views/SpeakScenes.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", { label: "口语", to: "/english/speak" }, "题库"], tabs: SPEAK_TABS },
        },
        // ---------- 其他学科 / 管理 ----------
        {
          path: "chinese",
          component: () => import("../views/ComingSoon.vue"),
          meta: { subject: "chinese", title: "语文", tags: ["识字与词汇", "古诗文", "阅读理解", "写作表达"] },
        },
        {
          path: "math",
          component: () => import("../views/MathHome.vue"),
          meta: { subject: "math", module: "books", crumbs: ["数学", "一课通关", "课程"], tabs: MATH_TABS },
        },
        {
          path: "math/books/:bookId",
          component: () => import("../views/MathBook.vue"),
          meta: { subject: "math", module: "books", title: "年级课程" },
        },
        {
          path: "math/books/:bookId/:lessonId",
          component: () => import("../views/MathLesson.vue"),
          meta: { subject: "math", module: "books", title: "课程视频" },
        },
        {
          path: "math/progress",
          component: () => import("../views/MathProgress.vue"),
          meta: { subject: "math", module: "progress", crumbs: ["数学", { label: "一课通关", to: "/math" }, "学习进度"], tabs: MATH_TABS },
        },
        // 首版路径兼容（2026-11-23 已上线过 /math/lessons）
        { path: "math/lessons", redirect: "/math/books/yongle-g3" },
        {
          path: "math/lessons/:id",
          redirect: (to) => `/math/books/yongle-g3/${String(to.params.id)}`,
        },
        { path: "admin", component: () => import("../views/AdminPage.vue"), meta: { title: "管理后台" } },
        {
          path: ":pathMatch(.*)*",
          component: () => import("../views/NotFound.vue"),
          meta: { title: "页面不存在" },
        },
      ],
    },

    // ---------- 旧路径 redirect（书签/习惯不断） ----------
    { path: "/plan", redirect: "/english/words/plan" },
    { path: "/words/browse", redirect: "/english/words/browse" },
    { path: "/words/add", redirect: "/english/words/browse" },
    { path: "/quiz", redirect: "/english/words/study" },
    { path: "/reading", redirect: "/english/reading/home" },
    { path: "/reading/study/:testNo/:part", redirect: (to) => `/english/reading/study/${String(to.params.testNo)}/${String(to.params.part)}` },
    { path: "/reading/quiz/:testNo", redirect: (to) => `/english/reading/quiz/${String(to.params.testNo)}` },
    { path: "/reading/add", redirect: "/english/reading/add" },
    { path: "/listening", redirect: "/english/listening/home" },
    { path: "/listening/review", redirect: "/english/listening/home" },
    { path: "/listening/:testNo/:part", redirect: (to) => `/english/listening/part/${String(to.params.testNo)}/${String(to.params.part)}` },
    // 旧版听力首页用了错误链接 /english/listening/:testNo/:part
    { path: "/english/listening/:testNo/:part", redirect: (to) => `/english/listening/part/${String(to.params.testNo)}/${String(to.params.part)}` },
    { path: "/speak", redirect: "/english/speak" },
    { path: "/speak/shadow", redirect: "/english/speak/shadow" },
    { path: "/speak/talk", redirect: "/english/speak/talk" },
    { path: "/speak/review", redirect: "/english/speak" },
    { path: "/speak/make", redirect: "/english/speak/make" },
    { path: "/speak/scenes", redirect: "/english/speak/scenes" },
  ],
});

// 浏览器标签标题：优先用完整面包屑（含页签对应层级），没有时用 meta.title
router.afterEach((to) => {
  const crumbs = (to.meta.crumbs ?? []).map((c) => (typeof c === "string" ? c : c.label));
  const title = crumbs.length ? crumbs.join(" · ") : (to.meta.title ?? "");
  document.title = title ? `${title} · 火焰学习` : "火焰学习";
});

// 路由守卫：除登录/注册外，所有页面都必须有有效会话；
// 会话缺失/过期/被服务端拒绝 → 统一回登录页，不再渲染任何业务页面。
router.beforeEach(async (to) => {
  const PUBLIC = new Set(["/login", "/register"]);
  if (PUBLIC.has(to.path)) return true;

  if (!getToken()) return { path: "/login", query: { redirect: to.fullPath }, replace: true };

  const { useAuthStore } = await import("../stores/auth");
  const auth = useAuthStore();
  await auth.restore();
  if (!auth.username) return { path: "/login", query: { redirect: to.fullPath }, replace: true };

  // 非管理员禁止进管理页
  if (to.path === "/admin" && !auth.isAdmin) return "/";

  return true;
});
