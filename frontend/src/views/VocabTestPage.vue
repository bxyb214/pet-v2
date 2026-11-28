<template>
  <div class="page leveltest">
    <!-- 开场 -->
    <n-card v-if="stage === 'intro'" size="small" class="hero">
      <p class="eyebrow">单词量评测</p>
      <h1>你现在是 KET 还是 PET 水平？</h1>
      <p class="lead">
        从 KET / PET 词库分层抽 {{ PER_EXAM * 2 }} 个词，看英文选中文，约 5 分钟。
        测的是「认不认识」，不是拼写，不用紧张。
      </p>
      <ul class="facts">
        <li><b>{{ PER_EXAM * 2 }}</b> 道题</li>
        <li><b>KET {{ PER_EXAM }}</b> + <b>PET {{ PER_EXAM }}</b></li>
        <li>覆盖 <b>{{ Math.round(PASS_RATE * 100) }}%</b> 视为达到该级别</li>
      </ul>
      <div class="actions">
        <n-button type="primary" size="large" :disabled="!banksReady" @click="start">
          开始评测
        </n-button>
        <BackButton to="/english/words/browse" label="返回词库" variant="text" />
      </div>
      <p v-if="!banksReady" class="muted">词库加载中…</p>
      <p v-else-if="failed" class="muted">词库加载失败，请刷新页面重试。</p>
      <div v-else-if="last" class="lastbox">
        <span class="lastk">上次评测</span>
        <b>{{ headlineOf(last) }}</b>
        <span class="muted">{{ dateOf(last.at) }} · 约 {{ last.estimated.toLocaleString() }} 词</span>
      </div>
    </n-card>

    <!-- 答题 -->
    <section v-else-if="stage === 'quiz' && q" class="quizbox">
      <header class="qbar">
        <BackButton to="/english/words/browse" label="退出" variant="text" />
        <span class="cnt tnum">{{ index + 1 }} / {{ questions.length }}</span>
        <span class="exam" :class="q.item.exam">
          {{ q.item.exam === "ket" ? "KET" : "PET" }} · {{ BANK_SHORT[q.item.bank] ?? "词汇" }}
        </span>
      </header>
      <n-progress
        type="line"
        :percentage="Math.round(((index + (locked ? 1 : 0)) / questions.length) * 100)"
        :height="6"
        :show-indicator="false"
        color="#16a34a"
        rail-color="#dce8e0"
        class="qprog"
      />
      <n-card size="small" class="qcard">
        <p class="qword">{{ q.item.en }}</p>
        <div class="opts">
          <button
            v-for="(opt, i) in q.options"
            :key="opt"
            type="button"
            class="opt"
            :class="optClass(opt)"
            :disabled="locked"
            @click="answer(opt)"
          >
            <span class="no">{{ i + 1 }}</span>
            <span class="otxt">{{ opt }}</span>
            <span v-if="locked && opt === q.answer" class="mark ok" aria-hidden="true">✓</span>
            <span v-else-if="locked && opt === picked" class="mark bad" aria-hidden="true">✕</span>
          </button>
        </div>
        <button type="button" class="skip" :disabled="locked" @click="answer(null)">
          不认识，跳过
        </button>
      </n-card>
    </section>

    <!-- 结果 -->
    <section v-else-if="stage === 'result' && result" class="resultbox">
      <n-card size="small" class="verdict" :class="result.level">
        <p class="eyebrow">评测结果</p>
        <h1>{{ headlineOf(result) }}</h1>
        <p class="lead">{{ subOf(result) }}</p>
        <p class="estimate">
          识别词汇量约 <b>{{ result.estimated.toLocaleString() }}</b> 词
          <span>（基于本平台 {{ result.level === "pet" ? "PET" : "KET" }} 词库估算）</span>
        </p>
      </n-card>

      <div class="exams">
        <article v-for="e in examCards" :key="e.exam" class="exam" :class="e.verdict">
          <header>
            <b>{{ e.exam === "pet" ? "PET" : "KET" }}</b>
            <n-tag size="small" round :bordered="false" :type="tagType(e.verdict)">
              {{ VERDICT_LABEL[e.verdict] }}
            </n-tag>
          </header>
          <p class="acc tnum">{{ Math.round(e.accuracy * 100) }}<small>%</small></p>
          <p class="muted">
            答对 {{ e.correct }} / {{ e.total }} · 估算认识
            {{ e.estimated.toLocaleString() }} / {{ e.bankTotal.toLocaleString() }} 词
          </p>
          <p v-if="e.weak.length" class="weak">
            薄弱：{{ e.weak.map((w) => w.label).join(" / ") }}
          </p>
        </article>
      </div>

      <p class="note">
        每级只抽 {{ PER_EXAM }} 题，结果会有抽样误差；建议过一段时间再测一次看变化。
      </p>
      <div class="actions">
        <n-button type="primary" size="large" @click="start">再测一次</n-button>
        <n-button secondary size="large" @click="goStudy">去背薄弱词库</n-button>
        <BackButton to="/" label="返回首页" variant="text" />
      </div>
    </section>

    <LoadingBlock v-else plain text="准备中…" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCard, NProgress, NTag } from "naive-ui";
import BackButton from "../components/BackButton.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import { loadBanks, EMPTY_BANKS } from "../core/banks";
import type { WordBanks } from "../core/plan";
import {
  BANK_SHORT, PASS_RATE, PER_EXAM, VERDICT_LABEL, buildVocabTest, loadVocabResult,
  saveVocabResult, scoreVocabTest, type ExamScore, type VocabQuestion, type VocabResult,
  type Verdict,
} from "../core/vocabTest";
import { useAuthStore } from "../stores/auth";
import { useLearningStore } from "../stores/learning";

const router = useRouter();
const auth = useAuthStore();
const learning = useLearningStore();

const banks = ref<WordBanks>(EMPTY_BANKS);
const banksReady = ref(false);
const stage = ref<"intro" | "quiz" | "result">("intro");
const questions = ref<VocabQuestion[]>([]);
const chosen = ref<Array<string | null>>([]);
const index = ref(0);
const picked = ref<string | null>(null);
const locked = ref(false);
const result = ref<VocabResult | null>(null);
const last = ref<VocabResult | null>(null);
const failed = ref(false);
let timer = 0;

const owner = computed(() => learning.owner || auth.username || "");
const q = computed(() => questions.value[index.value] ?? null);
const examCards = computed<ExamScore[]>(() =>
  result.value ? [result.value.ket, result.value.pet] : [],
);

onMounted(async () => {
  last.value = loadVocabResult(owner.value);
  const r = await loadBanks().catch(() => null);
  if (r) banks.value = r.banks;
  banksReady.value = true;
});
onUnmounted(() => window.clearTimeout(timer));

function start(): void {
  if (!banksReady.value) return;
  window.clearTimeout(timer);
  const qs = buildVocabTest(banks.value);
  failed.value = qs.length === 0;
  if (!qs.length) return;
  questions.value = qs;
  chosen.value = questions.value.map(() => null);
  index.value = 0;
  picked.value = null;
  locked.value = false;
  result.value = null;
  stage.value = "quiz";
}

function answer(opt: string | null): void {
  if (locked.value || !q.value) return;
  locked.value = true;
  picked.value = opt;
  chosen.value[index.value] = opt;
  timer = window.setTimeout(() => {
    if (index.value >= questions.value.length - 1) {
      const r = scoreVocabTest(questions.value, chosen.value, banks.value);
      result.value = r;
      last.value = r;
      saveVocabResult(owner.value, r);
      stage.value = "result";
    } else {
      index.value += 1;
      picked.value = null;
    }
    locked.value = false;
  }, 460);
}

function optClass(opt: string): Record<string, boolean> {
  if (!locked.value || !q.value) return {};
  const isAnswer = opt === q.value.answer;
  return {
    right: isAnswer,
    wrong: opt === picked.value && !isAnswer,
    dim: !isAnswer && opt !== picked.value,
  };
}

function headlineOf(r: VocabResult): string {
  if (r.level === "pet") return "达到 PET 水平";
  if (r.level === "ket") return "达到 KET 水平";
  return "还没到 KET 水平";
}

function subOf(r: VocabResult): string {
  if (r.level === "pet") return "PET 抽样覆盖达到 80%，继续保持阅读和词汇计划就能稳住。";
  if (r.level === "ket") return "KET 抽样覆盖达到 80%；PET 还需要继续积累词汇。";
  return "先把 KET 必默词过一遍，再回来测一次会更有底。";
}

function tagType(v: Verdict): "success" | "warning" | "default" {
  if (v === "reached") return "success";
  if (v === "near") return "warning";
  return "default";
}

function dateOf(ts: number): string {
  return new Date(ts).toLocaleDateString("zh-CN", { month: "long", day: "numeric" });
}

/** 优先跳到当前备考级别的薄弱词库，没有就回词库页 */
function goStudy(): void {
  const own = auth.exam === "pet" ? result.value?.pet : result.value?.ket;
  const weak = own?.weak[0];
  if (weak) {
    void router.push({ path: "/english/words/study", query: { bank: weak.bank } });
    return;
  }
  void router.push("/english/words/browse");
}
</script>

<style scoped>
.leveltest { max-width: 820px; margin: 0 auto; }
.hero { padding: 6px 2px; }
.eyebrow { margin: 0 0 8px; font-size: 12px; font-weight: 800; letter-spacing: 0.08em; color: var(--c-primary-strong); }
.hero h1, .verdict h1 { margin: 0; font-size: clamp(24px, 4.4vw, 34px); line-height: 1.25; color: var(--c-text); letter-spacing: -0.02em; }
.lead { margin: 10px 0 0; font-size: 14.5px; line-height: 1.7; color: var(--c-text-2); }
.facts { display: flex; gap: 10px; flex-wrap: wrap; list-style: none; padding: 0; margin: 16px 0 0; }
.facts li { padding: 7px 12px; border: 1px solid var(--c-line); border-radius: var(--r-pill); background: var(--c-mint-bg); font-size: 12.5px; color: var(--c-text-2); }
.facts b { color: var(--c-primary-strong); }
.actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 20px; }
.lastbox { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 18px; padding: 10px 14px; border-radius: 12px; background: var(--c-primary-soft); font-size: 13px; color: var(--c-text-2); }
.lastk { font-weight: 800; color: var(--c-primary-strong); }
.lastbox b { color: var(--c-text); }

.qbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.cnt { margin-left: auto; font-size: 13px; font-weight: 800; color: var(--c-text-2); }
.exam { font-size: 11px; font-weight: 800; padding: 3px 9px; border-radius: var(--r-pill); background: var(--c-info-soft); color: var(--c-info); }
.exam.pet { background: var(--c-accent-soft); color: var(--c-accent); }
.qprog { margin-bottom: 12px; }
.qcard { text-align: center; padding: 10px 4px 4px; }
.qword {
  margin: 8px 0 20px; font-family: var(--font-word); font-weight: 800;
  font-size: clamp(28px, 6vw, 44px); line-height: 1.3; color: var(--c-text);
  word-break: break-word; overflow-wrap: anywhere;
}
.opts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.opt {
  display: flex; align-items: center; gap: 10px; min-height: 56px; padding: 10px 14px;
  border: 1px solid var(--c-line); border-radius: 14px; background: var(--c-surface);
  font: inherit; font-size: 15px; font-weight: 600; color: var(--c-text); text-align: left;
  cursor: pointer; transition: border-color var(--dur-2), background var(--dur-2);
}
.opt:hover:not(:disabled) { border-color: var(--c-line-strong); background: var(--c-mint-bg); }
.opt:disabled { cursor: default; }
.opt.right { border-color: #86cf9f; background: var(--c-primary-soft); }
.opt.wrong { border-color: #e7a4a4; background: #fdf0f0; }
.opt.dim { opacity: 0.55; }
.no {
  flex: none; width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center;
  background: var(--c-mint-bg); font-size: 12px; font-weight: 800; color: var(--c-text-2);
}
.otxt { flex: 1; }
.mark { font-weight: 800; }
.mark.ok { color: var(--c-primary-strong); }
.mark.bad { color: #c2410c; }
.skip {
  margin-top: 16px; border: 0; background: none; font: inherit; font-size: 12.5px;
  color: var(--c-text-3); cursor: pointer; text-decoration: underline; text-underline-offset: 3px;
}
.skip:disabled { opacity: 0.4; cursor: default; }

.verdict { padding: 4px 2px; }
.verdict.ket { border-left: 4px solid var(--c-info); }
.verdict.pet { border-left: 4px solid var(--c-primary-strong); }
.verdict.below { border-left: 4px solid var(--c-line-strong); }
.estimate { margin: 14px 0 0; font-size: 14.5px; color: var(--c-text-2); }
.estimate b { font-size: 22px; color: var(--c-primary-strong); }
.estimate span { font-size: 12.5px; color: var(--c-text-3); }
.exams { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }
.exam { border: 1px solid var(--c-line); border-radius: 14px; padding: 14px 16px; background: var(--c-surface); }
.exam.reached { border-color: #bfe3d1; }
.exam header { display: flex; align-items: center; gap: 8px; }
.exam header b { font-size: 14px; }
.acc { margin: 8px 0 2px; font-size: 30px; font-weight: 800; color: var(--c-text); line-height: 1.1; }
.acc small { font-size: 15px; color: var(--c-text-3); margin-left: 2px; }
.weak { margin: 8px 0 0; font-size: 12px; color: var(--c-accent); }
.note { margin: 14px 2px 0; font-size: 12.5px; color: var(--c-text-3); line-height: 1.6; }
.muted { color: var(--c-text-2); font-size: 13px; }

@media (max-width: 640px) {
  .opts { grid-template-columns: 1fr; }
  .exams { grid-template-columns: 1fr; }
  .actions { gap: 8px; }
}
</style>
