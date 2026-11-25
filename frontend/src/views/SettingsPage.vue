<template>
  <div class="page">
    <n-card size="small" class="card">
      <div class="sect-head">
        <h2>备考级别</h2>
        <span class="sect-hint">选择后只显示这一级别的词库和教材；已掌握/错题记录保留，进行中的计划会按新级别重新分词</span>
      </div>

      <div class="exams">
        <button
          v-for="e in exams"
          :key="e.id"
          type="button"
          class="exam"
          :class="{ on: e.id === current, soon: e.soon }"
          :disabled="e.soon || busy"
          :aria-pressed="e.id === current"
          @click="choose(e)"
        >
          <span class="top">
            <span class="tag">{{ e.name }}</span>
            <span v-if="e.soon" class="badge">敬请期待</span>
            <span v-else-if="e.id === current" class="badge cur">
              <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12.5l4.5 4.5L19 6.5" />
              </svg>
              当前
            </span>
          </span>
          <span class="desc">{{ e.desc || "" }}</span>
        </button>
      </div>

      <p v-if="current === 'ket'" class="note">
        KET 目前只有词库（核心词表 / 生难词 / 动词短语 / 易混词 / 同义替换），阅读、听力、口语还是 PET 的内容。
      </p>
    </n-card>

    <n-card v-if="!auth.isAdmin" size="small" class="card">
      <div class="sect-head">
        <h2>AI 计费</h2>
        <span class="sect-hint">只统计你本人的付费 AI 用量</span>
      </div>
      <div class="billing">
        <div class="billing-stat">
          <span>今日</span>
          <b class="tnum">{{ usage ? fmtMilli(usage.totals.today.est_cost_milli) : usageLoading ? "…" : "—" }}</b>
        </div>
        <div class="billing-stat">
          <span>本月</span>
          <b class="tnum">{{ usage ? fmtMilli(usage.totals.month.est_cost_milli) : usageLoading ? "…" : "—" }}</b>
        </div>
        <div class="billing-action">
          <n-button size="small" secondary @click="router.push('/settings/usage')">查看明细</n-button>
        </div>
      </div>
      <p v-if="!usage && !usageLoading" class="usage-note">用量暂时加载失败，可进入明细页重试。</p>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCard, useDialog, useMessage } from "naive-ui";

import { loadBanks, DEFAULT_EXAMS, type ExamMeta } from "../core/banks";
import { fmtMilli, loadMyUsage, type MyUsage } from "../core/usage";
import { useAuthStore } from "../stores/auth";
import { useLearningStore } from "../stores/learning";

const auth = useAuthStore();
const learning = useLearningStore();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();
const exams = ref<ExamMeta[]>(DEFAULT_EXAMS);
const current = ref(auth.exam);
const busy = ref(false);
const usage = ref<MyUsage | null>(null);
const usageLoading = ref(false);

async function loadUsageSummary(): Promise<void> {
  usageLoading.value = true;
  try {
    usage.value = await loadMyUsage();
  } catch {
    usage.value = null;
  } finally {
    usageLoading.value = false;
  }
}

onMounted(async () => {
  const loaded = await loadBanks();
  if (loaded.exams.length) exams.value = loaded.exams;
  current.value = auth.exam;
  if (!auth.isAdmin) void loadUsageSummary();
});

async function doChoose(e: ExamMeta): Promise<void> {
  busy.value = true;
  try {
    await auth.setExam(e.id);
    current.value = e.id;
    message.success(`已切换到 ${e.name}`);
  } catch (err) {
    message.error("切换失败：" + (err as Error).message);
  } finally {
    busy.value = false;
  }
}

function choose(e: ExamMeta): void {
  if (e.soon || busy.value || e.id === current.value) return;
  const plan = learning.data.plan;
  if (plan.length > 0) {
    dialog.warning({
      title: "切换级别会重新切分进行中的计划",
      content:
        `你有一个 ${plan.length} 天的词汇计划（已打卡 ${plan.days_done.length} 天）。` +
        `切换到 ${e.name} 后，每天的学习词表会按 ${e.name} 词库重新计算；` +
        "已打卡记录、掌握度和错题都不会删除。确定切换吗？",
      positiveText: `切换到 ${e.name}`,
      negativeText: "取消",
      onPositiveClick: () => doChoose(e),
    });
    return;
  }
  void doChoose(e);
}
</script>

<style scoped>
.page { width: 100%; }

.card { margin-bottom: 16px; }

.sect-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.sect-head h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  color: var(--c-text);
  letter-spacing: 0.02em;
}
.sect-hint { font-size: 12px; color: var(--c-text-3); }

/* 级别卡 */
.exams {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
  gap: 10px;
}
.exam {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: flex-start;
  padding: 13px 14px 14px;
  border: 1.5px solid var(--c-line);
  border-radius: var(--r-btn);
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color var(--dur-2) var(--ease-out),
    box-shadow var(--dur-2) var(--ease-out),
    transform var(--dur-2) var(--ease-out),
    background var(--dur-2) var(--ease-out);
}
.exam:hover:not(:disabled) {
  border-color: #a9dcc0;
  transform: translateY(-1px);
  box-shadow: var(--shadow-1);
}
.exam.on {
  border-color: var(--c-primary);
  background: linear-gradient(180deg, #f4fbf7 0%, #ffffff 70%);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.09), var(--shadow-1);
}
.exam.soon {
  border-style: dashed;
  border-color: var(--c-line-strong);
  background: #fcfdfc;
  cursor: not-allowed;
}
.exam:disabled:not(.soon) { opacity: 0.6; }

.top { display: flex; align-items: center; gap: 7px; width: 100%; }
.tag {
  font-size: 15.5px;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: var(--c-text);
}
.soon .tag { color: var(--c-text-3); }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: auto;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--r-pill);
  background: #f2f5f3;
  color: var(--c-text-3);
  white-space: nowrap;
  line-height: 1.5;
}
.badge.cur { background: var(--c-primary-strong); color: #fff; }

.desc {
  width: 100%;
  font-size: 12px;
  line-height: 1.55;
  color: var(--c-text-2);
  overflow-wrap: anywhere;
}
.soon .desc { color: var(--c-text-3); }

.note {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: var(--r-sm);
  background: var(--c-accent-soft);
  border: 1px solid #f4dfc2;
  font-size: 12.5px;
  line-height: 1.7;
  color: #8a5a13;
}

/* AI 计费入口 */
.billing { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
.billing-stat { display: flex; flex-direction: column; gap: 2px; min-width: 88px; }
.billing-stat span { font-size: 11.5px; color: var(--c-text-3); }
.billing-stat b { font-size: 17px; color: var(--c-primary-strong); }
.billing-action { margin-left: auto; }
.usage-note { margin: 10px 0 0; font-size: 12px; color: var(--c-text-3); }
.tnum { font-variant-numeric: tabular-nums; }

@media (max-width: 520px) {
  .exams { grid-template-columns: 1fr 1fr; }
  .tag { font-size: 14.5px; }
}
</style>
