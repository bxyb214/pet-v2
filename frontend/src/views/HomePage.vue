<template>
  <main class="page home">
    <header class="greet">
      <div>
        <h1>{{ greetText }}，{{ userName }}</h1>
        <p>{{ dateText }} · 今天也一起点亮火焰吧</p>
      </div>
      <div v-if="progress.total" class="goal" :title="`今日完成 ${progress.done}/${progress.total} 项`">
        <span class="ring" :style="ringStyle"><i>{{ progress.done }}/{{ progress.total }}</i></span>
        <span class="goal-txt">
          <b>今日 {{ progress.done }} / {{ progress.total }}</b>
          <span>英语计划完成度</span>
        </span>
      </div>
    </header>

    <section class="todaybar" aria-label="今天的学习任务">
      <span class="tag">今天</span>
      <div v-if="progress.total" class="items">
        <span v-for="t in activeTasks" :key="t.key" class="it" :class="{ done: t.done }">
          <i class="dot" :class="t.done ? 'done' : 'doing'" aria-hidden="true"></i>
          {{ t.label }} <small>{{ t.short }}</small>
        </span>
      </div>
      <div v-else class="today-empty">
        <span>还没有学习计划</span>
        <button type="button" class="mini solid" @click="go('/english/words/plan')">创建单词计划</button>
        <button type="button" class="mini" @click="go('/english/words/browse')">先随便学</button>
      </div>
      <button v-if="progress.total" type="button" class="mini solid continue" @click="go(continueRoute)">
        {{ continueLabel }}
      </button>
    </section>

    <section class="leveltest" aria-label="单词量评测">
      <span class="lt-ic"><n-icon :component="RibbonOutline" size="18" /></span>
      <div class="lt-txt">
        <b>单词量评测</b>
        <span>{{ levelSub }}</span>
      </div>
      <button type="button" class="lt-btn" @click="go('/english/words/level-test')">
        {{ vocabLast ? "看上次结果" : "开始评测" }}
      </button>
    </section>

    <section class="subject en">
      <header class="subject-head">
        <span class="s-badge en"><n-icon :component="LanguageOutline" size="17" /></span>
        <h2>英语</h2>
        <span class="meta">{{ examText }} · {{ moduleCount }} 个板块</span>
        <span class="stat">{{ progress.total ? `今日 ${progress.done} / ${progress.total}` : "还没有计划" }}</span>
        <router-link class="go" to="/english/words/browse">进入英语 →</router-link>
      </header>
      <div class="modgrid en" :class="{ few: moduleCount < 5 }">
        <router-link v-if="hasModule('words')" class="mod" to="/english/words/browse">
          <span class="top"><span class="m-ic g"><n-icon :component="ReaderOutline" size="15" /></span>单词</span>
          <span class="status">
            <span v-if="words.hasPlan" class="mini-tag" :class="{ done: words.todayDone }">{{ words.todayDone ? "今日已完成" : "今日" }}</span>
            <template v-if="words.hasPlan">第 {{ words.day }} 天<br>待复习 {{ dueMistakes }} 词</template>
            <template v-else>还没有词汇计划</template>
          </span>
        </router-link>

        <router-link v-if="hasModule('reading')" class="mod" to="/english/reading/home">
          <span class="top"><span class="m-ic b"><n-icon :component="LibraryOutline" size="15" /></span>阅读</span>
          <span class="status">
            <span v-if="reading.hasPlan" class="mini-tag" :class="{ done: reading.todayDone }">{{ reading.todayDone ? "今日已完成" : "今日" }}</span>
            <template v-if="reading.hasPlan">第 {{ reading.day }} 天<br>{{ reading.doneDays }}/{{ reading.totalDays }} 天已完成</template>
            <template v-else>还没有阅读计划</template>
          </span>
        </router-link>

        <router-link v-if="hasModule('listening')" class="mod" to="/english/listening/home">
          <span class="top"><span class="m-ic b"><n-icon :component="HeadsetOutline" size="15" /></span>听力</span>
          <span class="status">六套真题<br>纯播放器</span>
        </router-link>

        <router-link v-if="hasModule('speak')" class="mod" to="/english/speak">
          <span class="top"><span class="m-ic o"><n-icon :component="MicOutline" size="15" /></span>口语</span>
          <span class="status">
            <span v-if="speak.hasPlan" class="mini-tag" :class="{ done: speak.todayDone }">{{ speak.todayDone ? "今日已完成" : "今日" }}</span>
            <template v-if="speak.hasPlan">第 {{ speak.day }} 天<br>今日开口 {{ formatTime(speakTime.shadow) }}</template>
            <template v-else>45 场景 · 自由练习</template>
          </span>
        </router-link>
      </div>
      <p v-if="moduleNote" class="module-note">{{ moduleNote }}</p>
    </section>

    <section class="subject ma">
      <header class="subject-head">
        <span class="s-badge ma"><n-icon :component="CalculatorOutline" size="17" /></span>
        <h2>数学</h2>
        <span class="meta">李永乐一课通关<template v-if="mathView.gradeName"> · {{ mathView.gradeName }}</template></span>
        <span class="stat">{{ mathView.detail }}</span>
        <router-link class="go" to="/math">进入数学 →</router-link>
      </header>
      <div class="modgrid ma">
        <router-link class="mod" :to="mathView.route">
          <span class="top"><span class="m-ic y"><n-icon :component="PlayCircleOutline" size="15" /></span>一课通关</span>
          <span class="status">{{ mathActionText }}<br>{{ mathView.grades }}</span>
        </router-link>
        <router-link class="mod" to="/math/progress">
          <span class="top"><span class="m-ic b"><n-icon :component="StatsChartOutline" size="15" /></span>学习进度</span>
          <span class="status">{{ mathView.detail }}<br>按年级查看进度墙</span>
        </router-link>
      </div>
    </section>

    <section class="subject cn">
      <header class="subject-head">
        <span class="s-badge cn"><n-icon :component="BookOutline" size="17" /></span>
        <h2>语文</h2>
        <span class="meta">筹备中</span>
        <span class="stat">即将上线</span>
      </header>
      <div class="modgrid cn">
        <div v-for="m in chineseModules" :key="m.name" class="mod off">
          <span class="top">{{ m.name }}<span class="soon">筹备中</span></span>
          <span class="status">{{ m.desc }}</span>
        </div>
      </div>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NIcon } from "naive-ui";
import {
  BookOutline, CalculatorOutline, HeadsetOutline, LanguageOutline,
  LibraryOutline, MicOutline, PlayCircleOutline, ReaderOutline, RibbonOutline,
  StatsChartOutline,
} from "@vicons/ionicons5";
import { api } from "../core/api";
import {
  greetingOf, nextSpeakRoute, overallProgress, pickContinue, planProgress, speakProgress, summarizeMath,
} from "../core/home";
import { formatTime, lessonKey, loadMath, type MathData, type VideoRec } from "../core/math";
import { englishModulesFor, moduleAvailable } from "../core/examContent";
import { loadVocabResult, PER_EXAM, type VocabResult } from "../core/vocabTest";
import type { DayCheck } from "../core/speak";
import { useAuthStore } from "../stores/auth";
import { useLearningStore } from "../stores/learning";

type TaskKey = "words" | "reading" | "speak";
type TodayTask = {
  key: TaskKey; label: string; short: string;
  exists: boolean; done: boolean; route: string;
};

const router = useRouter();
const auth = useAuthStore();
const learning = useLearningStore();

const speakLength = ref(0);
const speakChecks = ref<DayCheck[]>([]);
const speakTime = ref({ shadow: 0, make: 0, talk: 0 });
const mathData = ref<MathData | null>(null);
const vocabLast = ref<VocabResult | null>(null);

const userName = computed(() => auth.displayName || auth.username || "同学");
const greetText = computed(() => greetingOf(new Date().getHours()));
const dateText = new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric", weekday: "long" });
const EXAM_TEXT: Record<string, string> = {
  pet: "PET 备考", ket: "KET 备考", fce: "FCE 备考", junior: "初中英语同步",
};
const examText = computed(() => EXAM_TEXT[auth.exam] ?? "英语学习");
const moduleCount = computed(() => englishModulesFor(auth.exam).length);
const hasModule = (m: string) => moduleAvailable(auth.exam, m);
/** 首页评测入口：显示上次结果，没测过就给一句说明 */
const levelSub = computed(() => {
  const r = vocabLast.value;
  if (!r) return `${PER_EXAM * 2} 道题，看看有没有达到 KET / PET 标准`;
  const lv = r.level === "pet" ? "PET 水平" : r.level === "ket" ? "KET 水平" : "KET 以下";
  const d = new Date(r.at).toLocaleDateString("zh-CN", { month: "numeric", day: "numeric" });
  return `上次：${lv} · ${d} · 约 ${r.estimated.toLocaleString()} 词`;
});
const moduleNote = computed(() => {
  if (moduleCount.value >= 5) return "";
  if (auth.exam === "ket") return "KET 已上线词库、阅读（含语法）、听力（5 本 24 套音频）与口语（45 个场景）；口语可按 45 天计划练习。";
  return `${examText.value} 已上线 ${moduleCount.value} 个板块，其余内容整理中。`;
});

const words = computed(() => planProgress(learning.data.plan.length, learning.data.plan.days_done));
const reading = computed(() => planProgress(
  learning.data.plan.reading_length,
  learning.data.plan.reading_days_done,
));
const speak = computed(() => speakProgress(speakLength.value, speakChecks.value));
const dueMistakes = computed(() => learning.dueMistakes.length);
const speakRoute = computed(() => nextSpeakRoute(speak.value.day, speakChecks.value));

const tasks = computed<TodayTask[]>(() => {
  const all: TodayTask[] = [
    {
      key: "words", label: "单词", exists: words.value.hasPlan, done: words.value.todayDone,
      short: words.value.todayDone ? "已完成" : `第 ${words.value.day} 天`,
      route: `/english/words/study?day=${words.value.day}`,
    },
    {
      key: "reading", label: "阅读", exists: reading.value.hasPlan, done: reading.value.todayDone,
      short: reading.value.todayDone ? "已完成" : `第 ${reading.value.day} 天`,
      route: "/english/reading/home",
    },
    {
      key: "speak", label: "口语", exists: speak.value.hasPlan, done: speak.value.todayDone,
      short: speak.value.todayDone
        ? "已完成"
        : speakTime.value.shadow ? `跟读 ${formatTime(speakTime.value.shadow)}` : `第 ${speak.value.day} 天`,
      route: speakRoute.value,
    },
  ];
  return all.filter((t) => hasModule(t.key));
});
const activeTasks = computed(() => tasks.value.filter((t) => t.exists));
const progress = computed(() => overallProgress(tasks.value));
const continueRoute = computed(() => pickContinue(tasks.value, "/english/words/browse"));
const continueLabel = computed(() =>
  progress.value.total > 0 && progress.value.done >= progress.value.total ? "今天已完成 · 自由练习" : "继续",
);
const ringStyle = computed(() => {
  const pct = progress.value.total
    ? Math.round((progress.value.done / progress.value.total) * 100)
    : 0;
  return { background: `conic-gradient(var(--c-primary) 0 ${pct}%, var(--c-line) ${pct}% 100%)` };
});

function recOf(id: string): VideoRec | null {
  return learning.progressOf(lessonKey(id));
}
const mathView = computed(() => {
  const sum = summarizeMath(mathData.value?.books ?? [], recOf);
  if (sum.hasBooks) return sum;
  // 读取 math.json 前/失败时给稳定的静态信息，避免出现「还没有开始」的误导
  return { ...sum, grades: "三年级 / 四年级已上线", detail: "查看课程与学习进度" };
});
const mathActionText = computed(() => {
  if (mathView.value.lessonLabel) return `继续 ${mathView.value.lessonLabel}`;
  const { done, total } = mathView.value;
  return total > 0 && done >= total ? "本轮课程已学完" : "选择年级开始";
});
const chineseModules = [
  { name: "识字与词汇", desc: "按年级同步生字与词语" },
  { name: "古诗文", desc: "课内必背 + 理解" },
  { name: "阅读理解", desc: "短文精读与题型训练" },
  { name: "写作表达", desc: "看图写话与作文" },
];

function go(path: string): void {
  void router.push(path);
}

onMounted(async () => {
  vocabLast.value = loadVocabResult(learning.owner || auth.username || "");
  const [plan, days, time, md] = await Promise.allSettled([
    api<{ length: number }>("/speak/plan"),
    api<{ days: DayCheck[] }>("/speak/days"),
    api<{ totals: { shadow: number; make: number; talk: number } }>("/speak/time/today"),
    loadMath(),
  ]);
  if (plan.status === "fulfilled") speakLength.value = Number(plan.value.length) || 0;
  if (days.status === "fulfilled") speakChecks.value = days.value.days ?? [];
  if (time.status === "fulfilled") {
    const t = time.value.totals;
    speakTime.value = {
      shadow: Number(t?.shadow) || 0,
      make: Number(t?.make) || 0,
      talk: Number(t?.talk) || 0,
    };
  }
  if (md.status === "fulfilled") mathData.value = md.value;
});
</script>

<style scoped>
.home { display: flex; flex-direction: column; }
.greet { display: flex; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.greet h1 { margin: 0; font-size: var(--fs-display); color: var(--c-text); letter-spacing: -0.02em; }
.greet p { margin: 6px 0 0; color: var(--c-text-2); font-size: var(--fs-sub); }
.goal { margin-left: auto; display: flex; align-items: center; gap: 10px; background: var(--c-surface); border: 1px solid var(--c-line); border-radius: 999px; padding: 7px 14px 7px 8px; box-shadow: var(--shadow-card); }
.ring { width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center; flex: none; }
.ring i { width: 28px; height: 28px; border-radius: 50%; background: var(--c-surface); display: grid; place-items: center; font-style: normal; font-size: 10px; font-weight: 800; color: var(--c-primary-strong); font-variant-numeric: tabular-nums; }
.goal-txt b { display: block; font-size: 13px; color: var(--c-text); }
.goal-txt span { display: block; font-size: 11.5px; color: var(--c-text-2); margin-top: 1px; }

.todaybar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 14px; margin-bottom: 14px; border-radius: 15px; background: linear-gradient(100deg, var(--c-primary-soft), var(--c-mint-bg)); border: 1px solid var(--c-line-strong); }
.tag { font-size: 11px; font-weight: 800; color: var(--c-primary-strong); background: var(--c-surface); border: 1px solid var(--c-line-strong); border-radius: 999px; padding: 3px 9px; flex: none; }
.items { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; min-width: 0; }
.it { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: var(--c-text); white-space: nowrap; }
.it small { font-weight: 500; color: var(--c-text-2); font-size: 12px; }
.it.done { color: var(--c-text-2); }
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex: none; }
.dot.done { background: var(--c-primary); }
.dot.doing { background: var(--c-accent); }
.today-empty { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--c-text-2); font-size: 13px; }
.continue { margin-left: auto; }
.mini { border: 1px solid var(--c-line-strong); background: var(--c-surface); color: var(--c-primary-strong); border-radius: 10px; padding: 7px 13px; font: inherit; font-size: 12.5px; font-weight: 800; cursor: pointer; min-height: 44px; }
.mini.solid { background: var(--c-primary-strong); border-color: var(--c-primary-strong); color: #fff; }
.mini:active { transform: scale(0.985); }

.leveltest { display: flex; align-items: center; gap: 12px; padding: 12px 14px; margin-bottom: 14px; border-radius: 15px; border: 1px solid var(--c-line-strong); background: var(--c-surface); box-shadow: var(--shadow-card); }
.lt-ic { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; flex: none; background: var(--c-accent-soft); color: var(--c-accent); }
.lt-txt { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.lt-txt b { font-size: 13.5px; color: var(--c-text); }
.lt-txt span { font-size: 11.5px; color: var(--c-text-2); }
.lt-btn { margin-left: auto; flex: none; min-height: 40px; padding: 8px 15px; border: 1px solid var(--c-primary-strong); border-radius: 10px; background: var(--c-primary-strong); color: #fff; font: inherit; font-size: 12.5px; font-weight: 800; cursor: pointer; }
.lt-btn:active { transform: scale(0.985); }

.subject { margin-bottom: 16px; }
.subject-head { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; margin: 0 2px 8px; }
.subject-head h2 { margin: 0; font-size: 16px; color: var(--c-text); }
.s-badge { width: 30px; height: 30px; border-radius: 10px; display: grid; place-items: center; flex: none; }
.s-badge.en { background: var(--c-primary-soft); color: var(--c-primary-strong); }
.s-badge.ma { background: var(--c-info-soft); color: var(--c-info); }
.s-badge.cn { background: var(--c-accent-soft); color: var(--c-accent); }
.meta { color: var(--c-text-3); font-size: 12px; }
.stat { margin-left: auto; color: var(--c-text-2); font-size: 12px; font-weight: 600; }
.go { color: var(--c-primary-strong); font-size: 12.5px; font-weight: 800; text-decoration: none; white-space: nowrap; }
.go:hover { text-decoration: underline; }
.ma .go { color: var(--c-info); }

.modgrid { display: grid; gap: 9px; }
.modgrid.en { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.modgrid.en.few { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); }
.modgrid.ma { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.modgrid.cn { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.module-note {
  margin: 10px 2px 0; font-size: 12.5px; color: var(--c-text-2, #6b7f74); line-height: 1.6;
}
.mod { position: relative; text-align: left; background: var(--c-surface); border: 1px solid var(--c-line); border-radius: 14px; padding: 11px 12px; display: flex; flex-direction: column; gap: 7px; min-height: 90px; box-shadow: var(--shadow-card); text-decoration: none; color: var(--c-text); transition: border-color 0.12s, transform 0.12s; }
a.mod:hover { border-color: var(--c-line-strong); transform: translateY(-1px); }
.mod .top { display: flex; align-items: center; gap: 7px; font-weight: 800; font-size: 13.5px; }
.m-ic { width: 26px; height: 26px; border-radius: 8px; display: grid; place-items: center; flex: none; }
.m-ic.g { background: var(--c-primary-soft); color: var(--c-primary-strong); }
.m-ic.b { background: var(--c-info-soft); color: var(--c-info); }
.m-ic.o { background: var(--c-accent-soft); color: var(--c-accent); }
.m-ic.y { background: var(--c-info-soft); color: var(--c-info); }
.mod .status { color: var(--c-text-2); font-size: 11.5px; line-height: 1.55; margin-top: auto; }
.mini-tag { display: inline-block; font-size: 10px; font-weight: 800; color: var(--c-accent); background: var(--c-accent-soft); border-radius: 999px; padding: 1px 6px; margin-bottom: 3px; }
.mini-tag.done { color: var(--c-primary-strong); background: var(--c-primary-soft); }
.mod.off { border-style: dashed; border-color: var(--c-line-strong); background: var(--c-accent-soft); color: var(--c-text-3); cursor: default; }
.mod.off .top { color: var(--c-text-2); }
.mod.off .soon { margin-left: auto; font-size: 9.5px; font-weight: 800; color: var(--c-accent); }

@media (max-width: 1100px) {
  .modgrid.en { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .modgrid.cn { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 767px) {
  .greet h1 { font-size: var(--fs-title); }
  .goal { display: none; }
  .todaybar .continue { margin-left: 0; }
  .modgrid.en { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .modgrid.ma { grid-template-columns: 1fr; }
  .subject-head .stat { display: none; }
}
</style>
