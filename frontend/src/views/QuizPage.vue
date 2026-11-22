<template>
  <div class="page quiz">
    <!-- ========== 开局设置 ========== -->
    <n-card v-if="!round.length && !finished" size="small">
      <template #header>
        <div class="chead">
          <h2>开始一轮</h2>
          <n-tag v-if="dueInBank.length" type="warning" size="small" round :bordered="false">
            {{ dueInBank.length }} 个错题到期
          </n-tag>
        </div>
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
        <span class="hint">答错的词自动进错题本，按 1 / 2 / 4 / 7 / 15 天复习</span>
      </div>
    </n-card>

    <!-- ========== 答题中 ========== -->
    <template v-else-if="q && !finished">
      <!-- 进度：可数的分段，已答的分段会变成绿/橙，能看出这一轮走到哪、对了几题 -->
      <header class="qhead">
        <div class="segs" aria-hidden="true">
          <i
            v-for="(s, i) in segStates"
            :key="i"
            class="seg"
            :class="s"
          ></i>
        </div>
        <span class="cnt tnum"><b>{{ qIndex + 1 }}</b><i>/&nbsp;{{ round.length }}</i></span>
      </header>

      <section class="qcard" :class="{ answered }">
        <div class="qtop">
          <span class="dim">{{ DIM_LABEL[q.dim] }}</span>
          <span v-if="!answered" class="tip">{{ tip }}</span>
        </div>

        <div class="stem">
          <template v-if="q.dim === 'w2m'">
            <p class="word" :style="wordStyle">{{ q.word.en }}</p>
            <p v-if="q.word.phonetic" class="phon">{{ q.word.phonetic }}</p>
          </template>
          <template v-else>
            <p class="word cn" :style="wordStyle">{{ q.word.cn }}</p>
          </template>
        </div>

        <!-- 拼写 -->
        <div v-if="q.dim === 'spell'" class="spellrow">
          <n-input
            v-model:value="typed"
            size="large"
            placeholder="拼出这个单词，回车提交"
            :disabled="answered"
            :status="answered && !lastCorrect ? 'error' : undefined"
            @keyup.enter="submit(typed)"
          />
          <n-button v-if="!answered" type="primary" size="large" :disabled="!typed.trim()" @click="submit(typed)">
            提交
          </n-button>
        </div>

        <!-- 选择题 -->
        <div v-else class="opts">
          <button
            v-for="(opt, i) in q.options"
            :key="opt + i"
            type="button"
            class="opt"
            :class="optClass(opt)"
            :disabled="answered"
            @click="submit(opt)"
          >
            <span class="okbd" aria-hidden="true">{{ i + 1 }}</span>
            <span class="otxt">{{ opt }}</span>
            <span class="omark" aria-hidden="true">
              <svg v-if="answered && opt === q.answer" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12.5l4.5 4.5L19 6.5" />
              </svg>
              <svg v-else-if="answered && opt === picked && opt !== q.answer" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
                <path d="M7 7l10 10M17 7L7 17" />
              </svg>
            </span>
          </button>
        </div>

        <!-- 反馈 -->
        <transition name="fb">
          <div v-if="answered" class="fb" :class="lastCorrect ? 'ok' : 'bad'">
            <div class="fbhead">
              <span class="fbicon">
                <svg v-if="lastCorrect" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M5 12.5l4.5 4.5L19 6.5" />
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 8v5" /><circle cx="12" cy="16.6" r="0.6" fill="currentColor" />
                </svg>
              </span>
              <div class="fbtxt">
                <p class="fbtitle">{{ lastCorrect ? "答对了" : "这次的正确答案" }}</p>
                <p class="fbsub">{{ lastCorrect ? "保持住，下一个也稳了" : "看一眼就记住了，它会再回来一次" }}</p>
              </div>
            </div>

            <p class="fbans">
              <b>{{ q.word.en }}</b>
              <span v-if="q.word.phonetic" class="ph">{{ q.word.phonetic }}</span>
              <span v-if="q.word.pos" class="pos">{{ q.word.pos }}</span>
              <span class="cn">{{ q.word.cn }}</span>
            </p>
            <p v-if="q.dim === 'spell' && !lastCorrect && typed.trim()" class="fbtyped">
              你写的是 <s>{{ typed.trim() }}</s>
            </p>
            <p v-if="q.word.example" class="fbex">{{ q.word.example }}</p>

            <div class="fbactions">
              <n-button secondary type="primary" @click="playAudio(q.word)">
                <template #icon>
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" />
                    <path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" />
                  </svg>
                </template>
                听发音
              </n-button>
              <n-button type="primary" @click="next">{{ isLast ? "看结果" : "下一题" }}</n-button>
            </div>
          </div>
        </transition>
      </section>
    </template>

    <!-- ========== 结算 ========== -->
    <section v-else class="result">
      <p class="reye">本轮完成</p>
      <p class="rbig tnum">{{ correctCount }}<i>/ {{ round.length }}</i></p>

      <!-- 这一轮的答题结果，一段一题：与答题时的进度条同构 -->
      <div class="segs rsegs" aria-hidden="true">
        <i v-for="(s, i) in segStates" :key="i" class="seg" :class="s"></i>
      </div>

      <p class="rrate">
        正确率 <b class="tnum">{{ rate }}%</b>
        <span class="dotsep">·</span>
        {{ rateCopy }}
      </p>

      <div v-if="wrongWords.length" class="rwrong">
        <p class="rtitle">要再看的 {{ wrongWords.length }} 个词</p>
        <ul>
          <li v-for="w in wrongWords" :key="w.id" :title="`${w.en} ${w.cn}`">
            <b>{{ w.en }}</b>
            <span>{{ w.cn }}</span>
          </li>
        </ul>
      </div>

      <div class="ractions">
        <n-button type="primary" size="large" @click="restart">再来一轮</n-button>
        <router-link v-if="wrongWords.length" to="/english/words/mistakes" class="linkbtn">去错题本</router-link>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import {
  NButton, NCard, NCheckbox, NInput, NRadioButton,
  NRadioGroup, NTag,
} from "naive-ui";
import { useRoute } from "vue-router";
import { useLearningStore } from "../stores/learning";
import { availableBankKeys, loadBanks, type BankMeta } from "../core/banks";
import { useAuthStore } from "../stores/auth";
import { makeRound, checkAnswer, DIM_LABEL, type QuizDim, type QuizQuestion } from "../core/quiz";
import type { WordBanks, BankKey, PlanWord } from "../core/plan";

const learning = useLearningStore();
const auth = useAuthStore();
const banks = ref<WordBanks>({});
const bankMeta = ref<Record<string, BankMeta>>({});
/** 当前级别下的词库标签（PET 四库 / KET 五库） */
const BANK_TABS = computed<Array<{ key: BankKey; label: string }>>(() =>
  availableBankKeys(banks.value, bankMeta.value, auth.exam).map((k) => ({
    key: k,
    label: bankMeta.value[k]?.short || k,
  })),
);

const bank = ref<BankKey>("");
// 从词库页「学习本词库」进入时带上词库
const route = useRoute();
const qBank = String(route.query.bank ?? "");
if (qBank) bank.value = qBank as BankKey;

void loadBanks().then((r) => {
  banks.value = r.banks;
  bankMeta.value = r.bankMeta;
  const keys = availableBankKeys(r.banks, r.bankMeta, auth.exam);
  if (!bank.value || !keys.includes(bank.value)) bank.value = (keys[0] as BankKey) ?? "";
});
const count = ref(10);
const mistakeFirst = ref(true);

const round = ref<QuizQuestion[]>([]);
const qIndex = ref(0);
const answered = ref(false);
const lastCorrect = ref(false);
const picked = ref("");
const typed = ref("");
const finished = ref(false);
const correctCount = ref(0);
/** 每题结果：true 对 / false 错 / null 未答——驱动顶部分段进度 */
const results = ref<Array<boolean | null>>([]);
const wrongWords = ref<PlanWord[]>([]);

const q = computed(() => round.value[qIndex.value] ?? null);
const isLast = computed(() => qIndex.value >= round.value.length - 1);
const rate = computed(() =>
  round.value.length ? Math.round((correctCount.value / round.value.length) * 100) : 0,
);
const rateCopy = computed(() =>
  rate.value === 100 ? "全对，很稳" : rate.value >= 80 ? "不错，再巩固一轮" : "错的几个再来一次就好",
);

const dueInBank = computed(() => {
  const ids = new Set(learning.dueMistakes);
  return (banks.value[bank.value] ?? []).filter((w) => ids.has(w.id));
});

const segStates = computed(() =>
  round.value.map((_, i) => {
    const r = results.value[i];
    if (r === true) return "ok";
    if (r === false) return "bad";
    return i === qIndex.value ? "now" : "todo";
  }),
);

/** 维度提示：告诉孩子这一步要做什么，不用猜 */
const tip = computed(() => {
  if (!q.value) return "";
  if (q.value.dim === "spell") return "听发音后拼出来";
  if (q.value.dim === "w2m") return "选它的意思";
  return "选对应的英文";
});

/** 长词自适应：词库里有 100+ 字符的释义，固定字号必溢出 */
const wordStyle = computed(() => {
  if (!q.value) return {};
  const text = q.value.dim === "m2w" ? q.value.word.cn : q.value.word.en;
  const n = (text ?? "").length;
  const isCn = q.value.dim === "m2w";
  const size = isCn
    ? n <= 8 ? 30 : n <= 14 ? 26 : n <= 24 ? 22 : 19
    : n <= 12 ? 42 : n <= 20 ? 34 : n <= 30 ? 28 : 23;
  return { fontSize: `${size}px` };
});

function optClass(opt: string): Record<string, boolean> {
  if (!answered.value) return {};
  const isAnswer = opt === q.value?.answer;
  return {
    right: isAnswer,
    wrong: !isAnswer && opt === picked.value,
    dimmed: !isAnswer && opt !== picked.value,
  };
}

function start(): void {
  const list = banks.value[bank.value] ?? [];
  let pickedList: PlanWord[] | undefined;
  if (mistakeFirst.value && dueInBank.value.length) {
    pickedList = [...dueInBank.value, ...list.filter((w) => !idsOf(dueInBank.value).has(w.id))];
  }
  round.value = makeRound(list, count.value, [...ALL_DIMS.value], pickedList);
  results.value = new Array(round.value.length).fill(null);
  wrongWords.value = [];
  qIndex.value = 0;
  correctCount.value = 0;
  answered.value = false;
  picked.value = "";
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
  picked.value = ans;
  lastCorrect.value = checkAnswer(ans, q.value.answer);
  const wordId = q.value.word.id;
  if (lastCorrect.value) {
    correctCount.value += 1;
    learning.recordRight(wordId, q.value.dim); // 错题本划维度（不在错题本时无副作用）
    learning.recordMastery(wordId, [q.value.dim]);
  } else {
    learning.recordWrong(wordId, [...ALL_DIMS.value]); // 答错全维度重欠 + 回 1 天间隔
    if (!wrongWords.value.some((w) => w.id === wordId)) wrongWords.value.push(q.value.word);
  }
  results.value[qIndex.value] = lastCorrect.value;
}

/** 防连点：答完 300ms 内不响应下一题，避免一下跳过两题 */
let lastNext = 0;
function next(): void {
  const now = Date.now();
  if (now - lastNext < 300) return;
  lastNext = now;
  if (isLast.value) {
    finished.value = true;
    return;
  }
  qIndex.value += 1;
  answered.value = false;
  picked.value = "";
  typed.value = "";
  playIfW2M();
}

function restart(): void {
  round.value = [];
  results.value = [];
  wrongWords.value = [];
  finished.value = false;
}

function playIfW2M(): void {
  // 朗读规则红线：仅看词选义（w2m）答题前自动播放发音
  if (q.value?.dim === "w2m") playAudio(q.value.word);
}

function playAudio(word: PlanWord): void {
  if (word.audio) void new Audio(`/media/audio/${word.audio}`).play().catch(() => {});
}

/** 键盘：数字键选选项，Enter 下一题 */
function onKey(e: KeyboardEvent): void {
  const tag = (e.target as HTMLElement | null)?.tagName;
  if (tag === "INPUT" || tag === "TEXTAREA") return;
  if (!q.value || finished.value) return;
  if (!answered.value) {
    if (/^[1-9]$/.test(e.key) && q.value.options.length) {
      const opt = q.value.options[Number(e.key) - 1];
      if (opt) submit(opt);
    }
    return;
  }
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    next();
  }
}
onMounted(() => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));

const FULL_DIMS: QuizDim[] = ["w2m", "m2w", "spell"];
/** 本次要考的维度：KET 按旧站规则不考拼写 */
const ALL_DIMS = computed<QuizDim[]>(() => {
  const dims = bankMeta.value[bank.value]?.dims;
  return (dims && dims.length ? dims : FULL_DIMS) as QuizDim[];
});
</script>

<style scoped>
.page { width: 100%; }

/* ---------- 开局 ---------- */
.chead { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.chead h2 { margin: 0; font-size: 15px; font-weight: 800; color: var(--c-text); }
.setrow { display: flex; gap: 14px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.lbl {
  font-size: 12.5px; color: var(--c-text-3); font-weight: 700;
  min-width: 34px; letter-spacing: 0.04em;
}
.startrow { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-top: 4px; }
.hint { font-size: 12.5px; color: var(--c-text-2); line-height: 1.6; }

/* ---------- 顶部分段进度 ---------- */
.qhead { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.segs { display: flex; gap: 4px; flex: 1; min-width: 0; }
.seg {
  flex: 1 1 0;
  height: 6px;
  border-radius: 999px;
  background: var(--c-line);
  transition: background var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out);
}
.seg.ok { background: var(--c-primary); }
.seg.bad { background: #e5a13c; }
/* 当前题用流动的浅绿，与「已完成」的实色区分开 */
.seg.now {
  background: linear-gradient(90deg, #86efac 0%, #d9f7e5 50%, #86efac 100%);
  background-size: 220% 100%;
  animation: segflow 1.8s linear infinite;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.1);
}
@keyframes segflow {
  from { background-position: 120% 0; }
  to { background-position: -120% 0; }
}
.cnt {
  display: inline-flex; align-items: baseline; gap: 1px;
  flex: none; letter-spacing: 0.01em;
}
.cnt b { font-size: 15px; font-weight: 800; color: var(--c-text); }
.cnt i { font-style: normal; font-size: 12.5px; font-weight: 600; color: var(--c-text-3); }

/* ---------- 题卡 ---------- */
.qcard {
  background: var(--c-card);
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  padding: 20px 22px 22px;
}
.qtop { display: flex; align-items: center; gap: 10px; }
.dim {
  font-size: 11.5px; font-weight: 700; letter-spacing: 0.04em;
  color: var(--c-primary-strong);
  background: var(--c-primary-soft);
  padding: 3px 9px; border-radius: var(--r-pill);
}
.tip { font-size: 12px; color: var(--c-text-3); }

.stem { text-align: center; padding: 26px 4px 24px; }
.word {
  margin: 0;
  font-family: var(--font-word);
  font-weight: 800;
  line-height: 1.28;
  letter-spacing: 0.2px;
  color: var(--c-text);
  word-break: break-word;
  overflow-wrap: anywhere;
}
.word.cn { font-family: var(--font-base); }
.phon {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--c-text-3);
  font-family: var(--font-en);
  letter-spacing: 0.02em;
}

/* ---------- 拼写 ---------- */
.spellrow { display: flex; gap: 10px; align-items: stretch; max-width: 560px; margin: 0 auto; }
.spellrow :deep(.n-input) { flex: 1; }
.spellrow :deep(.n-input__input-el) { font-family: var(--font-en); letter-spacing: 0.06em; }

/* ---------- 选项 ---------- */
.opts { display: grid; gap: 10px; }
.opt {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-height: 58px;
  padding: 13px 44px 13px 16px;
  border: 1.5px solid var(--c-line);
  border-radius: var(--r-btn);
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color var(--dur-2) var(--ease-out),
    background var(--dur-2) var(--ease-out),
    transform var(--dur-1) var(--ease-out),
    box-shadow var(--dur-2) var(--ease-out);
}
.opt:hover:not(:disabled) {
  border-color: #a9dcc0;
  background: #fbfefc;
  box-shadow: var(--shadow-1);
}
.opt:active:not(:disabled) { transform: scale(0.994); }

.otxt {
  font-size: 16px;
  line-height: 1.5;
  color: var(--c-text);
  word-break: break-word;
  overflow-wrap: anywhere;
}
/* 选项序号只在有鼠标的设备上出现：触屏上纯噪音 */
.okbd {
  display: none;
  flex: none;
  width: 21px; height: 21px;
  border-radius: 6px;
  background: #f1f6f3;
  color: var(--c-text-3);
  font-size: 11px; font-weight: 700;
  align-items: center; justify-content: center;
  font-variant-numeric: tabular-nums;
}
@media (hover: hover) and (pointer: fine) {
  .okbd { display: inline-flex; }
}
.omark {
  position: absolute;
  right: 14px; top: 50%;
  transform: translateY(-50%);
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
}
.omark svg { width: 18px; height: 18px; }

.opt.right {
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
  color: var(--c-primary-strong);
  animation: pop var(--dur-2) var(--ease-spring) both;
}
.opt.right .otxt { color: #14532d; font-weight: 700; }
.opt.right .omark { color: var(--c-primary); }

.opt.wrong {
  border-color: #e8a13c;
  background: #fdf6ec;
  animation: shake 260ms var(--ease-out) both;
}
.opt.wrong .otxt { color: #8a5a13; }
.opt.wrong .omark { color: #d97706; }

.opt.dimmed { opacity: 0.52; }
.opt:disabled { cursor: default; }

@keyframes pop {
  0% { transform: scale(1); }
  55% { transform: scale(1.012); }
  100% { transform: scale(1); }
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-3px); }
  50% { transform: translateX(3px); }
  75% { transform: translateX(-1.5px); }
}

/* ---------- 反馈 ---------- */
.fb {
  margin-top: 16px;
  padding: 16px;
  border-radius: var(--r-sm);
  border: 1px solid transparent;
}
.fb.ok { background: #f2fbf6; border-color: #cdebd9; }
.fb.bad { background: #fffaf3; border-color: #f3e0c4; }

.fbhead { display: flex; gap: 10px; align-items: flex-start; }
.fbicon {
  flex: none;
  width: 22px; height: 22px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin-top: 1px;
}
.fb.ok .fbicon { background: var(--c-primary); color: #fff; }
.fb.bad .fbicon { background: #e8a13c; color: #fff; }
.fbicon svg { width: 14px; height: 14px; }

.fbtxt { min-width: 0; }
.fbtitle { margin: 0; font-size: 15px; font-weight: 800; letter-spacing: 0.02em; }
.fb.ok .fbtitle { color: #14532d; }
.fb.bad .fbtitle { color: #7c4a0b; }
.fbsub { margin: 2px 0 0; font-size: 12.5px; color: var(--c-text-2); line-height: 1.5; }

.fbans {
  margin: 12px 0 0;
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 15px;
}
.fbans b { font-family: var(--font-word); font-size: 18px; color: var(--c-text); }
.fbans .ph { font-size: 12.5px; color: var(--c-text-3); font-family: var(--font-en); }
.fbans .pos { font-size: 12px; color: var(--c-accent); font-weight: 600; }
.fbans .cn { color: var(--c-text-2); }
.fbtyped { margin: 8px 0 0; font-size: 13px; color: var(--c-text-2); }
.fbtyped s { color: #b42318; opacity: 0.85; }
.fbex {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--c-text-2);
  font-family: var(--font-en);
}
.fbactions { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.fbactions :deep(.n-button) { flex: 1; min-width: 120px; }

.fb-enter-active { transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out); }
.fb-leave-active { transition: opacity 120ms var(--ease-out); }
.fb-enter-from { opacity: 0; transform: translateY(6px); }
.fb-leave-to { opacity: 0; }

/* ---------- 结算 ---------- */
.result {
  width: 100%;
  max-width: 620px;
  margin: 0 auto;
  background: var(--c-card);
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  padding: 30px 24px 22px;
  text-align: center;
  animation: rin var(--dur-3) var(--ease-out) both;
}
.reye {
  margin: 0 0 4px;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: var(--c-primary-strong);
}
.rbig {
  margin: 0;
  font-size: 54px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--c-text);
}
.rbig i {
  font-style: normal;
  font-size: 20px;
  font-weight: 700;
  color: var(--c-text-3);
  margin-left: 2px;
}
.rsegs { margin: 18px 0 0; }
.rrate { margin: 12px 0 0; font-size: 13px; color: var(--c-text-2); }
.rrate b { color: var(--c-primary-strong); font-weight: 800; }
.dotsep { margin: 0 6px; color: var(--c-line-strong); }

.rwrong {
  margin: 20px 0 0;
  text-align: left;
  border-top: 1px dashed var(--c-line);
  padding-top: 14px;
}
.rtitle { margin: 0 0 10px; font-size: 12.5px; font-weight: 700; color: var(--c-text-2); }
.rwrong ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(158px, 1fr));
  gap: 7px;
}
.rwrong li {
  display: flex;
  align-items: baseline;
  gap: 7px;
  padding: 8px 10px;
  border-radius: var(--r-sm);
  background: #fffaf3;
  border: 1px solid #f4e4cd;
  font-size: 12.5px;
  min-width: 0;
}
.rwrong li b {
  font-family: var(--font-word);
  font-size: 14px;
  color: var(--c-text);
  flex: none;
  max-width: 55%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rwrong li span {
  color: var(--c-text-2);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ractions {
  display: flex;
  gap: 12px;
  justify-content: center;
  align-items: center;
  margin-top: 22px;
  flex-wrap: wrap;
}
.linkbtn {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--c-primary-strong);
  text-decoration: none;
  padding: 10px 14px;
  border-radius: var(--r-pill);
}
.linkbtn:hover { background: var(--c-primary-soft); }

@keyframes rin {
  from { opacity: 0; transform: translateY(8px) scale(0.99); }
  to { opacity: 1; transform: none; }
}

@media (max-width: 767px) {
  .qcard { padding: 16px 14px 18px; border-radius: 16px; }
  .stem { padding: 20px 2px 18px; }
  .fbactions :deep(.n-button) { min-width: 0; }
  .rbig { font-size: 46px; }
  .result { padding: 26px 16px 20px; }
}

@media (prefers-reduced-motion: reduce) {
  .seg.now { animation: none; background: var(--c-primary); }
  .opt.right, .opt.wrong, .result { animation: none; }
}
</style>
