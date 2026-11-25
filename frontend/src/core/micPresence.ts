/**
 * 麦克风占用登记：谁在采集麦克风就登记一个 stop 回调，
 * 页面据此显示数字人；数字人下的「关闭麦克风」一次性停止全部占用者。
 */
import { ref } from "vue";

let seq = 0;
/**
 * 数字人面板底部按钮的文案与样式：跟读评分时主按钮是「提交」，
 * 其余场景是「关闭麦克风」；cancelLabel 有值时再多一个「取消」按钮。
 */
export type MicAction = { label?: string; tone?: "close" | "submit"; cancelLabel?: string };
type Holder = { stop: () => void; cancel: () => void; action: MicAction };

const holders = new Map<number, Holder>();

/** 是否有麦克风正在被调用（含开发环境的模拟语音） */
export const micActive = ref(false);
/** 当前占用者希望数字人按钮显示什么（多个占用者时取最后登记的那个） */
export const micAction = ref<MicAction>({ label: "关闭麦克风", tone: "close" });

function sync(): void {
  micActive.value = holders.size > 0;
  let last: Holder | null = null;
  for (const h of holders.values()) last = h;
  const action: MicAction = {
    label: last?.action.label ?? "关闭麦克风",
    tone: last?.action.tone ?? "close",
  };
  if (last?.action.cancelLabel) action.cancelLabel = last.action.cancelLabel;
  micAction.value = action;
}

/**
 * 登记一次麦克风占用。返回释放函数（幂等）。
 * stop 应负责关闭音频轨道/连接；数字人按钮调用 stopMic() 时会执行它。
 * cancel 是数字人「取消」按钮：放弃本次录音（跟读评分不提交），不传则不显示取消。
 * action 决定数字人按钮文案：「关闭麦克风」/「提交」（跟读评分）。
 */
export function holdMic(
  stop: () => void,
  action: MicAction = {},
  cancel?: () => void,
): () => void {
  const id = ++seq;
  holders.set(id, { stop, cancel: cancel ?? stop, action });
  sync();
  let released = false;
  return () => {
    if (released) return;
    released = true;
    holders.delete(id);
    sync();
  };
}

/** 关闭/提交：调用所有占用者（复制一份，避免回调中释放导致遍历跳过）。 */
export function stopMic(): void {
  for (const { stop } of [...holders.values()]) {
    try {
      stop();
    } catch {
      /* 单个关闭失败不影响其他占用者 */
    }
  }
}

/** 取消：放弃本次录音（跟读评分不提交），由占用者自行释放麦克风。 */
export function cancelMic(): void {
  for (const { cancel } of [...holders.values()]) {
    try {
      cancel();
    } catch {
      /* 单个取消失败不影响其他占用者 */
    }
  }
}

/** 仅测试用：清空登记。 */
export function resetMicForTest(): void {
  holders.clear();
  sync();
}
