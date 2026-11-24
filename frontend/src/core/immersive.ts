import { onBeforeUnmount, ref, watch, type WatchSource } from "vue";

/**
 * 沉浸式作答状态（模块级单例）：
 * 做题轮次进行中隐藏内容区面包屑与页签，只留页面自己的退出/进度条。
 * 组件卸载时自动复位，避免影响后续页面。
 */
export const immersive = ref(false);

export function useImmersive(active: WatchSource<boolean>): void {
  watch(active, (v) => { immersive.value = v; }, { immediate: true });
  onBeforeUnmount(() => { immersive.value = false; });
}
