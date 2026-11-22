<template>
  <div class="page">
    <div class="stats">
      <div class="card stat"><div class="ico">🔁</div><div><div class="v">{{ rows.length }}</div><div class="l">错题总数</div></div></div>
      <div class="card stat warn"><div class="ico">⏰</div><div><div class="v">{{ dueRows.length }}</div><div class="l">今天到期</div></div></div>
      <div class="card stat"><div class="ico">✅</div><div><div class="v">{{ graduated }}</div><div class="l">已划完全维度</div></div></div>
    </div>

    <n-card size="small">
      <template #header>错题本 · 记忆曲线</template>
      <template #header-extra>
        <n-radio-group v-model:value="filter" size="small">
          <n-radio-button value="due">今天到期</n-radio-button>
          <n-radio-button value="all">全部</n-radio-button>
        </n-radio-group>
      </template>

      <n-empty
        v-if="!shown.length"
        description="没有错题，太棒了！答错的词会自动进入这里，按 1/2/4/7/15 天间隔反复出现。"
      >
        <template #icon><span style="font-size:36px">🎉</span></template>
      </n-empty>

      <div v-else class="rows">
        <div v-for="r in shown" :key="r.id" class="row" :class="{ due: r.due }">
          <div class="left">
            <span class="w">{{ r.en }}</span>
            <n-tag size="small" :bordered="false" class="banktag">{{ r.bank }}</n-tag>
            <span class="muted">{{ r.cn }}</span>
          </div>
          <div class="dims">
            <n-tag v-for="d in r.dims" :key="d" size="small" type="warning" :bordered="false" round>
              {{ (DIM_LABEL as Record<string, string>)[d] ?? d }}
            </n-tag>
            <n-tag v-if="!r.dims.length" size="small" type="success" :bordered="false" round>✓ 全部划掉</n-tag>
          </div>
          <div class="right muted">
            <span v-if="r.due" class="duetxt">今天到期</span>
            <span v-else>{{ r.due_at }} 再见</span>
            <span>第 {{ r.stage + 1 }} 轮</span>
          </div>
        </div>
      </div>

      <template v-if="rows.length" #footer>
        <n-button type="primary" size="large" @click="goStudy">
          去学习（{{ dueRows.length }} 题到期，错题优先已默认开启）
        </n-button>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NCard, NEmpty, NRadioButton, NRadioGroup, NTag } from "naive-ui";
import { useLearningStore } from "../stores/learning";
import { loadBanks, EMPTY_BANKS, type BankMeta } from "../core/banks";
import { DIM_LABEL } from "../core/quiz";
import type { WordBanks, BankKey, PlanWord } from "../core/plan";

const learning = useLearningStore();
const router = useRouter();
const banks = ref<WordBanks>(EMPTY_BANKS);
const bankMeta = ref<Record<string, BankMeta>>({});
void loadBanks().then((r) => {
  banks.value = r.banks;
  bankMeta.value = r.bankMeta;
});

const filter = ref<"due" | "all">("due");

const wordIndex = computed(() => {
  const m = new Map<string, { w: PlanWord; bank: string }>();
  for (const k of Object.keys(banks.value) as BankKey[]) {
    for (const w of banks.value[k] ?? []) {
      m.set(w.id, { w, bank: bankMeta.value[k]?.short || k });
    }
  }
  return m;
});

interface Row {
  id: string;
  en: string;
  cn: string;
  bank: string;
  dims: string[];
  stage: number;
  due_at: string;
  due: boolean;
}

const rows = computed<Row[]>(() =>
  learning.data.mistakes.map((m) => {
    const hit = wordIndex.value.get(m.word_id);
    const today = new Date().toISOString().slice(0, 10);
    return {
      id: m.word_id,
      en: hit?.w.en ?? m.word_id,
      cn: hit?.w.cn ?? "",
      bank: hit?.bank ?? "—",
      dims: m.dims,
      stage: m.stage,
      due_at: m.due_at,
      due: Boolean(m.due_at && m.due_at <= today && m.dims.length > 0),
    };
  }),
);
const dueRows = computed(() => rows.value.filter((r) => r.due));
const shown = computed(() => (filter.value === "due" ? dueRows.value : rows.value));
const graduated = computed(() => rows.value.filter((r) => !r.dims.length).length);

function goStudy(): void {
  void router.push("/english/words/study");
}
</script>

<style scoped>
.page { width: 100%; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.stat { display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: var(--c-surface, #fff); border: 1px solid var(--c-line, #e5efe9); border-radius: 16px; box-shadow: var(--shadow-sm); }
.stat .ico { width: 42px; height: 42px; border-radius: 12px; background: var(--c-primary-soft, #e7f6ec); display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.stat.warn .ico { background: #fef3c7; }
.stat .v { font-size: 22px; font-weight: 800; }
.stat .l { font-size: 12px; color: var(--c-text-2, #6b7f74); }
.rows { display: flex; flex-direction: column; }
.row { display: flex; align-items: center; gap: 12px; padding: 11px 4px; border-bottom: 1px solid var(--c-line, #e5efe9); flex-wrap: wrap; }
.row:last-child { border-bottom: 0; }
.row.due { background: rgba(217, 119, 6, 0.04); }
.left { display: flex; align-items: center; gap: 8px; min-width: 260px; }
.w { font-weight: 800; font-size: 15px; }
.banktag { background: var(--c-primary-soft, #e7f6ec); color: var(--c-primary-strong, #15803d); }
.dims { display: flex; gap: 6px; flex-wrap: wrap; flex: 1; }
.right { display: flex; gap: 14px; margin-left: auto; }
.duetxt { color: var(--amber, #d97706); font-weight: 700; }
.muted { color: var(--c-text-2, #6b7f74); font-size: 13px; }
</style>
