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
        <span class="leaf">🔥</span>
        <span class="logo-txt">火焰学习</span>
      </router-link>
      <div class="spacer"></div>
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
      <!-- 桌面/平板侧栏 -->
      <aside class="sider">
        <SiderNav />
      </aside>

      <!-- 内容区：面包屑 + 页签 + 页面，统一同一宽度容器 -->
      <main class="main" :class="[widthClass, { 'mic-on': micActive }]">
        <div class="stack">
          <div v-if="crumbs.length" class="crumb">
            <template v-for="(c, i) in crumbs" :key="i">
              <span v-if="i" class="sep">/</span>
              <b v-if="i === crumbs.length - 1">{{ c }}</b>
              <span v-else>{{ c }}</span>
            </template>
          </div>

          <div v-if="route.meta.tabs?.length" class="tabs-wrap">
            <nav class="tabs3">
              <router-link
                v-for="t in route.meta.tabs"
                :key="t.to"
                :to="t.to"
                class="t"
                :class="{ active: isActiveTab(t.to) }"
              >{{ t.label }}</router-link>
            </nav>
          </div>

          <router-view />
        </div>
      </main>
    </div>

    <!-- 麦克风占用期间的数字人：固定在右侧 1/3，关闭按钮在数字人下方 -->
    <MicCompanion v-if="micActive" />

    <!-- 手机抽屉导航 -->
    <n-drawer v-model:show="drawer" placement="left" :width="264">
      <n-drawer-content body-content-style="padding: 16px 12px">
        <SiderNav @go="drawer = false" />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref, type Component } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NDrawer, NDrawerContent, NDropdown, NIcon, type DropdownOption } from "naive-ui";
import { LogOutOutline, SettingsOutline, ShieldCheckmarkOutline } from "@vicons/ionicons5";
import SiderNav from "./SiderNav.vue";
import MicCompanion from "../components/MicCompanion.vue";
import { useAuthStore } from "../stores/auth";
import { devMode, ensureDevMode } from "../core/devMode";
import { micActive } from "../core/micPresence";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const drawer = ref(false);

onMounted(() => {
  void ensureDevMode();
});

/** 内容宽度三档（唯一来源，页面内不再自己设宽） */
const widthClass = computed(() => {
  const w = route.meta.width;
  return w ? `w-${w}` : "";
});

/** 有页签的页面，当前页已由页签表达，面包屑只保留学科/板块两级，避免同一信息占两行 */
const crumbs = computed(() => {
  const c = route.meta.crumbs;
  if (!c?.length) return [];
  return route.meta.tabs?.length && c.length > 2 ? c.slice(0, -1) : c;
});

function isActiveTab(to: string): boolean {
  return route.path === to || route.path.startsWith(to + "/");
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
    { key: "settings", label: "设置", icon: renderIcon(SettingsOutline) },
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
  else if (key === "admin") void router.push("/admin");
  else if (key === "logout") logout();
}

function logout(): void {
  auth.logout();
  void router.push("/login");
}
</script>

<style scoped>
.shell { min-height: 100vh; display: flex; flex-direction: column; background: var(--c-bg, #f7faf8); }
.topbar {
  height: 56px; display: flex; align-items: center; gap: 12px; padding: 0 20px;
  background: var(--c-surface, #fff); border-bottom: 1px solid var(--c-line, #e5efe9);
  position: sticky; top: 0; z-index: 20;
}
.menu-btn { display: none; border: 1px solid var(--c-line, #e5efe9); background: #fff; border-radius: 10px; width: 38px; height: 38px; align-items: center; justify-content: center; color: var(--c-text, #1f2d26); cursor: pointer; flex: none; }
.logo { font-weight: 800; font-size: 18px; color: var(--c-primary-strong, #15803d); display: flex; align-items: center; gap: 8px; text-decoration: none; white-space: nowrap; }
.leaf { width: 30px; height: 30px; border-radius: 10px; background: linear-gradient(135deg, #22c55e, #16a34a); display: flex; align-items: center; justify-content: center; font-size: 16px; flex: none; }
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
.sider { width: 240px; flex-shrink: 0; background: var(--c-surface, #fff); border-right: 1px solid var(--c-line, #e5efe9); padding: 16px 12px; display: flex; flex-direction: column; }
.sider :deep(.nav) { flex: 1; }

/* 内容区：外框负责内边距，.stack 负责宽度 */
.main { flex: 1; min-width: 0; padding: 22px 28px 56px; display: flex; justify-content: center; }
.stack { width: 100%; max-width: 960px; min-width: 0; }
.main.w-narrow .stack { max-width: 720px; }

/* 麦克风开启：右侧给数字人让出约 1/3 宽，内容整体左移而不是被盖住 */
.main { transition: padding-right 0.25s ease, padding-bottom 0.25s ease; }
.main.mic-on { padding-right: calc(clamp(320px, 33vw, 420px) + 32px); }

.crumb { font-size: 13px; color: var(--c-text-2, #6b7f74); margin-bottom: 10px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.crumb b { color: var(--c-primary-strong, #15803d); }
.sep { color: var(--c-line, #cfe0d5); }

.tabs-wrap { margin-bottom: 18px; overflow-x: auto; scrollbar-width: none; -ms-overflow-style: none; }
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

/* ---------- 平板：侧栏收成图标条 ---------- */
@media (max-width: 1023px) {
  .sider { width: 74px; padding: 14px 8px; align-items: center; }
  .sider :deep(.sider-title),
  .sider :deep(.sider-foot),
  .sider :deep(.s-txt),
  .sider :deep(.n-name) { display: none; }
  .sider :deep(.subj) { justify-content: center; padding: 8px; }
  .sider :deep(.nav-item) { justify-content: center; padding: 10px 0; }
  .sider :deep(.divider) { width: 100%; }
  .main { padding: 18px 20px 48px; }
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
  .topbar { padding: 0 12px; gap: 8px; height: 52px; }
  .logo { font-size: 16px; }
  .logo-txt { display: none; }
  .uname { display: none; }
  .userbtn { padding-right: 8px; gap: 5px; }
  .userbtn.dev { padding-left: 5px; gap: 7px; }
  .main { padding: 14px 14px 40px; }
  .crumb { font-size: 12.5px; }
  .tabs3 .t { padding: 8px 16px; font-size: 14px; }
}
</style>
