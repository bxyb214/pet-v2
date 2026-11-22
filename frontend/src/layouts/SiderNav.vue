<template>
  <nav class="nav">
    <div class="sider-title">学科</div>
    <button
      v-for="s in subjects"
      :key="s.key"
      class="subj"
      :class="[s.key, { active: subject === s.key }]"
      :title="s.name"
      @click="pick(s)"
    >
      <span class="s-ico"><n-icon :component="s.icon" size="20" /></span>
      <span class="s-txt">
        <b class="s-name">{{ s.name }}</b>
        <i class="s-sub">{{ s.desc }}</i>
      </span>
    </button>

    <template v-if="subject === 'english'">
      <div class="divider"></div>
      <div class="sider-title">英语 · 板块</div>
      <button
        v-for="m in EN_MODULES"
        :key="m.key"
        class="nav-item"
        :class="{ active: module === m.key }"
        :title="m.name"
        @click="goModule(m)"
      >
        <span class="n-ico"><n-icon :component="m.icon" size="19" /></span>
        <span class="n-name">{{ m.name }}</span>
      </button>
    </template>

    <div class="sider-foot">绿野成长 · 每天进步一点点</div>
  </nav>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { computed } from "vue";
import { NIcon } from "naive-ui";
import {
  LanguageOutline, BookOutline, CalculatorOutline,
  ReaderOutline, LibraryOutline, HeadsetOutline, MicOutline,
} from "@vicons/ionicons5";
import type { Component } from "vue";
import { useAuthStore } from "../stores/auth";

type Module = { key: string; name: string; icon: Component; first: string };
type Subject = { key: "english" | "chinese" | "math"; name: string; icon: Component; desc: string; first: string };

const SUBJECTS: Subject[] = [
  { key: "english", name: "英语", icon: LanguageOutline, desc: "", first: "/english/words/browse" },
  { key: "chinese", name: "语文", icon: BookOutline, desc: "筹备中", first: "/chinese" },
  { key: "math", name: "数学", icon: CalculatorOutline, desc: "筹备中", first: "/math" },
];

const EN_MODULES: Module[] = [
  { key: "words", name: "单词", icon: ReaderOutline, first: "/english/words/browse" },
  { key: "reading", name: "阅读", icon: LibraryOutline, first: "/english/reading/home" },
  { key: "listening", name: "听力", icon: HeadsetOutline, first: "/english/listening/home" },
  { key: "speak", name: "口语", icon: MicOutline, first: "/english/speak" },
];

const emit = defineEmits<{ (e: "go"): void }>();
const route = useRoute();
const router = useRouter();
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

const subject = computed(() => (route.meta.subject as string | undefined) ?? "english");
const module = computed(() => (route.meta.module as string | undefined) ?? "");

function pick(s: Subject): void {
  void router.push(s.first);
  emit("go");
}
function goModule(m: Module): void {
  void router.push(m.first);
  emit("go");
}
</script>

<style scoped>
.nav { display: flex; flex-direction: column; gap: 6px; }
.sider-title { font-size: 12px; color: var(--c-text-2, #6b7f74); font-weight: 600; letter-spacing: 2px; margin: 4px 8px 6px; }
.subj {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 12px;
  cursor: pointer; border: 1.5px solid transparent; background: none; font: inherit;
  text-align: left; width: 100%; transition: background 0.15s, border-color 0.15s;
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
  font-size: 15px; min-height: 46px;
}
.nav-item .n-ico { display: inline-flex; align-items: center; flex-shrink: 0; }
.nav-item:hover { background: var(--c-mint-bg, #f2faf5); color: var(--c-text, #1f2d26); }
.nav-item.active { background: var(--c-primary-soft, #e7f6ec); color: var(--c-primary-strong, #15803d); border-color: var(--c-primary, #16a34a); }
.sider-foot { margin-top: auto; font-size: 11px; color: var(--c-text-2, #6b7f74); text-align: center; padding: 10px; }
</style>
