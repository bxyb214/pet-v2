<template>
  <main class="page">
    <button class="ghost back" @click="back">← 返回口语</button>
    <h1>{{ title }}</h1>
    <p class="sub">{{ subtitle }}</p>

    <div class="ctrl card">
      <div class="status">{{ status }}</div>
      <div v-if="conn" class="timer" :class="{ warn: elapsed >= 720 }">
        {{ mmss(elapsed) }}<span v-if="elapsed >= 720"> · 该收尾啦</span>
      </div>
      <div class="ctrlbtns">
        <n-button v-if="!conn" type="primary" size="large" @click="start">开始对话</n-button>
        <template v-else>
          <n-button type="primary" size="large" secondary @click="stop">结束对话（进入复盘）</n-button>
          <n-button size="large" quaternary @click="askHelp">怎么说？</n-button>
        </template>
      </div>
    </div>

    <n-alert v-if="hint" :type="hintKind === 'praise' ? 'success' : 'info'" class="hint" :bordered="false">
      <div class="hintrow">
        <span class="tag">{{ hintKind === "praise" ? "做得好" : "小提示" }}</span>
        <span class="hint-txt">{{ hint }}</span>
        <n-button quaternary size="tiny" @click="hint = ''">×</n-button>
      </div>
    </n-alert>

    <div class="chat" ref="chatBox">
      <div v-for="(m, i) in lines" :key="i" class="line" :class="m.who">
        <span class="who">{{ m.who === "me" ? "我" : "AI" }}</span>
        <span class="txt">{{ m.text }}</span>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NAlert, NButton } from "naive-ui";
import { api } from "../core/api";
import { loadSpeak, type Scene, type SpeakData } from "../core/speak";
import { createSpeakConn, type SpeakConn } from "../core/speakRTC";

const route = useRoute();
const router = useRouter();
const data = ref<SpeakData | null>(null);
const scene = ref<Scene | null>(null);
const day = computed(() => Number(route.query.day ?? 0));
const conn = ref<SpeakConn | null>(null);
const status = ref("");
const lines = ref<{ who: "me" | "ai"; text: string }[]>([]);
const chatBox = ref<HTMLElement | null>(null);
const hint = ref("");
const hintKind = ref<"hint" | "praise">("hint");
const elapsed = ref(0);
let timer = 0;

const title = computed(() => (scene.value ? `场景对话 · ${scene.value.title}` : "自由对话"));
const subtitle = computed(() =>
  scene.value
    ? `${scene.value.cn} · ${scene.value.focus}`
    : "围绕今天练的句型开口聊，AI 会引导你多用这些句子",
);

onMounted(async () => {
  data.value = await loadSpeak();
  const sid = String(route.query.scene ?? "");
  if (sid) scene.value = (data.value.scenes ?? []).find((c) => c.id === sid) ?? null;
});
onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  conn.value?.close();
});

async function start(): Promise<void> {
  const patterns = scene.value ? [] : await recentPatterns();
  const boot = await api<{ instructions: string }>("/english/speak/boot", {
    method: "POST",
    body: JSON.stringify({
      mode: "talk",
      day: day.value,
      scene_title: scene.value?.title ?? "",
      scene_focus: scene.value?.focus ?? "",
      patterns,
    }),
  });
  try {
    conn.value = await createSpeakConn({
      mode: "talk",
      instructions: boot.instructions,
      turnDetection: "vad",
      onStatus: (s) => (status.value = s),
      onUserTranscript: (t) => {
        lines.value.push({ who: "me", text: t });
        void scroll();
      },
      onReply: (t) => {
        lines.value.push({ who: "ai", text: t });
        void scroll();
      },
      onError: (m) => (status.value = "出错：" + m),
      onHint: (t) => {
        hintKind.value = "hint";
        hint.value = t;
      },
      onPraise: (t) => {
        hintKind.value = "praise";
        hint.value = t;
      },
    });
    lines.value = [];
    hint.value = "";
    status.value = "连接中…";
    elapsed.value = 0;
    timer = window.setInterval(() => {
      elapsed.value = conn.value?.elapsedSec() ?? elapsed.value;
    }, 1000);
  } catch (e) {
    status.value = (e as Error).message;
  }
}

/** 自由对话模式：把最近练过的跟读句子当句型目标传给 boot（最多 3 句） */
async function recentPatterns(): Promise<string[]> {
  const d = data.value ?? (await loadSpeak());
  const packs = d.packs.slice(0, 1);
  const out: string[] = [];
  for (const p of packs) {
    for (const id of p.ids.slice(0, 3)) {
      const s = d.shadow.find((x) => x.id === id);
      if (s) out.push(s.en);
    }
  }
  return out;
}

/** 「怎么说？」：服务端生成中文提示 + 简单英文示范句（气泡展示，不打断语音） */
async function askHelp(): Promise<void> {
  const lastAi = [...lines.value].reverse().find((l) => l.who === "ai")?.text ?? "";
  try {
    const r = await api<{ cn: string; en: string; en_cn: string }>("/english/speak/help", {
      method: "POST",
      body: JSON.stringify({
        scene_title: scene.value?.title ?? "",
        last_ai_text: lastAi,
      }),
    });
    hintKind.value = "hint";
    hint.value = [r.cn, r.en, r.en_cn].filter(Boolean).join(" · ");
  } catch (e) {
    status.value = "求助失败：" + (e as Error).message;
  }
}

async function stop(): Promise<void> {
  const seconds = conn.value?.elapsedSec() ?? elapsed.value;
  conn.value?.close();
  conn.value = null;
  if (timer) { clearInterval(timer); timer = 0; }
  const turns = lines.value.filter((l) => l.who === "me").length;
  // 记账（不限流）
  try {
    await api("/english/speak/session_end", { method: "POST", body: JSON.stringify({ seconds, mode: "talk" }) });
  } catch { /* 离线不阻塞 */ }
  let logId = 0;
  try {
    const r = await api<{ ok: boolean; log_id: number }>("/english/speak/log", {
      method: "POST",
      body: JSON.stringify({
        mode: "talk",
        ref: scene.value?.id ?? "",
        day: day.value,
        turns,
        score: 0,
        issues: [],
        transcript: lines.value.map((l) => ({ role: l.who === "me" ? "user" : "assistant", text: l.text })),
      }),
    });
    logId = r.log_id ?? 0;
  } catch { /* 离线不阻塞 */ }
  // 生成会后复盘句 → 进复盘跟读页
  if (logId) {
    status.value = "正在整理你说的句子…";
    try {
      const r = await api<{ items: unknown[] }>("/english/speak/review", {
        method: "POST",
        body: JSON.stringify({ log_id: logId }),
      });
      if ((r.items ?? []).length > 0) {
        void router.push("/english/speak/review");
        return;
      }
    } catch { /* 无 Key 等：直接回首页 */ }
  }
  void router.push("/english/speak");
}

async function scroll(): Promise<void> {
  await nextTick();
  chatBox.value?.scrollTo({ top: chatBox.value.scrollHeight });
}
function mmss(s: number): string {
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${String(r).padStart(2, "0")}`;
}
function back(): void {
  conn.value?.close();
  void router.push("/english/speak");
}
</script>

<style scoped>
.page { width: 100%; }
h1 { color: var(--c-text); font-size: var(--fs-title); }
.sub { color: var(--c-text-2); font-size: var(--fs-sub); margin: 0 0 14px; }
.back { margin-bottom: 8px; }
.ctrl { padding: 16px; margin-bottom: 12px; text-align: center; }
.ctrlbtns { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
.status { color: var(--c-text-2); margin-bottom: 10px; min-height: 20px; }
.timer { font-variant-numeric: tabular-nums; font-weight: 700; color: var(--c-primary); margin-bottom: 10px; }
.timer.warn { color: var(--c-warn, #d97706); }
.ask { margin-left: 8px; }
.hint { display: flex; align-items: center; gap: 8px; padding: 10px 14px; margin-bottom: 12px; background: var(--c-primary-soft); border-left: 4px solid var(--c-primary); }
.tag { font-size: var(--fs-sub); font-weight: 700; color: var(--c-primary); flex-shrink: 0; }
.hint-txt { flex: 1; color: var(--c-text); }
.x { padding: 0 6px; font-size: 18px; line-height: 1; }
.chat { display: flex; flex-direction: column; gap: 8px; padding-bottom: 40px; }
.line { display: flex; gap: 8px; align-items: flex-start; }
.line.me { flex-direction: row-reverse; }
.who { background: var(--c-bg-mint); color: var(--c-primary); border-radius: var(--r-sm); padding: 2px 8px; font-size: var(--fs-sub); font-weight: 700; flex-shrink: 0; }
.line.me .who { background: var(--c-primary-soft); }
.txt { background: var(--c-surface); border-radius: var(--r-md); padding: 10px 14px; color: var(--c-text); box-shadow: var(--shadow-sm); max-width: 78%; }
.line.me .txt { background: var(--c-primary-soft); }
.pop-enter-active { transition: all 0.2s ease; }
.pop-enter-from { opacity: 0; transform: translateY(-6px); }
</style>
