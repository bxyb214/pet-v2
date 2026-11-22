<template>
  <main class="page">
    <button class="ghost back" @click="back">← 返回听力列表</button>
    <h1>{{ label }}</h1>
    <p class="sub">听音频作答 · 点击字幕或「题 N」可跳转音频 · 提交后判分</p>

    <div v-if="!test || !pt" class="empty card">加载中…</div>
    <template v-else>
      <!-- 播放器 -->
      <div class="player card">
        <audio ref="audioEl" :src="pt.audio" preload="metadata" @timeupdate="onTime" @loadedmetadata="onMeta"></audio>
        <div class="p-controls">
          <button class="btn" @click="togglePlay">{{ playing ? "⏸ 暂停" : "▶ 播放" }}</button>
          <button class="chip" :class="{ on: rate > 1 }" @click="cycleRate">{{ rate }}x</button>
          <span class="ptime">{{ fmtTime(cur) }} / {{ fmtTime(dur) }}</span>
        </div>
        <div class="p-bar" @click="seek($event)">
          <div class="p-fill" :style="{ width: dur ? (cur / dur) * 100 + '%' : '0%' }"></div>
        </div>
      </div>

      <!-- 字幕 -->
      <div class="sub card" ref="subBox">
        <div v-for="(s, i) in pt.sentences" :key="i" class="sub-line">
          <div v-if="divAt(i)" class="sub-div" @click="jump(divAt(i)!.t0)">题 {{ divAt(i)!.no }} · 第 {{ divAt(i)!.no }} 题从这里开始 ▸</div>
          <div class="sub-text" :class="{ on: i === activeIdx }" @click="jump(s.t0)">{{ s.text }}</div>
        </div>
      </div>

      <!-- 题目 -->
      <div class="qs">
        <div v-for="(it, qi) in pt.items" :key="it.no" class="q card" :class="{ wrong: submitted && wrongSet.has(it.no), right: submitted && !wrongSet.has(it.no) }">
          <div class="q-head">
            <span class="qno">{{ it.no }}</span>
            <span class="qstem">{{ it.stem }}</span>
            <button v-if="submitted" class="chip" @click="jump(it.t0 || 0)">回听</button>
          </div>
          <img v-if="it.img" class="qimg" :src="it.img" alt="" />
          <template v-if="pt.kind === 'fill'">
            <input
              v-model="answers[it.no] as string"
              class="fill-input"
              type="text"
              :placeholder="submitted ? '已提交' : '输入答案'"
              :disabled="submitted"
            />
          </template>
          <template v-else>
            <button
              v-for="(opt, oi) in it.options ?? []" :key="oi"
              class="opt"
              :class="{
                picked: answers[it.no] === oi,
                correct: submitted && oi === it.answer,
                wrongPick: submitted && answers[it.no] === oi && oi !== it.answer,
              }"
              :disabled="submitted"
              @click="answers[it.no] = oi"
            >
              <span class="opt-key">{{ String.fromCharCode(65 + oi) }}</span>
              <img v-if="pt.kind === 'picture'" class="opt-img" :src="opt" alt="" />
              <span v-else class="opt-text">{{ opt }}</span>
            </button>
          </template>
          <div v-if="submitted && wrongSet.has(it.no)" class="q-why">
            正确答案：{{ correctText(it) }}
          </div>
        </div>
      </div>

      <!-- 提交 / 成绩 -->
      <div class="actions">
        <button v-if="!submitted" class="btn big" :disabled="answeredCount === 0" @click="submit">
          提交（{{ answeredCount }}/{{ pt.items.length }}）
        </button>
        <template v-else>
          <div class="result card" :class="{ pass: grade.right === grade.total }">
            {{ grade.right }} / {{ grade.total }} 正确
            <span v-if="grade.right === grade.total"> · 🎉 全对！</span>
          </div>
          <button class="btn ghost" @click="reset">再练一遍</button>
          <button class="btn" @click="back">返回</button>
        </template>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useLearningStore } from "../stores/learning";
import {
  activeSentenceIdx, gradePart, loadListening, mistakeKey, progressKey,
  type GradeResult, type LTest,
} from "../core/listening";

const route = useRoute();
const router = useRouter();
const learning = useLearningStore();

const test = ref<LTest | null>(null);
const partNo = ref(0);
const pt = computed(() => test.value?.parts.find((p) => p.part === partNo.value) ?? null);
const label = computed(() => (test.value ? `${test.value.title} · Part ${partNo.value}${pt.value?.label ? " · " + pt.value.label : ""}` : "听力"));

const audioEl = ref<HTMLAudioElement | null>(null);
const playing = ref(false);
const cur = ref(0);
const dur = ref(0);
const rate = ref(1);
const activeIdx = ref(-1);
const subBox = ref<HTMLElement | null>(null);

const answers = reactive<Record<number, string | number>>({});
const submitted = ref(false);
const grade = ref<GradeResult>({ right: 0, total: 0, wrongNos: [] });
const wrongSet = computed(() => new Set(grade.value.wrongNos));
const answeredCount = computed(() => Object.keys(answers).length);

onMounted(async () => {
  const d = await loadListening();
  test.value = d.tests.find((t) => t.no === Number(route.params.testNo)) ?? null;
  partNo.value = Number(route.params.part);
});

function togglePlay(): void {
  const a = audioEl.value;
  if (!a) return;
  if (a.paused) { void a.play(); playing.value = true; }
  else { a.pause(); playing.value = false; }
}
function onTime(): void {
  const a = audioEl.value;
  if (!a || !pt.value) return;
  cur.value = a.currentTime;
  const idx = activeSentenceIdx(pt.value.sentences, a.currentTime);
  if (idx !== activeIdx.value) activeIdx.value = idx;
}
function onMeta(): void {
  dur.value = audioEl.value?.duration ?? 0;
}
function cycleRate(): void {
  rate.value = rate.value === 1 ? 1.25 : 1;
  if (audioEl.value) audioEl.value.playbackRate = rate.value;
}
function seek(e: MouseEvent): void {
  const a = audioEl.value;
  if (!a || !dur.value) return;
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
  a.currentTime = Math.max(0, (e.clientX - r.left) / r.width) * dur.value;
}
function jump(t: number): void {
  const a = audioEl.value;
  if (!a) return;
  a.currentTime = t;
  if (a.paused) { void a.play(); playing.value = true; }
}
function divAt(i: number) {
  if (!pt.value) return null;
  const s = pt.value.sentences[i];
  return s.no ? s : null;
}
function fmtTime(t: number): string {
  const m = Math.floor(t / 60);
  const s = Math.floor(t % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}
function correctText(it: { answer: number | string; options: string[] | null }): string {
  if (typeof it.answer === "number" && it.options) return `${String.fromCharCode(65 + it.answer)}. ${it.options[it.answer]}`;
  return String(it.answer);
}

function submit(): void {
  if (!pt.value || !test.value) return;
  grade.value = gradePart(pt.value, answers);
  submitted.value = true;
  const book = test.value.book;
  // 错题记账：每题一维 q
  for (const no of grade.value.wrongNos) {
    learning.recordWrong(mistakeKey(book, partNo.value, no), ["q"]);
  }
  // 已在错题本且这次答对 → 划维度（recordRight 对不在错题本的键 no-op）
  for (const it of pt.value.items) {
    if (!grade.value.wrongNos.includes(it.no)) {
      learning.recordRight(mistakeKey(book, partNo.value, it.no), "q");
    }
  }
  // 完卷记进度
  if (answeredCount.value === pt.value.items.length) {
    learning.recordProgress(progressKey(book, test.value.no, partNo.value));
  }
  // 停止播放，聚焦反馈
  audioEl.value?.pause();
  playing.value = false;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function reset(): void {
  for (const k of Object.keys(answers)) delete answers[Number(k)];
  submitted.value = false;
  grade.value = { right: 0, total: 0, wrongNos: [] };
}

function back(): void {
  void router.push("/english/listening");
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.empty { padding: 40px; text-align: center; color: var(--c-text-2); }

.player { padding: 14px; margin-bottom: 14px; }
.p-controls { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.ptime { color: var(--c-text-2); font-size: var(--fs-sub); margin-left: auto; font-variant-numeric: tabular-nums; }
.p-bar { height: 8px; background: var(--c-mint-bg); border-radius: 4px; cursor: pointer; position: relative; }
.p-fill { height: 100%; background: var(--c-primary); border-radius: 4px; }

.card.sub { max-height: 260px; overflow-y: auto; padding: 10px 14px; margin-bottom: 14px; }
.sub-line { margin: 2px 0; }
.sub-div {
  background: var(--c-primary-soft); color: var(--c-primary); font-weight: 600; font-size: var(--fs-sub);
  border-radius: var(--r-sm); padding: 6px 10px; margin: 8px 0 4px; cursor: pointer;
}
.sub-text { color: var(--c-text-2); font-size: var(--fs-sub); padding: 2px 6px; cursor: pointer; border-radius: 4px; }
.sub-text.on { background: var(--c-primary-soft); color: var(--c-primary); font-weight: 600; }

.qs { display: flex; flex-direction: column; gap: 10px; }
.q { padding: 14px; }
.q.wrong { border-color: var(--c-danger); }
.q.right { border-color: var(--c-primary); }
.q-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.qno {
  background: var(--c-primary); color: #fff; border-radius: 50%;
  min-width: 26px; height: 26px; display: inline-flex; align-items: center; justify-content: center;
  font-size: var(--fs-sub); font-weight: 700;
}
.qstem { color: var(--c-text); flex: 1; }
.qimg { max-width: 100%; border-radius: var(--r-sm); margin-bottom: 10px; }
.fill-input {
  width: 100%; min-height: 44px; border: 1px solid var(--c-line); border-radius: var(--r-sm);
  padding: 8px 12px; font-size: var(--fs-body);
}
.opt {
  display: flex; align-items: center; gap: 10px; width: 100%;
  background: var(--c-mint-bg); border: 1px solid var(--c-line); border-radius: var(--r-sm);
  padding: 10px 12px; margin-bottom: 6px; cursor: pointer; text-align: left; min-height: 44px;
}
.opt.picked { border-color: var(--c-primary); background: var(--c-primary-soft); }
.opt.correct { border-color: var(--c-primary); background: var(--c-primary-soft); }
.opt.wrongPick { border-color: #e8a13c; background: #fdf6ec; }
.opt-key { font-weight: 700; color: var(--c-primary); }
.opt-img { max-height: 120px; border-radius: var(--r-sm); }
.opt-text { color: var(--c-text); }
.q-why { color: var(--c-text-2); font-size: var(--fs-sub); margin-top: 8px; }

.actions { margin: 16px 0 40px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.btn.big { min-height: 48px; padding: 0 24px; font-size: var(--fs-body); }
.result { padding: 12px 20px; font-weight: 700; color: var(--c-text); }
.result.pass { color: var(--c-primary); }
.chip {
  background: var(--c-mint-bg); border: 1px solid var(--c-line); border-radius: 999px;
  padding: 4px 12px; font-size: var(--fs-sub); cursor: pointer; color: var(--c-text-2);
}
.chip.on { background: var(--c-primary-soft); color: var(--c-primary); border-color: var(--c-primary); }
</style>
