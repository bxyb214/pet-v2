<template>
  <div class="page">
    <n-card size="small">
      <template #header>
        <span class="hd">词汇计划</span>
      </template>
      <template #header-extra>
        <n-tag v-if="hasPlan" type="success" size="small" round :bordered="false">进行中</n-tag>
      </template>

      <!-- 空状态：与创建表单分开，只给一个主动作 -->
      <div v-if="!hasPlan && !creating && !previewDays.length" class="empty">
        <p class="empty-t">还没有词汇计划</p>
        <p class="empty-s">按天数把词库不重不漏切好，每天学一部分，完成后自动打勾</p>
        <n-button type="primary" size="large" @click="creating = true">创建词汇计划</n-button>
      </div>

      <template v-if="hasPlan">
        <!-- 进度用「可数的格子」而不是百分比：看得出哪天做了、还剩几格 -->
        <PlanWall :length="planLen" :days-done="learning.data.plan.days_done" />

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
          共 {{ previewDays.length }} 天，每天约 {{ avgTotal }} 词（{{ bankNames }}）。
          <n-tag v-if="!validateOk" type="error" size="small">切分校验未通过，请重试</n-tag>
        </p>
        <div v-if="previewDays.length" class="grid">
          <div v-for="d in previewDays.slice(0, 8)" :key="d.day" class="daycard">
            <p class="daynum">第 {{ d.day }} 天</p>
            <p class="muted">{{ d.total }} 词 · {{ dayBreakdown(d) }}</p>
          </div>
        </div>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCard, NInputNumber, NPopconfirm, NTag } from "naive-ui";
import { useLearningStore } from "../stores/learning";
import PlanWall from "../components/PlanWall.vue";
import { availableBankKeys, loadBanks, EMPTY_BANKS, type BankMeta } from "../core/banks";
import { useAuthStore } from "../stores/auth";
import { splitPlan, validatePlan, type PlanDay, type WordBanks } from "../core/plan";

const learning = useLearningStore();
const router = useRouter();
const days = ref(30);
const banks = ref<WordBanks>(EMPTY_BANKS);
const bankMeta = ref<Record<string, BankMeta>>({});
const previewDays = ref<PlanDay[]>([]);
const validateOk = ref(false);
const creating = ref(false);
const auth = useAuthStore();

/** 当前级别下要参与计划的词库（PET 四库 / KET 五库），顺序即切分顺序 */
const activeKeys = ref<string[]>([]);
void loadBanks().then((r) => {
  banks.value = r.banks;
  bankMeta.value = r.bankMeta;
  activeKeys.value = availableBankKeys(r.banks, r.bankMeta, auth.exam);
});

const bankNames = computed(() =>
  activeKeys.value.map((k) => bankMeta.value[k]?.short || k).join(" / "),
);
function dayBreakdown(d: PlanDay): string {
  return activeKeys.value
    .map((k) => (d.banks[k]?.length ?? 0))
    .filter((n) => n > 0)
    .join("+");
}

const hasPlan = computed(() => learning.data.plan.length > 0);
const planLen = computed(() => learning.data.plan.length);
const validDays = computed(() => Number.isInteger(days.value) && days.value >= 1 && days.value <= 180);
const avgTotal = computed(() =>
  previewDays.value.length
    ? Math.round(previewDays.value.reduce((s, d) => s + d.total, 0) / previewDays.value.length)
    : 0,
);

function preview(): void {
  const plan = splitPlan(banks.value, days.value, activeKeys.value);
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
.hd {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 16px;
  color: var(--c-text);
}
/* 标题前导细条：替代 emoji，安静但有标记感 */
.hd::before {
  content: "";
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--c-primary);
  flex: none;
}
.empty { text-align: center; padding: 22px 8px 10px; }
.empty-t { margin: 0 0 4px; font-weight: 700; font-size: 17px; color: var(--c-text); }
.empty-s { margin: 0 0 16px; font-size: 13.5px; color: var(--c-text-2); }
.muted { color: var(--c-text-2); font-size: 13.5px; }
.actions { display: flex; gap: 12px; margin-top: 14px; align-items: center; }
.genrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.genrow.mt { margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--c-line); }
.lbl { font-size: 14px; color: var(--c-text-2); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 12px; }
.daycard { background: var(--c-mint-bg, #f6faf7); border-radius: 10px; padding: 10px 12px; }
.daynum { margin: 0 0 2px; font-weight: 700; font-size: 13.5px; }

</style>
