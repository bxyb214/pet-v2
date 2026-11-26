<template>
  <div class="usage-page">
    <div class="topline">
      <BackButton to="/settings" label="返回备考" variant="text" />
      <span class="hint">费用为服务端估算，仅供对账</span>
    </div>

    <n-card size="small" class="card">
      <div class="sect-head">
        <h2>AI 额度</h2>
        <span class="sect-hint">一次性总额度 · 用完需管理员调整</span>
      </div>

      <LoadingBlock v-if="loading && !data" plain />
      <EmptyState v-else-if="error && !data" :title="error" plain>
        <template #action>
          <n-button size="small" secondary @click="retry">重试</n-button>
        </template>
      </EmptyState>

      <template v-else-if="data">
        <p v-if="!data.status.ai_enabled" class="notice neutral">
          尚未开通付费 AI。免费功能（单词、阅读、听力、题库）不受影响；下面是历史用量。
        </p>
        <p v-else-if="data.status.unlimited" class="notice ok">
          管理员账号不受总额度限制；累计已用 {{ fmtMilli(data.status.credit.used_milli) }}。
          单次 AI 对话上限约 {{ fmtMinutes(data.status.max_session_sec) }}。
        </p>
        <p v-else-if="data.status.credit.stage >= 2" class="notice danger">
          {{ data.status.message || "AI 总额度已用完，免费功能仍可用。" }}
        </p>
        <p v-else-if="data.status.credit.stage === 1" class="notice warn">
          AI 总额度已用 80%，用完将暂停付费功能。
        </p>
        <p v-else class="notice ok">
          额度可用，剩余 {{ fmtMilli(data.status.remaining_milli) }}；单次 AI 对话上限约
          {{ fmtMinutes(data.status.max_session_sec) }}。
        </p>
        <p v-if="error" class="notice danger">{{ error }}</p>

        <div v-if="data.status.ai_enabled" class="budget">
          <div class="budget-row">
            <div class="budget-label">
              <span>总额度</span>
              <b class="tnum">{{ fmtMilli(data.status.credit.used_milli) }} / {{ fmtMilli(data.status.credit.budget_milli) }}</b>
            </div>
            <span class="reset">{{ data.status.unlimited ? "管理员不限额度" : "用尽后付费 AI 暂停" }}</span>
            <div class="bar"><i :class="tone(data.status.credit.stage)" :style="{ width: pct(data.status.credit.ratio) + '%' }"></i></div>
          </div>
        </div>
        <p v-else class="meta">未开通期间不会产生新的 AI 费用；历史用量仍会保留。</p>
      </template>
    </n-card>

    <section v-if="data" class="tiles">
      <div v-for="t in tiles" :key="t.label" class="tile">
        <span class="tile-label">{{ t.label }}</span>
        <b class="tile-cost tnum">{{ fmtMilli(t.totals.est_cost_milli) }}</b>
        <span class="tile-sub">{{ t.totals.active_days }} 天 · 对话 {{ fmtMinutes(t.totals.rt_seconds) }}</span>
        <span class="tile-sub">评测 {{ t.totals.soe_calls }} 次 · TTS {{ fmtChars(t.totals.tts_chars) }} 字</span>
      </div>
    </section>

    <n-card v-if="data" size="small" class="card">
      <div class="sect-head">
        <h2>每日明细</h2>
        <span class="sect-hint">只列有 AI 消耗的日期</span>
      </div>

      <div class="month-row">
        <n-date-picker
          :value="monthTs"
          type="month"
          size="small"
          style="width: 140px"
          :clearable="false"
          @update:value="reload"
        />
        <span class="hint">所选月合计 <b class="tnum">{{ fmtMilli(data.totals.month.est_cost_milli) }}</b></span>
      </div>

      <div v-if="data.days.length" class="table-wrap">
        <div class="table">
          <div class="thead">
            <span>日期</span><span>对话</span><span>AI 说话</span><span>评测</span><span>TTS 字符</span><span>LLM tok</span><span>预估</span>
          </div>
          <div v-for="d in data.days" :key="d.day" class="trow">
            <span class="tnum">{{ d.day.slice(5) }}</span>
            <span class="tnum">{{ fmtMinutes(d.rt_seconds) }}</span>
            <span class="tnum">{{ fmtMinutes(d.rt_ai_seconds) }}</span>
            <span class="tnum">{{ d.soe_calls }} 次</span>
            <span class="tnum">{{ fmtChars(d.tts_chars) }}</span>
            <span class="tnum">{{ d.llm_tok }}</span>
            <span class="tnum cost">{{ fmtMilli(d.est_cost_milli) }}</span>
          </div>
        </div>
      </div>
      <EmptyState v-else plain title="这个月还没有 AI 用量" desc="使用付费 AI 功能后，这里会按天记录。" />
    </n-card>

    <p class="foot">
      费用由服务端按记账单价估算，仅用于对账与参考；TTS 缓存命中不计费，免费功能（单词、阅读、听力、题库）不计费。
      AI 总额度用尽后付费接口会被服务端拦截，免费功能仍可正常使用；需要更多额度请联系管理员。
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { NButton, NCard, NDatePicker } from "naive-ui";
import BackButton from "../components/BackButton.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import EmptyState from "../components/EmptyState.vue";
import {
  fmtChars,
  fmtMilli,
  fmtMinutes,
  loadMyUsage,
  localMonth,
  type MyUsage,
  type UsageTotals,
} from "../core/usage";

const data = ref<MyUsage | null>(null);
const monthTs = ref(Date.now());
const loading = ref(false);
const error = ref("");

const tiles = computed<{ label: string; totals: UsageTotals }[]>(() => {
  const d = data.value;
  if (!d) return [];
  return [
    { label: "今日", totals: d.totals.today },
    { label: "本周", totals: d.totals.week },
    { label: "所选月", totals: d.totals.month },
    { label: "今年", totals: d.totals.year },
  ];
});

function pct(ratio: number): number {
  return Math.min(100, Math.max(0, Math.round(ratio * 100)));
}

function tone(stage: number): "ok" | "warn" | "danger" {
  return stage >= 2 ? "danger" : stage === 1 ? "warn" : "ok";
}

async function fetchUsage(month: string): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    data.value = await loadMyUsage(month);
  } catch (e) {
    error.value = "加载用量失败：" + (e as Error).message;
  } finally {
    loading.value = false;
  }
}

async function reload(ts: number): Promise<void> {
  monthTs.value = ts;
  await fetchUsage(localMonth(ts));
}

function retry(): void {
  void fetchUsage(localMonth(monthTs.value));
}

onMounted(() => {
  void fetchUsage(localMonth(monthTs.value));
});
</script>

<style scoped>
.usage-page { width: 100%; }
.card { margin-bottom: 16px; }

.topline { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.hint { font-size: 12px; color: var(--c-text-3); }

.sect-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.sect-head h2 { margin: 0; font-size: 14px; font-weight: 800; color: var(--c-text); letter-spacing: 0.02em; }
.sect-hint { font-size: 12px; color: var(--c-text-3); }

.notice { margin: 0 0 12px; padding: 10px 12px; border-radius: var(--r-sm); font-size: 12.5px; line-height: 1.7; }
.notice.neutral { background: #f4f7f5; color: var(--c-text-2); border: 1px solid var(--c-line); }
.notice.ok { background: var(--c-primary-soft, #e7f6ec); color: var(--c-primary-strong, #15803d); border: 1px solid #ccebdc; }
.notice.warn { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.notice.danger { background: #fff1f1; color: #b42318; border: 1px solid #f5c6c6; }

.budget { display: grid; gap: 14px; }
.budget-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px 12px; align-items: center; }
.budget-label { display: flex; align-items: baseline; gap: 8px; min-width: 0; font-size: 12.5px; color: var(--c-text-3); }
.budget-label b { color: var(--c-text); font-size: 13px; }
.bar { grid-column: 1 / -1; height: 8px; border-radius: 999px; background: #eef4f0; overflow: hidden; }
.bar i { display: block; height: 100%; border-radius: 999px; background: var(--c-primary); transition: width 0.2s ease; }
.bar i.warn { background: var(--c-accent, #d97706); }
.bar i.danger { background: var(--c-danger, #dc2626); }
.reset { grid-row: 1; grid-column: 2; font-size: 11.5px; color: var(--c-text-3); white-space: nowrap; }
.meta { margin: 0; font-size: 12px; color: var(--c-text-3); }

.tiles { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }
.tile {
  display: flex; flex-direction: column; gap: 4px; min-width: 0;
  padding: 12px 13px; background: #fff; border: 1px solid var(--c-line);
  border-radius: var(--r-btn); box-shadow: var(--shadow-1);
}
.tile-label { font-size: 11.5px; font-weight: 700; color: var(--c-text-3); }
.tile-cost { font-size: 20px; line-height: 1.2; color: var(--c-primary-strong); }
.tile-sub { font-size: 11.5px; color: var(--c-text-2); overflow-wrap: anywhere; }

.month-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.month-row .hint b { color: var(--c-text); }

.table-wrap { overflow-x: auto; }
.table { min-width: 620px; }
.thead, .trow {
  display: grid; grid-template-columns: 0.8fr 0.9fr 0.9fr 0.7fr 0.9fr 0.8fr 1.1fr;
  gap: 8px; align-items: center; padding: 8px 10px;
}
.thead { font-size: 11.5px; font-weight: 700; color: var(--c-text-3); border-bottom: 1px solid var(--c-line); }
.trow { font-size: 12.5px; color: var(--c-text); border-bottom: 1px solid var(--c-line); }
.trow:last-child { border-bottom: none; }
.thead span:not(:first-child), .trow span:not(:first-child) { text-align: right; }
.trow .cost { color: var(--c-primary-strong); font-weight: 700; }
.tnum { font-variant-numeric: tabular-nums; }

.empty { margin: 0; padding: 16px 0; text-align: center; font-size: 12.5px; color: var(--c-text-3); }
.empty p { margin: 0 0 10px; }
.foot { margin: 4px 2px 0; font-size: 11.5px; line-height: 1.7; color: var(--c-text-3); }

@media (max-width: 640px) {
  .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
