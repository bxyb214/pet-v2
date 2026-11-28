<template>
  <main class="page">
    <h1>阅读精读</h1>
    <p class="sub" v-if="data">{{ data.meta.sentences }} 句 · {{ totalTests }} 套 · 按 Part 精读，或整套测</p>

    <!-- 错题复习入口 -->
    <n-alert v-if="dueCount" type="warning" class="review-card" :bordered="false">
      <div class="card-h">
        <span>📖 阅读错题复习 · <b>{{ dueCount }}</b> 题维度到期</span>
        <n-button type="warning" size="small" @click="startReview">开始复习</n-button>
      </div>
    </n-alert>

    <!-- 教材分组 -->
    <section v-for="b in bookGroups" :key="b.id" class="fold">
      <button class="fold-h" :aria-expanded="!!openMap[b.id]" @click="toggle(b.id)">
        <svg class="chev" :class="{ open: openMap[b.id] }" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6" /></svg>
        <span class="fold-t">
          <b>{{ b.name }}</b>
          <span class="desc">{{ b.desc }}</span>
        </span>
        <span class="meta">{{ b.testCount }} 套 · {{ b.sentCount }} 句</span>
        <span class="fold-act">{{ openMap[b.id] ? "收起" : "展开" }}</span>
      </button>
      <div class="fold-b" :class="{ open: openMap[b.id] }">
        <div class="fold-inner">
          <div v-for="t in b.tests" :key="t.no" class="card testcard">
            <div class="card-h">
              <div>
                <p class="title">{{ t.title }} <span class="muted">· {{ testSentences(t).length }} 句</span></p>
                <p v-if="t.note" class="desc">{{ t.note }}</p>
              </div>
              <n-button type="primary" size="small" @click="startQuiz(t.no, 0)">测整套</n-button>
            </div>
            <div class="parts">
              <div v-for="p in t.parts" :key="p.part" class="partrow">
                <div class="pl">
                  <span class="pno">Part {{ p.part }}</span>
                  <span class="pkind long">{{ p.kind }}</span>
                  <span class="pkind short">{{ shortKind(p.kind) }}</span>
                  <span class="pn">{{ p.sentences.length }} 句</span>
                </div>
                <div class="pact">
                  <n-button secondary size="small" @click="startStudy(t.no, p.part)">学习</n-button>
                  <n-button size="small" @click="startQuiz(t.no, p.part)">测验</n-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 加句：操作入口放浮动按钮，不占页签 -->
    <router-link to="/english/reading/add" class="fab">＋ 加句</router-link>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { NAlert, NButton } from "naive-ui";
import { useLearningStore } from "../stores/learning";
import { useAuthStore } from "../stores/auth";
import {
  loadReading, testSentences, withCustomSentences,
  type ReadingData, type RTest,
} from "../core/reading";

const router = useRouter();
const learning = useLearningStore();
const auth = useAuthStore();
const data = ref<ReadingData | null>(null);
const openMap = reactive<Record<string, boolean>>({});
onMounted(async () => {
  const base = await loadReading(auth.exam);
  data.value = withCustomSentences(base, learning.data.custom_sentences);
  // 只有 1 本书时默认展开，多本默认收起（05 规范）
  const books = data.value.books.filter((b) => data.value!.tests.some((t) => (t.book || "t2") === b.id));
  if (books.length === 1) openMap[books[0].id] = true;
});

// R8 到期错题数（按句子维度）
const dueCount = computed(() => {
  const today = new Date().toISOString().slice(0, 10);
  return learning.data.mistakes.filter((m) => m.dims.length && m.due_at && m.due_at <= today).length;
});

function startReview(): void {
  void router.push({ path: "/english/reading/quiz/0", query: { review: "1" } });
}

const totalTests = computed(() => data.value?.tests.length ?? 0);

const bookGroups = computed(() => {
  const d = data.value;
  if (!d) return [];
  return d.books
    .filter((b) => d.tests.some((t) => (t.book || "t2") === b.id))
    .map((b) => {
      const tests = d.tests.filter((t) => (t.book || "t2") === b.id);
      return {
        ...b, tests,
        testCount: tests.length,
        sentCount: tests.reduce((a, t) => a + testSentences(t).length, 0),
      };
    });
});

function toggle(id: string): void {
  openMap[id] = !openMap[id];
}

/** 窄屏用的短标签：去掉括号里的补充说明（"七选五（句子还原）" → "七选五"），保证一行放得下 */
function shortKind(kind: string): string {
  return kind.replace(/（[^）]*）/g, "").trim() || kind;
}

function startStudy(testNo: number, part: number): void {
  void router.push(`/english/reading/study/${testNo}/${part}`);
}

function startQuiz(testNo: number, part: number): void {
  void router.push({ path: `/english/reading/quiz/${testNo}`, query: part ? { part: String(part) } : {} });
}

</script>

<style scoped>
.page { width: 100%; }
h1 { font-size: var(--fs-display); font-weight: 800; letter-spacing: .2px; color: var(--c-text); margin: 0 0 4px; }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 16px; }
.review-card { margin-bottom: 14px; }
.review-card .card-h { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.card { background: var(--c-card); border-radius: var(--r-card); box-shadow: var(--shadow-card); padding: 16px; margin-bottom: 14px; }
.card-h { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.title { font-size: var(--fs-title); font-weight: 500; margin: 0 0 2px; }
.muted { color: var(--c-text-2); font-weight: 400; font-size: var(--fs-sub); }
.desc { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0; }
.btn { background: var(--c-primary); color: #fff; border: 0; border-radius: var(--r-btn); padding: 10px 18px; font-size: var(--fs-body); min-height: 44px; cursor: pointer; white-space: nowrap; }

/* 悬浮「加句」入口（加句是操作，不占页签） */
.fab {
  position: fixed; right: 26px; bottom: 30px; z-index: 15;
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--c-primary); color: #fff; text-decoration: none;
  padding: 12px 18px; border-radius: 999px; font-weight: 700; font-size: 14.5px;
  box-shadow: 0 8px 22px rgba(22, 163, 74, 0.28);
}
.fab:hover { background: var(--c-primary-strong); }
@media (max-width: 767px) {
  .fab { right: 14px; bottom: 16px; padding: 10px 14px; font-size: 14px; }
  .page { padding-bottom: 56px; }
}
.fold { border: 1px solid var(--c-line); border-radius: var(--r-card); margin-bottom: 14px; background: var(--c-card); overflow: hidden; }
.fold-h { display: flex; align-items: center; gap: 12px; width: 100%; padding: 14px 16px; background: none; border: 0; cursor: pointer; text-align: left; min-height: 60px; }
.fold-h:hover { background: var(--c-mint-bg, #f2faf5); }
.chev { flex: none; color: var(--c-text-2); transition: transform 0.2s ease, color 0.2s; }
.chev.open { transform: rotate(90deg); color: var(--c-primary); }
.fold-t { flex: 1; min-width: 0; }
.fold-t b { font-size: var(--fs-title); display: block; }
.fold-t .desc { display: block; }
.meta { color: var(--c-text-2); font-size: var(--fs-sub); white-space: nowrap; }
.fold-act { flex: none; font-size: 13px; font-weight: 700; color: var(--c-primary-strong); background: var(--c-primary-soft); padding: 6px 14px; border-radius: 999px; white-space: nowrap; }
.fold-b { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.26s ease; }
.fold-b.open { grid-template-rows: 1fr; }
.fold-inner { overflow: hidden; min-height: 0; padding: 0 16px; }
.fold-b.open .fold-inner { padding-bottom: 16px; }
.testcard { box-shadow: none; border: 1px solid var(--c-line); }
/* 每个 Part 一行：左信息、右「学习 / 测验」，不再把 6×2 个按钮堆成一片 */
.parts { margin-top: 12px; border: 1px solid var(--c-line); border-radius: var(--r-sm); overflow: hidden; }
.partrow { display: flex; align-items: center; gap: 12px; padding: 8px 10px 8px 12px; }
.partrow + .partrow { border-top: 1px solid var(--c-line); }
.partrow:hover { background: var(--c-mint-bg); }
.pl { flex: 1; min-width: 0; display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.pno { font-size: var(--fs-sub); font-weight: 800; color: var(--c-primary-strong); white-space: nowrap; }
.pkind { font-size: var(--fs-sub); color: var(--c-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pkind.short { display: none; }
.pn { font-size: 12.5px; color: var(--c-text-2); white-space: nowrap; }
.pact { flex: none; display: flex; gap: 6px; }
@media (max-width: 520px) {
  .partrow { gap: 8px; padding: 8px; }
  .pl { gap: 6px; }
  .pn { display: none; }
  .pkind.long { display: none; }
  .pkind.short { display: inline; }
}
</style>
