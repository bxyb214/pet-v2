<template>
  <main class="page">
    <button class="ghost back" @click="back">← 返回口语</button>
    <h1>造句练习</h1>
    <p class="sub">挑一个 PET 常用句型，用你自己的话造一句。AI 会告诉你怎么说得更好。</p>

    <div v-if="loading" class="card empty">加载中…</div>
    <template v-else>
      <div class="groups">
        <button
          v-for="g in groups"
          :key="g.id"
          class="gbtn"
          :class="{ on: g.id === group?.id }"
          @click="pick(g.id)"
        >
          {{ g.name }}
        </button>
      </div>

      <div v-if="group" class="card panel">
        <div class="gname">{{ group.name }} <span class="gcn">{{ group.cn }}</span></div>

        <div class="sents">
          <button
            v-for="(s, i) in group.items"
            :key="s.id"
            class="sent"
            :class="{ on: i === si }"
            @click="pickSentence(i)"
          >
            <span class="en">{{ s.en }}</span>
            <span class="cn">{{ s.cn }}</span>
          </button>
        </div>

        <div class="practice">
          <div class="prompt">用这个句型，说一句你自己的话：</div>
          <textarea v-model="mine" rows="2" placeholder="例如：The reason is I want to play football."></textarea>
          <div class="actions">
            <n-button type="primary" :disabled="!mine.trim() || checking" :loading="checking" @click="check">
              {{ checking ? "AI 正在看…" : "让 AI 看看" }}
            </n-button>
            <n-button secondary :disabled="!mine.trim()" @click="speakMine">听我这句话</n-button>
          </div>
          <div v-if="fb" class="fb" :class="{ good: fb.ok }">
            <div class="fb-title">{{ fb.ok ? "说得不错！" : "再改一点就更好了" }}</div>
            <div class="fb-comment">{{ fb.comment }}</div>
            <div v-if="fb.improved" class="fb-better">
              <n-tag size="small" type="success" :bordered="false">更好的说法</n-tag>
              <span class="better">{{ fb.improved }}</span>
              <n-button size="tiny" secondary @click="play(fb.improved)">听示范</n-button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { NButton, NTag } from "naive-ui";
import { api } from "../core/api";
import { loadSpeak, type PatternGroup, type SpeakData } from "../core/speak";

const router = useRouter();
const data = ref<SpeakData | null>(null);
const loading = ref(true);
const groupId = ref("");
const si = ref(0);
const mine = ref("");
const checking = ref(false);
const fb = ref<{ ok: boolean; comment: string; improved: string } | null>(null);

const groups = computed<PatternGroup[]>(() => data.value?.patterns ?? []);
const group = computed(() => groups.value.find((g) => g.id === groupId.value) ?? null);

onMounted(async () => {
  data.value = await loadSpeak();
  if (groups.value.length) groupId.value = groups.value[0].id;
  loading.value = false;
});

function pick(id: string): void {
  groupId.value = id;
  si.value = 0;
  mine.value = "";
  fb.value = null;
}
function pickSentence(i: number): void {
  si.value = i;
  fb.value = null;
}

async function check(): Promise<void> {
  if (!group.value || !mine.value.trim()) return;
  checking.value = true;
  fb.value = null;
  try {
    fb.value = await api<{ ok: boolean; comment: string; improved: string }>("/english/speak/check", {
      method: "POST",
      body: JSON.stringify({ pattern: group.value.items[si.value]?.en ?? "", sentence: mine.value.trim() }),
    });
  } catch (e) {
    fb.value = { ok: false, comment: "AI 暂时不可用：" + (e as Error).message, improved: "" };
  }
  checking.value = false;
}

async function play(text: string): Promise<void> {
  try {
    const r = await api<{ b64: string; mime: string }>("/english/speak/tts", {
      method: "POST",
      body: JSON.stringify({ text }),
    });
    void new Audio(`data:${r.mime};base64,${r.b64}`).play();
  } catch { /* 忽略播放失败 */ }
}

function speakMine(): void {
  void play(mine.value.trim());
}
function back(): void {
  void router.push("/english/speak");
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.empty { padding: 28px 16px; text-align: center; color: var(--c-text-2); }
.groups { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
.gbtn { border: 1px solid var(--c-line, #d1d5db); background: var(--c-surface); color: var(--c-text); border-radius: 999px; padding: 6px 12px; font-size: var(--fs-sub); cursor: pointer; }
.gbtn.on { background: var(--c-primary); border-color: var(--c-primary); color: #fff; font-weight: 700; }
.panel { padding: 16px; }
.gname { font-weight: 800; color: var(--c-text); margin-bottom: 10px; }
.gcn { font-weight: 400; color: var(--c-text-2); font-size: var(--fs-sub); margin-left: 6px; }
.sents { display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow: auto; margin-bottom: 14px; }
.sent { text-align: left; background: var(--c-bg-mint); border: 1px solid transparent; border-radius: var(--r-md); padding: 8px 12px; cursor: pointer; display: flex; flex-direction: column; gap: 2px; }
.sent.on { border-color: var(--c-primary); background: var(--c-primary-soft); }
.sent .en { color: var(--c-text); font-weight: 600; }
.sent .cn { color: var(--c-text-2); font-size: var(--fs-sub); }
.practice { border-top: 1px dashed var(--c-line, #e5e7eb); padding-top: 12px; }
.prompt { color: var(--c-text-2); font-size: var(--fs-sub); margin-bottom: 6px; }
textarea { width: 100%; box-sizing: border-box; border: 1px solid var(--c-line, #d1d5db); border-radius: var(--r-md); padding: 10px; font-family: inherit; font-size: var(--fs-body, 16px); color: var(--c-text); resize: vertical; }
.actions { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.fb { margin-top: 14px; padding: 12px; border-radius: var(--r-md); background: #fef3c7; }
.fb.good { background: var(--c-primary-soft); }
.fb-title { font-weight: 800; margin-bottom: 4px; color: var(--c-text); }
.fb-comment { color: var(--c-text); font-size: var(--fs-sub); }
.fb-better { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 8px; }
.tag { font-size: var(--fs-sub); color: var(--c-primary); font-weight: 700; }
.better { font-weight: 700; color: var(--c-text); }
.small { padding: 2px 8px; font-size: var(--fs-sub); }
</style>
