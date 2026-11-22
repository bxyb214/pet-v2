<template>
  <div class="page">
    <!-- 开局设置 -->
    <n-card v-if="!round.length && !finished" title="开始一轮学习" size="small">
      <template #header-extra>
        <n-tag v-if="dueInBank.length" type="warning" size="small" round :bordered="false">
          本库有 {{ dueInBank.length }} 个错题到期
        </n-tag>
      </template>

      <div class="setrow">
        <span class="lbl">词库</span>
        <n-radio-group v-model:value="bank">
          <n-radio-button v-for="b in BANK_TABS" :key="b.key" :value="b.key">{{ b.label }}</n-radio-button>
        </n-radio-group>
      </div>
      <div class="setrow">
        <span class="lbl">题量</span>
        <n-radio-group v-model:value="count">
          <n-radio-button :value="10">10 题</n-radio-button>
          <n-radio-button :value="20">20 题</n-radio-button>
        </n-radio-group>
        <n-checkbox v-model:checked="mistakeFirst">错题优先</n-checkbox>
      </div>
      <div class="startrow">
        <n-button type="primary" size="large" @click="start">开始测验</n-button>
        <span class="muted">答错的词自动进错题本，按 1/2/4/7/15 天复习</span>
      </div>
    </n-card>

    <!-- 答题中 -->
    <template v-else-if="q && !finished">
      <n-card size="small" class="qcard">
        <div class="progressrow">
          <n-progress
            type="line"
            :percentage="Math.round((qIndex / round.length) * 100)"
            :show-indicator="false"
            :height="8"
          />
          <span class="muted">{{ qIndex + 1 }} / {{ round.length }}</span>
        </div>
        <n-tag size="small" :bordered="false" class="dimtag">{{ DIM_LABEL[q.dim] }}</n-tag>

        <div class="stem">
          <template v-if="q.dim === 'w2m'">
            <p class="word">{{ q.word.en }}</p>
            <p class="phon">{{ q.word.phonetic }}</p>
          </template>
          <template v-else><p class="word cn">{{ q.word.cn }}</p></template>
        </div>

        <div v-if="!answered" class="answers">
          <n-input
            v-if="q.dim === 'spell'"
            v-model:value="typed"
            size="large"
            placeholder="拼写单词后回车"
            @keyup.enter="submit(typed)"
          />
          <n-button v-if="q.dim === 'spell'" type="primary" size="large" :disabled="!typed" @click="submit(typed)">提交</n-button>
          <n-button
            v-for="opt in q.options"
            :key="opt"
            size="large"
            secondary
            class="optbtn"
            @click="submit(opt)"
          >{{ opt }}</n-button>
        </div>

        <div v-else class="feedback" :class="lastCorrect ? 'ok' : 'bad'">
          <p class="fbtitle">{{ lastCorrect ? "✓ 答对了！" : "再试一次，正确答案：" + q.answer }}</p>
          <p v-if="!lastCorrect" class="fbans">{{ q.word.en }}（{{ q.word.pos }}）{{ q.word.cn }}</p>
          <p v-if="q.word.example" class="fbex">{{ q.word.example }}</p>
          <div class="fbactions">
            <n-button secondary @click="playAudio(q.word)">🔊 听发音</n-button>
            <n-button type="primary" @click="next">下一题</n-button>
          </div>
        </div>
      </n-card>
    </template>

    <!-- 完成 -->
    <n-result
      v-else
      status="success"
      title="本轮完成！"
      :description="`答对 ${correctCount} / ${round.length} 题`"
    >
      <template #footer>
        <n-button type="primary" size="large" @click="restart">再来一轮</n-button>
      </template>
    </n-result>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import {
  NButton, NCard, NCheckbox, NInput, NProgress, NRadioButton,
  NRadioGroup, NResult, NTag,
} from "naive-ui";
import { useRoute } from "vue-router";
import { useLearningStore } from "../stores/learning";
import { loadBanks } from "../core/banks";
import { makeRound, checkAnswer, DIM_LABEL, type QuizDim, type QuizQuestion } from "../core/quiz";
import type { WordBanks, BankKey, PlanWord } from "../core/plan";

const BANK_TABS: Array<{ key: BankKey; label: string }> = [
  { key: "bimo", label: "必默" },
  { key: "gaopin", label: "高频" },
  { key: "guding", label: "固搭" },
  { key: "tongyi", label: "同义" },
];

const learning = useLearningStore();
const banks = ref<WordBanks>({ bimo: [], gaopin: [], guding: [], tongyi: [] });
void loadBanks().then((r) => (banks.value = r.banks));

const bank = ref<BankKey>("bimo");
// 从词库页「学习本词库」进入时带上词库（bimo/gaopin/guding/tongyi）
const route = useRoute();
const qBank = String(route.query.bank ?? "");
if (["bimo", "gaopin", "guding", "tongyi"].includes(qBank)) bank.value = qBank as BankKey;
const count = ref(10);
const mistakeFirst = ref(true);

const round = ref<QuizQuestion[]>([]);
const qIndex = ref(0);
const answered = ref(false);
const lastCorrect = ref(false);
const typed = ref("");
const finished = ref(false);
const correctCount = ref(0);

const q = computed(() => round.value[qIndex.value] ?? null);
const dueInBank = computed(() => {
  const ids = new Set(learning.dueMistakes);
  return banks.value[bank.value].filter((w) => ids.has(w.id));
});

function start(): void {
  const list = banks.value[bank.value];
  let picked: PlanWord[] | undefined;
  if (mistakeFirst.value && dueInBank.value.length) {
    picked = [...dueInBank.value, ...list.filter((w) => !idsOf(dueInBank.value).has(w.id))];
  }
  round.value = makeRound(list, count.value, [...ALL_DIMS], picked);
  qIndex.value = 0;
  correctCount.value = 0;
  answered.value = false;
  finished.value = false;
  typed.value = "";
  playIfW2M();
}

function idsOf(ws: PlanWord[]): Set<string> {
  return new Set(ws.map((w) => w.id));
}

function submit(ans: string): void {
  if (!q.value || answered.value) return;
  answered.value = true;
  lastCorrect.value = checkAnswer(ans, q.value.answer);
  const wordId = q.value.word.id;
  if (lastCorrect.value) {
    correctCount.value += 1;
    learning.recordRight(wordId, q.value.dim); // 错题本划维度（不在错题本时无副作用）
    learning.recordMastery(wordId, [q.value.dim]);
  } else {
    learning.recordWrong(wordId, [...ALL_DIMS]); // 答错全维度重欠 + 回 1 天间隔
  }
}

function next(): void {
  if (qIndex.value >= round.value.length - 1) {
    finished.value = true;
    return;
  }
  qIndex.value += 1;
  answered.value = false;
  typed.value = "";
  playIfW2M();
}

function restart(): void {
  round.value = [];
  finished.value = false;
}

function playIfW2M(): void {
  // 朗读规则红线：仅看词选义（w2m）答题前自动播放发音
  if (q.value?.dim === "w2m") playAudio(q.value.word);
}

function playAudio(word: PlanWord): void {
  if (word.audio) void new Audio(`/media/audio/${word.audio}`).play().catch(() => {});
}

const ALL_DIMS: QuizDim[] = ["w2m", "m2w", "spell"];
</script>

<style scoped>
.page { width: 100%; }
.startrow { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-top: 4px; }
.setrow { display: flex; gap: 16px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.lbl { font-size: 13px; color: var(--c-text-2, #6b7f74); font-weight: 600; min-width: 36px; }
.progressrow { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.progressrow :first-child { flex: 1; }
.muted { color: var(--c-text-2, #6b7f74); font-size: 13px; flex-shrink: 0; }
.dimtag { margin-bottom: 8px; }
.stem { text-align: center; margin: 18px 0 22px; }
.word { font-size: 38px; font-weight: 800; margin: 0; }
.word.cn { font-size: 32px; }
.phon { color: var(--c-text-2, #6b7f74); margin: 4px 0 0; }
.answers { display: grid; gap: 10px; }
.optbtn { justify-content: flex-start; min-height: 54px; }
.feedback { border-radius: 12px; padding: 16px; margin-top: 10px; }
.feedback.ok { background: var(--c-primary-soft, #e7f6ec); }
.feedback.bad { background: #fef2f2; }
.fbtitle { font-weight: 700; margin: 0 0 6px; font-size: 17px; }
.ok .fbtitle { color: var(--c-primary-strong, #15803d); }
.bad .fbtitle { color: #dc2626; }
.fbans { margin: 0 0 4px; }
.fbex { color: var(--c-text-2, #6b7f74); font-size: 13px; margin: 0 0 10px; }
.fbactions { display: flex; gap: 10px; }
</style>
