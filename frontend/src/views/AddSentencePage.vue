<template>
  <div class="page">
    <n-card title="添加精读句子" size="small" class="mb">
      <template #header-extra><span class="muted">加入对应 Part 后，进入该 Part 的精读与测验</span></template>

      <n-form label-placement="left" label-width="120">
        <n-form-item label="教材">
          <n-select v-model:value="book" :options="bookOptions" style="max-width: 280px" />
        </n-form-item>
        <n-form-item label="Test / Part">
          <div class="row2">
            <n-select v-model:value="testNo" :options="testOptions" />
            <n-select v-model:value="part" :options="partOptions" />
          </div>
        </n-form-item>
        <n-form-item label="英文句子">
          <n-input v-model:value="en" type="textarea" :rows="2" placeholder="The race now starts at 4 pm." />
        </n-form-item>
        <n-form-item label="中文翻译">
          <n-input v-model:value="cn" placeholder="比赛现在改到下午 4 点开始。" />
        </n-form-item>
        <n-form-item label="关键短语（选填）">
          <n-input v-model:value="key" placeholder="须是英文句子中的原文片段，填了可出「选词填空」题" />
        </n-form-item>
        <n-form-item v-if="warn" label=" ">
          <n-alert type="warning" size="small" :bordered="false" style="width: 100%">{{ warn }}</n-alert>
        </n-form-item>
        <n-form-item label="讲解笔记（选填）">
          <n-input v-model:value="note" type="textarea" :rows="2" />
        </n-form-item>
      </n-form>
      <n-button type="primary" size="large" :disabled="!canAdd" @click="add">添加句子</n-button>
    </n-card>

    <n-card v-if="mySentences.length" :title="`已添加 ${mySentences.length} 句`" size="small">
      <div v-for="s in mySentences" :key="s.sid" class="sent">
        <p class="sent-en">{{ s.en }}</p>
        <p class="sent-meta">{{ bookName(s.book) }} Test {{ s.test_no }} · Part {{ s.part }}</p>
        <n-popconfirm @positive-click="remove(s.sid)">
          <template #trigger><n-button size="tiny" quaternary type="error">删除</n-button></template>
          确定删除这句？
        </n-popconfirm>
      </div>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  NAlert, NButton, NCard, NForm, NFormItem, NInput, NPopconfirm, NSelect,
} from "naive-ui";
import { useLearningStore } from "../stores/learning";
import { useAuthStore } from "../stores/auth";
import { customSid, loadReading, type ReadingData } from "../core/reading";
import type { CustomSentenceItem } from "../core/merge";

const learning = useLearningStore();
const auth = useAuthStore();
const data = ref<ReadingData | null>(null);
const book = ref("t2");
const testNo = ref(1);
const part = ref(1);
const en = ref("");
const cn = ref("");
const key = ref("");
const note = ref("");

onMounted(async () => {
  data.value = await loadReading(auth.exam);
  const first = data.value.tests[0];
  if (first) {
    book.value = first.book || "t2";
    testNo.value = first.no;
    part.value = first.parts[0]?.part ?? 1;
  }
});

const books = computed(() => data.value?.books ?? []);
const bookOptions = computed(() => books.value.map((b) => ({ label: b.name, value: b.id })));
const testsOfBook = computed(() =>
  (data.value?.tests ?? []).filter((t) => (t.book || "t2") === book.value),
);
const testOptions = computed(() => testsOfBook.value.map((t) => ({ label: t.title, value: t.no })));
const partsOfTest = computed(() => testsOfBook.value.find((t) => t.no === testNo.value)?.parts ?? []);
const partOptions = computed(() => partsOfTest.value.map((p) => ({ label: `Part ${p.part} · ${p.kind}`, value: p.part })));

function bookName(id: string): string {
  return data.value?.books.find((b) => b.id === id)?.name ?? id;
}

const trimmedEn = computed(() => en.value.trim());
const warn = computed(() => {
  if (!trimmedEn.value) return "";
  if (!key.value.trim()) return "";
  return key.value && !trimmedEn.value.includes(key.value.trim())
    ? "关键短语不在句子中，保存后不会出选词填空题"
    : "";
});
const canAdd = computed(() => trimmedEn.value.length > 0 && partsOfTest.value.length > 0);

const mySentences = computed(() => learning.data.custom_sentences);

function add(): void {
  if (!canAdd.value) return;
  const item: CustomSentenceItem = {
    sid: customSid(book.value, testNo.value, part.value, trimmedEn.value),
    book: book.value,
    test_no: testNo.value,
    part: part.value,
    en: trimmedEn.value,
    cn: cn.value.trim(),
    key: key.value.trim(),
    note: note.value.trim(),
  };
  learning.addCustomSentence(item);
  en.value = "";
  cn.value = "";
  key.value = "";
  note.value = "";
}

function remove(sid: string): void {
  learning.removeCustomSentence(sid);
}
</script>

<style scoped>
.page { width: 100%; }
.mb { margin-bottom: 16px; }
.muted { color: var(--c-text-2, #6b7f74); font-size: 13px; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; width: 100%; }
.row2 > * { min-width: 0; }
.sent { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid var(--c-line, #e5efe9); }
.sent:last-child { border-bottom: 0; }
.sent-en { flex: 1; margin: 0; font-size: 14px; }
.sent-meta { margin: 0; color: var(--c-text-2, #6b7f74); font-size: 13px; white-space: nowrap; }
@media (max-width: 767px) {
  :deep(.n-form-item) { display: block; }
  :deep(.n-form-item-label) { width: auto !important; padding-bottom: 4px; }
  :deep(.n-form-item-blank) { min-width: 0; }
  .row2 { grid-template-columns: 1fr; }
  .sent { flex-wrap: wrap; }
}
</style>
