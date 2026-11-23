<template>
  <main class="page">
    <BackButton />
    <h1>场景题库</h1>
    <p class="sub">PET 真题场景共 {{ total }} 个，按 Part 分类；每日计划里也会列出当天的场景。</p>

    <div class="filters">
      <button
        v-for="f in filters" :key="f.id"
        class="fbtn" :class="{ on: part === f.id }"
        @click="part = f.id"
      >{{ f.name }} <span class="cnt">{{ countOf(f.id) }}</span></button>
      <input v-model="q" class="search" type="search" placeholder="搜索场景 / 中文" />
    </div>

    <div v-if="loading" class="card empty">加载中…</div>
    <template v-else>
      <section v-for="grp in groups" :key="grp.part" class="group">
        <div class="ghead">Part {{ grp.part }} · {{ grp.title }} <span class="gcount">{{ grp.items.length }}</span></div>
        <div class="grid">
          <button v-for="s in grp.items" :key="s.id" class="scene card" @click="practice(s)">
            <span class="st">{{ s.title }}</span>
            <span class="scn">{{ s.cn }}</span>
            <span class="sf">{{ s.focus }}</span>
            <span class="sl">{{ s.level }}</span>
            <span class="go">练这个场景 →</span>
          </button>
        </div>
      </section>
      <div v-if="!groups.length" class="card empty">没有匹配的场景</div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { loadSpeak, type Scene, type SpeakData } from "../core/speak";
import BackButton from "../components/BackButton.vue";

const router = useRouter();
const data = ref<SpeakData | null>(null);
const loading = ref(true);
const part = ref<number | 0>(0);
const q = ref("");

const PART_TITLES: Record<number, string> = {
  1: "个人信息与日常问答",
  2: "图片描述",
  3: "讨论协商",
  4: "扩展讨论",
};
const filters = [
  { id: 0, name: "全部" },
  { id: 1, name: "Part 1" },
  { id: 2, name: "Part 2" },
  { id: 3, name: "Part 3" },
  { id: 4, name: "Part 4" },
];

const scenes = computed<Scene[]>(() => data.value?.scenes ?? []);
const total = computed(() => scenes.value.length);

function countOf(id: number): number {
  return id === 0 ? scenes.value.length : scenes.value.filter((s) => s.part === id).length;
}

const groups = computed(() => {
  const needle = q.value.trim().toLowerCase();
  const filtered = scenes.value.filter((s) => {
    if (part.value !== 0 && s.part !== part.value) return false;
    if (!needle) return true;
    return `${s.title} ${s.cn} ${s.focus}`.toLowerCase().includes(needle);
  });
  const byPart = new Map<number, Scene[]>();
  for (const s of filtered) {
    if (!byPart.has(s.part)) byPart.set(s.part, []);
    byPart.get(s.part)!.push(s);
  }
  return [...byPart.entries()]
    .sort(([a], [b]) => a - b)
    .map(([p, items]) => ({ part: p, title: PART_TITLES[p] ?? "其他", items }));
});

onMounted(async () => {
  try {
    data.value = await loadSpeak();
  } finally {
    loading.value = false;
  }
});

function practice(s: Scene): void {
  void router.push(`/english/speak/talk?scene=${encodeURIComponent(s.id)}`);
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.filters { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 16px; }
.fbtn {
  border: 1px solid var(--c-line); background: var(--c-surface); color: var(--c-text);
  border-radius: 999px; padding: 7px 14px; font: inherit; font-size: var(--fs-sub);
  font-weight: 600; cursor: pointer;
}
.fbtn.on { background: var(--c-primary-strong); border-color: var(--c-primary-strong); color: #fff; }
.cnt { opacity: 0.75; font-weight: 400; margin-left: 2px; }
.search {
  flex: 1; min-width: 180px; max-width: 320px;
  border: 1px solid var(--c-line); border-radius: 999px; padding: 8px 14px;
  font: inherit; font-size: var(--fs-sub); color: var(--c-text); background: var(--c-surface);
}
.group { margin-bottom: 18px; }
.ghead { font-weight: 800; color: var(--c-text); margin-bottom: 8px; }
.gcount { color: var(--c-text-2); font-weight: 400; font-size: var(--fs-sub); margin-left: 4px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.scene {
  text-align: left; padding: 12px; cursor: pointer; border: 1px solid var(--c-line);
  background: var(--c-surface); border-radius: var(--r-card); display: flex; flex-direction: column; gap: 4px;
  transition: border-color var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out);
}
.scene:hover { border-color: var(--c-primary); transform: translateY(-1px); }
.st { color: var(--c-text); font-weight: 700; }
.scn { color: var(--c-text-2); font-size: var(--fs-sub); }
.sf { color: var(--c-text-3); font-size: 12.5px; line-height: 1.5; }
.sl { align-self: flex-start; background: var(--c-mint-bg); color: var(--c-primary-strong); border-radius: 999px; padding: 1px 8px; font-size: 12px; }
.go { color: var(--c-primary-strong); font-size: 13px; font-weight: 700; margin-top: 4px; }
.empty { padding: 32px; text-align: center; color: var(--c-text-2); }
</style>
