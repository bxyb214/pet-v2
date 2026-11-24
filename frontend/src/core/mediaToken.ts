/**
 * 数学视频媒体令牌：登录用户向 /media/token 换取，拼到视频 URL 的 `mt=`。
 *
 * 为什么不用 Cookie：iOS AirPlay 由电视端直接取流，接收端不会带本站 Cookie；
 * 令牌放 URL 才能让投屏继续可用，服务端再用 nginx auth_request 校验并限时（默认 6 小时）。
 * 只在内存缓存：换设备/新标签页会重新用登录态换取，不把令牌落到 localStorage。
 */
import { api } from "./api";

type MediaToken = { token: string; expires_at: number };

/** 距过期不足 5 分钟就重新换取 */
const REFRESH_AHEAD = 300;

let cached: MediaToken | null = null;
let inflight: Promise<string> | null = null;
let generation = 0;

/** 退出登录时清掉，避免把上一个账号的令牌带进下一个会话。 */
export function clearMediaToken(): void {
  generation += 1;
  cached = null;
  inflight = null;
}

export async function mediaToken(): Promise<string> {
  if (cached && cached.expires_at - Date.now() / 1000 > REFRESH_AHEAD) return cached.token;
  if (!inflight) {
    const gen = generation;
    inflight = api<MediaToken>("/media/token", { method: "POST" })
      .then((r) => {
        if (gen === generation) cached = r;
        return r.token;
      })
      .finally(() => {
        if (gen === generation) inflight = null;
      });
  }
  return inflight;
}
