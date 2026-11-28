<template>
  <main class="page" v-if="ready">
    <!-- 结果页 -->
    <template v-if="finished">
      <section class="card done-card">
        <p class="reye">本轮完成</p>
        <p class="rbig tnum">{{ correct }}<i>/ {{ items.length }}</i></p>
        <p class="rrate">
          正确率 <b class="tnum">{{ rate }}%</b>
          <span class="dotsep">·</span>
          {{ rate >= 60 ? "这一套过关了" : "错的几句再来一遍就好" }}
        </p>
        <div class="actions">
          <button class="btn" @click="restart">再来一轮</button>
          <BackButton to="/english/reading/home" label="返回阅读" variant="text" />
        </div>
      </section>
    </template>

    <!-- 答题页 -->
    <template v-else-if="q">
      <div class="topbar">
        <BackButton
          to="/english/reading/home"
          label="退出"
          variant="text"
          confirm="已答题目会计入错题本，本轮进度会保留，下次可以继续。"
        />
        <p class="label">{{ label }}</p>
        <span class="pos tnum">{{ idx + 1 }} / {{ items.length }}</span>
      </div>
      <!-- 一题一段：对=实绿、错=暖橙、正在做=流动绿 -->
      <div class="segs" aria-hidden="true">
        <i
          v-for="(it, i) in items"
          :key="i"
          class="seg"
          :class="{ ok: results[i] === true, bad: results[i] === false, now: i === idx && results[i] == null }"
        ></i>
      </div>

      <section class="card">
        <p class="dimlabel">{{ TYPE_LABEL[q.type] }}</p>
        <p class="prompt">{{ q.prompt }}</p>

        <div class="answers">
          <button
            v-for="(o, i) in q.options"
            :key="i"
            class="optcard"
            :class="optClass(i)"
            :disabled="answered"
            @click="submit(i)"
          >
            <i class="kbd" aria-hidden="true">{{ "ABCD"[i] }}</i>
            <span class="olabel">{{ o.label }}</span>
            <span class="omark" aria-hidden="true">
              <svg v-if="answered && o.correct" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12.5l4.5 4.5L19 6.5" />
              </svg>
              <svg v-else-if="answered && i === picked" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
                <path d="M7 7l10 10M17 7L7 17" />
              </svg>
            </span>
          </button>
        </div>

        <!-- 反馈区：答题后才给听整句（朗读红线） -->
        <transition name="fb">
          <div v-if="answered" class="feedback" :class="lastCorrect ? 'ok' : 'bad'">
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
                <p class="fbtitle">{{ lastCorrect ? "答对了" : "这次的正确答案是 " + correctLabel }}</p>
                <p class="fbsub">{{ lastCorrect ? "保持住，下一个也稳了" : "看一眼就记住了，它会再回来一次" }}</p>
              </div>
            </div>
            <p v-if="!lastCorrect && q.type === 'grammar' && q.q?.why" class="fbwhy">{{ q.q.why }}</p>
            <p v-if="!lastCorrect && q.type !== 'grammar'" class="fbsent">{{ q.s.en }}</p>
            <p v-if="q.type !== 'meaning'" class="fbcn">{{ q.s.cn }}</p>
            <div class="fbactions">
              <button class="audiobtn" :disabled="audioPending(q.s.en)" @click="say(q.s.en)">
                <span v-if="audioPending(q.s.en)" class="audio-spin" aria-hidden="true" />
                <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" />
                  <path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" />
                </svg>
                听整句
              </button>
              <button class="btn nextbtn" @click="next">下一题</button>
            </div>
          </div>
        </transition>
      </section>
    </template>
    <!-- 空态：没有到期错题 / 题库缺失 / 加载失败 -->
    <section v-else class="card done-card">
      <p class="reye">{{ emptyTitle || "暂无内容" }}</p>
      <p class="rrate">{{ emptyDesc }}</p>
      <div class="actions">
        <BackButton :to="emptyTo" :label="emptyLabel" />
        <BackButton
          v-if="emptyTo !== '/english/reading/home'"
          to="/english/reading/home"
          label="返回阅读"
          variant="text"
        />
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useLearningStore } from "../stores/learning";
import { useAuthStore } from "../stores/auth";
import BackButton from "../components/BackButton.vue";
import {
  clearReadingSession, loadReadingSession, saveReadingSession,
} from "../core/readingQuizSession";
import {
  buildQuizItems, grammarIndex, itemForDim, loadReading, withCustomSentences,
  type QuizItem, type RSentence, type ReadingData,
} from "../core/reading";
import { audioPending, say } from "../core/say";
import { buildReadingPlan, partKey, readingDayOf, readingParts, type ReadingPartRef } from "../core/plan";

const TYPE_LABEL: Record<string, string> = { meaning: "读懂句意", blank: "选词填空", grammar: "语法选择" };

const route = useRoute();
const router = useRouter();
const learning = useLearningStore();
const auth = useAuthStore();

/** 续做按「用户 + 测验范围」隔离；范围优先用计划进度键，复习/语法用完整路径 */
const owner = computed(() => learning.owner || auth.username || "-");
const scope = computed(() => progressKey.value || route.fullPath);
/** 题目指纹：题目集合变了就不恢复，避免错位 */
const itemSig = computed(() => items.value.map((i) => `${i.s.id}:${i.type}:${i.prompt}`).join("|"));

const ready = ref(false);
const items = ref<QuizItem[]>([]);
const idx = ref(0);
const answered = ref(false);
const lastCorrect = ref(false);
/** 选了第几个选项（用于答错时标记） */
const picked = ref(-1);
/** 每题结果：true 对 / false 错 / null 未答——驱动顶部分段条 */
const results = ref<Array<boolean | null>>([]);
const finished = ref(false);
const correct = ref(0);
const rate = computed(() =>
  items.value.length ? Math.round((correct.value / items.value.length) * 100) : 0,
);
const label = ref("");
const progressKey = ref("");
const partRef = ref<ReadingPartRef | null>(null);

/** 空态：review 无到期错题 / 题号或考点不存在 / 题库加载失败 */
const emptyTitle = ref("");
const emptyDesc = ref("");
const emptyTo = ref("/english/reading/home");
const emptyLabel = ref("返回阅读");

function setEmpty(title: string, desc: string, to = "/english/reading/home", label = "返回阅读"): void {
  emptyTitle.value = title;
  emptyDesc.value = desc;
  emptyTo.value = to;
  emptyLabel.value = label;
}

const q = computed(() => items.value[idx.value] ?? null);
const correctLabel = computed(() => q.value?.options.find((o) => o.correct)?.label ?? "");

const today = new Date().toISOString().slice(0, 10);

function dueDims(s: RSentence): string[] {
  const m = learning.data.mistakes.find((x) => x.word_id === s.id);
  if (!m || !m.dims.length || !m.due_at || m.due_at > today) return [];
  return m.dims;
}

function reviewItems(sentences: RSentence[], pool: RSentence[]): QuizItem[] {
  const out: QuizItem[] = [];
  for (const s of sentences) {
    for (const dim of dueDims(s)) {
      const it = itemForDim(s, dim, pool);
      if (it) out.push(it);
    }
  }
  return out;
}

onMounted(async () => {
  let d: ReadingData;
  try {
    const base = await loadReading(auth.exam);
    d = withCustomSentences(base, learning.data.custom_sentences);
  } catch {
    setEmpty("阅读题库加载失败", "请检查网络后刷新重试。");
    ready.value = true;
    return;
  }
  const allSentences = d.tests.flatMap((x) => x.parts.flatMap((p) => p.sentences));
  const testNo = Number(route.params.testNo);
  const gc = route.query.gc ? Number(route.query.gc) : null;
  const review = route.query.review === "1";

  if (review) {
    // R8 错题复习：只考欠的维度
    items.value = reviewItems(allSentences, allSentences);
    label.value = "阅读错题复习（只考欠的维度）";
    if (!items.value.length) {
      setEmpty(
        "今天没有到期的阅读错题",
        "阅读错题会按 1/2/4/7/15 天的间隔到期；到期后再来复习就好。",
        "/english/reading/mistakes",
        "去错题本",
      );
    }
  } else if (gc != null) {
    // 语法专项
    const pool = grammarIndex(d.tests, d.grammar.examples ?? [])[gc] ?? [];
    items.value = pool.slice(0, 20);
    label.value = `语法专项 · ${route.query.label ?? "考点 " + gc}（20 题上限）`;
    if (!items.value.length) {
      setEmpty("这个语法考点暂时没有题目", "换一个考点，或先返回阅读继续精读。");
    }
  } else {
    const t = d.tests.find((x) => x.no === testNo);
    if (!t) {
      setEmpty("没有找到这套阅读题", "链接可能已过期，返回阅读重新选择一套。");
      ready.value = true;
      return;
    }
    const partQ = route.query.part ? Number(route.query.part) : 0;
    const sentences: RSentence[] = partQ
      ? (t.parts.find((p) => p.part === partQ)?.sentences ?? [])
      : t.parts.flatMap((p) => p.sentences);
    // R8 错题优先：到期错题（只考欠的维度）排前面，其余题照常
    const rev = reviewItems(sentences, allSentences);
    const rest = buildQuizItems(sentences, allSentences);
    items.value = [...rev, ...rest];
    if (!items.value.length) {
      setEmpty("这套阅读题暂时没有内容", "返回阅读换一套试试。");
    }
    results.value = new Array(items.value.length).fill(null);
    label.value = `${t.title}${partQ ? " · Part " + partQ : " · 全套"}${rev.length ? `（含 ${rev.length} 道错题）` : ""}`;
    progressKey.value = `read:${t.book || "t2"}:${t.no}:${partQ || "all"}`;
    if (partQ) partRef.value = { book: t.book || "t2", testNo: t.no, part: partQ };
  }
  if (results.value.length !== items.value.length) {
    results.value = new Array(items.value.length).fill(null);
  }
  restoreSession();
  ready.value = true;
});

/** 从上次离开的位置继续；题目集合变了就从头开始 */
function restoreSession(): void {
  if (!items.value.length) return;
  const saved = loadReadingSession(owner.value, scope.value, itemSig.value);
  if (!saved || saved.results.length !== items.value.length) return;
  idx.value = Math.min(saved.idx, items.value.length - 1);
  results.value = saved.results;
  correct.value = saved.correct_count;
  answered.value = saved.answered && results.value[idx.value] != null;
  picked.value = answered.value ? saved.picked : -1;
  lastCorrect.value = answered.value ? results.value[idx.value] === true : false;
}

function persistSession(): void {
  if (!items.value.length || finished.value) return;
  saveReadingSession(owner.value, scope.value, {
    sig: itemSig.value,
    idx: idx.value,
    results: results.value.map((v) => (v === true ? true : v === false ? false : null)),
    correct_count: correct.value,
    answered: answered.value,
    picked: picked.value,
  });
}

/** 当前题对应句子上的错题维度键 */
function dimOf(item: QuizItem): string {
  if (item.type === "grammar" && item.q) {
    const i = item.s.gq.indexOf(item.q);
    return `grammar:g${i >= 0 ? i : 0}`;
  }
  return item.type; // meaning / blank
}

function optClass(i: number): Record<string, boolean> {
  if (!answered.value) return {};
  const isRight = !!q.value?.options[i]?.correct;
  return { right: isRight, wrong: !isRight && i === picked.value, dimmed: !isRight && i !== picked.value };
}

function submit(i: number): void {
  if (!q.value || answered.value) return;
  answered.value = true;
  picked.value = i;
  lastCorrect.value = q.value.options[i].correct;
  results.value[idx.value] = lastCorrect.value;
  const dim = dimOf(q.value);
  if (lastCorrect.value) {
    correct.value += 1;
    learning.recordRight(q.value.s.id, dim); // 错题本划维度（不在错题本时无副作用）
  } else {
    learning.recordWrong(q.value.s.id, [dim]); // 该维度重欠 + 回 1 天间隔（R8）
  }
  persistSession();
}

function next(): void {
  if (idx.value >= items.value.length - 1) {
    finished.value = true;
    finishBookkeeping();
    return;
  }
  idx.value += 1;
  answered.value = false;
  picked.value = -1;
  persistSession();
}

function finishBookkeeping(): void {
  clearReadingSession(owner.value, scope.value);
  if (correct.value < items.value.length * 0.6) return;
  // R6 测验完成进度
  if (progressKey.value) learning.recordProgress(progressKey.value);
  // R9 阅读计划打勾：Part 测验达标 → 反查所属天
  if (partRef.value && learning.data.plan.reading_length > 0) {
    // 与计划页同源：同一组教材 + 同一套切分函数，避免两边算出不同的天
    const books = learning.data.plan.reading_books ?? [];
    void loadReading(auth.exam).then((d) => {
      const plan = buildReadingPlan(readingParts(d.tests, books), learning.data.plan.reading_length);
      const day = readingDayOf(plan, partKey(partRef.value!));
      if (day) learning.markReadingDayDone(day);
    });
  }
}

function restart(): void {
  clearReadingSession(owner.value, scope.value);
  idx.value = 0;
  correct.value = 0;
  answered.value = false;
  picked.value = -1;
  lastCorrect.value = false;
  results.value = new Array(items.value.length).fill(null);
  finished.value = false;
}

function back(): void {
  void router.push("/english/reading");
}
</script>

<style scoped>
.page { width: 100%; }
.topbar { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.label { flex: 1; margin: 0; color: var(--c-text-2); font-size: var(--fs-sub); }
.pos { color: var(--c-text-2); font-size: var(--fs-sub); }
.segs { display: flex; gap: 4px; margin-bottom: 16px; }
.seg {
  flex: 1 1 0; height: 5px; border-radius: 999px; background: var(--c-line);
  transition: background var(--dur-2) var(--ease-out);
}
.seg.ok { background: var(--c-primary); }
.seg.bad { background: #e5a13c; }
.seg.now { background: linear-gradient(90deg, #4ade80 0%, #86efac 50%, #4ade80 100%); background-size: 220% 100%; animation: flow 1.8s linear infinite; }
@keyframes flow {
  from { background-position: 120% 0; }
  to { background-position: -120% 0; }
}
.card {
  background: var(--c-card);
  border: 1px solid var(--c-line);
  border-radius: var(--r-card);
  box-shadow: var(--shadow-1);
  padding: 20px 22px 22px;
}
.dimlabel {
  display: inline-block;
  color: var(--c-primary-strong);
  background: var(--c-primary-soft);
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.04em;
  padding: 3px 9px;
  border-radius: var(--r-pill);
  margin: 0 0 12px;
}
.prompt { font-size: 17px; line-height: 1.75; margin: 0 0 16px; color: var(--c-text); }
.answers { display: grid; gap: 10px; }

.optcard {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--c-card);
  border: 1.5px solid var(--c-line);
  border-radius: var(--r-btn);
  padding: 13px 44px 13px 14px;
  font-size: var(--fs-body);
  min-height: 54px;
  text-align: left;
  cursor: pointer;
  transition: border-color var(--dur-2) var(--ease-out),
    background var(--dur-2) var(--ease-out), box-shadow var(--dur-2) var(--ease-out);
}
.optcard:hover:not(:disabled) { border-color: #a9dcc0; background: #fbfefc; box-shadow: var(--shadow-1); }
.kbd {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 7px;
  background: #f1f6f3;
  color: var(--c-text-2);
  font-size: 11.5px;
  font-weight: 700;
  font-style: normal;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.olabel { color: var(--c-text); line-height: 1.5; word-break: break-word; overflow-wrap: anywhere; }
.omark {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.omark svg { width: 18px; height: 18px; }

.optcard.right {
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
  animation: pop var(--dur-2) var(--ease-spring) both;
}
.optcard.right .olabel { color: #14532d; font-weight: 700; }
.optcard.right .kbd { background: #cdebd9; color: #14532d; }
.optcard.right .omark { color: var(--c-primary); }

.optcard.wrong {
  border-color: #e8a13c;
  background: #fdf6ec;
  animation: shake 260ms var(--ease-out) both;
}
.optcard.wrong .olabel { color: #8a5a13; }
.optcard.wrong .omark { color: #d97706; }

.optcard.dimmed { opacity: 0.52; }
.optcard:disabled { cursor: default; }

/* ---------- 反馈 ---------- */
.feedback {
  margin-top: 16px;
  padding: 16px;
  border-radius: var(--r-sm);
  border: 1px solid transparent;
}
.feedback.ok { background: #f2fbf6; border-color: #cdebd9; }
.feedback.bad { background: #fffaf3; border-color: #f3e0c4; }

.fbhead { display: flex; gap: 10px; align-items: flex-start; }
.fbicon {
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 1px;
}
.fbicon svg { width: 14px; height: 14px; }
.ok .fbicon { background: var(--c-primary); color: #fff; }
.bad .fbicon { background: #e8a13c; color: #fff; }

.fbtxt { min-width: 0; }
.fbtitle { margin: 0; font-size: 15px; font-weight: 800; letter-spacing: 0.02em; }
.ok .fbtitle { color: #14532d; }
.bad .fbtitle { color: #7c4a0b; }
.fbsub { margin: 2px 0 0; font-size: 12.5px; color: var(--c-text-2); line-height: 1.5; }

.fbwhy { margin: 12px 0 0; font-size: 13px; line-height: 1.7; color: var(--c-text-2); }
.fbsent {
  margin: 10px 0 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--c-text);
  font-family: var(--font-en);
}
.fbcn { color: var(--c-text-2); font-size: 12.5px; margin: 4px 0 0; line-height: 1.6; }

.fbactions { display: flex; gap: 10px; margin-top: 14px; flex-wrap: wrap; }
.audiobtn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: #fff;
  color: var(--c-primary-strong);
  border: 1px solid #cdebd9;
  border-radius: var(--r-btn);
  font-weight: 600;
  padding: 0 16px;
  min-height: 40px;
  font-size: 14px;
  cursor: pointer;
}
.audiobtn:hover { background: var(--c-primary-soft); }
.nextbtn { flex: 1; min-width: 120px; }

/* ---------- 结果 ---------- */
.done-card { text-align: center; padding: 30px 22px 24px; }
.reye {
  margin: 0 0 4px;
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.16em;
  color: var(--c-primary-strong);
}
.rbig {
  margin: 0;
  font-size: 52px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--c-text);
}
.rbig i { font-style: normal; font-size: 20px; font-weight: 700; color: var(--c-text-3); margin-left: 2px; }
.rrate { margin: 10px 0 0; font-size: 13px; color: var(--c-text-2); }
.rrate b { color: var(--c-primary-strong); font-weight: 800; }
.dotsep { margin: 0 6px; color: var(--c-line-strong); }
.actions { display: flex; gap: 10px; justify-content: center; align-items: center; margin-top: 20px; }

.fb-enter-active { transition: opacity var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out); }
.fb-enter-from { opacity: 0; transform: translateY(6px); }

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

@media (prefers-reduced-motion: reduce) {
  .optcard.right, .optcard.wrong { animation: none; }
}
</style>
