<template>
  <div class="page">
    <n-card size="small" class="card">
      <div class="sect-head">
        <h2>我在备考</h2>
        <span class="sect-hint">选择后只显示这一级别的词库和教材，随时可换，记录不丢</span>
      </div>

      <div class="exams">
        <button
          v-for="e in exams"
          :key="e.id"
          type="button"
          class="exam"
          :class="{ on: e.id === current, soon: e.soon }"
          :disabled="e.soon || busy"
          :aria-pressed="e.id === current"
          @click="choose(e)"
        >
          <span class="top">
            <span class="tag">{{ e.name }}</span>
            <span v-if="e.soon" class="badge">敬请期待</span>
            <span v-else-if="e.id === current" class="badge cur">
              <svg viewBox="0 0 24 24" width="11" height="11" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round">
                <path d="M5 12.5l4.5 4.5L19 6.5" />
              </svg>
              当前
            </span>
          </span>
          <span class="desc">{{ e.desc || "" }}</span>
        </button>
      </div>

      <p v-if="current === 'ket'" class="note">
        KET 目前只有词库（核心词表 / 生难词 / 动词短语 / 易混词 / 同义替换），阅读、听力、口语还是 PET 的内容。
      </p>
    </n-card>

    <n-card size="small" class="card">
      <div class="sect-head">
        <h2>账号</h2>
        <span class="sect-hint">需要改密码请找老师</span>
      </div>
      <dl class="rows">
        <div class="row"><dt>用户名</dt><dd>{{ auth.username }}</dd></div>
        <div class="row"><dt>昵称</dt><dd>{{ auth.displayName || auth.username }}</dd></div>
        <div class="row"><dt>可用板块</dt><dd class="perms">{{ permText }}</dd></div>
      </dl>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { NCard, useMessage } from "naive-ui";
import { loadBanks, DEFAULT_EXAMS, type ExamMeta } from "../core/banks";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();
const message = useMessage();
const exams = ref<ExamMeta[]>(DEFAULT_EXAMS);
const current = ref(auth.exam);
const busy = ref(false);

const permText = computed(() => {
  const parts = ["词汇", "阅读", "听力"];
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

.card { margin-bottom: 16px; }

.sect-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.sect-head h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  color: var(--c-text);
  letter-spacing: 0.02em;
}
.sect-hint { font-size: 12px; color: var(--c-text-3); }

/* ---------- 级别卡 ---------- */
.exams {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
  gap: 10px;
}
.exam {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 5px;
  align-items: flex-start;
  padding: 13px 14px 14px;
  border: 1.5px solid var(--c-line);
  border-radius: var(--r-btn);
  background: #fff;
  cursor: pointer;
  text-align: left;
  transition: border-color var(--dur-2) var(--ease-out),
    box-shadow var(--dur-2) var(--ease-out),
    transform var(--dur-2) var(--ease-out),
    background var(--dur-2) var(--ease-out);
}
.exam:hover:not(:disabled) {
  border-color: #a9dcc0;
  transform: translateY(-1px);
  box-shadow: var(--shadow-1);
}
.exam.on {
  border-color: var(--c-primary);
  background: linear-gradient(180deg, #f4fbf7 0%, #ffffff 70%);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.09), var(--shadow-1);
}
.exam.soon {
  border-style: dashed;
  border-color: var(--c-line-strong);
  background: #fcfdfc;
  cursor: not-allowed;
}
.exam:disabled:not(.soon) { opacity: 0.6; }

.top { display: flex; align-items: center; gap: 7px; width: 100%; }
.tag {
  font-size: 15.5px;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: var(--c-text);
}
.soon .tag { color: var(--c-text-3); }

.badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  margin-left: auto;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: var(--r-pill);
  background: #f2f5f3;
  color: var(--c-text-3);
  white-space: nowrap;
  line-height: 1.5;
}
.badge.cur { background: var(--c-primary-strong); color: #fff; }

.desc {
  width: 100%;
  font-size: 12px;
  line-height: 1.55;
  color: var(--c-text-2);
  overflow-wrap: anywhere;
}
.soon .desc { color: var(--c-text-3); }

.note {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: var(--r-sm);
  background: var(--c-accent-soft);
  border: 1px solid #f4dfc2;
  font-size: 12.5px;
  line-height: 1.7;
  color: #8a5a13;
}

/* ---------- 账号信息 ---------- */
.rows { margin: 0; display: grid; gap: 0; }
.row {
  display: flex;
  align-items: baseline;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px solid var(--c-line);
}
.row:last-child { border-bottom: none; padding-bottom: 2px; }
.row dt {
  flex: none;
  width: 76px;
  font-size: 12.5px;
  color: var(--c-text-3);
}
.row dd {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--c-text);
  min-width: 0;
  overflow-wrap: anywhere;
}
.perms { color: var(--c-primary-strong); }

@media (max-width: 520px) {
  .exams { grid-template-columns: 1fr 1fr; }
  .tag { font-size: 14.5px; }
}
</style>
