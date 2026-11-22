import { createRouter, createWebHistory } from "vue-router";
import { getToken } from "../core/api";

declare module "vue-router" {
  interface RouteMeta {
    /** 所属学科（布局侧边栏高亮） */
    subject?: "english" | "chinese" | "math";
    /** 所属二级板块 */
    module?: "words" | "reading" | "listening" | "speak";
    /** 面包屑 */
    crumbs?: string[];
    /** 三级页签条（内容区顶部） */
    tabs?: { label: string; to: string }[];
    /** 内容宽度档位（默认 960；narrow=720 仅沉浸式作答/对话页） */
    width?: "wide" | "narrow";
    /** ComingSoon / 占位页文案 */
    title?: string;
    icon?: string;
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
  { label: "错题", to: "/english/reading/mistakes" },
];
const LISTEN_TABS = [
  { label: "教材", to: "/english/listening/home" },
  { label: "错题", to: "/english/listening/review" },
];
const SPEAK_TABS = [
  { label: "计划", to: "/english/speak" },
  { label: "跟读", to: "/english/speak/shadow" },
  { label: "对话", to: "/english/speak/talk" },
  { label: "复盘", to: "/english/speak/review" },
  { label: "造句", to: "/english/speak/make" },
];

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/english/words/browse" },
    { path: "/login", component: () => import("../views/Login.vue") },
    { path: "/register", component: () => import("../views/Register.vue") },

    {
      path: "/",
      component: () => import("../layouts/AppLayout.vue"),
      children: [
        // ---------- 英语 · 单词 ----------
        {
          path: "english/words/browse",
          component: () => import("../views/BrowsePage.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", "单词", "词库"], tabs: WORD_TABS },
        },
        {
          path: "english/words/study",
          component: () => import("../views/QuizPage.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", "单词", "学习"], tabs: WORD_TABS },
        },
        {
          path: "english/words/plan",
          component: () => import("../views/PlanPage.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", "单词", "计划"], tabs: WORD_TABS },
        },
        {
          path: "english/words/mistakes",
          component: () => import("../views/WordsMistakes.vue"),
          meta: { subject: "english", module: "words", crumbs: ["英语", "单词", "错题"], tabs: WORD_TABS },
        },
        // ---------- 英语 · 阅读 ----------
        {
          path: "english/reading/home",
          component: () => import("../views/ReadingHome.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", "阅读", "教材"], tabs: READING_TABS },
        },
        {
          path: "english/reading/study/:testNo/:part",
          component: () => import("../views/ReadingStudy.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", "阅读", "精读"] },
        },
        {
          path: "english/reading/quiz/:testNo",
          component: () => import("../views/ReadingQuiz.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", "阅读", "测验"], width: "narrow" },
        },
        {
          path: "english/reading/add",
          component: () => import("../views/AddSentencePage.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", "阅读", "加句"], tabs: READING_TABS },
        },
        {
          path: "english/reading/mistakes",
          component: () => import("../views/ReadingMistakes.vue"),
          meta: { subject: "english", module: "reading", crumbs: ["英语", "阅读", "错题"], tabs: READING_TABS },
        },
        // ---------- 英语 · 听力 ----------
        {
          path: "english/listening/home",
          component: () => import("../views/ListeningHome.vue"),
          meta: { subject: "english", module: "listening", crumbs: ["英语", "听力", "教材"], tabs: LISTEN_TABS },
        },
        {
          path: "english/listening/part/:testNo/:part",
          component: () => import("../views/ListeningPartPage.vue"),
          meta: { subject: "english", module: "listening", crumbs: ["英语", "听力", "测验"] },
        },
        {
          path: "english/listening/review",
          component: () => import("../views/ListeningReview.vue"),
          meta: { subject: "english", module: "listening", crumbs: ["英语", "听力", "错题"], tabs: LISTEN_TABS },
        },
        // ---------- 英语 · 口语 ----------
        {
          path: "english/speak",
          component: () => import("../views/SpeakHome.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", "口语", "计划"], tabs: SPEAK_TABS },
        },
        {
          path: "english/speak/shadow",
          component: () => import("../views/SpeakShadow.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", "口语", "跟读"] },
        },
        {
          path: "english/speak/talk",
          component: () => import("../views/SpeakTalk.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", "口语", "对话"], width: "narrow" },
        },
        {
          path: "english/speak/review",
          component: () => import("../views/SpeakReview.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", "口语", "复盘"], width: "narrow" },
        },
        {
          path: "english/speak/make",
          component: () => import("../views/SentencePage.vue"),
          meta: { subject: "english", module: "speak", crumbs: ["英语", "口语", "造句"] },
        },
        // ---------- 其他学科 / 管理 ----------
        {
          path: "chinese",
          component: () => import("../views/ComingSoon.vue"),
          meta: { subject: "chinese", title: "语文", icon: "📚", tags: ["识字与词汇", "古诗文", "阅读理解", "写作表达"] },
        },
        {
          path: "math",
          component: () => import("../views/ComingSoon.vue"),
          meta: { subject: "math", title: "数学", icon: "🧮", tags: ["计算能力", "思维训练", "应用题", "图形几何"] },
        },
        { path: "admin", component: () => import("../views/AdminPage.vue") },
      ],
    },

    // ---------- 旧路径 redirect（书签/习惯不断） ----------
    { path: "/plan", redirect: "/english/words/plan" },
    { path: "/words/browse", redirect: "/english/words/browse" },
    { path: "/words/add", redirect: "/english/words/browse" },
    { path: "/quiz", redirect: "/english/words/study" },
    { path: "/reading", redirect: "/english/reading/home" },
    { path: "/reading/study/:testNo/:part", redirect: "/english/reading/study/:testNo/:part" },
    { path: "/reading/quiz/:testNo", redirect: "/english/reading/quiz/:testNo" },
    { path: "/reading/add", redirect: "/english/reading/add" },
    { path: "/listening", redirect: "/english/listening/home" },
    { path: "/listening/review", redirect: "/english/listening/review" },
    { path: "/listening/:testNo/:part", redirect: "/english/listening/part/:testNo/:part" },
    { path: "/speak", redirect: "/english/speak" },
    { path: "/speak/shadow", redirect: "/english/speak/shadow" },
    { path: "/speak/talk", redirect: "/english/speak/talk" },
    { path: "/speak/review", redirect: "/english/speak/review" },
    { path: "/speak/make", redirect: "/english/speak/make" },
    { path: "/:pathMatch(.*)*", redirect: "/english/words/browse" },
  ],
});

// 路由守卫：未登录跳转登录页（本地模式除外）；非管理员禁止进管理页；
// 未开通口语的用户进入口语子页 → 回口语首页并弹权限提示（AI 调用有费用）
router.beforeEach(async (to) => {
  const localOnly = localStorage.getItem("pet_local_only") === "true";
  const PUBLIC = new Set(["/login", "/register"]);
  if (!localOnly && !PUBLIC.has(to.path) && !getToken()) return "/login";
  if (to.path === "/admin") {
    const { useAuthStore } = await import("../stores/auth");
    const auth = useAuthStore();
    await auth.restore();
    if (!auth.isAdmin) return "/english/words/browse";
  }
  if (to.path.startsWith("/english/speak") && to.path !== "/english/speak") {
    const { useAuthStore } = await import("../stores/auth");
    const auth = useAuthStore();
    if (!localOnly) {
      await auth.restore();
      if (auth.username && !auth.perms.includes("speak")) return "/english/speak?locked=1";
    }
  }
  return true;
});
