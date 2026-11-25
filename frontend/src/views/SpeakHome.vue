<template>
  <main class="page">
    <h1>口语</h1>
    <p class="sub">每天 5 分钟跟读 + 10 分钟造句 + 15 分钟自由对话（10 分钟对话 + 5 分钟复盘）</p>
    <div v-if="banner" class="aibanner" :class="banner.tone">{{ banner.text }}</div>

    <LoadingBlock v-if="!authReady" />
    <template v-else>
      <!-- 今日已用（只记录不限流）：放在日历上方 -->
      <PaidAiNotice v-if="loaded" :status="aiStatus" prominent />
      <div v-if="loaded && hasPlan && (usage || timeTotals)" class="card usage">
        <span v-if="timeTotals">今日开口：跟读 <b>{{ fmtSec(timeTotals.shadow) }}</b> · 造句 <b>{{ fmtSec(timeTotals.make) }}</b> · 对话 <b>{{ fmtSec(timeTotals.talk) }}</b></span>
        <span v-if="usage">跟读评测 <b>{{ usage.soe_calls }}</b> 次</span>
        <span v-if="usage" class="cost">预估 {{ (usage.est_cost_milli / 1000).toFixed(2) }} 元</span>
        <span v-if="aiStatus" class="cost">AI 额度剩余 {{ (aiStatus.remaining_milli / 1000).toFixed(2) }} 元</span>
      </div>

      <!-- 每日入口：5 + 10 + 15；作用于日历中选中的那天 -->
      <section v-if="loaded && hasPlan" class="entries" aria-label="每日口语练习入口">
        <div class="entry-head">
          <span class="entry-day">{{ pickedDay === null ? "今天" : "已选" }} · 第 {{ activeDay }} 天</span>
          <span v-if="hasPlan" class="entry-hint">点下方日历可切换练习日</span>
          <n-button v-if="pickedDay !== null" size="tiny" quaternary @click="setPickedDay(null)">回到今天</n-button>
        </div>
        <div class="entry-grid">
          <button class="entry card" @click="goShadow(activeDay)">
            <b><n-icon :component="MicOutline" size="18" />跟读纠音 · 5 分钟</b>
            <span>逐句跟读 · AI 打分与建议</span>
          </button>
          <button class="entry card" @click="goMake(activeDay)">
            <b><n-icon :component="CreateOutline" size="18" />造句练习 · 10 分钟</b>
            <span>PET 常用句型 · AI 点评优化</span>
          </button>
          <button class="entry card" @click="goTalk(activeDay)">
            <b><n-icon :component="ChatbubblesOutline" size="18" />自由对话 · 15 分钟</b>
            <span>10 分钟对话 + 5 分钟复盘 · 边说边优化</span>
          </button>
        </div>
      </section>

      <!-- 口语计划：有则删除，没有才创建 -->
      <section class="card sec">
        <div class="sec-head">
          <b>口语计划</b>
          <span v-if="hasPlan" class="done">已完成 {{ doneDays }}/{{ planLength }} 天</span>
        </div>

        <LoadingBlock v-if="!loaded" plain />
        <template v-else-if="hasPlan">
          <p class="plan-hint">共 {{ planLength }} 天，每天完成「跟读 + 造句 + 对话」自动打勾；点日期切换上方练习日，想换天数请先删除计划。</p>

          <div class="cal">
            <button
              v-for="d in planDays" :key="d.day"
              type="button"
              class="cell"
              :class="{ done: planDayDone(d, checkMap), today: d.day === todayDay, sel: d.day === activeDay }"
              :title="`第 ${d.day} 天 · ${sourceRangeText(d)} · ${d.title} · 场景：${d.sceneTitles.join('、')} · 点击切换练习日`"
              :aria-pressed="d.day === activeDay"
              @click="pickDay(d.day)"
            >{{ d.day }}</button>
          </div>

          <p v-if="activePlanDay" class="picked-line">
            第 {{ activeDay }} 天 · {{ sourceRangeText(activePlanDay) }} · {{ activePlanDay.title }}
          </p>

          <div v-if="planData" class="legend">
            <span v-for="p in planData.plan.phases" :key="p.name">· {{ p.name }}（{{ p.desc }}）</span>
          </div>

          <div v-if="activeScenes.length" class="today-scenes">
            <span class="ts-label">{{ activeDay === todayDay ? `今天（第 ${activeDay} 天）` : `第 ${activeDay} 天` }}的场景</span>
            <button v-for="s in activeScenes" :key="s.id" class="sc" @click="goSceneById(s.id)">
              {{ s.title }}
            </button>
          </div>

          <div class="plan-actions">
            <n-button type="error" strong class="del-plan" @click="delOpen = true">
              <template #icon>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13M10 11v6M14 11v6" />
                </svg>
              </template>
              删除计划
            </n-button>
          </div>
        </template>
        <template v-else>
          <EmptyState
            plain
            title="还没有口语计划"
            desc="创建计划后才会出现 5 / 10 / 15 分钟入口。没有计划时，可到「跟读 / 造句 / 对话」选择题库内容自由练习，不计时、不打卡。"
          >
            <template #action>
              <n-button type="primary" @click="creating = true">创建计划</n-button>
            </template>
          </EmptyState>
          <div v-if="creating" class="create">
            <div class="genrow">
              <span class="lbl">计划天数</span>
              <n-input-number v-model:value="days" :min="1" :max="90" style="width: 132px" />
              <span class="muted">共 {{ previewDays.length }} 天</span>
              <n-button v-if="validDays" type="primary" @click="savePlan">确认生成</n-button>
              <n-button quaternary @click="creating = false">取消</n-button>
            </div>
            <p class="muted reset-note">创建新计划会重置之前的打卡进度（练习时长与历史记录保留）。</p>
            <div v-if="previewDays.length" class="preview">
              <div v-for="d in previewDays.slice(0, 6)" :key="d.day" class="pv">
                <b>第 {{ d.day }} 天</b>
                <span>{{ sourceRangeText(d) }} · {{ d.shadowIds.length }} 句 · {{ d.sceneIds.length }} 个场景</span>
                <i>{{ d.title }}</i>
                <em>{{ d.sceneTitles.slice(0, 3).join("、") }}{{ d.sceneTitles.length > 3 ? "…" : "" }}</em>
              </div>
              <p v-if="previewDays.length > 6" class="muted">… 其余 {{ previewDays.length - 6 }} 天同理</p>
            </div>
          </div>
        </template>
      </section>
    </template>

    <DeletePlanModal
      v-model:show="delOpen"
      note="删除后打卡记录保留，可重新创建新计划。"
      @confirm="removePlan"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NIcon, NInputNumber } from "naive-ui";
import { MicOutline, ChatbubblesOutline, CreateOutline } from "@vicons/ionicons5";
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";
import {
  budgetBanner, loadAiStatus, type AiStatus,
} from "../core/aiStatus";
import PaidAiNotice from "../components/PaidAiNotice.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import EmptyState from "../components/EmptyState.vue";
import DeletePlanModal from "../components/DeletePlanModal.vue";
import {
  loadSpeak, planDayDone, sourceRangeText, splitSpeakPlan,
  type DayCheck, type PlanDayView, type SpeakData,
} from "../core/speak";

const router = useRouter();
const auth = useAuthStore();
const planData = ref<SpeakData | null>(null);
const checks = ref<DayCheck[]>([]);
const planLength = ref(0);
const loaded = ref(false);
const creating = ref(false);
const delOpen = ref(false);
const days = ref(30);
const usage = ref<{ rt_seconds: number; soe_calls: number; est_cost_milli: number } | null>(null);
const timeTotals = ref<{ shadow: number; make: number; talk: number } | null>(null);
const authReady = ref(false);
const aiStatus = ref<AiStatus | null>(null);
const banner = computed(() => budgetBanner(aiStatus.value));

const hasPlan = computed(() => planLength.value > 0);
const effectiveLength = computed(() => planLength.value || (planData.value?.plan.days?.length ?? 90));
const planDays = computed<PlanDayView[]>(() => splitSpeakPlan(planData.value, effectiveLength.value));
const checkMap = computed<Record<number, DayCheck>>(() => {
  const m: Record<number, DayCheck> = {};
  for (const c of checks.value) m[c.day] = c;
  return m;
});
const todayDay = computed(() => planDays.value.find((d) => !planDayDone(d, checkMap.value))?.day ?? planDays.value.length);
const doneDays = computed(() => planDays.value.filter((d) => planDayDone(d, checkMap.value)).length);
/** 日历里点选的那天；null = 跟随「今天」。按用户存 sessionStorage，跨页面返回仍保留。 */
const PICK_PREFIX = "pet_speak_day::";
const pickedDay = ref<number | null>(null);
function pickStorageKey(): string {
  return PICK_PREFIX + (auth.username || "anon");
}
function readPickedDay(): number | null {
  try {
    const n = Number(sessionStorage.getItem(pickStorageKey()));
    return Number.isInteger(n) && n >= 1 ? n : null;
  } catch {
    return null;
  }
}
function setPickedDay(day: number | null): void {
  pickedDay.value = day;
  try {
    if (day) sessionStorage.setItem(pickStorageKey(), String(day));
    else sessionStorage.removeItem(pickStorageKey());
  } catch { /* 隐私模式忽略 */ }
}
const activeDay = computed(() => {
  const n = pickedDay.value;
  if (n && n >= 1 && n <= planDays.value.length) return n;
  return todayDay.value || 1;
});
const activePlanDay = computed(() =>
  planDays.value.find((d) => d.day === activeDay.value) ?? null,
);
const validDays = computed(() => Number.isInteger(days.value) && days.value >= 1 && days.value <= 90);
const previewDays = computed<PlanDayView[]>(() =>
  validDays.value ? splitSpeakPlan(planData.value, days.value) : [],
);
/** 选中计划日包含的真题场景（来自 45 场景题库） */
const activeScenes = computed(() => {
  const pd = activePlanDay.value;
  if (!pd) return [];
  return pd.sceneIds.map((id, i) => ({ id, title: pd.sceneTitles[i] ?? id }));
});

onMounted(async () => {
  await auth.restore();
  authReady.value = true;
  pickedDay.value = readPickedDay();
  planData.value = await loadSpeak();
  await refresh();
  aiStatus.value = await loadAiStatus(true);
  loaded.value = true;
});

async function refresh(): Promise<void> {
  try {
    const r = await api<{ length: number }>("/speak/plan");
    planLength.value = r.length ?? 0;
    // 计划变短/删除后，清掉失效的选中日
    if (pickedDay.value !== null && (!planLength.value || pickedDay.value > planLength.value)) {
      setPickedDay(null);
    }
  } catch { /* 离线保持 0（默认 90 天） */ }
  if (!hasPlan.value) {
    // 无计划：不读打卡/用量/开口时长（自由练习也不计时）
    checks.value = [];
    usage.value = null;
    timeTotals.value = null;
    return;
  }
  try {
    const r = await api<{ days: DayCheck[] }>("/speak/days");
    checks.value = r.days ?? [];
  } catch { /* 离线保持空 */ }
  try {
    usage.value = await api<{ rt_seconds: number; soe_calls: number; est_cost_milli: number }>("/speak/usage_today");
  } catch { /* 离线忽略 */ }
  try {
    const r = await api<{ totals: { shadow: number; make: number; talk: number } }>("/speak/time/today");
    timeTotals.value = r.totals;
  } catch { /* 离线忽略 */ }
}

function fmtSec(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

async function savePlan(): Promise<void> {
  if (!validDays.value) return;
  try {
    const r = await api<{ length: number }>("/speak/plan", {
      method: "PUT",
      body: JSON.stringify({ length: days.value }),
    });
    planLength.value = r.length;
    setPickedDay(null);
    creating.value = false;
  } catch (e) {
    console.error(e);
  }
}

async function removePlan(): Promise<void> {
  try {
    await api("/speak/plan", { method: "DELETE" });
    planLength.value = 0;
    setPickedDay(null);
  } catch { /* 离线忽略 */ }
}

function pickDay(day: number): void {
  setPickedDay(day);
}

function goShadow(day: number): void {
  void router.push(`/english/speak/shadow?day=${day}`);
}
function goTalk(day: number): void {
  void router.push(`/english/speak/talk?day=${day}`);
}
function goMake(day: number): void {
  void router.push(`/english/speak/make?day=${day}`);
}
function goSceneById(id: string): void {
  void router.push(`/english/speak/talk?scene=${encodeURIComponent(id)}`);
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 16px; }
.locked { padding: 40px 24px; text-align: center; }
.sec { padding: 16px; margin-bottom: 14px; }
.sec-head { display: flex; justify-content: space-between; margin-bottom: 10px; color: var(--c-text); }
.done { color: var(--c-primary); font-weight: 600; }
.plan-hint { color: var(--c-text-2); font-size: 13.5px; margin: 0 0 12px; }
.cal { display: grid; grid-template-columns: repeat(15, minmax(0, 1fr)); gap: 6px; }
@media (max-width: 1023px) { .cal { grid-template-columns: repeat(10, minmax(0, 1fr)); } }
@media (max-width: 767px) { .cal { grid-template-columns: repeat(7, minmax(0, 1fr)); } }
.cell {
  aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  width: 100%; padding: 0; appearance: none; font-family: inherit;
  background: #fff; border: 1px solid var(--c-line); border-radius: 10px;
  font-size: 12.5px; font-weight: 600;
  color: var(--c-text-3); cursor: pointer; min-width: 0;
  font-variant-numeric: tabular-nums;
  transition: border-color var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out),
    box-shadow var(--dur-2) var(--ease-out);
}
.cell:hover { border-color: #a9dcc0; transform: translateY(-1px); color: var(--c-text-2); }
.cell:active { transform: translateY(0) scale(0.97); }
.cell:focus-visible { outline: 3px solid var(--c-accent); outline-offset: 2px; }
.cell.done { background: linear-gradient(180deg, #1cb257 0%, #16a34a 100%); border-color: #148f41; color: #fff; }
.cell.today {
  background: var(--c-primary-soft); border: 1.5px solid var(--c-primary);
  color: var(--c-primary-strong); font-weight: 800;
}
/* 当前选中的练习日：外圈描边，与“今天”的浅绿底、已完成绿块都能区分 */
.cell.sel {
  border-color: var(--c-primary-strong);
  box-shadow: 0 0 0 2.5px rgba(21, 128, 61, 0.28);
  transform: translateY(-1px);
}
.picked-line { margin: 10px 0 0; color: var(--c-primary-strong); font-size: 13px; font-weight: 600; }
.legend {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 4px 16px; margin-top: 12px;
  color: var(--c-text-2); font-size: 12.5px; line-height: 1.6;
}
.plan-actions { display: flex; gap: 10px; align-items: center; margin-top: 14px; flex-wrap: wrap; }
/* 删除计划：填充红 + 图标 + 投影，避免被当成普通文字按钮 */
.del-plan { min-height: 42px; padding: 0 18px; box-shadow: 0 6px 14px rgba(220, 38, 38, 0.18); }
.del-plan:hover { box-shadow: 0 8px 18px rgba(220, 38, 38, 0.26); }
.today-scenes { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 12px; }
.ts-label { color: var(--c-text-2); font-size: 13px; font-weight: 600; }
.create { margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--c-line); }
.genrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.lbl { font-size: 14px; color: var(--c-text-2); }
.muted { color: var(--c-text-2); font-size: 13.5px; }
.reset-note { margin: 8px 0 0; }
.preview { margin-top: 10px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 8px; }
.pv { background: var(--c-mint-bg, #f6faf7); border-radius: 10px; padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
.pv b { color: var(--c-text); font-size: 13.5px; }
.pv span { color: var(--c-text-2); font-size: 12.5px; }
.pv i { color: var(--c-text-3); font-size: 12px; font-style: normal; }
.pv em { color: var(--c-primary-strong); font-size: 12px; font-style: normal; }
.entries { margin-bottom: 16px; }
.entry-head {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin: 0 2px 8px; font-size: 13.5px;
}
.entry-day { font-weight: 800; color: var(--c-primary-strong); }
.entry-hint { color: var(--c-text-2); }
.entry-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
@media (max-width: 767px) { .entry-grid { grid-template-columns: 1fr; } }
.entry {
  padding: 16px; min-height: 84px; text-align: left; cursor: pointer;
  background: var(--c-surface); border: 1px solid var(--c-line); border-radius: var(--r-btn);
  box-shadow: var(--shadow-1); position: relative;
  transition: border-color var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out),
    box-shadow var(--dur-2) var(--ease-out);
}
.entry:hover { border-color: #a9dcc0; transform: translateY(-1px); box-shadow: var(--shadow-2); }
.entries .entry:first-child { background: linear-gradient(180deg, #f4fbf7 0%, #ffffff 72%); border-color: #cfeadd; }
.entry b { display: flex; align-items: center; gap: 6px; color: var(--c-text); margin-bottom: 6px; font-size: 16px; }
.entry b :deep(.n-icon) { color: var(--c-primary); }
.entry span { color: var(--c-text-2); font-size: var(--fs-sub); line-height: 1.5; }
.usage { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; padding: 10px 14px; margin-bottom: 12px; color: var(--c-text-2); font-size: var(--fs-sub); }
.usage b { color: var(--c-primary); }
.usage .cost { margin-left: auto; color: var(--c-text-2); }
.sc { display: inline-flex; align-items: center; gap: 6px; background: var(--c-mint-bg); border: none; border-radius: 999px; padding: 6px 12px; margin: 0 6px 6px 0; cursor: pointer; color: var(--c-text); }
</style>
