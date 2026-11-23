<template>
  <div class="page">
    <p v-if="!banksReady" class="loading">词库加载中…</p>

    <n-card v-else-if="!planDay" size="small">
      <n-empty description="没有找到这一天的词汇计划">
        <template #extra>
          <n-button type="primary" @click="router.push('/english/words/plan')">去创建计划</n-button>
        </template>
      </n-empty>
    </n-card>

    <template v-else>
      <div class="planbar">
        <b>第 {{ dayNo }} 天 · 学习</b>
        <span>{{ breakdown }}</span>
        <span class="total">共 {{ planDay.total }} 词</span>
      </div>

      <!-- 学习也能按四个部分分别进行 -->
      <nav class="banknav" aria-label="选择词库">
        <button
          v-for="k in bankKeys"
          :key="k"
          type="button"
          class="bankchip"
          :class="{ on: k === bank }"
          @click="switchBank(k)"
        >
          <span class="bn">{{ bankMeta[k]?.short || k }}</span>
          <span class="bc tnum">{{ planDay.banks[k]?.length ?? 0 }}</span>
        </button>
      </nav>

      <n-card size="small" class="studycard">
        <template #header>
          <div class="cardhead">
            <span>{{ bankMeta[bank]?.short || bank }}</span>
            <span class="idx tnum">{{ words.length ? index + 1 : 0 }} / {{ words.length }}</span>
          </div>
        </template>

        <WordStudyCard v-if="word" :key="word.id" :word="word" />
        <p v-else class="muted">这个词库今天没有单词。</p>

        <div class="navrow">
          <n-button :disabled="index <= 0" @click="prev">上一张</n-button>
          <n-button :disabled="index >= words.length - 1" @click="next">下一张</n-button>
        </div>

        <div class="actions">
          <n-button type="primary" :disabled="!words.length" @click="goTest">去测试本库</n-button>
          <router-link to="/english/words/plan" class="linkbtn">返回计划</router-link>
        </div>
      </n-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NCard, NEmpty } from "naive-ui";
import WordStudyCard from "../components/WordStudyCard.vue";
import { availableBankKeys, loadBanks, EMPTY_BANKS, type BankMeta } from "../core/banks";
import { splitPlan, type WordBanks } from "../core/plan";
import { useLearningStore } from "../stores/learning";
import { useAuthStore } from "../stores/auth";

const learning = useLearningStore();
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();

const banks = ref<WordBanks>(EMPTY_BANKS);
const bankMeta = ref<Record<string, BankMeta>>({});
const banksReady = ref(false);
void loadBanks()
  .then((r) => {
    banks.value = r.banks;
    bankMeta.value = r.bankMeta;
  })
  .finally(() => {
    banksReady.value = true;
  });

const planLength = computed(() => learning.data.plan.length);
const activeKeys = computed(() => availableBankKeys(banks.value, bankMeta.value, auth.exam));
const planDays = computed(() =>
  planLength.value > 0 ? splitPlan(banks.value, planLength.value, activeKeys.value) : [],
);
const dayNo = computed(() => {
  const n = Number(route.query.day ?? 0);
  if (Number.isInteger(n) && n >= 1 && n <= planLength.value) return n;
  const done = new Set(learning.data.plan.days_done);
  for (let d = 1; d <= planLength.value; d++) {
    if (!done.has(String(d))) return d;
  }
  return planLength.value || 0;
});
const planDay = computed(() => planDays.value[dayNo.value - 1] ?? null);
const bankKeys = computed(() =>
  activeKeys.value.filter((k) => (planDay.value?.banks[k]?.length ?? 0) > 0),
);

const bank = ref(String(route.query.bank ?? ""));
const index = ref(0);
watch(
  [bankKeys, () => route.query.bank, dayNo],
  () => {
    if (!bankKeys.value.length) {
      bank.value = "";
    } else if (!bankKeys.value.includes(bank.value)) {
      bank.value = bankKeys.value[0];
    }
    index.value = 0;
  },
);

const words = computed(() => planDay.value?.banks[bank.value] ?? []);
const word = computed(() => words.value[index.value] ?? null);
const breakdown = computed(() => {
  const pd = planDay.value;
  if (!pd) return "";
  return activeKeys.value
    .map((k) => ({ label: bankMeta.value[k]?.short || k, n: pd.banks[k]?.length ?? 0 }))
    .filter((x) => x.n > 0)
    .map((x) => `${x.label} ${x.n}`)
    .join(" · ");
});

function switchBank(k: string): void {
  if (k === bank.value) return;
  bank.value = k;
  index.value = 0;
}
function prev(): void {
  if (index.value > 0) index.value -= 1;
}
function next(): void {
  if (index.value < words.value.length - 1) index.value += 1;
}
function goTest(): void {
  void router.push({ path: "/english/words/study", query: { day: String(dayNo.value), bank: bank.value } });
}
</script>

<style scoped>
.page { width: 100%; max-width: 820px; margin: 0 auto; }
.loading { padding: 20px; text-align: center; color: var(--c-text-2); }

.planbar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  padding: 10px 14px; margin-bottom: 12px;
  background: var(--c-primary-soft); border: 1px solid #cfeadd;
  border-radius: var(--r-btn); color: var(--c-text-2); font-size: 13px;
}
.planbar b { color: var(--c-primary-strong); font-size: 14px; }
.total { margin-left: auto; color: var(--c-primary-strong); font-weight: 700; }

.banknav { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.bankchip {
  display: inline-flex; align-items: center; gap: 7px;
  min-height: 38px; padding: 0 13px;
  border: 1.5px solid var(--c-line); border-radius: var(--r-pill);
  background: #fff; color: var(--c-text-2);
  font: inherit; cursor: pointer;
  transition: border-color var(--dur-2) var(--ease-out),
    background var(--dur-2) var(--ease-out), color var(--dur-2) var(--ease-out);
}
.bankchip:hover { border-color: #a9dcc0; background: #fbfefc; }
.bankchip .bn { font-size: 13px; font-weight: 700; }
.bankchip .bc { font-size: 12px; color: var(--c-text-3); }
.bankchip.on {
  border-color: var(--c-primary);
  background: var(--c-primary-soft);
  color: var(--c-primary-strong);
}
.bankchip.on .bc { color: var(--c-primary-strong); }
.bankchip:focus-visible { outline: 2px solid var(--c-primary); outline-offset: 2px; }

.studycard :deep(.n-card__content) { padding-top: 6px; }
.cardhead {
  display: flex; align-items: baseline; gap: 10px;
  font-size: 13.5px; font-weight: 700; color: var(--c-text);
}
.idx { margin-left: auto; font-size: 12.5px; font-weight: 600; color: var(--c-text-3); }

.navrow { display: flex; gap: 10px; justify-content: center; margin-top: 16px; }
.navrow :deep(.n-button) { min-width: 108px; }
.actions { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-top: 16px; }
.muted { color: var(--c-text-2); font-size: 13.5px; text-align: center; padding: 28px 0; }
</style>
