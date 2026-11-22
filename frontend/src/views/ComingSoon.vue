<template>
  <main class="page">
    <div class="card soon">
      <div class="big">{{ meta.icon }}</div>
      <h2>{{ meta.title }} · 敬请期待</h2>
      <p>板块正在筹备，内容规划好后第一时间上线</p>
      <div class="tags">
        <span v-for="t in meta.tags" :key="t" class="tag">{{ t }}</span>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const meta = computed(() => ({
  title: (route.meta.title as string) ?? "板块",
  icon: (route.meta.icon as string) ?? "📚",
  tags: (route.meta.tags as string[]) ?? [],
}));
</script>

<style scoped>
.page { width: 100%; }
.soon { padding: 70px 24px; text-align: center; }
.big { font-size: 54px; margin-bottom: 14px; }
h2 { font-size: 24px; margin: 0 0 8px; color: var(--c-text, #1f2d26); }
p { color: var(--c-text-2, #6b7f74); }
.tags { display: flex; gap: 10px; justify-content: center; margin-top: 18px; flex-wrap: wrap; }
.tag { background: var(--c-primary-soft, #e7f6ec); color: var(--c-primary-strong, #15803d); border-radius: 999px; padding: 6px 16px; font-size: 13px; font-weight: 600; }
</style>
