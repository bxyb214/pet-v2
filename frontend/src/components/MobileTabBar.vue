<template>
  <nav v-if="modules.length" class="tabbar" :aria-label="`${subjectName}板块导航`">
    <router-link
      v-for="m in modules"
      :key="m.key"
      :to="m.first"
      class="tb"
      :class="{ active: isActive(m.key) }"
      :title="m.name"
      :aria-current="isActive(m.key) ? 'page' : undefined"
    >
      <span class="tb-ico"><n-icon :component="m.icon" size="21" /></span>
      <span class="tb-name">{{ m.name }}</span>
    </router-link>
  </nav>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { NIcon } from "naive-ui";
import { modulesForSubject } from "../layouts/navModules";

/**
 * 手机（≤767px）底部二级导航：当前学科的板块（单词/阅读/…）。
 * 桌面和平板不渲染；无板块（首页、语文）也不渲染。
 */
const route = useRoute();
const modules = computed(() => modulesForSubject(route.meta.subject));
const subjectName = computed(() => (route.meta.subject === "math" ? "数学" : "英语"));
const current = computed(() => route.meta.module ?? "");

function isActive(key: string): boolean {
  return current.value === key;
}
</script>

<style scoped>
.tabbar {
  display: none;
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 30;
  align-items: stretch; justify-content: center;
  padding: 6px max(8px, env(safe-area-inset-right, 0px)) calc(6px + env(safe-area-inset-bottom, 0px)) max(8px, env(safe-area-inset-left, 0px));
  background: var(--c-surface, #fff);
  border-top: 1px solid var(--c-line, #e6eee9);
  box-shadow: 0 -6px 18px rgba(16, 40, 28, 0.06);
}
.tb {
  flex: 1 1 0; min-width: 0; max-width: 110px; min-height: 52px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
  padding: 3px 2px; border-radius: 12px;
  color: var(--c-text-2, #64756c); text-decoration: none; font-weight: 600;
  -webkit-tap-highlight-color: transparent;
}
.tb-ico {
  width: 46px; height: 28px; border-radius: 999px;
  display: inline-flex; align-items: center; justify-content: center;
  transition: background 0.15s ease, color 0.15s ease;
}
.tb-name { font-size: 11.5px; line-height: 1.2; letter-spacing: 0.2px; white-space: nowrap; }
.tb:active .tb-ico { background: var(--c-mint-bg, #f2faf5); }
.tb.active { color: var(--c-primary-strong, #15803d); }
.tb.active .tb-ico { background: var(--c-primary-soft, #e7f6ec); }
.tb:focus-visible { outline: 3px solid var(--c-primary, #16a34a); outline-offset: -2px; }

@media (max-width: 767px) {
  .tabbar { display: flex; }
}
</style>
