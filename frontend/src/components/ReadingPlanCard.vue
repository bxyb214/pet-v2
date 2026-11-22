<template>
  <n-card size="small">
    <template #header>
      <span class="hd">📖 阅读计划</span>
    </template>
    <template #header-extra>
      <n-tag v-if="hasPlan" type="success" size="small" round :bordered="false">进行中</n-tag>
    </template>

    <template v-if="!hasPlan && !creating">
      <div class="empty">
        <p class="empty-t">还没有阅读计划</p>
        <p class="empty-s">按教材 Part 切分，当天 Part 测验 ≥60% 自动打勾</p>
        <n-button type="primary" @click="creating = true">创建阅读计划</n-button>
      </div>
    </template>

    <template v-else>
      <template v-if="hasPlan">
        <div class="planrow">
          <span class="big">{{ plan.reading_length }} 天计划</span>
          <span class="muted">已完成 {{ doneCount }} / {{ plan.reading_length }} 天</span>
        </div>
        <n-progress type="line" :percentage="progressPct" :height="10" :border-radius="5" indicator-placement="inside" />
        <div class="actions">
          <n-button type="primary" secondary @click="goReading">去阅读</n-button>
          <n-popconfirm @positive-click="remove">
            <template #trigger><n-button type="error" quaternary>删除计划</n-button></template>
            删除后可重新生成，学习记录保留。确定？
          </n-popconfirm>
        </div>
      </template>

      <template v-if="creating">
        <div class="genrow" :class="{ mt: hasPlan }">
          <span class="lbl">计划天数</span>
          <n-input-number v-model:value="days" :min="1" :max="180" style="width: 132px" />
          <n-button secondary :disabled="!validDays" @click="preview">预览</n-button>
          <n-button v-if="previewDays.length && validateOk" type="primary" @click="confirm">确认生成</n-button>
          <n-button v-if="!hasPlan" quaternary @click="creating = false">取消</n-button>
        </div>
        <p v-if="previewDays.length" class="muted">
          共 {{ previewDays.length }} 天，覆盖 {{ totalParts }} 个 Part（精读 + 测验）。
        </p>
        <div v-if="previewDays.length" class="grid">
          <div v-for="d in previewDays.slice(0, 8)" :key="d.day" class="daycard">
            <p class="daynum">第 {{ d.day }} 天</p>
            <p class="muted">{{ d.parts.length }} 个 Part</p>
          </div>
        </div>
      </template>
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCard, NInputNumber, NPopconfirm, NProgress, NTag } from "naive-ui";
import { useLearningStore } from "../stores/learning";
import { loadReading } from "../core/reading";
import { buildReadingPlan, validateReadingPlan, type ReadingPlanDay, type ReadingPartRef } from "../core/plan";

const learning = useLearningStore();
const router = useRouter();
const plan = computed(() => learning.data.plan);
const hasPlan = computed(() => plan.value.reading_length > 0);
const creating = ref(false);
const days = ref(30);
const previewDays = ref<ReadingPlanDay[]>([]);
const validateOk = ref(false);
const allParts = ref<ReadingPartRef[]>([]);

onMounted(async () => {
  const d = await loadReading();
  allParts.value = d.tests.flatMap((t) =>
    t.parts.map((p) => ({ book: t.book || "t2", testNo: t.no, part: p.part })),
  );
});

const validDays = computed(() => Number.isInteger(days.value) && days.value >= 1 && days.value <= 180);
const totalParts = computed(() => allParts.value.length);
const doneCount = computed(() => plan.value.reading_days_done.length);
const progressPct = computed(() =>
  plan.value.reading_length ? Math.round((doneCount.value / plan.value.reading_length) * 100) : 0,
);

function preview(): void {
  const p = buildReadingPlan(allParts.value, days.value);
  previewDays.value = p;
  validateOk.value = validateReadingPlan(allParts.value, p);
}
function confirm(): void {
  learning.setReadingPlan(previewDays.value.length);
  previewDays.value = [];
  creating.value = false;
}
function remove(): void {
  learning.deleteReadingPlan();
  creating.value = false;
}
function goReading(): void {
  void router.push("/english/reading/home");
}
</script>

<style scoped>
.hd { font-weight: 700; font-size: 16px; }
.empty { text-align: center; padding: 18px 8px 8px; }
.empty-t { margin: 0 0 4px; font-weight: 700; font-size: 16px; color: var(--c-text); }
.empty-s { margin: 0 0 14px; font-size: 13.5px; color: var(--c-text-2); }
.planrow { display: flex; align-items: baseline; gap: 12px; margin-bottom: 10px; }
.big { font-size: 20px; font-weight: 800; color: var(--c-text); }
.muted { color: var(--c-text-2); font-size: 13.5px; }
.actions { display: flex; gap: 12px; margin-top: 14px; align-items: center; }
.genrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.genrow.mt { margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--c-line); }
.lbl { font-size: 14px; color: var(--c-text-2); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-top: 12px; }
.daycard { background: var(--c-mint-bg, #f6faf7); border-radius: 10px; padding: 10px 12px; }
.daynum { margin: 0 0 2px; font-weight: 700; font-size: 13.5px; }
</style>
