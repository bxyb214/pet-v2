<template>
  <div class="page">
    <!-- 统计卡 -->
    <div class="stats">
      <div class="card stat" v-for="s in statCards" :key="s.label">
        <div class="ico" :class="s.tone"><n-icon :component="s.icon" size="21" /></div>
        <div><div class="v">{{ s.value }}</div><div class="l">{{ s.label }}</div></div>
      </div>
    </div>

    <!-- 词库分类 -->
    <div class="cats">
      <button
        v-for="c in CATS"
        :key="c.key"
        class="cat"
        :class="{ active: current === c.key }"
        @click="pickCat(c.key)"
      >{{ c.label }}<span class="cnt">{{ countOf(c.key) }}</span></button>
    </div>

    <!-- 当前词库掌握度：已掌握 / 学习中 / 未学习 -->
    <div v-if="!isCustom && bankStats.total" class="mastery">
      <div class="mhead">
        <span class="mtitle">本词库掌握度</span>
        <span class="msub">{{ bankStats.total }} 词</span>
      </div>
      <div
        class="mbar"
        role="img"
        :aria-label="`已掌握 ${bankStats.masteredPct}%，学习中 ${bankStats.learningPct}%，未学习 ${bankStats.unlearnedPct}%`"
      >
        <i class="m-mastered" :style="{ width: bankStats.masteredPct + '%' }"></i>
        <i class="m-learning" :style="{ width: bankStats.learningPct + '%' }"></i>
        <i class="m-unlearned" :style="{ width: bankStats.unlearnedPct + '%' }"></i>
      </div>
      <div class="mlegend">
        <span><i class="dot mastered"></i>已掌握 <b>{{ bankStats.masteredPct }}%</b><em>{{ bankStats.mastered }}</em></span>
        <span><i class="dot learning"></i>学习中 <b>{{ bankStats.learningPct }}%</b><em>{{ bankStats.learning }}</em></span>
        <span><i class="dot unlearned"></i>未学习 <b>{{ bankStats.unlearnedPct }}%</b><em>{{ bankStats.unlearned }}</em></span>
      </div>
    </div>

    <!-- 我的生词（Excel 批量导入） -->
    <template v-if="current === 'custom'">
      <n-card title="批量导入生词" size="small" class="mb">
        <template #header-extra><span class="muted">线下整理好 Excel 后上传，自动配到对应词库</span></template>
        <div class="improw">
          <n-button size="large" secondary @click="downloadTemplate">
            <template #icon><n-icon :component="DownloadOutline" /></template>
            下载 Excel 模板
          </n-button>
          <input ref="fileInput" type="file" accept=".xlsx" hidden @change="onImportFile" />
          <n-button type="primary" size="large" :loading="importBusy" :disabled="importBusy" @click="pickFile">
            {{ importBusy ? "导入中…" : "上传 Excel" }}
          </n-button>
          <n-radio-group v-model:value="importExam" size="large">
            <n-radio-button value="pet">PET</n-radio-button>
            <n-radio-button value="ket">KET</n-radio-button>
            <n-radio-button value="fce">FCE</n-radio-button>
          </n-radio-group>
        </div>
        <p class="muted mt">
          模板列：单词 / 词库 / 词性 / 释义 / 英文例句 / 中文翻译。词库填：必默 · 高频 · 固搭 · 同义（KET 为核心词 / 生难词 / 短语 / 易混词 / 同义）；已存在的词自动跳过。
        </p>
        <n-alert v-if="importResult" type="success" size="small" class="mt" closable @close="importResult = null">
          成功导入 {{ importResult.added }} 个词{{ importResult.skipped.length ? `；跳过 ${importResult.skipped.length} 行` : "" }}
          <ul v-if="importResult.skipped.length" class="imp-skips">
            <li v-for="s in importResult.skipped" :key="s">{{ s }}</li>
          </ul>
        </n-alert>
        <n-alert v-if="importErr" type="error" size="small" class="mt" closable @close="importErr = ''">{{ importErr }}</n-alert>
      </n-card>

      <n-card :title="`我的生词（${myWords.length}）`" size="small">
        <n-empty v-if="!myWords.length" description="还没有生词，先上传一份 Excel 试试" />
        <div v-else class="wordrows">
          <div v-for="w in myWords" :key="w.id" class="wordrow">
            <span class="w">
              {{ w.word }}
              <n-tag v-if="w.bank" size="small" :bordered="false">{{ bankLabelOf(w.bank) }}</n-tag>
              <n-tag size="small" :bordered="false">{{ w.pos || "—" }}</n-tag>
            </span>
            <span class="d muted">{{ w.definition }}</span>
            <n-popconfirm @positive-click="remove(w.id)">
              <template #trigger><n-button size="tiny" quaternary type="error">删除</n-button></template>
              确定删除「{{ w.word }}」？
            </n-popconfirm>
          </div>
        </div>
      </n-card>
    </template>

    <!-- 教材词库 -->
    <template v-else>
      <div class="toolbar">
        <n-input v-model:value="keyword" :placeholder="isSynBank ? '搜索短语或释义…' : '搜索单词或释义…'" size="medium" clearable style="max-width: 280px">
          <template #prefix><n-icon :component="SearchOutline" /></template>
        </n-input>
        <div class="spacer"></div>
        <n-button v-if="!isCustom" type="primary" size="medium" @click="studyCurrent">
          <template #icon><n-icon :component="PlayOutline" /></template>
          学习本词库
        </n-button>
        <n-radio-group v-model:value="view" size="small">
          <n-radio-button value="list">列表</n-radio-button>
          <n-radio-button value="card">卡片</n-radio-button>
        </n-radio-group>
      </div>

      <!-- 列表视图 -->
      <n-data-table
        v-if="view === 'list'"
        :columns="columns"
        :data="filtered"
        :bordered="false"
        size="large"
        :scroll-x="860"
        :pagination="{ pageSize: 12 }"
      />

      <!-- 卡片视图（闪卡） -->
      <template v-else>
        <n-empty v-if="!filtered.length" description="没有匹配的单词" />
        <div v-else class="flashcard card" @click="flipped = !flipped">
          <template v-if="!flipped">
            <p class="word">{{ frontOf(filtered[idx]) }}</p>
            <p class="phon">{{ filtered[idx].phonetic || " " }}</p>
            <div class="fc-act">
              <n-button size="small" secondary @click.stop="sayEn(filtered[idx])">
                <template #icon><n-icon :component="VolumeHighOutline" /></template>
                听发音
              </n-button>
            </div>
            <p class="sub">点击卡片看{{ isSynBank ? "同义说法" : "释义" }}</p>
          </template>
          <template v-else>
            <template v-if="isSynBank">
              <p class="word cn">{{ altEnOf(filtered[idx]) }}</p>
              <p class="ex-cn">{{ altCnOf(filtered[idx]) || "（暂无同义说法）" }}</p>
              <div class="fc-act">
                <n-button size="small" secondary @click.stop="sayAlt(filtered[idx])">
                  <template #icon><n-icon :component="VolumeHighOutline" /></template>
                  听同义说法
                </n-button>
              </div>
            </template>
            <template v-else>
              <p class="word cn">{{ filtered[idx].cn }}</p>
              <template v-if="exOf(filtered[idx]).en">
                <p class="ex">{{ exOf(filtered[idx]).en }}</p>
                <p v-if="exOf(filtered[idx]).cn" class="ex-cn">{{ exOf(filtered[idx]).cn }}</p>
                <div class="fc-act">
                  <n-button size="small" tertiary @click.stop="say(exOf(filtered[idx]).en)">
                    <template #icon><n-icon :component="VolumeHighOutline" /></template>
                    听例句
                  </n-button>
                </div>
              </template>
            </template>
            <p class="sub">点击返回单词</p>
          </template>
        </div>
        <div class="nav">
          <n-button secondary :disabled="idx === 0" @click="prev">上一张</n-button>
          <span class="muted">{{ idx + 1 }} / {{ filtered.length }}</span>
          <n-button secondary :disabled="idx >= filtered.length - 1" @click="next">下一张</n-button>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, h, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  NAlert, NButton, NCard, NDataTable, NEmpty, NIcon, NInput,
  NPopconfirm, NProgress, NRadioButton, NRadioGroup, NTag, type DataTableColumns,
} from "naive-ui";
import {
  VolumeHighOutline, SearchOutline, LibraryOutline, CheckmarkCircleOutline,
  AlertCircleOutline, CreateOutline, PlayOutline, DownloadOutline,
} from "@vicons/ionicons5";
import { api, downloadFile } from "../core/api";
import { splitExample, say } from "../core/say";
import { availableBankKeys, loadBanks, type BankMeta, type ExamMeta } from "../core/banks";
import { useAuthStore } from "../stores/auth";
import type { WordBanks, BankKey, PlanWord } from "../core/plan";
import type { CustomWordItem } from "../core/merge";
import { bucketOf, masteryPct, masteryStats, requiredDimsForBank } from "../core/mastery";
import { enPart, isSynonymWord } from "../core/quiz";
import { useLearningStore } from "../stores/learning";

type CatKey = BankKey | "custom";

const learning = useLearningStore();
const auth = useAuthStore();
const router = useRouter();
const banks = ref<WordBanks>({});
const bankMeta = ref<Record<string, BankMeta>>({});
const exams = ref<ExamMeta[]>([]);

/** 词库分类：当前级别下的词库 + 我的生词（词库顺序来自 banks.json） */
const CATS = computed<Array<{ key: CatKey; label: string }>>(() => {
  const keys = availableBankKeys(banks.value, bankMeta.value, auth.exam);
  return [
    ...keys.map((k) => ({ key: k as CatKey, label: bankMeta.value[k]?.short || k })),
    { key: "custom" as CatKey, label: "我的生词" },
  ];
});

const current = ref<CatKey>("");
const isCustom = computed(() => current.value === "custom");
// 手机屏默认用卡片视图（表格在窄屏只能横向滑动，不适合孩子）
const view = ref<"list" | "card">(typeof window !== "undefined" && window.innerWidth < 768 ? "card" : "list");
const keyword = ref("");
const idx = ref(0);
const flipped = ref(false);

// 生词本（Excel 批量导入）
const myWords = ref<CustomWordItem[]>([]);
const importExam = ref<"pet" | "ket" | "fce">("pet");
const importBusy = ref(false);
const importErr = ref("");
const importResult = ref<{ added: number; skipped: string[]; skipped_more: number } | null>(null);
void loadBanks().then((r) => {
  banks.value = r.banks;
  bankMeta.value = r.bankMeta;
  exams.value = r.exams;
  const keys = availableBankKeys(r.banks, r.bankMeta, auth.exam);
  current.value = (keys[0] as CatKey) ?? "custom";
});
void api<CustomWordItem[]>("/words/custom").then((r) => (myWords.value = r)).catch(() => (myWords.value = []));

function pickCat(k: CatKey): void {
  current.value = k;
  idx.value = 0;
  flipped.value = false;
  keyword.value = "";
}
function countOf(k: CatKey): number {
  return k === "custom" ? myWords.value.length : (banks.value[k]?.length ?? 0);
}
/** 导入生词的词库短名（手动添加无 bank 字段） */
function bankLabelOf(bank: string): string {
  return bankMeta.value[bank]?.short || bank;
}

// 掌握度查询
const masteryDimsMap = computed(() => {
  const m = new Map<string, string[]>();
  for (const it of learning.data.mastery) m.set(it.word_id, it.mastered_dims);
  return m;
});
const mistakeMap = computed(() => {
  const m = new Map<string, string[]>();
  for (const it of learning.data.mistakes) m.set(it.word_id, it.dims);
  return m;
});
/** 当前词库的必考维度（KET 两型、PET 三型） */
const currentBankKey = computed<BankKey | "">(() =>
  current.value === "custom" ? "" : (current.value as BankKey),
);
const requiredDims = computed(() =>
  requiredDimsForBank(currentBankKey.value, bankMeta.value[currentBankKey.value]?.dims),
);
const bankStats = computed(() =>
  masteryStats(
    currentBankKey.value ? (banks.value[currentBankKey.value] ?? []) : [],
    learning.data.mastery,
    learning.data.mistakes,
    requiredDims.value,
  ),
);
/** 全部教材词库合计（顶部统计卡用） */
const allStats = computed(() => {
  let total = 0;
  let mastered = 0;
  let learningCount = 0;
  let unlearned = 0;
  for (const k of availableBankKeys(banks.value, bankMeta.value, auth.exam)) {
    const s = masteryStats(
      banks.value[k] ?? [],
      learning.data.mastery,
      learning.data.mistakes,
      requiredDimsForBank(k, bankMeta.value[k]?.dims),
    );
    total += s.total;
    mastered += s.mastered;
    learningCount += s.learning;
    unlearned += s.unlearned;
  }
  // 与 core/mastery 一致：百分比保留一位小数，避免 1/712 显示成 0%
  const pct = (n: number): number => (total ? Math.round((n / total) * 1000) / 10 : 0);
  const masteredPct = pct(mastered);
  const learningPct = Math.min(pct(learningCount), Math.round((100 - masteredPct) * 10) / 10);
  return {
    total, mastered, learning: learningCount, unlearned,
    masteredPct, learningPct, unlearnedPct: total ? Math.round((100 - masteredPct - learningPct) * 10) / 10 : 0,
  };
});
function statusOf(id: string): { label: string; type: "success" | "warning" | "default" } {
  const bucket = bucketOf(masteryDimsMap.value.get(id), mistakeMap.value.get(id), requiredDims.value);
  if (bucket === "mastered") return { label: "✓ 已掌握", type: "success" };
  if (bucket === "learning") {
    const owed = (mistakeMap.value.get(id) ?? []).length;
    return { label: owed ? "复习中" : "学习中", type: "warning" };
  }
  return { label: "未学", type: "default" };
}
function pctOf(id: string): number {
  return masteryPct(masteryDimsMap.value.get(id), requiredDims.value);
}
function exOf(w: PlanWord): { en: string; cn: string } {
  return splitExample(String(w.example ?? ""), String(w.example_cn ?? ""));
}

/* ---------- 同义替换库：展示「原短语 ↔ 同义短语」配对 ---------- */
/** 整库都是同义词（tongyi / ksyn）时启用同义展示 */
const isSynBank = computed(
  () => currentBankKey.value !== "" && (banks.value[currentBankKey.value] ?? []).length > 0
    && (banks.value[currentBankKey.value] ?? []).every(isSynonymWord),
);

/** 词条字段里的中英对照拆开：「make something to take home 制作可带回家的物品」→ 英文 + 中文 */
function altEnOf(w: PlanWord): string {
  return enPart(String(w.alt ?? ""));
}
function altCnOf(w: PlanWord): string {
  const direct = String(w.alt_cn ?? "").trim();
  if (direct) return direct;
  const s = String(w.alt ?? "").trim();
  const m = s.match(/[㐀-鿿][\s\S]*$/);
  return m ? m[0].trim() : "";
}
/** 正面短语：同义库显示英文部分（词条 en 本身是「英文 中文」混排） */
function frontOf(w: PlanWord): string {
  return isSynBank.value ? enPart(String(w.en ?? "")) : String(w.en ?? "");
}
/** 词条 en 里的中文部分（列表 / 卡片背面展示用） */
function cnOf(w: PlanWord): string {
  const s = String(w.cn ?? "").trim();
  if (s && /[㐀-鿿]/.test(s)) return s;
  const m = String(w.en ?? "").match(/[㐀-鿿][\s\S]*$/);
  return m ? m[0].trim() : s;
}
function sayEn(w: PlanWord): void {
  say(enPart(String(w.en ?? "")) || String(w.en ?? ""));
}
function sayAlt(w: PlanWord): void {
  say(altEnOf(w) || String(w.alt ?? ""));
}
/** 只保留一个「去学习」入口：带上当前词库，学习页自动选中 */
function studyCurrent(): void {
  const bank = current.value === "custom"
    ? (availableBankKeys(banks.value, bankMeta.value, auth.exam)[0] ?? "bimo")
    : current.value;
  void router.push({ path: "/english/words/study", query: { bank } });
}

const filtered = computed<PlanWord[]>(() => {
  const list = current.value === "custom" ? [] : (banks.value[current.value] ?? []);
  const kw = keyword.value.trim().toLowerCase();
  if (!kw) return list;
  return list.filter((w) => w.en.toLowerCase().includes(kw) || w.cn.toLowerCase().includes(kw));
});

watch([current, keyword], () => {
  idx.value = 0;
  flipped.value = false;
});

function prev(): void {
  if (idx.value > 0) idx.value--;
  flipped.value = false;
}
function next(): void {
  if (idx.value < filtered.value.length - 1) idx.value++;
  flipped.value = false;
}

// 统计卡
const statCards = computed(() => {
  const due = learning.dueMistakes.length;
  const custom = myWords.value.length;
  return [
    { icon: LibraryOutline, tone: "green", label: "教材词库总数", value: allStats.value.total },
    { icon: CheckmarkCircleOutline, tone: "green", label: `已掌握 ${allStats.value.masteredPct}%`, value: allStats.value.mastered },
    { icon: AlertCircleOutline, tone: "amber", label: "错题到期", value: due },
    { icon: CreateOutline, tone: "green", label: "我的生词", value: custom },
  ];
});

// n-data-table 列定义（同义库：第二列显示 ↔ 同义说法；普通库：释义 / 例句）
const columns = computed<DataTableColumns<PlanWord>>(() => [
  {
    title: isSynBank.value ? "短语" : "单词",
    key: "en",
    width: 280,
    render: (w) =>
      h("div", { class: "wc" }, [
        h("div", { class: "wc-1" }, [
          h("b", { class: "w-en" }, isSynBank.value ? enPart(String(w.en ?? "")) : w.en),
          w.pos && !isSynBank.value ? h(NTag, { size: "tiny", bordered: false, style: "margin-left:6px" }, { default: () => w.pos }) : null,
          h(
            NButton,
            {
              size: "small", quaternary: true, circle: true, title: "朗读",
              style: "color:#16a34a;margin-left:2px",
              onClick: (e: MouseEvent) => { e.stopPropagation(); isSynBank.value ? sayEn(w) : say(String(w.en)); },
            },
            { icon: () => h(NIcon, { size: 17 }, { default: () => h(VolumeHighOutline) }) },
          ),
        ]),
        isSynBank.value
          ? h("div", { class: "wc-phon" }, cnOf(w))
          : w.phonetic ? h("div", { class: "wc-phon" }, String(w.phonetic)) : null,
      ]),
  },
  isSynBank.value
    ? {
        title: "同义说法",
        key: "alt",
        render: (w) =>
          h("div", { class: "wc-ex" }, [
            h("div", { class: "ex-alt" }, [
              h("span", { class: "alt-arrow" }, "↔ "),
              h("span", { class: "ex-alt-en" }, altEnOf(w) || "—"),
            ]),
            altCnOf(w) ? h("div", { class: "ex-cn2" }, altCnOf(w)) : null,
          ]),
      }
    : {
        title: "释义 / 例句",
        key: "cn",
        render: (w) => {
          const ex = splitExample(String(w.example ?? ""), String(w.example_cn ?? ""));
          return h("div", { class: "wc-ex" }, [
            h("div", { class: "ex-cn" }, String(w.cn ?? "—")),
            ex.en ? h("div", { class: "ex-en" }, ex.en) : null,
            ex.cn ? h("div", { class: "ex-cn2" }, ex.cn) : null,
          ]);
        },
      },
  {
    title: "掌握度",
    key: "pct",
    width: 140,
    render: (w) => {
      const p = pctOf(w.id);
      return h("div", { class: "pct" }, [
        h(NProgress, { type: "line", percentage: p, height: 8, borderRadius: 4, showIndicator: false, color: "#16a34a", railColor: "#dce8e0" }),
        h("span", { class: "pct-t" }, `${p}%`),
      ]);
    },
  },
  {
    title: "状态",
    key: "st",
    width: 100,
    render: (w) => {
      const s = statusOf(w.id);
      return h(
        NTag,
        {
          size: "small", type: s.type, bordered: false, round: true,
          style: s.type === "default" ? "background:#eef3ef;color:#4d6b5c;font-weight:600" : "font-weight:600",
        },
        { default: () => s.label },
      );
    },
  },
]);

// 生词本操作
function downloadTemplate(): void {
  void downloadFile("/words/custom/import/template", "生词导入模板.xlsx");
}
/** 隐藏 file input 用 JS 触发：label 包 n-button 时点击不转发（button 是交互元素） */
const fileInput = ref<HTMLInputElement | null>(null);
function pickFile(): void {
  fileInput.value?.click();
}
async function onImportFile(ev: Event): Promise<void> {
  const input = ev.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = ""; // 允许重选同一个文件
  if (!file) return;
  importBusy.value = true;
  importErr.value = "";
  try {
    const form = new FormData();
    form.append("file", file);
    // multipart 上传：api() 是 JSON 通道，附件走 downloadFile 同级的裸 fetch 并带鉴权
    const token = localStorage.getItem("pet_access") ?? "";
    const res = await fetch(`/api/v1/words/custom/import?exam=${importExam.value}`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error(body?.detail ?? `导入失败 (${res.status})`);
    importResult.value = body;
    myWords.value = await api<CustomWordItem[]>("/words/custom");
  } catch (e) {
    importErr.value = e instanceof Error ? e.message : "导入失败";
  } finally {
    importBusy.value = false;
  }
}
async function remove(id: number): Promise<void> {
  await api(`/words/custom/${id}`, { method: "DELETE" });
  myWords.value = await api<CustomWordItem[]>("/words/custom");
}
</script>

<style scoped>
.page { width: 100%; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px; }
@media (max-width: 767px) {
  .stats { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
  .stat { padding: 12px; gap: 10px; }
  .stat .v { font-size: 20px; }
  .stat .l { font-size: 11.5px; }
}
.stat { display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: var(--c-surface, #fff); border: 1px solid var(--c-line, #e5efe9); border-radius: var(--r-card); box-shadow: var(--shadow-1); }
.stat .ico { width: 42px; height: 42px; border-radius: 12px; background: var(--c-primary-soft, #e7f6ec); color: var(--c-primary-strong, #15803d); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.stat .ico.amber { background: #fef3c7; color: #b45309; }
.stat .v { font-size: 22px; font-weight: 800; }
.stat .l { font-size: 13px; color: var(--c-text-2, #6b7f74); }

.cats { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
@media (max-width: 767px) {
  .cats { flex-wrap: nowrap; overflow-x: auto; padding-bottom: 4px; scrollbar-width: none; }
  .cats::-webkit-scrollbar { display: none; }
  .cat { white-space: nowrap; flex: none; }
  .toolbar { flex-wrap: wrap; }
}
.cat { border: 1.5px solid var(--c-line, #e5efe9); background: var(--c-surface, #fff); color: var(--c-text-2, #6b7f74); border-radius: 999px; padding: 9px 18px; font-size: 15px; font-weight: 600; cursor: pointer; transition: all 0.15s; }
.cat.active { background: var(--c-primary-strong, #15803d); border-color: var(--c-primary-strong, #15803d); color: #fff; }
.cat .cnt { font-size: 12px; opacity: 0.8; margin-left: 4px; }

/* 掌握度比例：已掌握 / 学习中 / 未学习 */
.mastery {
  background: var(--c-surface, #fff);
  border: 1px solid var(--c-line, #e5efe9);
  border-radius: var(--r-card, 16px);
  box-shadow: var(--shadow-1);
  padding: 14px 16px 12px;
  margin-bottom: 14px;
}
.mhead { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }
.mtitle { font-size: 13.5px; font-weight: 800; color: var(--c-text, #1f2d26); }
.msub { margin-left: auto; font-size: 12.5px; color: var(--c-text-2, #6b7f74); }
.mbar {
  display: flex; height: 10px; border-radius: 999px; overflow: hidden;
  background: #eef3ef;
}
.mbar i { display: block; height: 100%; transition: width var(--dur-2, 200ms) ease; }
.mbar .m-mastered { background: #16a34a; }
.mbar .m-learning { background: #e5a13c; }
.mbar .m-unlearned { background: #dce8e0; }
.mlegend { display: flex; gap: 18px; flex-wrap: wrap; margin-top: 9px; font-size: 12.5px; color: var(--c-text-2, #6b7f74); }
.mlegend span { display: inline-flex; align-items: center; gap: 5px; }
.mlegend b { color: var(--c-text, #1f2d26); font-weight: 800; }
.mlegend em { font-style: normal; color: var(--c-text-3, #8aa094); font-variant-numeric: tabular-nums; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.mastered { background: #16a34a; }
.dot.learning { background: #e5a13c; }
.dot.unlearned { background: #dce8e0; }

.toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.spacer { flex: 1; }
.mt { margin-top: 14px; }
.mb { margin-bottom: 14px; }
.improw { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.imp-skips { max-height: 160px; overflow: auto; margin: 8px 0 0; padding-left: 18px; font-size: 12px; color: var(--c-text-2, #6b7f74); }
.muted { color: var(--c-text-2, #6b7f74); font-size: 13px; }
.wordrows { display: flex; flex-direction: column; }
.wordrow { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--c-line, #e5efe9); }
.wordrow:last-child { border-bottom: 0; }
.wordrow .w { min-width: 180px; font-weight: 600; }
.wordrow .d { flex: 1; }

.flashcard { background: var(--c-surface, #fff); border-radius: 16px; box-shadow: var(--shadow-sm); border: 1px solid var(--c-line, #e5efe9); padding: 48px 24px; text-align: center; min-height: 200px; cursor: pointer; margin-bottom: 12px; }
.word { font-size: 34px; font-weight: 800; margin: 0; }
.word.cn { font-size: 28px; }
.phon { color: var(--c-text-2, #6b7f74); margin: 6px 0 0; }
.sub { color: var(--c-text-2, #6b7f74); font-size: 13px; margin: 10px 0 0; }
.ex { font-size: 15px; color: var(--c-text, #1f2d26); }
.nav { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
:deep(.w-en) { font-weight: 800; font-size: 15px; }
/* 词条单元格：单词 + 音标两行，右侧释义 + 例句 */
:deep(.wc) { display: flex; flex-direction: column; gap: 2px; padding: 2px 0; }
:deep(.wc-1) { display: flex; align-items: center; gap: 4px; }
:deep(.wc-phon) { color: var(--c-text-2, #6b7f74); font-size: 12.5px; }
:deep(.wc-ex) { display: flex; flex-direction: column; gap: 1px; padding: 2px 0; }
:deep(.ex-cn) { font-weight: 600; font-size: 14.5px; color: var(--c-text, #1f2d26); }
:deep(.ex-en) { font-size: 13px; color: var(--c-text-2, #6b7f74); line-height: 1.45; }
:deep(.ex-cn2) { font-size: 12px; color: #8aa094; line-height: 1.4; }
/* 同义说法列 */
:deep(.ex-alt) { display: flex; align-items: baseline; }
:deep(.alt-arrow) { color: #8aa094; font-weight: 700; margin-right: 6px; }
:deep(.ex-alt-en) { font-weight: 600; font-size: 14.5px; color: var(--c-primary-strong, #15803d); line-height: 1.5; }
:deep(.pct) { display: flex; align-items: center; gap: 6px; }
:deep(.pct .n-progress) { flex: 1; }
:deep(.pct-t) { font-size: 12px; color: var(--c-text-2, #6b7f74); font-variant-numeric: tabular-nums; width: 40px; text-align: right; }
.fc-act { margin-top: 12px; display: flex; justify-content: center; }
.ex-cn { color: var(--c-text-2, #6b7f74); font-size: 13px; }
</style>
