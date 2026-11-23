/**
 * 麦克风占用登记：谁在采集麦克风就登记一个 stop 回调，
 * 页面据此显示数字人；数字人下的「关闭麦克风」一次性停止全部占用者。
 */
import { ref } from "vue";

let seq = 0;
const holders = new Map<number, () => void>();

/** 是否有麦克风正在被调用（含开发环境的模拟语音） */
export const micActive = ref(false);

function sync(): void {
  micActive.value = holders.size > 0;
}

/**
 * 登记一次麦克风占用。返回释放函数（幂等）。
 * stop 应负责关闭音频轨道/连接；数字人按钮调用 stopMic() 时会执行它。
 */
export function holdMic(stop: () => void): () => void {
  const id = ++seq;
  holders.set(id, stop);
  sync();
  let released = false;
  return () => {
    if (released) return;
    released = true;
    holders.delete(id);
    sync();
  };
}

/** 关闭麦克风：停止所有占用者（复制一份，避免回调中释放导致遍历跳过）。 */
export function stopMic(): void {
  for (const stop of [...holders.values()]) {
    try {
      stop();
    } catch {
      /* 单个关闭失败不影响其他占用者 */
    }
  }
}

/** 仅测试用：清空登记。 */
export function resetMicForTest(): void {
  holders.clear();
  sync();
}
