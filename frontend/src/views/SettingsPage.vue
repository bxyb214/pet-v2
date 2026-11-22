<template>
  <div class="page">
    <n-card size="small">
      <template #header>学习设置</template>

      <section class="block">
        <h2>我在备考</h2>
        <p class="hint">选择后，单词、词汇计划等只显示这个级别的词库；随时可以切换，学习记录不会丢。</p>

        <div class="exams">
          <button
            v-for="e in exams"
            :key="e.id"
            class="exam"
            :class="{ on: e.id === current, soon: e.soon }"
            :disabled="e.soon"
            @click="choose(e)"
          >
            <span class="tag">{{ e.name }}</span>
            <span class="desc">{{ e.desc || "" }}</span>
            <span v-if="e.soon" class="soon-tag">敬请期待</span>
            <span v-else-if="e.id === current" class="cur">当前</span>
          </button>
        </div>

        <p v-if="current === 'ket'" class="note">
          KET 目前只有词库（核心词表 / 生难词 / 动词短语 / 易混词 / 同义替换），阅读、听力、口语还是 PET 的内容。
        </p>
      </section>

      <section class="block">
        <h2>账号</h2>
        <n-descriptions :column="1" label-placement="left" size="small" bordered>
          <n-descriptions-item label="用户名">{{ auth.username }}</n-descriptions-item>
          <n-descriptions-item label="昵称">{{ auth.displayName || auth.username }}</n-descriptions-item>
          <n-descriptions-item label="权限">{{ permText }}</n-descriptions-item>
        </n-descriptions>
      </section>

      <template #footer>
        <span class="hint">{{ status }}</span>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import {
  NCard, NDescriptions, NDescriptionsItem, useMessage,
} from "naive-ui";
import { loadBanks, DEFAULT_EXAMS, type ExamMeta } from "../core/banks";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const message = useMessage();
const exams = ref<ExamMeta[]>(DEFAULT_EXAMS);
const current = ref(auth.exam);
const status = ref("");
const busy = ref(false);

const permText = computed(() => {
  const parts = ["词汇 / 阅读 / 听力"];
  if (auth.perms.includes("speak")) parts.push("口语");
  return parts.join(" · ");
});

onMounted(async () => {
  const loaded = await loadBanks();
  if (loaded.exams.length) exams.value = loaded.exams;
  current.value = auth.exam;
});

async function choose(e: ExamMeta): Promise<void> {
  if (e.soon || busy.value || e.id === current.value) return;
  busy.value = true;
  try {
    await auth.setExam(e.id);
    current.value = e.id;
    status.value = `已切换到 ${e.name}`;
    message.success(`已切换到 ${e.name}`);
  } catch (err) {
    message.error("切换失败：" + (err as Error).message);
  } finally {
    busy.value = false;
  }
}
</script>

<style scoped>
.page { width: 100%; }
.block { margin-bottom: 22px; }
.block:last-of-type { margin-bottom: 6px; }
h2 { font-size: 15px; font-weight: 700; color: var(--c-text, #1f2d26); margin: 0 0 6px; }
.hint { font-size: 12.5px; color: var(--c-text-2, #6b7f74); margin: 0 0 12px; line-height: 1.7; }
.exams { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
.exam {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
  padding: 14px 16px;
  border: 2px solid #e3ece6;
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.exam:hover:not(:disabled) { border-color: #9ed9b4; transform: translateY(-1px); }
.exam.on { border-color: #16a34a; box-shadow: 0 4px 14px rgba(22, 163, 74, 0.12); }
.exam.soon { opacity: 0.55; cursor: not-allowed; }
.tag { font-size: 16px; font-weight: 800; color: var(--c-text, #1f2d26); }
.desc { font-size: 12px; color: var(--c-text-2, #6b7f74); }
.cur, .soon-tag {
  position: absolute; top: 10px; right: 10px;
  font-size: 11px; padding: 1px 8px; border-radius: 999px;
}
.cur { background: #e7f6ec; color: #16a34a; font-weight: 700; }
.soon-tag { background: #f1f3f2; color: #8a9a90; }
.note {
  margin: 12px 0 0; padding: 10px 12px; border-radius: 10px;
  background: #f4faf6; border: 1px solid #d9eee1;
  font-size: 12.5px; color: #3d6350; line-height: 1.7;
}
</style>
