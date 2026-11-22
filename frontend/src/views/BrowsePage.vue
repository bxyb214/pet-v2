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

    <!-- 其他单词（手动上传） -->
    <template v-if="current === 'custom'">
      <n-card title="添加单词" size="small" class="mb">
        <template #header-extra><span class="muted">AI 自动配例句、词性、释义，可修改后保存</span></template>
        <div class="addrow">
          <n-input v-model:value="word" placeholder="输入单词，如 shadow" size="large" @keyup.enter="enrich" />
          <n-button type="primary" size="large" :loading="busy" :disabled="!word.trim()" @click="enrich">
            {{ busy ? "生成中…" : "AI 补全" }}
          </n-button>
        </div>
        <n-alert v-if="err" type="error" size="small" class="mt">{{ err }}</n-alert>

        <template v-if="filled">
          <n-form label-placement="left" label-width="88" class="mt">
            <n-form-item label="单词"><n-input v-model:value="filled.word" /></n-form-item>
            <n-form-item label="词性"><n-input v-model:value="filled.pos" placeholder="n. / v. / adj." /></n-form-item>
            <n-form-item label="释义"><n-input v-model:value="filled.definition" /></n-form-item>
            <n-form-item label="英文例句"><n-input v-model:value="filled.example_en" /></n-form-item>
            <n-form-item label="中文翻译"><n-input v-model:value="filled.example_cn" /></n-form-item>
          </n-form>
          <n-button type="primary" @click="save">保存到我的生词本</n-button>
        </template>
      </n-card>

      <n-card :title="`我的生词（${myWords.length}）`" size="small">
        <n-empty v-if="!myWords.length" description="还没有手动添加的单词" />
        <div v-else class="wordrows">
          <div v-for="w in myWords" :key="w.id" class="wordrow">
            <span class="w">{{ w.word }} <n-tag size="small" :bordered="false">{{ w.pos || "—" }}</n-tag></span>
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
        <n-input v-model:value="keyword" placeholder="搜索单词或释义…" size="medium" clearable style="max-width: 280px">
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
            <p class="word">{{ filtered[idx].en }}</p>
            <p class="phon">{{ filtered[idx].phonetic || " " }}</p>
            <div class="fc-act">
              <n-button size="small" secondary @click.stop="say(String(filtered[idx].en))">
                <template #icon><n-icon :component="VolumeHighOutline" /></template>
                听发音
              </n-button>
            </div>
            <p class="sub">点击卡片看释义</p>
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
  NAlert, NButton, NCard, NDataTable, NEmpty, NForm, NFormItem, NIcon, NInput,
  NPopconfirm, NProgress, NRadioButton, NRadioGroup, NTag, type DataTableColumns,
} from "naive-ui";
import {
  VolumeHighOutline, SearchOutline, LibraryOutline, CheckmarkCircleOutline,
  AlertCircleOutline, CreateOutline, PlayOutline,
} from "@vicons/ionicons5";
import { api } from "../core/api";
import { splitExample, say } from "../core/say";
import { availableBankKeys, loadBanks, type BankMeta, type ExamMeta } from "../core/banks";
import { useAuthStore } from "../stores/auth";
import type { WordBanks, BankKey, PlanWord } from "../core/plan";
import type { CustomWordItem } from "../core/merge";
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

// 生词本（其他单词）
const word = ref("");
const filled = ref<Omit<CustomWordItem, "id"> | null>(null);
const myWords = ref<CustomWordItem[]>([]);
const busy = ref(false);
const err = ref("");
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

// 掌握度查询
const masteryMap = computed(() => {
  const m = new Map<string, number>();
  for (const it of learning.data.mastery) m.set(it.word_id, it.mastered_dims.length);
  return m;
});
const mistakeMap = computed(() => {
  const m = new Map<string, string[]>();
  for (const it of learning.data.mistakes) m.set(it.word_id, it.dims);
  return m;
});
function statusOf(id: string): { label: string; type: "success" | "warning" | "default" } {
  const mastered = masteryMap.value.get(id) ?? 0;
  if (mastered >= 3) return { label: "✓ 已掌握", type: "success" };
  if ((mistakeMap.value.get(id) ?? []).length) return { label: "复习中", type: "warning" };
  if (mastered > 0) return { label: "学习中", type: "warning" };
  return { label: "未学", type: "default" };
}
function pctOf(id: string): number {
  return Math.round(((masteryMap.value.get(id) ?? 0) / 3) * 100);
}
function exOf(w: PlanWord): { en: string; cn: string } {
  return splitExample(String(w.example ?? ""), String(w.example_cn ?? ""));
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
  const total = CATS.value.filter((c) => c.key !== "custom").reduce((s, c) => s + (banks.value[c.key as BankKey]?.length ?? 0), 0);
  const masteredAll = [...masteryMap.value.values()].filter((n) => n >= 3).length;
  const due = learning.dueMistakes.length;
  const custom = myWords.value.length;
  return [
    { icon: LibraryOutline, tone: "green", label: "教材词库总数", value: total },
    { icon: CheckmarkCircleOutline, tone: "green", label: "已掌握", value: masteredAll },
    { icon: AlertCircleOutline, tone: "amber", label: "错题到期", value: due },
    { icon: CreateOutline, tone: "green", label: "我的生词", value: custom },
  ];
});

// n-data-table 列定义
const columns = computed<DataTableColumns<PlanWord>>(() => [
  {
    title: "单词",
    key: "en",
    width: 280,
    render: (w) =>
      h("div", { class: "wc" }, [
        h("div", { class: "wc-1" }, [
          h("b", { class: "w-en" }, w.en),
          w.pos ? h(NTag, { size: "tiny", bordered: false, style: "margin-left:6px" }, { default: () => w.pos }) : null,
          h(
            NButton,
            {
              size: "small", quaternary: true, circle: true, title: "朗读单词",
              style: "color:#16a34a;margin-left:2px",
              onClick: (e: MouseEvent) => { e.stopPropagation(); say(String(w.en)); },
            },
            { icon: () => h(NIcon, { size: 17 }, { default: () => h(VolumeHighOutline) }) },
          ),
        ]),
        w.phonetic ? h("div", { class: "wc-phon" }, String(w.phonetic)) : null,
      ]),
  },
  {
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
async function enrich(): Promise<void> {
  err.value = "";
  busy.value = true;
  try {
    filled.value = await api<Omit<CustomWordItem, "id">>("/words/custom/enrich", {
      method: "POST",
      body: JSON.stringify({ word: word.value.trim() }),
    });
  } catch (e) {
    err.value = e instanceof Error ? e.message : "生成失败，可手动填写后保存";
    filled.value = { word: word.value.trim(), pos: "", definition: "", example_en: "", example_cn: "" };
  } finally {
    busy.value = false;
  }
}
async function save(): Promise<void> {
  if (!filled.value) return;
  err.value = "";
  try {
    await api("/words/custom", { method: "POST", body: JSON.stringify(filled.value) });
    word.value = "";
    filled.value = null;
    myWords.value = await api<CustomWordItem[]>("/words/custom");
  } catch (e) {
    err.value = e instanceof Error ? e.message : "保存失败";
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
.stat { display: flex; align-items: center; gap: 12px; padding: 14px 16px; background: var(--c-surface, #fff); border: 1px solid var(--c-line, #e5efe9); border-radius: 16px; box-shadow: var(--shadow-sm); }
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
.cat.active { background: var(--c-primary, #16a34a); border-color: var(--c-primary, #16a34a); color: #fff; }
.cat .cnt { font-size: 12px; opacity: 0.8; margin-left: 4px; }

.toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.spacer { flex: 1; }
.mt { margin-top: 14px; }
.mb { margin-bottom: 14px; }
.addrow { display: flex; gap: 10px; }
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
:deep(.pct) { display: flex; align-items: center; gap: 6px; }
:deep(.pct .n-progress) { flex: 1; }
:deep(.pct-t) { font-size: 12px; color: var(--c-text-2, #6b7f74); font-variant-numeric: tabular-nums; width: 30px; text-align: right; }
.fc-act { margin-top: 12px; display: flex; justify-content: center; }
.ex-cn { color: var(--c-text-2, #6b7f74); font-size: 13px; }
</style>
