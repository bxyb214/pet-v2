/**
 * 开发/测试环境标记：由后端 `/api/v1/healthz` 的 `dev_mode` 决定。
 *
 * 开启后：
 * - 顶栏把用户名替换为 DEV 标签；
 * - Realtime / SOE 使用本地模拟连接，不请求语音服务；
 * - 其余 AI 接口由后端返回确定性结果（见 backend/app/services/dev_mock.py）。
 */
import { ref } from "vue";
import { api } from "./api";

export const devMode = ref(false);

let pending: Promise<boolean> | null = null;

export function ensureDevMode(): Promise<boolean> {
  if (!pending) {
    pending = api<{ dev_mode?: boolean }>("/healthz")
      .then((r) => {
        devMode.value = r.dev_mode === true;
        return devMode.value;
      })
      .catch(() => {
        devMode.value = false;
        return false;
      });
  }
  return pending;
}

/** 仅测试用：重置缓存，便于在用例间切换环境。 */
export function resetDevModeForTest(): void {
  pending = null;
  devMode.value = false;
}
