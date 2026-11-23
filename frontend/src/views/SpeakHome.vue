<template>
  <main class="page">
    <h1>口语</h1>
    <p class="sub">每天 5 分钟跟读 + 10 分钟造句 + 15 分钟自由对话（10 分钟对话 + 5 分钟复盘）</p>

    <div v-if="!authReady" class="locked card">加载中…</div>
    <!-- 未开通口语：占位 + 弹框提示（AI 调用有费用） -->
    <template v-else-if="locked">
      <div class="locked card">
        <div class="lock-icon">🔒</div>
        <p class="lock-msg">由于 AI 调用产生费用，请联系<b>管理员</b>开通口语功能</p>
        <p class="lock-sub">开通后即可使用跟读纠音、实时对话、造句练习</p>
      </div>
      <n-modal v-model:show="showLocked" preset="dialog" type="warning" title="口语功能未开通" style="max-width: 400px">
        <div style="text-align:center; padding: 6px 0;">
          <div style="font-size:40px">🔒</div>
          <p style="font-size:16px; margin:10px 0 4px;">由于 AI 调用产生费用，请联系<b style="color:var(--c-primary)">管理员</b>开通口语功能</p>
          <p style="color:var(--c-text-2); font-size:13px;">跟读纠音 · 实时对话 · 造句练习</p>
        </div>
        <template #action>
          <n-button type="primary" @click="showLocked = false">知道了</n-button>
        </template>
      </n-modal>
    </template>
    <template v-else>
      <!-- 口语计划：有则删除，没有才创建 -->
      <section class="card sec">
        <div class="sec-head">
          <b>口语计划</b>
          <span v-if="hasPlan" class="done">已完成 {{ doneDays }}/{{ planLength }} 天</span>
        </div>

        <div v-if="!loaded" class="muted">加载中…</div>
        <template v-else-if="hasPlan">
          <p class="plan-hint">共 {{ planLength }} 天，每天完成「跟读 + 造句 + 对话」自动打勾；想换天数请先删除计划。</p>

          <div class="cal">
            <div
              v-for="d in planDays" :key="d.day"
              class="cell"
              :class="{ done: planDayDone(d, checkMap), today: d.day === todayDay }"
              :title="`第 ${d.day} 天 · ${sourceRangeText(d)} · ${d.title} · 场景：${d.sceneTitles.join('、')}`"
              @click="goShadow(d.day)"
            >{{ d.day }}</div>
          </div>

          <div v-if="planData" class="legend">
            <span v-for="p in planData.plan.phases" :key="p.name">· {{ p.name }}（{{ p.desc }}）</span>
          </div>

          <div v-if="todayScenes.length" class="today-scenes">
            <span class="ts-label">今天（第 {{ todayDay }} 天）的场景</span>
            <button v-for="s in todayScenes" :key="s.id" class="sc" @click="goSceneById(s.id)">
              {{ s.title }}
            </button>
          </div>

          <div class="plan-actions">
            <n-popconfirm @positive-click="removePlan">
              <template #trigger><n-button type="error" quaternary>删除计划</n-button></template>
              删除后打卡记录保留，可重新创建新计划。确定？
            </n-popconfirm>
          </div>
        </template>
        <template v-else>
          <div class="plan-empty">
            <p class="pe-t">还没有口语计划</p>
            <p class="pe-s">选一个天数，系统会把当天的跟读句子和场景分到每天。</p>
            <n-button type="primary" @click="creating = true">创建计划</n-button>
          </div>
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

      <!-- 今日已用（只记录不限流） -->
      <div v-if="usage || timeTotals" class="card usage">
        <span v-if="timeTotals">今日开口：跟读 <b>{{ fmtSec(timeTotals.shadow) }}</b> · 造句 <b>{{ fmtSec(timeTotals.make) }}</b> · 对话 <b>{{ fmtSec(timeTotals.talk) }}</b></span>
        <span v-if="usage">跟读评测 <b>{{ usage.soe_calls }}</b> 次</span>
        <span v-if="usage" class="cost">预估 {{ (usage.est_cost_milli / 1000).toFixed(2) }} 元</span>
      </div>

      <!-- 每日入口：5 + 10 + 15 -->
      <section class="entries">
        <button class="entry card" @click="goShadow(todayDay || 1)">
          <b><n-icon :component="MicOutline" size="18" />跟读纠音 · 5 分钟</b>
          <span>逐句跟读 · AI 打分与建议</span>
        </button>
        <button class="entry card" @click="goMake(todayDay || 1)">
          <b><n-icon :component="CreateOutline" size="18" />造句练习 · 10 分钟</b>
          <span>PET 常用句型 · AI 点评优化</span>
        </button>
        <button class="entry card" @click="goTalk(todayDay || 1)">
          <b><n-icon :component="ChatbubblesOutline" size="18" />自由对话 · 15 分钟</b>
          <span>10 分钟对话 + 5 分钟复盘 · 边说边优化</span>
        </button>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NIcon, NInputNumber, NModal, NPopconfirm } from "naive-ui";
import { MicOutline, ChatbubblesOutline, CreateOutline } from "@vicons/ionicons5";
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";
import {
  loadSpeak, planDayDone, sourceRangeText, splitSpeakPlan,
  type DayCheck, type PlanDayView, type SpeakData,
} from "../core/speak";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const planData = ref<SpeakData | null>(null);
const checks = ref<DayCheck[]>([]);
const planLength = ref(0);
const loaded = ref(false);
const creating = ref(false);
const days = ref(30);
const usage = ref<{ rt_seconds: number; soe_calls: number; est_cost_milli: number } | null>(null);
const timeTotals = ref<{ shadow: number; make: number; talk: number } | null>(null);
const authReady = ref(false);
const showLocked = ref(route.query.locked === "1");

const locked = computed(
  () => localStorage.getItem("pet_local_only") !== "true" && !auth.perms.includes("speak"),
);
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
const validDays = computed(() => Number.isInteger(days.value) && days.value >= 1 && days.value <= 90);
const previewDays = computed<PlanDayView[]>(() =>
  validDays.value ? splitSpeakPlan(planData.value, days.value) : [],
);
/** 今天这个计划日包含的真题场景（来自 161 场景题库） */
const todayScenes = computed(() => {
  const pd = planDays.value.find((d) => d.day === todayDay.value);
  if (!pd) return [];
  return pd.sceneIds.map((id, i) => ({ id, title: pd.sceneTitles[i] ?? id }));
});

onMounted(async () => {
  await auth.restore();
  authReady.value = true;
  if (locked.value) {
    showLocked.value = true;
    return;
  }
  planData.value = await loadSpeak();
  await refresh();
  loaded.value = true;
});

async function refresh(): Promise<void> {
  try {
    const r = await api<{ length: number }>("/speak/plan");
    planLength.value = r.length ?? 0;
  } catch { /* 离线保持 0（默认 90 天） */ }
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
    creating.value = false;
  } catch (e) {
    console.error(e);
  }
}

async function removePlan(): Promise<void> {
  try {
    await api("/speak/plan", { method: "DELETE" });
    planLength.value = 0;
  } catch { /* 离线忽略 */ }
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
.lock-icon { font-size: 44px; margin-bottom: 10px; }
.lock-msg { color: var(--c-text); font-size: 17px; margin: 0 0 8px; }
.lock-msg b { color: var(--c-primary); }
.lock-sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 16px; }
.sec { padding: 16px; margin-bottom: 14px; }
.sec-head { display: flex; justify-content: space-between; margin-bottom: 10px; color: var(--c-text); }
.done { color: var(--c-primary); font-weight: 600; }
.plan-hint { color: var(--c-text-2); font-size: 13.5px; margin: 0 0 12px; }
.cal { display: grid; grid-template-columns: repeat(15, minmax(0, 1fr)); gap: 6px; }
@media (max-width: 1023px) { .cal { grid-template-columns: repeat(10, minmax(0, 1fr)); } }
@media (max-width: 767px) { .cal { grid-template-columns: repeat(7, minmax(0, 1fr)); } }
.cell {
  aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  background: #fff; border: 1px solid var(--c-line); border-radius: 10px;
  font-size: 12.5px; font-weight: 600;
  color: var(--c-text-3); cursor: pointer; min-width: 0;
  font-variant-numeric: tabular-nums;
  transition: border-color var(--dur-2) var(--ease-out), transform var(--dur-2) var(--ease-out);
}
.cell:hover { border-color: #a9dcc0; transform: translateY(-1px); color: var(--c-text-2); }
.cell.done { background: linear-gradient(180deg, #1cb257 0%, #16a34a 100%); border-color: #148f41; color: #fff; }
.cell.today {
  background: var(--c-primary-soft); border: 1.5px solid var(--c-primary);
  color: var(--c-primary-strong); font-weight: 800;
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.1);
}
.legend {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 4px 16px; margin-top: 12px;
  color: var(--c-text-2); font-size: 12.5px; line-height: 1.6;
}
.plan-actions { display: flex; gap: 10px; align-items: center; margin-top: 14px; flex-wrap: wrap; }
.plan-empty { text-align: center; padding: 22px 8px 10px; }
.pe-t { margin: 0 0 4px; font-weight: 700; font-size: 17px; color: var(--c-text); }
.pe-s { margin: 0 0 16px; font-size: 13.5px; color: var(--c-text-2); }
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
.entries { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
@media (max-width: 767px) { .entries { grid-template-columns: 1fr; } }
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
