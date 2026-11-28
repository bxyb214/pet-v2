<template>
  <section class="empty-mod">
    <div class="ico" aria-hidden="true"><n-icon :component="icon" size="38" /></div>
    <h2>{{ examName }} · {{ moduleName }}内容整理中</h2>
    <p>{{ message }}</p>
    <div class="acts">
      <router-link class="btn solid" to="/english/words/browse">去单词词库</router-link>
      <router-link class="btn" to="/">回首页</router-link>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NIcon } from "naive-ui";
import { CreateOutline, HeadsetOutline, LanguageOutline, LibraryOutline, MicOutline } from "@vicons/ionicons5";
import { useAuthStore } from "../stores/auth";

/** 级别没有该板块内容时统一显示的空状态。 */
const props = defineProps<{ module: string }>();
const auth = useAuthStore();

const NAMES: Record<string, string> = {
  words: "单词", reading: "阅读", grammar: "语法", listening: "听力", speak: "口语",
};
const ICONS = {
  words: LanguageOutline, reading: LibraryOutline, grammar: CreateOutline,
  listening: HeadsetOutline, speak: MicOutline,
};
const EXAM_NAMES: Record<string, string> = {
  pet: "PET", ket: "KET", fce: "FCE", junior: "初中英语",
};

const moduleName = computed(() => NAMES[props.module] ?? "该板块");
const examName = computed(() => EXAM_NAMES[auth.exam] ?? "当前级别");
const icon = computed(() => ICONS[props.module as keyof typeof ICONS] ?? LanguageOutline);
const message = computed(() =>
  auth.exam === "ket"
    ? "KET 目前有词库、阅读（含语法）、听力和口语，这个板块还没有内容。"
    : `${examName.value} 的内容还没有整理好，先到单词板块学习吧。`,
);
</script>

<style scoped>
.empty-mod {
  margin: 24px auto;
  max-width: 560px;
  padding: 56px 28px;
  text-align: center;
  background: var(--c-surface, #fff);
  border: 1px solid var(--c-line, #e5efe9);
  border-radius: 20px;
}
.ico {
  width: 72px; height: 72px; margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 22px;
  background: var(--c-primary-soft, #e7f6ec);
  color: var(--c-primary-strong, #15803d);
}
h2 { margin: 0 0 10px; font-size: 21px; color: var(--c-text, #1f2d26); }
p { margin: 0; color: var(--c-text-2, #6b7f74); line-height: 1.7; font-size: 14px; }
.acts { display: flex; gap: 10px; justify-content: center; margin-top: 22px; flex-wrap: wrap; }
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  min-height: 40px; padding: 0 18px; border-radius: 12px;
  border: 1px solid var(--c-line, #e5efe9); background: #fff;
  color: var(--c-text, #1f2d26); text-decoration: none; font-weight: 600; font-size: 14px;
}
.btn.solid {
  background: var(--c-primary, #16a34a);
  border-color: var(--c-primary, #16a34a);
  color: #fff;
}
.btn:hover { border-color: var(--c-primary, #16a34a); }
</style>
