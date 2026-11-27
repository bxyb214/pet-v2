<template>
  <div class="shell">
    <!-- 顶栏 -->
    <header class="topbar">
      <button class="menu-btn" aria-label="打开导航" @click="drawer = true">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>
      <router-link to="/" class="logo">
        <span class="leaf" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5Z" />
          </svg>
        </span>
        <span class="logo-txt">火焰学习</span>
      </router-link>
      <div class="spacer"></div>
      <PwaInstallHint />
      <n-dropdown
        v-if="auth.username"
        trigger="click"
        placement="bottom-end"
        :options="userMenu"
        @select="onUserMenu"
      >
        <button
          class="userbtn" type="button" aria-haspopup="menu"
          :class="{ dev: devMode }"
          :aria-label="`用户菜单：${userName}`" :title="userName"
        >
          <span v-if="devMode" class="devbadge" title="开发环境：AI 接口返回模拟结果">DEV</span>
          <span class="avatar">{{ initial }}</span>
          <span v-if="!devMode" class="uname">{{ userName }}</span>
          <svg class="chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="m6 9 6 6 6-6" />
          </svg>
        </button>
      </n-dropdown>
    </header>

    <div class="body-wrap">
      <!-- 桌面/平板侧栏：默认按宽度收起，用户可手动切换 -->
      <aside class="sider" :class="{ collapsed: siderCollapsed }">
        <button
          class="sider-toggle" type="button"
          :aria-expanded="!siderCollapsed"
          :aria-label="siderCollapsed ? '展开侧栏' : '收起侧栏'"
          :title="siderCollapsed ? '展开侧栏' : '收起侧栏'"
          @click="toggleSider"
        >
          <n-icon :component="siderCollapsed ? ChevronForwardOutline : ChevronBackOutline" size="18" />
          <span v-if="!siderCollapsed">收起</span>
        </button>
        <SiderNav />
      </aside>

      <!-- 内容区：面包屑 + 页签 + 页面，统一同一宽度容器 -->
      <main class="main" :class="[widthClass, { 'mic-on': micActive, 'has-tabbar': showTabBar }]">
        <div class="stack">
          <nav v-if="!immersive && crumbs.length" class="crumb" aria-label="面包屑">
            <template v-for="(c, i) in crumbs" :key="i">
              <span v-if="i" class="sep" aria-hidden="true">/</span>
              <b v-if="c.current" aria-current="page">{{ c.label }}</b>
              <router-link v-else-if="c.to" :to="c.to">{{ c.label }}</router-link>
              <span v-else>{{ c.label }}</span>
            </template>
          </nav>

          <div v-if="!immersive && showTabs" class="tabs-wrap">
            <nav class="tabs3" aria-label="页面分区">
              <router-link
                v-for="t in tabs"
                :key="t.to"
                :to="tabTo(t.to)"
                class="t"
                :class="{ active: isActiveTab(t.to) }"
                :aria-current="isActiveTab(t.to) ? 'page' : undefined"
              >{{ t.label }}</router-link>
            </nav>
          </div>

          <router-view />
        </div>
      </main>
    </div>

    <!-- 手机端底部二级导航：当前学科板块（桌面隐藏） -->
    <MobileTabBar v-if="showTabBar" />

    <!-- 麦克风占用期间的数字人：固定在右侧 1/3，关闭按钮在数字人下方 -->
    <MicCompanion v-if="micActive" />

    <!-- 手机抽屉导航：只放一级（首页 + 学科），板块在底部栏 -->
    <n-drawer v-model:show="drawer" placement="left" :width="264">
      <n-drawer-content body-content-style="padding: 16px 12px">
        <SiderNav :show-modules="false" @go="drawer = false" />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onBeforeUnmount, onMounted, ref, type Component } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NDrawer, NDrawerContent, NDropdown, NIcon, type DropdownOption } from "naive-ui";
import {
  ChevronBackOutline, ChevronForwardOutline,
  LogOutOutline, PersonOutline, SettingsOutline, ShieldCheckmarkOutline,
} from "@vicons/ionicons5";
import SiderNav from "./SiderNav.vue";
import MobileTabBar from "../components/MobileTabBar.vue";
import MicCompanion from "../components/MicCompanion.vue";
import PwaInstallHint from "../components/PwaInstallHint.vue";
import { modulesForSubject } from "./navModules";
import { useAuthStore } from "../stores/auth";
import { devMode, ensureDevMode } from "../core/devMode";
import { immersive } from "../core/immersive";
import { micActive } from "../core/micPresence";
import { isSiderCollapsed, parseSiderPref, type SiderPref } from "../core/siderPref";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const drawer = ref(false);

/** 侧栏折叠：没手动切换过就跟随窗口宽度（<1280 收起），切换后记住选择 */
const SIDER_KEY = "pet_sider";

function readSiderPref(): SiderPref {
  try {
    return parseSiderPref(localStorage.getItem(SIDER_KEY));
  } catch {
    return null;
  }
}

const siderPref = ref<SiderPref>(readSiderPref());
const siderCollapsed = ref(isSiderCollapsed(window.innerWidth, siderPref.value));

function toggleSider(): void {
  const next: Exclude<SiderPref, null> = siderCollapsed.value ? "open" : "closed";
  siderPref.value = next;
  siderCollapsed.value = next === "closed";
  try {
    localStorage.setItem(SIDER_KEY, next);
  } catch {
    /* 隐私模式等无法持久化时，仅本次会话生效 */
  }
}

function onResize(): void {
  // 手动选择优先；只有「自动」模式才随宽度变化
  if (!siderPref.value) siderCollapsed.value = isSiderCollapsed(window.innerWidth, null);
}

onMounted(() => {
  void ensureDevMode();
  window.addEventListener("resize", onResize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize);
});

/** 内容宽度三档（唯一来源，页面内不再自己设宽） */
const widthClass = computed(() => {
  const w = route.meta.width;
  return w ? `w-${w}` : "";
});

/** 有页签的页面，当前页已由页签表达，面包屑只保留学科/板块两级，避免同一信息占两行 */
const tabs = computed(() => route.meta.tabs ?? []);
/** 前缀匹配会同时命中父级页签（如 /english/speak 与 /english/speak/shadow），取最长的那一个 */
const activeTabTo = computed(() => {
  let best = "";
  for (const t of tabs.value) {
    const hit = route.path === t.to || route.path.startsWith(t.to + "/");
    if (hit && t.to.length > best.length) best = t.to;
  }
  return best;
});
const hasActiveTab = computed(() => activeTabTo.value !== "");
/** 页签条只在有命中项时渲染，避免「页签都在、谁都不亮」 */
const showTabs = computed(() => tabs.value.length > 0 && hasActiveTab.value);

/** 手机底栏：当前学科有板块、且不在沉浸作答 / 麦克风面板时显示（桌面由 CSS 隐藏） */
const showTabBar = computed(
  () => modulesForSubject(route.meta.subject).length > 0 && !immersive.value && !micActive.value,
);

const crumbs = computed(() => {
  const c = route.meta.crumbs;
  if (!c?.length) return [];
  const list = showTabs.value && c.length > 2 ? c.slice(0, -1) : c;
  return list.map((item, i) => {
    const label = typeof item === "string" ? item : item.label;
    const to = typeof item === "string" ? "" : item.to;
    const current = i === list.length - 1;
    // 当前页只做标记，不再渲染成可点的链接
    return { label, to: current ? "" : to, current };
  });
});

function isActiveTab(to: string): boolean {
  return activeTabTo.value === to;
}

/** 口语页签保留当前练习日，避免切页签后跟读/造句/对话落到不同天的话题。 */
function tabTo(to: string): string {
  const d = route.query.day;
  if (!d || !to.startsWith("/english/speak/")) return to;
  return `${to}?day=${encodeURIComponent(String(d))}`;
}

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) });
}

const userName = computed(() => auth.displayName || auth.username || "学");
/** 折叠时显示的首字母：中文取首字，英文转大写；Array.from 兼容代理对 */
const initial = computed(() => {
  const ch = Array.from(userName.value)[0] ?? "学";
  return /^[a-z]$/.test(ch) ? ch.toUpperCase() : ch;
});

/** 右上角统一菜单：设置 / 管理（仅管理员）/ 退出 */
const userMenu = computed<DropdownOption[]>(() => {
  const who = devMode.value ? "开发环境 · DEV" : userName.value;
  const options: DropdownOption[] = [
    { key: "who", label: who, disabled: true },
    { type: "divider", key: "d1" },
    { key: "settings", label: "备考", icon: renderIcon(SettingsOutline) },
    { key: "account", label: "账号", icon: renderIcon(PersonOutline) },
  ];
  if (auth.isAdmin) {
    options.push({ key: "admin", label: "管理", icon: renderIcon(ShieldCheckmarkOutline) });
  }
  options.push(
    { type: "divider", key: "d2" },
    {
      key: "logout",
      label: "退出",
      icon: renderIcon(LogOutOutline),
      props: { style: "color: var(--c-danger, #dc2626)" },
    },
  );
  return options;
});

function onUserMenu(key: string): void {
  if (key === "settings") void router.push("/settings");
  else if (key === "account") void router.push("/account");
  else if (key === "admin") void router.push("/admin");
  else if (key === "logout") logout();
}

function logout(): void {
  auth.logout();
  void router.push("/login");
}
</script>

<style scoped>
.shell { min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column; background: var(--c-bg, #f7faf8); }
.topbar {
  height: calc(56px + env(safe-area-inset-top, 0px));
  padding: env(safe-area-inset-top, 0px) max(20px, env(safe-area-inset-right, 0px)) 0 max(20px, env(safe-area-inset-left, 0px));
  display: flex; align-items: center; gap: 12px;
  background: var(--c-surface, #fff); border-bottom: 1px solid var(--c-line, #e5efe9);
  position: sticky; top: 0; z-index: 20;
}
.menu-btn { display: none; border: 1px solid var(--c-line, #e5efe9); background: #fff; border-radius: 10px; width: 38px; height: 38px; align-items: center; justify-content: center; color: var(--c-text, #1f2d26); cursor: pointer; flex: none; }
.logo { font-weight: 800; font-size: 18px; color: var(--c-primary-strong, #15803d); display: flex; align-items: center; gap: 8px; text-decoration: none; white-space: nowrap; }
.leaf { width: 30px; height: 30px; border-radius: 10px; background: linear-gradient(135deg, #22c55e, #16a34a); display: flex; align-items: center; justify-content: center; color: #fff; flex: none; }
.leaf svg { display: block; }
.spacer { flex: 1; }
.userbtn {
  display: inline-flex; align-items: center; gap: 8px;
  min-height: 40px; padding: 3px 10px 3px 4px;
  background: transparent; border: 1px solid var(--c-line, #e5efe9); border-radius: 999px;
  cursor: pointer; font: inherit;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.userbtn:hover { background: var(--c-mint-bg, #f2faf5); border-color: var(--c-line-strong, #d3e0d8); }
.userbtn:focus-visible { outline: 3px solid var(--c-primary, #16a34a); outline-offset: 2px; }
/* DEV 在用户左侧，二者之间留出明确间距，不叠在一起 */
.userbtn.dev { padding-left: 6px; gap: 10px; }
.uname {
  font-size: 14px; color: var(--c-text, #1f2d26); font-weight: 600;
  white-space: nowrap; max-width: 120px; overflow: hidden; text-overflow: ellipsis;
}
.chev { color: var(--c-text-2, #6b7f74); flex: none; }
.devbadge {
  display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px;
  border-radius: 999px; background: var(--c-accent-soft, #fff7ed);
  border: 1px solid var(--c-accent, #d97706); color: var(--c-text, #1f2d26);
  font-size: 12px; font-weight: 800; letter-spacing: 0.08em; line-height: 1; flex: none;
}
.devbadge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: var(--c-accent, #d97706); }
.avatar { width: 34px; height: 34px; border-radius: 50%; background: var(--c-primary-soft, #e7f6ec); display: flex; align-items: center; justify-content: center; font-size: 15px; font-weight: 800; color: var(--c-primary-strong, #15803d); flex: none; }

.body-wrap { display: flex; flex: 1; align-items: stretch; min-width: 0; }
.sider {
  width: 240px; flex-shrink: 0; background: var(--c-surface, #fff);
  border-right: 1px solid var(--c-line, #e5efe9); padding: 16px 12px;
  display: flex; flex-direction: column; overflow: hidden;
  transition: width 0.18s ease, padding 0.18s ease;
}
.sider :deep(.nav) { flex: 1; }
.sider-toggle {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  align-self: flex-end; flex: none; margin: 0 0 10px;
  min-height: 32px; padding: 4px 10px;
  background: var(--c-surface, #fff); color: var(--c-text-2, #6b7f74);
  border: 1px solid var(--c-line, #e5efe9); border-radius: 10px;
  font: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.sider-toggle:hover {
  background: var(--c-mint-bg, #f2faf5); color: var(--c-text, #1f2d26);
  border-color: var(--c-line-strong, #d3e0d8);
}
.sider-toggle:focus-visible { outline: 3px solid var(--c-primary, #16a34a); outline-offset: 2px; }
.sider.collapsed { width: 74px; padding: 14px 8px; align-items: center; }
.sider.collapsed .sider-toggle { align-self: center; padding: 6px; }
.sider.collapsed :deep(.sider-title),
.sider.collapsed :deep(.sider-foot),
.sider.collapsed :deep(.s-txt),
.sider.collapsed :deep(.n-name) { display: none; }
.sider.collapsed :deep(.subj) { justify-content: center; padding: 8px; }
.sider.collapsed :deep(.nav-item) { justify-content: center; padding: 10px 0; }
.sider.collapsed :deep(.divider) { width: 100%; }

/* 内容区：外框负责内边距，.stack 负责宽度 */
.main {
  flex: 1; min-width: 0; display: flex; justify-content: center;
  padding: 22px max(28px, env(safe-area-inset-right, 0px)) calc(56px + env(safe-area-inset-bottom, 0px)) max(28px, env(safe-area-inset-left, 0px));
}
.stack { width: 100%; max-width: 960px; min-width: 0; }
.main.w-narrow .stack { max-width: 720px; }

/* 麦克风开启：右侧给数字人让出约 1/3 宽，内容整体左移而不是被盖住 */
.main { transition: padding-right 0.25s ease, padding-bottom 0.25s ease; }
.main.mic-on { padding-right: calc(clamp(320px, 33vw, 420px) + 32px); }

.crumb { font-size: 13px; color: var(--c-text-2, #6b7f74); margin-bottom: 10px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.crumb b { color: var(--c-primary-strong, #15803d); }
.crumb a { color: var(--c-text-2, #6b7f74); text-decoration: none; border-radius: 4px; }
.crumb a:hover { color: var(--c-primary-strong, #15803d); text-decoration: underline; }
.crumb a:focus-visible { outline: 3px solid var(--c-primary, #16a34a); outline-offset: 2px; }
.sep { color: var(--c-line, #cfe0d5); }

.tabs-wrap {
  position: sticky; top: calc(56px + env(safe-area-inset-top, 0px)); z-index: 12;
  margin-bottom: 18px; padding: 4px 0;
  background: var(--c-bg);
  overflow-x: auto; scrollbar-width: none; -ms-overflow-style: none;
}
.tabs-wrap::-webkit-scrollbar { display: none; }
.tabs3 {
  display: inline-flex; background: var(--c-surface, #fff); border: 1px solid var(--c-line, #e5efe9);
  border-radius: 999px; padding: 4px; gap: 2px; box-shadow: var(--shadow-sm, 0 2px 10px rgba(22, 163, 74, 0.08));
  white-space: nowrap;
}
.tabs3 .t {
  padding: 8px 20px; border-radius: 999px; font-size: 14px; font-weight: 600;
  color: var(--c-text-2, #6b7f74); text-decoration: none; white-space: nowrap; flex: none;
  min-height: 38px; display: inline-flex; align-items: center; transition: background 0.15s, color 0.15s;
}
.tabs3 .t:hover { color: var(--c-text, #1f2d26); background: var(--c-mint-bg, #f2faf5); }
.tabs3 .t.active { background: var(--c-primary-strong, #15803d); color: #fff; }

/* ---------- 平板：允许手动展开（默认按 900px 阈值收起），只收紧内容内边距 ---------- */
@media (max-width: 1023px) {
  .main {
    padding: 18px max(20px, env(safe-area-inset-right, 0px)) calc(48px + env(safe-area-inset-bottom, 0px)) max(20px, env(safe-area-inset-left, 0px));
  }
  .main.mic-on { padding-right: 324px; }
}

/* 手机 / 竖屏平板：数字人在底部，内容向上留出空间 */
@media (max-width: 899px) {
  .main.mic-on { padding-right: 20px; padding-bottom: calc(38vh + 30px); }
}

/* ---------- 手机：侧栏改抽屉 ---------- */
@media (max-width: 767px) {
  .sider { display: none; }
  .menu-btn { display: inline-flex; }
  .topbar {
    height: calc(52px + env(safe-area-inset-top, 0px));
    padding: env(safe-area-inset-top, 0px) max(12px, env(safe-area-inset-right, 0px)) 0 max(12px, env(safe-area-inset-left, 0px));
    gap: 8px;
  }
  .logo { font-size: 16px; }
  .logo-txt { display: none; }
  .uname { display: none; }
  .userbtn { padding-right: 8px; gap: 5px; }
  .userbtn.dev { padding-left: 5px; gap: 7px; }
  .main {
    padding: 14px max(14px, env(safe-area-inset-right, 0px)) calc(40px + env(safe-area-inset-bottom, 0px)) max(14px, env(safe-area-inset-left, 0px));
  }
  /* 底部二级导航固定时，内容区让出栏高 + 一点呼吸空间 */
  .main.has-tabbar { padding-bottom: calc(76px + env(safe-area-inset-bottom, 0px)); }
  .crumb { font-size: 12.5px; }
  .tabs-wrap { top: calc(52px + env(safe-area-inset-top, 0px)); }
  .tabs3 .t { padding: 8px 16px; font-size: 14px; }
}
</style>
