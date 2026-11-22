<template>
  <main class="page" v-if="sent">
    <div class="topbar">
      <button class="ghost" @click="back">← 返回</button>
      <p class="label">{{ label }}</p>
      <span class="pos">{{ idx + 1 }} / {{ sentences.length }}</span>
    </div>

    <section class="card">
      <p class="en">{{ sent.en }}</p>
      <p class="cn">{{ sent.cn }}</p>

      <div v-if="sent.parse?.length" class="parse">
        <span v-for="(p, i) in sent.parse" :key="i" class="ptag"><i>{{ p.r }}</i>{{ p.t }}</span>
      </div>

      <div v-if="sent.gram?.length" class="gram">
        <div v-for="g in sent.gram" :key="g.c" class="gram-item">
          <p class="gram-g">〔考点 {{ g.c }}〕{{ g.g }}</p>
          <p class="gram-d">{{ g.d }}</p>
        </div>
      </div>

      <div class="note">
        <p class="note-t">{{ sent.tense }}</p>
        <p class="note-b">{{ sent.note }}</p>
      </div>

      <div class="actions">
        <button class="audiobtn" @click="speak(sent.en)">🔊 听整句</button>
        <button class="ghost" :disabled="idx === 0" @click="idx--">← 上一句</button>
        <button class="btn" @click="advance">
          {{ idx === sentences.length - 1 ? "去做题 →" : "下一句 →" }}
        </button>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useLearningStore } from "../stores/learning";
import { loadReading, speak, withCustomSentences, type RSentence } from "../core/reading";

const route = useRoute();
const router = useRouter();
const learning = useLearningStore();
const sentences = ref<RSentence[]>([]);
const idx = ref(0);
const label = ref("");
const testNo = ref(0);
const part = ref(0);
const studyKey = ref("");

const sent = computed(() => sentences.value[idx.value] ?? null);

onMounted(async () => {
  const d = withCustomSentences(await loadReading(), learning.data.custom_sentences);
  testNo.value = Number(route.params.testNo);
  part.value = Number(route.params.part);
  const t = d.tests.find((x) => x.no === testNo.value);
  const p = t?.parts.find((x) => x.part === part.value);
  sentences.value = p?.sentences ?? [];
  label.value = t ? `${t.title} · Part ${part.value}${p?.kind ? " · " + p.kind : ""}` : "";
  const book = t?.book || "t2";
  studyKey.value = `rstudy:${book}:${testNo.value}:${part.value}`;
  // R7 续学：从上次学到的句子继续
  const saved = learning.progressOf(studyKey.value);
  idx.value = Math.min(saved?.idx ?? 0, Math.max(sentences.value.length - 1, 0));
});

function advance(): void {
  if (!sentences.value.length) return;
  if (idx.value < sentences.value.length - 1) {
    idx.value += 1;
    learning.setStudyIdx(studyKey.value, idx.value); // R7 精读进度持久化
  } else {
    learning.recordProgress(studyKey.value); // 学完记完成日期
    goQuiz();
  }
}

function back(): void {
  void router.push("/english/reading");
}
function goQuiz(): void {
  void router.push({ path: `/english/reading/quiz/${testNo.value}`, query: { part: String(part.value) } });
}
</script>

<style scoped>
.page { width: 100%; }
.topbar { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.label { flex: 1; margin: 0; color: var(--c-text-2); font-size: var(--fs-sub); }
.pos { color: var(--c-text-2); font-size: var(--fs-sub); }
.card { background: var(--c-card); border-radius: var(--r-card); box-shadow: var(--shadow-card); padding: 20px; }
.en { font-size: var(--fs-body); line-height: 1.7; margin: 0 0 8px; }
.cn { color: var(--c-text-2); margin: 0 0 14px; }
.parse { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 14px; }
.ptag { background: var(--c-primary-soft); border-radius: var(--r-pill); padding: 5px 10px; font-size: var(--fs-sub); }
.ptag i { font-style: normal; color: var(--c-primary-strong); margin-right: 4px; }
.gram { border-top: 1px solid var(--c-line); padding-top: 12px; margin-bottom: 12px; }
.gram-item { margin-bottom: 8px; }
.gram-g { color: var(--c-primary-strong); font-size: var(--fs-sub); margin: 0 0 2px; }
.gram-d { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0; line-height: 1.6; }
.note { background: var(--c-bg); border-radius: var(--r-btn); padding: 12px 14px; margin-bottom: 14px; }
.note-t { font-weight: 500; margin: 0 0 4px; font-size: var(--fs-sub); }
.note-b { margin: 0; font-size: var(--fs-sub); line-height: 1.7; color: var(--c-text-1); }
.actions { display: flex; align-items: center; gap: 10px; }
.btn { background: var(--c-primary); color: #fff; border: 0; border-radius: var(--r-btn); padding: 12px 20px; font-size: var(--fs-body); min-height: 44px; cursor: pointer; margin-left: auto; }
.btn:disabled { opacity: 0.4; }
.ghost { background: none; border: 0; color: var(--c-primary-strong); font-size: var(--fs-body); min-height: 44px; cursor: pointer; padding: 0 8px; }
.ghost:disabled { opacity: 0.3; cursor: not-allowed; }
.audiobtn { background: var(--c-primary-soft); color: var(--c-primary-strong); border: 0; border-radius: var(--r-pill); padding: 10px 16px; min-height: 44px; cursor: pointer; }
</style>
