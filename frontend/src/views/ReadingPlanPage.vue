<template>
  <main class="page">
    <h1>阅读计划</h1>
    <p class="sub">先选教材，再定天数；按 Part 顺序切分，当天 Part 测验 ≥60% 自动打勾</p>

    <section class="card">
      <div v-if="hasPlan" class="card-h">
        <div>
          <p class="title">共 {{ planDays }} 天 · {{ planParts }} 个 Part</p>
          <p class="desc">{{ planBooksText }}</p>
        </div>
        <n-tag type="success" size="small" round :bordered="false">进行中</n-tag>
      </div>

      <!-- 进度墙 -->
      <template v-if="hasPlan">
        <PlanWall :length="planDays" :days-done="plan.reading_days_done" />
        <div class="actions">
          <n-button type="primary" secondary @click="goReading">去阅读</n-button>
          <n-button quaternary @click="startCreate">重新规划</n-button>
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

      <!-- 空状态 -->
      <div v-else-if="!creating" class="empty">
        <p class="empty-t">还没有阅读计划</p>
        <p class="empty-s">按教材的 Part 顺序切分，每天读几个 Part 并做对应测验</p>
        <n-button type="primary" size="large" :disabled="!books.length" @click="startCreate">创建阅读计划</n-button>
      </div>

      <!-- 创建表单 -->
      <div v-if="creating" class="form" :class="{ sep: hasPlan }">
        <div class="frow">
          <span class="lbl">教材</span>
          <n-checkbox-group v-model:value="picked">
            <n-checkbox v-for="b in books" :key="b.id" :value="b.id">
              {{ b.name }}<span class="bmeta">· {{ b.parts }} 个 Part</span>
            </n-checkbox>
          </n-checkbox-group>
        </div>
        <p v-if="!picked.length" class="warn">至少选一本教材，才能切分计划。</p>

        <div class="frow">
          <span class="lbl">计划天数</span>
          <n-input-number v-model:value="days" :min="1" :max="180" style="width: 132px" />
          <n-button secondary :disabled="!canPreview" @click="preview">预览</n-button>
          <n-button v-if="previewDays.length && validateOk" type="primary" @click="confirm">确认生成</n-button>
          <n-button quaternary @click="cancel">取消</n-button>
        </div>

        <p v-if="previewDays.length" class="muted">
          共 {{ previewDays.length }} 天，覆盖 {{ previewTotal }} 个 Part（{{ pickedNames }}），
          每天约 {{ avgParts }} 个。
          <n-tag v-if="!validateOk" type="error" size="small" style="margin-left: 6px">切分校验未通过，请重试</n-tag>
        </p>

        <div v-if="previewDays.length" class="days">
          <div v-for="d in previewDays.slice(0, 6)" :key="d.day" class="daycard">
            <p class="daynum">第 {{ d.day }} 天 <span class="dcnt">{{ d.parts.length }} 个 Part</span></p>
            <p v-for="g in dayGroups(d)" :key="g.label" class="dayrefs">
              <span class="gbook">{{ g.label }}</span><span class="gsep">·</span>{{ g.parts }}
            </p>
          </div>
          <p v-if="previewDays.length > 6" class="moredays">还有 {{ previewDays.length - 6 }} 天…</p>
        </div>
      </div>
    </section>

    <DeletePlanModal
      v-model:show="delOpen"
      note="删除后可重新生成，精读与错题记录都会保留。"
      @confirm="remove"
    />
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCheckbox, NCheckboxGroup, NInputNumber, NTag } from "naive-ui";
import PlanWall from "../components/PlanWall.vue";
import DeletePlanModal from "../components/DeletePlanModal.vue";
import { useLearningStore } from "../stores/learning";
import { useAuthStore } from "../stores/auth";
import { loadReading, type RBook, type RTest } from "../core/reading";
import {
  buildReadingPlan, readingParts, validateReadingPlan,
  type ReadingPartRef, type ReadingPlanDay,
} from "../core/plan";

const learning = useLearningStore();
const auth = useAuthStore();
const router = useRouter();

const plan = computed(() => learning.data.plan);
const hasPlan = computed(() => plan.value.reading_length > 0);
const planDays = computed(() => plan.value.reading_length);
/** 计划覆盖的教材（空 = 全部，含老计划） */
const planBooks = computed(() => plan.value.reading_books ?? []);

const tests = ref<RTest[]>([]);
const books = ref<(RBook & { parts: number })[]>([]);

onMounted(async () => {
  const d = await loadReading(auth.exam);
  tests.value = d.tests;
  const all: ReadingPartRef[] = readingParts(d.tests);
  books.value = d.books
    .filter((b) => all.some((p) => p.book === b.id))
    .map((b) => ({ ...b, parts: all.filter((p) => p.book === b.id).length }));
});

const bookName = (id: string): string => books.value.find((b) => b.id === id)?.name || id.toUpperCase();
/** 计划已生效时展示它覆盖哪些教材；没记录（老计划）= 全部 */
const planBooksText = computed(() =>
  planBooks.value.length
    ? planBooks.value.map(bookName).join(" + ")
    : `全部教材（${books.value.map((b) => b.name).join(" + ") || "Trainer 1 / Trainer 2"}）`,
);

const creating = ref(false);
const delOpen = ref(false);
const picked = ref<string[]>([]);
const days = ref(30);
const previewDays = ref<ReadingPlanDay[]>([]);
const validateOk = ref(false);

const pickedNames = computed(() => picked.value.map(bookName).join(" + "));
const canPreview = computed(
  () => picked.value.length > 0 && Number.isInteger(days.value) && days.value >= 1 && days.value <= 180,
);
const previewTotal = computed(() => previewDays.value.reduce((s, d) => s + d.parts.length, 0));
const avgParts = computed(() =>
  previewDays.value.length ? (previewTotal.value / previewDays.value.length).toFixed(1) : "0",
);
/** 剩余天数（按当前教材与天数算出来会比 1 天还碎时提示一下） */
const planParts = computed(() => {
  const parts = readingParts(tests.value, planBooks.value);
  return parts.length;
});

/** 一天里按「教材 · 套」归组，Part 号并排显示，比逐个 Part 全称好读 */
function dayGroups(d: ReadingPlanDay): { label: string; parts: string }[] {
  const map = new Map<string, number[]>();
  for (const p of d.parts) {
    const label = `${bookName(p.book)} · ${testTitle(p.testNo)}`;
    map.set(label, [...(map.get(label) ?? []), p.part]);
  }
  return [...map].map(([label, parts]) => ({ label, parts: parts.map((n) => `P${n}`).join(" ") }));
}

function testTitle(no: number): string {
  return tests.value.find((t) => t.no === no)?.title || `Test ${no}`;
}

function startCreate(): void {
  creating.value = true;
  previewDays.value = [];
  // 默认沿用当前计划的教材（无计划或老计划 = 全部教材）
  picked.value = planBooks.value.length ? [...planBooks.value] : books.value.map((b) => b.id);
}

function preview(): void {
  const parts = readingParts(tests.value, picked.value);
  const p = buildReadingPlan(parts, days.value);
  previewDays.value = p;
  validateOk.value = validateReadingPlan(parts, p);
}

function confirm(): void {
  learning.setReadingPlan(previewDays.value.length, picked.value);
  previewDays.value = [];
  creating.value = false;
}

function cancel(): void {
  creating.value = false;
  previewDays.value = [];
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
.page { width: 100%; }
h1 { font-size: var(--fs-display); font-weight: 800; letter-spacing: .2px; color: var(--c-text); margin: 0 0 4px; }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 16px; }
.card { background: var(--c-card); border-radius: var(--r-card); box-shadow: var(--shadow-card); padding: 16px; }
.card-h { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.title { font-size: var(--fs-title); font-weight: 700; margin: 0 0 2px; color: var(--c-text); }
.title .muted { color: var(--c-text-2); font-weight: 400; font-size: var(--fs-sub); }
.desc { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0; }
.empty { text-align: center; padding: 20px 8px 10px; }
.empty-t { margin: 0 0 4px; font-weight: 700; font-size: 16px; color: var(--c-text); }
.empty-s { margin: 0 0 14px; font-size: 13.5px; color: var(--c-text-2); }
.actions { display: flex; gap: 12px; margin-top: 14px; align-items: center; }
/* 删除计划：填充红 + 图标 + 投影，避免被当成普通文字按钮 */
.del-plan { min-height: 42px; padding: 0 18px; box-shadow: 0 6px 14px rgba(220, 38, 38, 0.18); }
.del-plan:hover { box-shadow: 0 8px 18px rgba(220, 38, 38, 0.26); }

.form { display: flex; flex-direction: column; gap: 12px; margin-top: 14px; }
.form.sep { margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--c-line); }
.frow { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.lbl { font-size: 14px; color: var(--c-text-2); flex: none; }
.bmeta { color: var(--c-text-2); font-size: 12.5px; margin-left: 4px; }
.warn { margin: -4px 0 0; font-size: 12.5px; color: var(--c-accent); }
.muted { color: var(--c-text-2); font-size: 13.5px; margin: 0; }
.days { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
.daycard { background: var(--c-mint-bg); border-radius: var(--r-sm); padding: 10px 12px; }
.daynum { margin: 0 0 2px; font-weight: 700; font-size: 13.5px; color: var(--c-text); }
.dcnt { font-weight: 400; font-size: 11.5px; color: var(--c-text-3); margin-left: 4px; }
.dayrefs { margin: 2px 0 0; font-size: 12px; color: var(--c-text); line-height: 1.5; }
.gbook { color: var(--c-text-3); }
.gsep { color: var(--c-text-3); margin: 0 5px; }
.moredays { margin: 0; align-self: center; font-size: 12.5px; color: var(--c-text-3); }

@media (max-width: 767px) {
  .card { padding: 14px 12px; }
  .card-h { gap: 8px; }
  .title { font-size: 19px; }
  .actions { flex-wrap: wrap; }
}
</style>
