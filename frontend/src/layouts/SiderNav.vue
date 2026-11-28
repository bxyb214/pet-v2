<template>
  <nav class="nav">
    <router-link
      to="/"
      class="nav-item home"
      :class="{ active: route.path === '/' }"
      title="首页"
      :aria-current="route.path === '/' ? 'page' : undefined"
      @click="emit('go')"
    >
      <span class="n-ico"><n-icon :component="HomeOutline" size="19" /></span>
      <span class="n-name">首页</span>
    </router-link>
    <div class="sider-title">学科</div>
    <router-link
      v-for="s in subjects"
      :key="s.key"
      :to="s.first"
      class="subj"
      :class="[s.cls, { active: subject === s.key }]"
      :title="s.name"
      :aria-current="subject === s.key ? 'true' : undefined"
      @click="emit('go')"
    >
      <span class="s-ico"><n-icon :component="s.icon" size="20" /></span>
      <span class="s-txt">
        <b class="s-name">{{ s.name }}</b>
        <i class="s-sub">{{ s.desc }}</i>
      </span>
    </router-link>

    <template v-if="showModules && subject === 'english'">
      <div class="divider"></div>
      <div class="sider-title">英语 · 板块</div>
      <router-link
        v-for="m in enModules"
        :key="m.key"
        :to="m.first"
        class="nav-item"
        :class="{ active: module === m.key }"
        :title="m.name"
        :aria-current="module === m.key ? 'true' : undefined"
        @click="emit('go')"
      >
        <span class="n-ico"><n-icon :component="m.icon" size="19" /></span>
        <span class="n-name">{{ m.name }}</span>
      </router-link>
    </template>

    <template v-if="showModules && subject === 'math'">
      <div class="divider"></div>
      <div class="sider-title">数学 · 板块</div>
      <router-link
        v-for="m in MATH_MODULES"
        :key="m.key"
        :to="m.first"
        class="nav-item"
        :class="{ active: module === m.key }"
        :title="m.name"
        :aria-current="module === m.key ? 'true' : undefined"
        @click="emit('go')"
      >
        <span class="n-ico"><n-icon :component="m.icon" size="19" /></span>
        <span class="n-name">{{ m.name }}</span>
      </router-link>
    </template>

    <div class="sider-foot">火焰学习 · 每天进步一点点</div>
  </nav>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router";
import { computed } from "vue";
import { NIcon } from "naive-ui";
import { HomeOutline } from "@vicons/ionicons5";
import { useAuthStore } from "../stores/auth";
import { MATH_MODULES, SUBJECTS, modulesForSubject } from "./navModules";

/** 手机抽屉只放一级导航（首页 + 学科），二级板块交给底部导航栏 */
withDefaults(defineProps<{ showModules?: boolean }>(), { showModules: true });

const emit = defineEmits<{ (e: "go"): void }>();
const route = useRoute();
const auth = useAuthStore();

/** 侧栏副标题跟随「我在备考」的级别 */
const EXAM_LABEL: Record<string, string> = {
  pet: "PET 备考进行中",
  ket: "KET 备考进行中",
  fce: "FCE 备考进行中",
  junior: "初中英语同步",
};
const subjects = computed(() =>
  SUBJECTS.map((s) =>
    s.key === "english" ? { ...s, desc: EXAM_LABEL[auth.exam] ?? "PET 备考进行中" } : s,
  ),
);

const subject = computed(() => (route.meta.subject as string | undefined) ?? "");
const module = computed(() => (route.meta.module as string | undefined) ?? "");
/** KET 已开放单词/阅读/听力；按级别过滤后，没内容的板块不显示 */
const enModules = computed(() => modulesForSubject("english", auth.exam));
</script>

<style scoped>
.nav { display: flex; flex-direction: column; gap: 6px; }
.sider-title { font-size: 12px; color: var(--c-text-2, #6b7f74); font-weight: 600; letter-spacing: 2px; margin: 4px 8px 6px; }
.subj {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px;
  cursor: pointer; border: 1.5px solid transparent; background: none; font: inherit;
  text-align: left; width: 100%; text-decoration: none;
  transition: background 0.15s, border-color 0.15s;
}
.subj .s-ico {
  width: 38px; height: 38px; border-radius: 12px; display: flex; align-items: center;
  justify-content: center; flex-shrink: 0;
}
.subj .s-txt { display: flex; flex-direction: column; min-width: 0; }
.subj .s-name { font-weight: 700; font-size: 15px; color: var(--c-text, #1f2d26); }
.subj .s-sub { font-size: 11px; color: var(--c-text-2, #6b7f74); font-style: normal; }
.subj.en .s-ico { background: var(--c-primary-soft, #e7f6ec); color: var(--c-primary-strong, #15803d); }
.subj.cn .s-ico { background: #fef3c7; color: #b45309; }
.subj.ma .s-ico { background: #dbeafe; color: #1d4ed8; }
.subj.active { background: var(--c-primary-soft, #e7f6ec); border-color: var(--c-primary, #16a34a); }
.subj.active.en .s-ico { background: var(--c-primary, #16a34a); color: #fff; }
.subj.cn.active { background: #fef3c7; border-color: #d97706; }
.subj.cn.active .s-ico { background: #d97706; color: #fff; }
.subj.ma.active { background: #dbeafe; border-color: #2563eb; }
.subj.ma.active .s-ico { background: #2563eb; color: #fff; }
.divider { height: 1px; background: var(--c-line, #e5efe9); margin: 10px 6px; }
.nav-item {
  display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-radius: 12px;
  cursor: pointer; color: var(--c-text-2, #6b7f74); font-weight: 600; transition: all 0.12s;
  border: 1.5px solid transparent; background: none; font: inherit; width: 100%; text-align: left;
  font-size: 15px; min-height: 46px; text-decoration: none;
}
.nav-item .n-ico { display: inline-flex; align-items: center; flex-shrink: 0; }
.nav-item:hover { background: var(--c-mint-bg, #f2faf5); color: var(--c-text, #1f2d26); }
.nav-item.active { background: var(--c-primary-soft, #e7f6ec); color: var(--c-primary-strong, #15803d); border-color: var(--c-primary, #16a34a); }
.sider-foot { margin-top: auto; font-size: 11px; color: var(--c-text-2, #6b7f74); text-align: center; padding: 10px; }
</style>
