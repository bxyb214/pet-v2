<!-- iOS 本地 TTS 调试面板：仅在 ?ttsdebug=1 时出现；不影响正常页面。 -->
<template>
  <div v-if="shown">
    <button v-if="!open" class="ttsdbg-fab" type="button" @click="open = true">TTS</button>
    <section v-else class="ttsdbg" role="dialog" aria-label="TTS 调试">
      <header>
        <b>本地 TTS 调试</b>
        <span class="ttsdbg-origin">{{ origin }}</span>
        <button type="button" class="ttsdbg-x" @click="open = false">×</button>
      </header>
      <div class="ttsdbg-row">
        <input v-model="text" class="ttsdbg-input" placeholder="要测试的英文" />
        <button type="button" :disabled="busy" @click="diagnose">{{ busy ? "测试中…" : "开始诊断" }}</button>
      </div>
      <div class="ttsdbg-row">
        <button type="button" :disabled="!playUrl" @click="playShared">共享元素播放</button>
        <button type="button" :disabled="!playUrl" @click="playNew">new Audio 播放</button>
        <button type="button" :disabled="busy" @click="runSay">走 say() 实测</button>
        <button type="button" :disabled="!report" @click="copy">复制结果</button>
      </div>
      <audio v-if="playUrl" :src="playUrl" controls playsinline class="ttsdbg-audio" @error="onAudioError" />
      <pre class="ttsdbg-out">{{ report || "点「开始诊断」" }}</pre>
      <p class="ttsdbg-hint">先点页面任意处解锁，再点播放；无声时看下方系统信息与最近一次朗读。</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { api, probeFile } from "../core/api";
import { lastLocalAttempt, playAudioUrl, say, unlockAudio } from "../core/say";
import { loadTtsConfig, ttsUrl } from "../core/ttsConfig";

const shown = computed(() => {
  if (typeof location === "undefined") return false;
  return new URLSearchParams(location.search).get("ttsdebug") === "1";
});
const origin = computed(() => (typeof location === "undefined" ? "" : location.origin));
const open = ref(shown.value);
const busy = ref(false);
const text = ref("hello");
const report = ref("");
const playUrl = ref("");

function log(line: string): void {
  report.value += line + "\n";
}

function describeError(e: unknown): string {
  const err = e as { name?: string; message?: string };
  return `${err?.name ?? "Error"}: ${err?.message ?? String(e)}`;
}

async function probe(label: string, url: string): Promise<number> {
  try {
    const p = await probeFile(url);
    const body = p.status >= 400 ? ` body=${p.body}` : "";
    log(`${label} -> ${p.status} ct=${p.contentType || "-"} len=${p.contentLength} range=${p.contentRange || "-"}${body}`);
    return p.status;
  } catch (e) {
    log(`${label} -> ERR ${describeError(e)}`);
    return 0;
  }
}

async function tryNew(url: string): Promise<string> {
  try {
    const a = new Audio(url);
    const res = await Promise.race([
      a.play().then(() => "ok"),
      new Promise<string>((resolve) => setTimeout(() => resolve("timeout 5s"), 5000)),
    ]);
    return res;
  } catch (e) {
    return describeError(e);
  }
}

async function diagnose(): Promise<void> {
  busy.value = true;
  report.value = "";
  playUrl.value = "";
  try {
    log(`UA: ${navigator.userAgent}`);
    log(`platform=${navigator.platform} touch=${navigator.maxTouchPoints} active=${navigator.userActivation?.hasBeenActive}`);
    const probeAudio = typeof Audio === "undefined" ? null : new Audio();
    log(`Audio=${typeof Audio} wav=${probeAudio?.canPlayType("audio/wav") || "-"} speech=${"speechSynthesis" in window}`);

    const cfg = await loadTtsConfig(true);
    log(`cfg enabled=${cfg.enabled} voice=${cfg.voice} v=${cfg.cache_version} max=${cfg.max_chars}`);

    const url = ttsUrl(text.value, cfg);
    log(`GET ${url}`);
    const status = await probe("GET 文字", url);
    let target = url;
    if (status === 404) {
      try {
        const out = await api<{ url: string; cached: boolean; ms?: number }>("/speak/tts/local", {
          method: "POST",
          body: JSON.stringify({ text: text.value }),
        });
        target = out.url;
        log(`POST -> ok cached=${out.cached} ms=${out.ms ?? "-"} url=${out.url}`);
        await probe("GET 合成后", out.url);
      } catch (e) {
        log(`POST -> ERR ${describeError(e)}`);
      }
    }
    playUrl.value = target;

    unlockAudio();
    const shared = await playAudioUrl(target, "");
    log(`共享元素 playAudioUrl -> ${shared ? "ok" : "failed"}`);
    log(`new Audio 直接播放 -> ${await tryNew(target)}`);

    const last = lastLocalAttempt();
    log(`最近一次 say: ${last ? `${last.status} text=${last.text} ${last.error ?? ""}` : "无"}`);
  } catch (e) {
    log(`ERR ${describeError(e)}`);
  } finally {
    busy.value = false;
  }
}

async function playShared(): Promise<void> {
  unlockAudio();
  const ok = await playAudioUrl(playUrl.value, "");
  log(`手动共享元素播放 -> ${ok ? "ok" : "failed"}`);
}

async function playNew(): Promise<void> {
  log(`手动 new Audio 播放 -> ${await tryNew(playUrl.value)}`);
}

/** 走真实的「点单词」路径：iOS 上会依次尝试缓存 GET → 超时合成 → 补播。 */
async function runSay(): Promise<void> {
  busy.value = true;
  report.value = "";
  const started = Date.now();
  const text0 = text.value;
  log(`say(${text0}) …（最多等 15s）`);
  try {
    say(text0);
    for (let i = 0; i < 30; i += 1) {
      await new Promise((resolve) => setTimeout(resolve, 500));
      const a = lastLocalAttempt();
      if (a && a.at >= started && a.status !== "miss") {
        log(`say -> ${a.status} url=${a.url}${a.error ? ` err=${a.error}` : ""}`);
        if (a.url) playUrl.value = a.url;
        return;
      }
    }
    const a = lastLocalAttempt();
    log(`15s 内未完成；最近一次：${a ? `${a.status} url=${a.url} ${a.error ?? ""}` : "无"}`);
  } catch (e) {
    log(`say ERR ${describeError(e)}`);
  } finally {
    busy.value = false;
  }
}

function onAudioError(): void {
  log(`<audio> error: ${describeError({ name: "MediaError" })}`);
}

async function copy(): Promise<void> {
  try {
    await navigator.clipboard.writeText(report.value);
    log("已复制");
  } catch {
    log("复制失败：请手动长按选择文本");
  }
}
</script>

<style scoped>
.ttsdbg-fab {
  position: fixed; right: 12px; bottom: 76px; z-index: 9999;
  width: 46px; height: 46px; border-radius: 50%;
  border: 1px solid var(--c-line); background: var(--c-surface); color: var(--c-text);
  font-weight: 700; box-shadow: var(--shadow-2); cursor: pointer;
}
.ttsdbg {
  position: fixed; inset: 6vh 3vw; z-index: 9999; overflow: auto;
  background: var(--c-surface); color: var(--c-text);
  border: 1px solid var(--c-line); border-radius: var(--r-card);
  box-shadow: var(--shadow-3); padding: 12px;
  font-size: 12px;
}
.ttsdbg header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.ttsdbg-origin { color: var(--c-text-3); font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.ttsdbg-x { margin-left: auto; border: 0; background: none; font-size: 22px; line-height: 1; cursor: pointer; color: var(--c-text-2); }
.ttsdbg-row { display: flex; gap: 8px; margin: 8px 0; flex-wrap: wrap; }
.ttsdbg-row button {
  border: 1px solid var(--c-line); background: var(--c-bg); color: var(--c-text);
  border-radius: var(--r-sm); padding: 7px 10px; font-size: 12px;
}
.ttsdbg-row button:disabled { opacity: 0.5; }
.ttsdbg-input { flex: 1; min-width: 140px; border: 1px solid var(--c-line); border-radius: var(--r-sm); padding: 7px 9px; font-size: 13px; }
.ttsdbg-audio { width: 100%; margin: 6px 0; }
.ttsdbg-out {
  white-space: pre-wrap; word-break: break-word; background: var(--c-bg);
  border-radius: var(--r-sm); padding: 8px; max-height: 42vh; overflow: auto;
}
.ttsdbg-hint { color: var(--c-text-3); font-size: 11px; margin: 6px 0 0; }
</style>
