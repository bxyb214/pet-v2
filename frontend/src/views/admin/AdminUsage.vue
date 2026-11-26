<template>
  <div class="adm-page">
    <section class="adm-stats">
      <div class="adm-stat"><b class="tnum">{{ fmtYuan(month?.total_cost_milli) }}</b><span>本月合计</span></div>
      <div class="adm-stat"><b class="tnum">{{ fmtYuan(month?.projection_cost_milli) }}</b><span>月末预测（线性外推）</span></div>
      <div class="adm-stat"><b class="tnum">{{ fmtYuan(day?.total_cost_milli) }}</b><span>所选日期合计</span></div>
      <div class="adm-stat"><b class="tnum">{{ alerts.length }}</b><span>本月额度告警</span></div>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>当日用量</h2>
          <p>按人汇总；费用按当前单价重算，只用于估算与对账。</p>
        </div>
        <div class="adm-actions">
          <n-date-picker :value="dayTs" type="date" size="small" style="width: 140px" :clearable="false" @update:value="onDay" />
          <span class="adm-kv">合计 <b>{{ fmtYuan(day?.total_cost_milli) }}</b></span>
        </div>
      </div>

      <div v-if="day?.users?.length" class="adm-rows">
        <div class="adm-thead"><span>用户</span><span>对话</span><span>TTS</span><span>评测</span><span>预估</span></div>
        <div v-for="r in day?.users ?? []" :key="r.user_id" class="adm-row">
          <span class="adm-name">{{ r.username }}</span>
          <span class="tnum">{{ Math.round(r.rt_seconds / 60) }} 分</span>
          <span class="tnum">{{ fmtChars(r.tts_chars) }}</span>
          <span class="tnum">{{ r.soe_calls }} 次</span>
          <span class="adm-money tnum">{{ fmtYuan(r.est_cost_milli) }}</span>
        </div>
      </div>
      <p v-else class="adm-empty">这一天还没有用量记录。</p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>本月用量</h2>
          <p>按人汇总整月；需要逐日明细可导出 CSV。</p>
        </div>
        <div class="adm-actions">
          <n-date-picker :value="monthTs" type="month" size="small" style="width: 140px" :clearable="false" @update:value="onMonth" />
          <n-button size="small" secondary :loading="exporting" @click="exportCsv">导出 CSV</n-button>
        </div>
      </div>

      <div v-if="month?.users?.length" class="adm-rows">
        <div class="adm-thead"><span>用户</span><span>对话</span><span>TTS</span><span>评测</span><span>预估</span></div>
        <div v-for="r in month?.users ?? []" :key="r.user_id" class="adm-row">
          <span class="adm-name">{{ r.username }}</span>
          <span class="tnum">{{ Math.round(r.rt_seconds / 60) }} 分</span>
          <span class="tnum">{{ fmtChars(r.tts_chars) }}</span>
          <span class="tnum">{{ r.soe_calls }} 次</span>
          <span class="adm-money tnum">{{ fmtYuan(r.est_cost_milli) }}</span>
        </div>
      </div>
      <p v-else class="adm-empty">这个月还没有用量记录。</p>
      <p class="adm-foot">
        已过 {{ month?.elapsed_days ?? 0 }} / {{ month?.days_in_month ?? 0 }} 天，当前合计
        {{ fmtYuan(month?.total_cost_milli) }}；预测值只按日均线性外推，不代表承诺费用。
      </p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>每日趋势</h2>
          <p>本月有记账的日期；空白日期表示没有调用。</p>
        </div>
      </div>
      <div v-if="month?.daily?.length" class="adm-rows">
        <div class="adm-thead"><span>日期</span><span>对话</span><span>TTS</span><span>评测</span><span>预估</span></div>
        <div v-for="d in month?.daily ?? []" :key="d.day" class="adm-row">
          <span class="adm-name tnum">{{ d.day.slice(5) }}</span>
          <span class="tnum">{{ Math.round(d.rt_seconds / 60) }} 分</span>
          <span class="tnum">{{ fmtChars(d.tts_chars) }}</span>
          <span class="tnum">{{ d.soe_calls }} 次</span>
          <span class="adm-money tnum">{{ fmtYuan(d.est_cost_milli) }}</span>
        </div>
      </div>
      <p v-else class="adm-empty">本月还没有记账。</p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>额度告警</h2>
          <p>同一账号同一阶段只记一次；可在「用户与额度」里清除。</p>
        </div>
      </div>
      <div v-if="alerts.length" class="adm-rows">
        <div class="adm-thead al"><span>用户</span><span>周期</span><span>阶段</span><span>时间</span></div>
        <div v-for="a in alerts" :key="a.id" class="adm-row al">
          <span class="adm-name">{{ a.username }}</span>
          <span>{{ a.period === "total" ? "总额 · 全部时间" : `${a.period === "day" ? "日" : "月"} · ${a.period_key}` }}</span>
          <span>
            <i class="adm-tag" :class="a.stage >= 2 ? 'danger' : 'warn'">{{ a.stage >= 2 ? "已用尽" : "达到阈值" }}</i>
          </span>
          <span class="tnum">{{ fmtTime(a.created_at) }}</span>
        </div>
      </div>
      <p v-else class="adm-empty">本月没有额度告警。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { NButton, NDatePicker, useMessage } from "naive-ui";
import { api, downloadFile } from "../../core/api";
import { fmtYuan, localDay, localMonth } from "./format";

type UsageRow = {
  user_id: number; username: string; rt_seconds: number; soe_calls: number;
  llm_in_tok: number; llm_out_tok: number; tts_chars: number; tts_calls: number;
  est_cost_milli: number;
};
type DayUsage = { day: string; total_cost_milli: number; users: UsageRow[] };
type DayTrend = {
  day: string; rt_seconds: number; soe_calls: number; llm_tok: number;
  tts_chars: number; est_cost_milli: number;
};
type MonthReport = {
  month: string; total_cost_milli: number; projection_cost_milli: number;
  days_in_month: number; elapsed_days: number;
  daily: DayTrend[]; users: UsageRow[];
};
type AlertRow = {
  id: number; user_id: number; username: string; period: string;
  period_key: string; stage: number; created_at: string | null;
};

const message = useMessage();
const dayTs = ref(Date.now());
const monthTs = ref(Date.now());
const day = ref<DayUsage | null>(null);
const month = ref<MonthReport | null>(null);
const alerts = ref<AlertRow[]>([]);
const exporting = ref(false);

function fmtChars(n: number): string {
  return n >= 10000 ? (n / 10000).toFixed(1) + " 万" : String(n ?? 0);
}

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function loadDay(): Promise<void> {
  try {
    day.value = await api<DayUsage>(`/admin/usage?day=${localDay(dayTs.value)}`);
  } catch {
    /* 忽略 */
  }
}

async function loadMonth(): Promise<void> {
  const m = localMonth(monthTs.value);
  try {
    month.value = await api<MonthReport>(`/admin/usage/report?month=${m}`);
  } catch {
    /* 忽略 */
  }
  try {
    const r = await api<{ items: AlertRow[] }>(`/admin/usage/alerts?month=${m}`);
    alerts.value = r.items ?? [];
  } catch {
    /* 忽略 */
  }
}

function onDay(ts: number): void {
  dayTs.value = ts;
  void loadDay();
}

function onMonth(ts: number): void {
  monthTs.value = ts;
  void loadMonth();
}

async function exportCsv(): Promise<void> {
  exporting.value = true;
  try {
    const m = localMonth(monthTs.value);
    await downloadFile(`/admin/usage/export?month=${m}`, `ai-usage-${m}.csv`);
  } catch (e) {
    message.error("导出失败：" + (e as Error).message);
  } finally {
    exporting.value = false;
  }
}

onMounted(() => {
  void loadDay();
  void loadMonth();
});
</script>

<style scoped>
.adm-thead.al, .adm-row.al { grid-template-columns: minmax(0, 1.2fr) minmax(0, 1.3fr) minmax(0, 1fr) minmax(0, 1.1fr); }
</style>
