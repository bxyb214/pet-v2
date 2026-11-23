/**
 * 口语练习时长：服务端累计，刷新不丢。
 *
 * getSeconds 返回「本次页面打开以来真正开口」的累计秒数；
 * 每 5 秒只上报增量，页面刷新后从 /speak/time/today 恢复。
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { api } from "./api";

export type SpeakMode = "shadow" | "make" | "talk";
type Totals = Record<SpeakMode, number>;

export function useSpeakTime(mode: SpeakMode, getSeconds: () => number) {
  const serverBase = ref(0);
  const local = ref(0);
  const total = computed(() => serverBase.value + local.value);
  let sent = 0;
  let ticker = 0;
  let flushing = false;

  async function load(): Promise<void> {
    try {
      const r = await api<{ totals: Totals }>("/speak/time/today");
      serverBase.value = r.totals?.[mode] ?? 0;
    } catch { /* 离线从 0 开始 */ }
  }

  async function flush(): Promise<void> {
    if (flushing) return;
    const current = Math.floor(getSeconds());
    const delta = Math.min(current - sent, 600);
    if (delta <= 0) return;
    flushing = true;
    try {
      const r = await api<{ totals: Totals }>("/speak/time", {
        method: "POST",
        body: JSON.stringify({ mode, seconds: delta }),
      });
      sent += delta;
      serverBase.value = r.totals?.[mode] ?? serverBase.value + delta;
      local.value = Math.max(0, current - sent);
    } catch { /* 下次重试，未上报部分仍留在 local */ }
    finally {
      flushing = false;
    }
  }

  function tick(): void {
    local.value = Math.max(0, Math.floor(getSeconds()) - sent);
  }

  function onVisibility(): void {
    if (document.visibilityState === "hidden") {
      tick();
      void flush();
    }
  }

  onMounted(() => {
    void load();
    document.addEventListener("visibilitychange", onVisibility);
    ticker = window.setInterval(() => {
      tick();
      void flush();
    }, 5000);
  });
  onBeforeUnmount(() => {
    if (ticker) clearInterval(ticker);
    document.removeEventListener("visibilitychange", onVisibility);
    void flush();
  });

  return { total, serverBase, local, flush };
}
