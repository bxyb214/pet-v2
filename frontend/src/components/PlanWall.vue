<template>
  <div class="pw">
    <div class="pw-head">
      <div class="pw-num">
        <b class="tnum">{{ doneCount }}</b><i>/ {{ length }} 天</i>
      </div>
      <div class="pw-chip tnum">{{ left === 0 ? "全部完成" : `还剩 ${left} 天` }}</div>
    </div>

    <div class="pw-wall" :class="{ weekly: length > 60 }">
      <div
        v-for="(c, i) in cells"
        :key="c.key"
        class="cell"
        :class="c.state"
        :style="{ animationDelay: `${Math.min(i * 18, 420)}ms` }"
        :title="c.title"
      >
        <span class="n tnum">{{ c.label }}</span>
        <svg v-if="c.state === 'done'" class="ck" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4.5 12.5l4.6 4.6L19.5 6.8" />
        </svg>
      </div>
    </div>

    <div class="pw-legend">
      <span><i class="dot done"></i>已完成</span>
      <span><i class="dot today"></i>今天</span>
      <span><i class="dot todo"></i>还没学</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 计划进度墙：一格一天（>60 天改成一格一周）。
 * 比百分比进度条多给三件事：哪天做了、断没断、还剩几格。
 * 计划按连续天数推进，第一个没做的天就是「今天」，它之前必然都做完了，所以只有三态。
 */
import { computed } from "vue";

const props = defineProps<{
  /** 计划总天数 */
  length: number;
  /** 已完成的天（字符串或数字都行，接口给的是字符串） */
  daysDone: Array<string | number>;
}>();

type CellState = "done" | "today" | "todo";
interface Cell { key: string; label: string; state: CellState; title: string }

const doneCount = computed(() => props.daysDone.length);
const left = computed(() => Math.max(props.length - doneCount.value, 0));
const doneSet = computed(() => new Set(props.daysDone.map(String)));

/** 第一个没做的天（全部做完为 0） */
const firstOpen = computed(() => {
  for (let d = 1; d <= props.length; d += 1) if (!doneSet.value.has(String(d))) return d;
  return 0;
});

const cells = computed<Cell[]>(() => {
  const len = props.length;
  const open = firstOpen.value;
  const stateOf = (d: number): CellState =>
    doneSet.value.has(String(d)) ? "done" : d === open ? "today" : "todo";

  if (len <= 60) {
    return Array.from({ length: len }, (_, i) => {
      const d = i + 1;
      return { key: `d${d}`, label: String(d), state: stateOf(d), title: `第 ${d} 天` };
    });
  }

  const weeks = Math.ceil(len / 7);
  return Array.from({ length: weeks }, (_, i) => {
    const days = Array.from({ length: 7 }, (_, k) => i * 7 + k + 1).filter((d) => d <= len);
    const done = days.filter((d) => doneSet.value.has(String(d))).length;
    const state: CellState = done === days.length ? "done" : open && days.includes(open) ? "today" : "todo";
    return { key: `w${i + 1}`, label: `W${i + 1}`, state, title: `第 ${i + 1} 周 · ${done}/${days.length} 天` };
  });
});
</script>

<style scoped>
.pw-head { display: flex; align-items: baseline; gap: 12px; margin-bottom: 14px; }
.pw-num { display: flex; align-items: baseline; gap: 4px; }
.pw-num b {
  font-size: 30px; font-weight: 800; line-height: 1;
  color: var(--c-text); font-variant-numeric: tabular-nums;
}
.pw-num i { font-style: normal; font-size: 14px; color: var(--c-text-2); }
.pw-chip {
  margin-left: auto; font-size: 13px; color: var(--c-text-2);
  background: var(--c-mint-bg); border: 1px solid var(--c-line);
  padding: 4px 10px; border-radius: var(--r-pill);
  white-space: nowrap;
}

.pw-wall { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
.pw-wall.weekly { grid-template-columns: repeat(4, minmax(0, 1fr)); }
/* 一周一格：不做正方形，否则会被拉成大方块 */
.pw-wall.weekly .cell { aspect-ratio: auto; height: 54px; }

.cell {
  position: relative;
  aspect-ratio: 1 / 1;
  min-height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  border: 1px solid var(--c-line);
  background: #fff;
  animation: cell-in var(--dur-3) var(--ease-out) both;
}
.cell .n {
  font-size: 12px; font-weight: 700; color: var(--c-text-3);
  font-variant-numeric: tabular-nums; letter-spacing: 0.2px;
}
.cell .ck {
  position: absolute; inset: 0; margin: auto;
  width: 15px; height: 15px;
  fill: none; stroke: #fff; stroke-width: 2.6;
  stroke-linecap: round; stroke-linejoin: round;
}
.cell.done {
  background: linear-gradient(180deg, #1cb257 0%, #16a34a 100%);
  border-color: #148f41;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.16);
}
.cell.done .n {
  position: absolute; top: 5px; left: 7px;
  font-size: 11px; font-weight: 700; color: rgba(255, 255, 255, 0.85);
}
.cell.today {
  background: var(--c-primary-soft);
  border: 1.5px solid var(--c-primary);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.1);
}
.cell.today .n { color: var(--c-primary-strong); font-size: 13px; }
.cell.today::after {
  content: ""; position: absolute; bottom: 6px;
  width: 4px; height: 4px; border-radius: 50%;
  background: var(--c-primary);
  animation: breathe 1.8s var(--ease-out) infinite;
}

@keyframes cell-in {
  from { opacity: 0; transform: translateY(4px) scale(0.94); }
  to { opacity: 1; transform: none; }
}
@keyframes breathe {
  0%, 100% { opacity: 0.35; transform: scale(0.9); }
  50% { opacity: 1; transform: scale(1.15); }
}

.pw-legend {
  display: flex; flex-wrap: wrap; gap: 14px;
  margin-top: 12px; font-size: 12px; color: var(--c-text-2);
}
.pw-legend span { display: inline-flex; align-items: center; gap: 6px; }
.dot {
  width: 10px; height: 10px; border-radius: 3px; display: inline-block;
  border: 1px solid var(--c-line); background: #fff;
}
.dot.done { background: var(--c-primary); border-color: var(--c-primary); }
.dot.today { background: var(--c-primary-soft); border-color: var(--c-primary); }

@media (min-width: 768px) {
  .pw-wall { grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 10px; }
  .pw-wall.weekly { grid-template-columns: repeat(6, minmax(0, 1fr)); }
}
@media (min-width: 1024px) {
  .pw-wall { grid-template-columns: repeat(15, minmax(0, 1fr)); }
  .pw-wall.weekly { grid-template-columns: repeat(8, minmax(0, 1fr)); }
}
@media (prefers-reduced-motion: reduce) {
  .cell { animation: none; }
  .cell.today::after { animation: none; opacity: 1; }
}
</style>
