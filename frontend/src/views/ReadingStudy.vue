<template>
  <main class="page" v-if="sent">
    <div class="topbar">
      <BackButton to="/english/reading/home" label="返回阅读" variant="text" />
      <p class="label">{{ label }}</p>
      <span class="pos tnum">{{ idx + 1 }} / {{ sentences.length }}</span>
    </div>

    <!-- 一句一段：看到哪、还剩几句 -->
    <div class="segs" aria-hidden="true">
      <i
        v-for="(s, i) in sentences"
        :key="s.id"
        class="seg"
        :class="{ read: i < idx, now: i === idx }"
      ></i>
    </div>

    <section class="card">
      <!-- 先读英文；翻译与解析默认收起，自己想一遍再揭晓 -->
      <div class="en-row">
        <p class="en">{{ sent.en }}</p>
        <button class="speak" aria-label="朗读整句" :disabled="audioPending(sent.en)" @click="say(sent.en)">
          <span v-if="audioPending(sent.en)" class="audio-spin" aria-hidden="true" />
          <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 5 6.5 9H3v6h3.5L11 19V5Z" />
            <path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" />
          </svg>
        </button>
      </div>

      <p v-if="sent.tense" class="tense"><span>时态</span>{{ sent.tense }}</p>

      <!-- 未展开：一个安静的「揭晓」入口 -->
      <button v-if="!show" class="reveal" @click="show = true">
        <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
          <circle cx="12" cy="12" r="2.8" />
        </svg>
        先自己读一遍，点这里看翻译与解析
      </button>

      <transition name="reveal-fade">
        <div v-if="show" class="detail">
          <p class="cn">{{ sent.cn }}</p>

          <section v-if="sent.parse?.length" class="blk">
            <h4>成分拆解</h4>
            <div class="parse">
              <span v-for="(p, i) in sent.parse" :key="i" class="ptag" :class="roleCls(p.r)">
                <i>{{ p.r }}</i><b>{{ p.t }}</b>
              </span>
            </div>
          </section>

          <section v-if="sent.gram?.length" class="blk">
            <h4>语法点</h4>
            <div class="grams">
              <div v-for="g in sent.gram" :key="g.c" class="gp">
                <button class="gtag" :title="`去练考点 ${g.c}`" @click="goGrammar(g.c)">
                  DAY {{ gMap[g.c]?.day ?? "–" }} · {{ g.c }}
                </button>
                <div class="gp-body">
                  <b>{{ g.g || gMap[g.c]?.name || ("考点 " + g.c) }}</b>
                  <span>{{ g.d }}</span>
                </div>
              </div>
            </div>
          </section>

          <section v-if="sent.point" class="blk">
            <h4>本句考点</h4>
            <p class="point">{{ sent.point }}</p>
          </section>

          <section v-if="sent.note" class="blk">
            <h4>注意</h4>
            <p class="note">{{ sent.note }}</p>
          </section>
        </div>
      </transition>

      <div class="actions">
        <button v-if="show" class="ghost" @click="show = false">收起解析</button>
        <button class="ghost" :disabled="idx === 0" @click="idx--">上一句</button>
        <button class="btn" @click="advance">{{ isLast ? "去做题" : "下一句" }}</button>
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
  loadReading, withCustomSentences,
  type RGrammar, type RSentence,
} from "../core/reading";
import { audioPending, say } from "../core/say";

const route = useRoute();
const router = useRouter();
const learning = useLearningStore();
const auth = useAuthStore();
const sentences = ref<RSentence[]>([]);
const grammar = ref<RGrammar | null>(null);
const idx = ref(0);
const label = ref("");
const testNo = ref(0);
const part = ref(0);
const studyKey = ref("");
const show = ref(false);

const sent = computed(() => sentences.value[idx.value] ?? null);
const isLast = computed(() => idx.value >= sentences.value.length - 1);

/** 考点编号 → 所属天与名称（语法点标签用） */
const gMap = computed<Record<number, { day: number; name: string }>>(() => {
  const m: Record<number, { day: number; name: string }> = {};
  for (const d of grammar.value?.days ?? []) {
    for (const p of d.points) m[p.c] = { day: d.day, name: p.name };
  }
  return m;
});

/** 成分 → 配色类：主语/谓语/宾语/状语/修饰，五色区分（沿用旧站的语义配色） */
function roleCls(r: string): string {
  const s = r || "";
  if (/主语/.test(s)) return "s";
  if (/谓语/.test(s)) return "v";
  if (/宾语|表语|补语/.test(s)) return "o";
  if (/状语/.test(s)) return "a";
  if (/定语|同位语|插入语/.test(s)) return "m";
  return "";
}

onMounted(async () => {
  const d = withCustomSentences(await loadReading(auth.exam), learning.data.custom_sentences);
  grammar.value = d.grammar;
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
    show.value = false; // 下一句重新藏起来
    learning.setStudyIdx(studyKey.value, idx.value); // R7 精读进度持久化
  } else {
    learning.recordProgress(studyKey.value); // 学完记完成日期
    goQuiz();
  }
}

function goQuiz(): void {
  void router.push({ path: `/english/reading/quiz/${testNo.value}`, query: { part: String(part.value) } });
}
function goGrammar(c: number): void {
  void router.push({ path: "/english/reading/quiz/0", query: { gc: String(c), label: gMap.value[c]?.name ?? "" } });
}
</script>

<style scoped>
.page { width: 100%; }

.topbar { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.label { flex: 1; margin: 0; color: var(--c-text-2); font-size: 13px; }
.pos { color: var(--c-text-3); font-size: 12.5px; }

.segs { display: flex; gap: 4px; margin-bottom: 16px; }
.seg {
  flex: 1 1 0; height: 5px; border-radius: 999px; background: var(--c-line);
  transition: background var(--dur-2) var(--ease-out);
}
.seg.read { background: #a7dcbd; }
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
  padding: 22px 24px 20px;
}

.en-row { display: flex; align-items: flex-start; gap: 12px; }
.en {
  flex: 1;
  margin: 0;
  font-family: var(--font-en);
  font-size: clamp(19px, 2.4vw, 24px);
  line-height: 1.58;
  font-weight: 600;
  letter-spacing: 0.1px;
  color: var(--c-text);
  overflow-wrap: anywhere;
}
.speak {
  flex: none;
  width: 40px; height: 40px;
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  border: 0; cursor: pointer;
  transition: background var(--dur-2) var(--ease-out), transform var(--dur-1) var(--ease-out);
}
.speak:hover { background: #d6f0e0; }
.speak:active { transform: scale(0.94); }

.tense {
  display: inline-flex; align-items: baseline; gap: 7px;
  margin: 14px 0 0;
  font-size: 12.5px; color: var(--c-text-2);
}
.tense span {
  font-size: 11px; font-weight: 700; color: var(--c-text-3);
  background: #f3f7f5; border-radius: var(--r-pill); padding: 2px 7px;
}

/* 揭晓入口：虚线 + 安静的颜色，不抢主句 */
.reveal {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: 100%; min-height: 52px; margin: 18px 0 0;
  border: 1px dashed var(--c-line-strong); border-radius: var(--r-btn);
  background: #fcfefd; color: var(--c-text-2);
  font-size: 13px; cursor: pointer;
  transition: border-color var(--dur-2) var(--ease-out), color var(--dur-2) var(--ease-out),
    background var(--dur-2) var(--ease-out);
}
.reveal:hover { border-color: #a9dcc0; color: var(--c-primary-strong); background: #f7fdf9; }

.detail { margin-top: 18px; }
.cn {
  margin: 0 0 16px;
  font-size: 15px;
  line-height: 1.75;
  color: var(--c-text);
}

.blk { margin-bottom: 16px; }
.blk:last-child { margin-bottom: 0; }
.blk h4 {
  margin: 0 0 8px;
  font-size: 11.5px; font-weight: 700; letter-spacing: 0.08em;
  color: var(--c-text-3);
}

/* ---------- 成分拆解：五色语义编码 ---------- */
.parse { display: flex; flex-wrap: wrap; gap: 7px; }
.ptag {
  display: inline-flex; align-items: baseline; gap: 6px;
  padding: 5px 10px;
  border-radius: 10px;
  border: 1px solid var(--c-line);
  background: #fff;
  font-size: 13px;
}
.ptag i { font-style: normal; font-size: 11px; font-weight: 700; }
.ptag b { font-family: var(--font-en); font-weight: 600; color: var(--c-text); }

.ptag.s { background: #f2f7ff; border-color: #cfe0ff; }
.ptag.s i { color: #2f6fed; }
.ptag.v { background: #fff5f2; border-color: #ffd8cf; }
.ptag.v i { color: #d9503a; }
.ptag.o { background: #f1fbf9; border-color: #cdeee9; }
.ptag.o i { color: #0f8c80; }
.ptag.a { background: #faf6ff; border-color: #e6dcf7; }
.ptag.a i { color: #6b4fce; }
.ptag.m { background: #fffaf1; border-color: #f3e4c8; }
.ptag.m i { color: #9c6c17; }

/* ---------- 语法点 ---------- */
.grams { display: grid; gap: 8px; }
.gp {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 10px 12px;
  border-radius: var(--r-sm);
  background: #fafcfb;
  border: 1px solid var(--c-line);
}
.gtag {
  flex: none;
  background: var(--c-primary-soft); color: var(--c-primary-strong);
  border: 0; border-radius: var(--r-pill);
  padding: 3px 9px;
  font-size: 11px; font-weight: 800; letter-spacing: 0.02em;
  cursor: pointer; white-space: nowrap;
  transition: background var(--dur-2) var(--ease-out);
}
.gtag:hover { background: #d6f0e0; }
.gp-body { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.gp-body b { font-size: 13.5px; font-weight: 700; color: var(--c-text); line-height: 1.5; }
.gp-body span { font-size: 12.5px; color: var(--c-text-2); line-height: 1.7; }

.point { margin: 0; font-size: 13.5px; color: var(--c-text); line-height: 1.7; }
.note { margin: 0; font-size: 13px; color: var(--c-text-2); line-height: 1.75; }

/* ---------- 操作 ---------- */
.actions { display: flex; align-items: center; gap: 8px; margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--c-line); }
.btn {
  margin-left: auto;
  min-height: 46px; padding: 0 22px;
  background: var(--c-primary-strong); color: #fff;
  border: 0; border-radius: var(--r-btn);
  font-size: 15px; font-weight: 700; font-family: inherit; cursor: pointer;
  transition: background var(--dur-2) var(--ease-out);
}
.btn:hover { background: #166534; }
.ghost {
  background: none; border: 0;
  color: var(--c-text-2); font-size: 14px; font-weight: 600;
  min-height: 44px; padding: 0 10px; border-radius: var(--r-sm); cursor: pointer;
  font-family: inherit;
}
.ghost:hover:not(:disabled) { color: var(--c-primary-strong); background: var(--c-primary-soft); }
.ghost:disabled { opacity: 0.35; cursor: not-allowed; }

.reveal-fade-enter-active { transition: opacity var(--dur-3) var(--ease-out), transform var(--dur-3) var(--ease-out); }
.reveal-fade-enter-from { opacity: 0; transform: translateY(6px); }

@media (max-width: 767px) {
  .card { padding: 16px 14px 14px; }
  .en { font-size: 19px; }
  .ptag { font-size: 12.5px; padding: 4px 8px; }
  .gp { padding: 9px 10px; }
  .actions { flex-wrap: wrap; }
  .btn { margin-left: 0; flex: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .seg.now { animation: none; background: #86efac; }
}
</style>
