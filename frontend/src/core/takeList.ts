/** 录音列表的 Vue 侧公共逻辑：按题加载、对象 URL、单条播放、最高分标记。 */
import { computed, onBeforeUnmount, ref, watch, type Ref } from "vue";
import { bestTake, listTakes, type Take } from "./takes";

export type TakeView = Take & { url: string };

/** key = 账号|题目；key 变化时自动换列表（切题/切句） */
export function useTakeList(key: Ref<string>) {
  const takes = ref<TakeView[]>([]);
  const playingId = ref("");
  let audioEl: HTMLAudioElement | null = null;

  const bestId = computed(() => bestTake(takes.value)?.id ?? "");

  function stopPlay(): void {
    const el = audioEl;
    audioEl = null;
    playingId.value = "";
    try { el?.pause(); } catch { /* noop */ }
  }

  function releaseUrls(): void {
    for (const t of takes.value) {
      try { URL.revokeObjectURL(t.url); } catch { /* noop */ }
    }
  }

  async function refresh(): Promise<void> {
    const current = key.value;
    stopPlay();
    releaseUrls();
    takes.value = [];
    if (!current) return;
    const rows = await listTakes(current);
    if (current !== key.value) return; // 已切到别的题
    takes.value = rows.map((t) => ({ ...t, url: URL.createObjectURL(t.blob) }));
  }

  /** 同一时间只播一条；再点一次停止 */
  function togglePlay(t: TakeView): void {
    if (playingId.value === t.id) {
      stopPlay();
      return;
    }
    stopPlay();
    const el = new Audio(t.url);
    audioEl = el;
    playingId.value = t.id;
    el.onended = () => {
      if (audioEl === el) stopPlay();
    };
    el.onerror = () => stopPlay();
    void el.play().catch(() => stopPlay());
  }

  watch(key, () => { void refresh(); }, { immediate: true });
  onBeforeUnmount(() => {
    stopPlay();
    releaseUrls();
  });

  return { takes, playingId, bestId, refresh, togglePlay, stopPlay };
}
