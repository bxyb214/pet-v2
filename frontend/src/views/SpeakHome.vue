<template>
  <main class="page">
    <h1>口语</h1>
    <p class="sub">90 天计划 · 跟读纠音 · 场景对话（需要管理员开通权限并配置语音 Key）</p>

    <div v-if="!authReady" class="locked card">加载中…</div>
    <!-- 未开通口语：占位 + 弹框提示（AI 调用有费用） -->
    <template v-else-if="locked">
      <div class="locked card">
        <div class="lock-icon">🔒</div>
        <p class="lock-msg">由于 AI 调用产生费用，请联系<b>小淏</b>开通口语功能</p>
        <p class="lock-sub">开通后即可使用跟读纠音、实时对话、口语复盘、造句练习</p>
      </div>
      <n-modal v-model:show="showLocked" preset="dialog" type="warning" title="口语功能未开通" style="max-width: 400px">
        <div style="text-align:center; padding: 6px 0;">
          <div style="font-size:40px">🔒</div>
          <p style="font-size:16px; margin:10px 0 4px;">由于 AI 调用产生费用，请联系<b style="color:var(--c-primary)">小淏</b>开通口语功能</p>
          <p style="color:var(--c-text-2); font-size:13px;">跟读纠音 · 实时对话 · 口语复盘 · 造句练习</p>
        </div>
        <template #action>
          <n-button type="primary" @click="showLocked = false">知道了</n-button>
        </template>
      </n-modal>
    </template>
    <template v-else>
      <!-- 90 天计划 -->
      <section class="card sec">
        <div class="sec-head"><b>90 天计划</b><span class="done">已完成 {{ doneDays }}/90 天</span></div>
        <div class="cal">
          <div
            v-for="d in 90" :key="d"
            class="cell"
            :class="{ done: dayDone(checkMap[d]), today: d === todayDay, phase0: phaseOfDay(planData?.plan ?? { title: '', phases: [] }, d) === null }"
            :title="`第 ${d} 天 · ${phaseOfDay(planData?.plan ?? { title: '', phases: [] }, d)?.name ?? ''}`"
            @click="goShadow(d)"
          >{{ d }}</div>
        </div>
        <div class="legend" v-if="planData">
          <span v-for="p in planData.plan.phases" :key="p.name">· {{ p.name }}（{{ p.desc }}）</span>
        </div>
      </section>

      <!-- 今日已用（只记录不限流） -->
      <div v-if="usage" class="card usage">
        <span>今日已练 <b>{{ usage.rt_seconds ? Math.round(usage.rt_seconds / 60) : 0 }}</b> 分钟对话</span>
        <span>跟读评测 <b>{{ usage.soe_calls }}</b> 次</span>
        <span class="cost">预估 {{ (usage.est_cost_milli / 1000).toFixed(2) }} 元</span>
      </div>

      <!-- 五入口 -->
      <section class="entries">
        <button class="entry card" @click="goShadow(todayDay || 1)">
          <b><n-icon :component="MicOutline" size="18" />跟读纠音</b>
          <span>逐句跟读 · AI 打分与建议</span>
        </button>
        <button class="entry card" @click="goTalk(todayDay || 1)">
          <b><n-icon :component="ChatbubblesOutline" size="18" />自由对话</b>
          <span>基于今天练的句型开口聊</span>
        </button>
        <button class="entry card" @click="showScenes = !showScenes">
          <b><n-icon :component="PeopleOutline" size="18" />场景对话</b>
          <span>{{ sceneCount }} 个 PET 真题场景任选</span>
        </button>
        <button class="entry card" @click="router.push('/english/speak/make')">
          <b><n-icon :component="CreateOutline" size="18" />造句练习</b>
          <span>PET 常用句型 · AI 点评优化</span>
        </button>
        <button class="entry card" @click="goReview">
          <b><n-icon :component="RefreshOutline" size="18" />口语复盘</b>
          <span>
            把你说过的话说得更好
            <em v-if="dueCount > 0" class="badge">{{ dueCount }}</em>
          </span>
        </button>
      </section>

      <!-- 场景选择 -->
      <section v-if="showScenes && planData" class="card sec">
        <div v-for="grp in sceneGroups" :key="grp.part" class="scg">
          <div class="scg-title">Part {{ grp.part }} · {{ grp.title }}</div>
          <button v-for="c in grp.items" :key="c.id" class="sc" @click="goScene(c)">
            {{ c.title }} <span class="sc-cn">{{ c.cn }}</span> <span class="lv">{{ c.level }}</span>
          </button>
        </div>
      </section>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NIcon, NModal } from "naive-ui";
import { MicOutline, ChatbubblesOutline, PeopleOutline, CreateOutline, RefreshOutline } from "@vicons/ionicons5";
import { api } from "../core/api";
import { useAuthStore } from "../stores/auth";
import { dayDone, loadSpeak, phaseOfDay, type Scene, type SpeakData, type DayCheck } from "../core/speak";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const planData = ref<SpeakData | null>(null);
const checks = ref<DayCheck[]>([]);
const showScenes = ref(false);
const usage = ref<{ rt_seconds: number; soe_calls: number; est_cost_milli: number } | null>(null);
const dueCount = ref(0);
const sceneCount = computed(() => planData.value?.scenes?.length ?? 0);
const authReady = ref(false);
// 权限弹框：被守卫从子页弹回（?locked=1）或直接进入时弹出
const showLocked = ref(route.query.locked === "1");

const locked = computed(
  () => localStorage.getItem("pet_local_only") !== "true" && !auth.perms.includes("speak"),
);
const todayDay = computed(() => {
  const next = checks.value.find((d) => !dayDone(d));
  return next ? next.day : 90;
});
const checkMap = computed<Record<number, DayCheck>>(() => {
  const m: Record<number, DayCheck> = {};
  for (const c of checks.value) m[c.day] = c;
  return m;
});
const doneDays = computed(() => checks.value.filter((d) => dayDone(d)).length);
const sceneGroups = computed(() => {
  const s = planData.value?.scenes ?? [];
  const byPart = new Map<number, Scene[]>();
  for (const c of s) {
    if (!byPart.has(c.part)) byPart.set(c.part, []);
    byPart.get(c.part)!.push(c);
  }
  return [...byPart.entries()].map(([part, items]) => ({
    part,
    title: part === 1 ? "个人信息" : part === 2 ? "图片描述" : part === 3 ? "讨论协商" : "扩展讨论",
    items,
  }));
});

onMounted(async () => {
  await auth.restore(); // 刷新后恢复 perms，避免已开通用户被误弹权限框
  authReady.value = true;
  if (locked.value) showLocked.value = true; // 恢复后仍锁定 → 弹框
  if (!locked.value) {
    planData.value = await loadSpeak();
    try {
      const r = await api<{ days: DayCheck[] }>("/english/speak/days");
      checks.value = r.days;
    } catch { /* 离线时保持空 */ }
    try {
      usage.value = await api<{ rt_seconds: number; soe_calls: number; est_cost_milli: number }>("/english/speak/usage_today");
    } catch { /* 离线忽略 */ }
    try {
      const r = await api<{ items: unknown[] }>("/english/speak/review/due");
      dueCount.value = (r.items ?? []).length;
    } catch { /* 离线忽略 */ }
  }
});

function goReview(): void {
  void router.push("/english/speak/review");
}

function goShadow(day: number): void {
  void router.push(`/english/speak/shadow?day=${day}`);
}
function goTalk(day: number): void {
  void router.push(`/english/speak/talk?day=${day}`);
}
function goScene(c: Scene): void {
  void router.push(`/english/speak/talk?scene=${encodeURIComponent(c.id)}`);
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
.sec-head { display: flex; justify-content: space-between; margin-bottom: 12px; color: var(--c-text); }
.done { color: var(--c-primary); font-weight: 600; }
.cal { display: grid; grid-template-columns: repeat(15, minmax(0, 1fr)); gap: 6px; }
@media (max-width: 1023px) { .cal { grid-template-columns: repeat(10, minmax(0, 1fr)); } }
@media (max-width: 767px) { .cal { grid-template-columns: repeat(7, minmax(0, 1fr)); } }
.cell {
  aspect-ratio: 1; display: flex; align-items: center; justify-content: center;
  background: var(--c-bg-mint); border-radius: var(--r-sm); font-size: var(--fs-sub);
  color: var(--c-text-2); cursor: pointer; border: 2px solid transparent; min-width: 0;
  font-variant-numeric: tabular-nums;
}
.cell.done { background: var(--c-primary); color: #fff; }
.cell.today { border-color: var(--c-primary); color: var(--c-primary); font-weight: 700; }
.legend { margin-top: 10px; color: var(--c-text-2); font-size: var(--fs-sub); }
.legend span { margin-right: 10px; }
.entries { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px; margin-bottom: 16px; }
.entry { padding: 16px; min-height: 84px; text-align: left; cursor: pointer; border: none; background: var(--c-surface); border-radius: var(--r-md); box-shadow: var(--shadow-sm); position: relative; }
.entry b { display: flex; align-items: center; gap: 6px; color: var(--c-text); margin-bottom: 6px; font-size: 16px; }
.entry b :deep(.n-icon) { color: var(--c-primary); }
.entry span { color: var(--c-text-2); font-size: var(--fs-sub); line-height: 1.5; }
.badge { display: inline-block; min-width: 18px; height: 18px; line-height: 18px; text-align: center; background: var(--c-primary); color: #fff; border-radius: 999px; font-size: 11px; font-style: normal; padding: 0 5px; margin-left: 4px; }
.usage { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; padding: 10px 14px; margin-bottom: 12px; color: var(--c-text-2); font-size: var(--fs-sub); }
.usage b { color: var(--c-primary); }
.usage .cost { margin-left: auto; color: var(--c-text-2); }
.scg { margin-bottom: 12px; }
.scg-title { color: var(--c-text); font-weight: 600; margin-bottom: 6px; }
.sc { display: inline-flex; align-items: center; gap: 6px; background: var(--c-bg-mint); border: none; border-radius: 999px; padding: 6px 12px; margin: 0 6px 6px 0; cursor: pointer; color: var(--c-text); }
.sc-cn { color: var(--c-text-2); font-size: var(--fs-sub); }
.lv { color: var(--c-primary); font-size: var(--fs-sub); }
</style>
