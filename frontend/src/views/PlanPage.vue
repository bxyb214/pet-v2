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

        <p v-if="totalQuestions" class="muted plan-gen">
          共 {{ totalQuestions }} 个单词 · {{ totalTestQuestions }} 道测试题
          （<template v-for="(t, i) in bankRules" :key="t.key"><template v-if="i">、</template>{{ t.label }} {{ t.dims }}</template>），
          学习和测试都可以按词库分别进行。
        </p>

        <div class="actions">
          <n-button secondary @click="goLearn">学习第 {{ nextPlanDay }} 天</n-button>
          <n-button type="primary" @click="goTest">测试第 {{ nextPlanDay }} 天</n-button>
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

      <!-- 创建 / 预览 -->
      <template v-if="creating">
        <div class="genrow" :class="{ mt: hasPlan }">
          <span class="lbl">计划天数</span>
          <n-input-number v-model:value="days" :min="1" :max="180" style="width: 132px" />
          <n-button secondary :disabled="!validDays" @click="preview">预览</n-button>
          <n-button v-if="previewDays.length && validateOk" type="primary" @click="confirmPlan">确认生成</n-button>
          <n-button v-if="!hasPlan" quaternary @click="cancelCreate">取消</n-button>
        </div>
        <LoadingBlock v-if="!banksReady" plain text="词库加载中…" />
        <p v-if="previewDays.length" class="muted">
          共 {{ previewDays.length }} 天，每种词库各自平均分到各天，每天约 {{ avgTotal }} 词（{{ bankNames }}）。
          <n-tag v-if="!validateOk" type="error" size="small">切分校验未通过，请重试</n-tag>
        </p>
        <div v-if="previewDays.length" class="grid">
          <div v-for="d in previewDays" :key="d.day" class="daycard">
            <p class="daynum">第 {{ d.day }} 天</p>
            <p class="muted">{{ d.total }} 词 · {{ dayBreakdown(d) }}</p>
          </div>
        </div>
      </template>
    </n-card>

    <DeletePlanModal
      v-model:show="delOpen"
      note="删除后学习进度保留，可重新生成新计划。"
      @confirm="deletePlan"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCard, NInputNumber, NTag } from "naive-ui";
import { useLearningStore } from "../stores/learning";
import PlanWall from "../components/PlanWall.vue";
import LoadingBlock from "../components/LoadingBlock.vue";
import DeletePlanModal from "../components/DeletePlanModal.vue";
import { availableBankKeys, loadBanks, EMPTY_BANKS, type BankMeta } from "../core/banks";
import { useAuthStore } from "../stores/auth";
import { splitPlan, validatePlan, type PlanDay, type WordBanks } from "../core/plan";
import { DIM_LABEL, testDimsForBank, type QuizDim } from "../core/quiz";

const learning = useLearningStore();
const router = useRouter();
const days = ref(30);
const banks = ref<WordBanks>(EMPTY_BANKS);
const bankMeta = ref<Record<string, BankMeta>>({});
const previewDays = ref<PlanDay[]>([]);
const validateOk = ref(false);
const creating = ref(false);
const delOpen = ref(false);
const auth = useAuthStore();

/** 当前级别下要参与计划的词库（PET 四库 / KET 五库），顺序即切分顺序 */
const activeKeys = ref<string[]>([]);
const banksReady = ref(false);
void loadBanks()
  .then((r) => {
    banks.value = r.banks;
    bankMeta.value = r.bankMeta;
    activeKeys.value = availableBankKeys(r.banks, r.bankMeta, auth.exam);
  })
  .finally(() => {
    banksReady.value = true;
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
/** 已生成的天/题：与学习页同一套 splitPlan，保证「生成」和「开练」内容一致 */
const planDays = computed(() =>
  hasPlan.value ? splitPlan(banks.value, planLen.value, activeKeys.value) : [],
);
const totalQuestions = computed(() => planDays.value.reduce((s, d) => s + d.total, 0));
/** 测试题量：每库词数 × 该库每题题型数（必默三型，其他库两型） */
const totalTestQuestions = computed(() =>
  planDays.value.reduce(
    (sum, d) =>
      sum +
      activeKeys.value.reduce(
        (s, k) =>
          s + (d.banks[k]?.length ?? 0) * testDimsForBank(k, bankMeta.value[k]?.dims).length,
        0,
      ),
    0,
  ),
);
/** 各库题型说明（页面文案用） */
const bankRules = computed(() =>
  activeKeys.value.map((k) => {
    const dims = testDimsForBank(k, bankMeta.value[k]?.dims) as QuizDim[];
    return {
      key: k,
      label: bankMeta.value[k]?.short || k,
      dims: dims.map((d) => DIM_LABEL[d]).join(" / "),
    };
  }),
);
/** 下一个未完成的天；全部完成则回到最后一天 */
const nextPlanDay = computed(() => {
  const done = new Set(learning.data.plan.days_done);
  for (let d = 1; d <= planLen.value; d++) {
    if (!done.has(String(d))) return d;
  }
  return planLen.value || 1;
});
const validDays = computed(
  () =>
    Number.isInteger(days.value) &&
    days.value >= 1 &&
    days.value <= 180 &&
    activeKeys.value.length > 0,
);
const avgTotal = computed(() =>
  previewDays.value.length
    ? Math.round(previewDays.value.reduce((s, d) => s + d.total, 0) / previewDays.value.length)
    : 0,
);

function preview(): void {
  if (!activeKeys.value.length) return;
  const plan = splitPlan(banks.value, days.value, activeKeys.value);
  previewDays.value = plan;
  // 只校验当前级别参与切分的库；banks.json 同时含 PET + KET，不能一起校验
  validateOk.value = validatePlan(banks.value, plan, activeKeys.value);
}
// 改天数后旧预览失效，避免「确认生成」沿用上一次的天数
watch(days, () => {
  previewDays.value = [];
  validateOk.value = false;
});
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
function goLearn(): void {
  void router.push(`/english/words/study/day?day=${nextPlanDay.value}`);
}
function goTest(): void {
  void router.push(`/english/words/study?day=${nextPlanDay.value}`);
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
.plan-gen { margin: 10px 0 0; line-height: 1.6; }
.actions { display: flex; gap: 12px; margin-top: 14px; align-items: center; }
/* 删除计划：填充红 + 图标 + 投影，避免被当成普通文字按钮 */
.del-plan { min-height: 42px; padding: 0 18px; box-shadow: 0 6px 14px rgba(220, 38, 38, 0.18); }
.del-plan:hover { box-shadow: 0 8px 18px rgba(220, 38, 38, 0.26); }
.genrow { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.genrow.mt { margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--c-line); }
.lbl { font-size: 14px; color: var(--c-text-2); }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 12px; }
.daycard { background: var(--c-mint-bg, #f6faf7); border-radius: 10px; padding: 10px 12px; }
.daynum { margin: 0 0 2px; font-weight: 700; font-size: 13.5px; }

</style>
