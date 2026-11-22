<template>
  <div class="page">
    <n-card size="small">
      <template #header>
        <span class="hd">🌱 词汇计划</span>
      </template>
      <template #header-extra>
        <n-tag v-if="hasPlan" type="success" size="small" round :bordered="false">进行中</n-tag>
      </template>

      <!-- 空状态：与创建表单分开，只给一个主动作 -->
      <div v-if="!hasPlan && !creating && !previewDays.length" class="empty">
        <p class="empty-t">还没有词汇计划</p>
        <p class="empty-s">按天数把四个词库不重不漏切好，每天学一部分，完成后自动打勾</p>
        <n-button type="primary" size="large" @click="creating = true">创建词汇计划</n-button>
      </div>

      <template v-if="hasPlan">
        <div class="planrow">
          <span class="stage">{{ progressPct >= 100 ? "🌳" : progressPct >= 60 ? "🌿" : "🌱" }}</span>
          <span class="big">{{ learning.data.plan.length }} 天计划</span>
          <span class="muted">已完成 {{ doneCount }} / {{ learning.data.plan.length }} 天</span>
        </div>
        <n-progress type="line" :percentage="progressPct" :height="12" :border-radius="6" indicator-placement="inside" />
        <div class="actions">
          <n-button type="primary" secondary @click="goStudy">去学习</n-button>
          <n-popconfirm @positive-click="deletePlan">
            <template #trigger><n-button type="error" quaternary>删除计划</n-button></template>
            删除后学习进度保留，可重新生成新计划。确定？
          </n-popconfirm>
        </div>
      </template>

      <!-- 创建 / 预览 -->
      <template v-if="creating">
        <div class="genrow" :class="{ mt: hasPlan }">
          <span class="lbl">计划天数</span>
          <n-input-number v-model:value="days" :min="1" :max="180" style="width: 132px" />
          <n-button secondary :disabled="!validDays" @click="preview">预览</n-button>
          <n-button v-if="previewDays.length && validateOk" type="primary" @click="confirmPlan">确认生成</n-button>
          <n-button v-if="!hasPlan" quaternary @click="cancelCreate">取消</n-button>
        </div>
        <p v-if="previewDays.length" class="muted">
          共 {{ previewDays.length }} 天，每天约 {{ avgTotal }} 词（必默 / 高频 / 固搭 / 同义）。
          <n-tag v-if="!validateOk" type="error" size="small">切分校验未通过，请重试</n-tag>
        </p>
        <div v-if="previewDays.length" class="grid">
          <div v-for="d in previewDays.slice(0, 8)" :key="d.day" class="daycard">
            <p class="daynum">第 {{ d.day }} 天</p>
            <p class="muted">{{ d.total }} 词 · {{ d.bimo.length }}+{{ d.gaopin.length }}+{{ d.guding.length }}+{{ d.tongyi.length }}</p>
          </div>
        </div>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCard, NInputNumber, NPopconfirm, NProgress, NTag } from "naive-ui";
import { useLearningStore } from "../stores/learning";
import { loadBanks, EMPTY_BANKS } from "../core/banks";
import { splitPlan, validatePlan, type PlanDay, type WordBanks } from "../core/plan";

const learning = useLearningStore();
const router = useRouter();
const days = ref(30);
const banks = ref<WordBanks>(EMPTY_BANKS);
const previewDays = ref<PlanDay[]>([]);
const validateOk = ref(false);
const creating = ref(false);
void loadBanks().then((r) => (banks.value = r.banks));

const hasPlan = computed(() => learning.data.plan.length > 0);
const validDays = computed(() => Number.isInteger(days.value) && days.value >= 1 && days.value <= 180);
const doneCount = computed(() => learning.data.plan.days_done.length);
const progressPct = computed(() =>
  learning.data.plan.length ? Math.round((doneCount.value / learning.data.plan.length) * 100) : 0,
);
const avgTotal = computed(() =>
  previewDays.value.length
    ? Math.round(previewDays.value.reduce((s, d) => s + d.total, 0) / previewDays.value.length)
    : 0,
);

function preview(): void {
  const plan = splitPlan(banks.value, days.value);
  previewDays.value = plan;
  validateOk.value = validatePlan(banks.value, plan);
}
function confirmPlan(): void {
  learning.setPlan(previewDays.value.length);
  previewDays.value = [];
  creating.value = false;
}
function cancelCreate(): void {
  creating.value = false;
  previewDays.value = [];
}
function deletePlan(): void {
  learning.deletePlan();
}
function goStudy(): void {
  void router.push("/english/words/study");
}
</script>

<style scoped>
.page { width: 100%; }
.hd { font-weight: 700; font-size: 16px; }
.empty { text-align: center; padding: 22px 8px 10px; }
.empty-t { margin: 0 0 4px; font-weight: 700; font-size: 17px; color: var(--c-text); }
.empty-s { margin: 0 0 16px; font-size: 13.5px; color: var(--c-text-2); }
.planrow { display: flex; align-items: baseline; gap: 10px; margin-bottom: 12px; }
.big { font-size: 21px; font-weight: 800; color: var(--c-text); }
.stage { font-size: 24px; }
.muted { color: var(--c-text-2); font-size: 13.5px; }
.actions { display: flex; gap: 12px; margin-top: 14px; align-items: center; }
.genrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.genrow.mt { margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--c-line); }
.lbl { font-size: 14px; color: var(--c-text-2); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 12px; }
.daycard { background: var(--c-mint-bg, #f6faf7); border-radius: 10px; padding: 10px 12px; }
.daynum { margin: 0 0 2px; font-weight: 700; font-size: 13.5px; }
</style>
