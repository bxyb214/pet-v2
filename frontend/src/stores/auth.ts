import { defineStore } from "pinia";
import { api, getToken, setToken } from "../core/api";
import { clearAiStatus } from "../core/aiStatus";
import { clearMediaToken } from "../core/mediaToken";
import { isTokenExpired } from "../core/token";
import { useLearningStore } from "./learning";

interface TokenResp {
  access_token: string;
  refresh_token: string;
  user_id: number;
  username: string;
  display_name: string;
  perms: string;
  is_admin: boolean;
  exam: string;
}

export const useAuthStore = defineStore("auth", {
  state: () => ({
    username: "",
    displayName: "",
    perms: "",
    isAdmin: false,
    /** 当前学习的考试级别：pet / ket / fce / junior */
    exam: "pet",
  }),
  actions: {
    async login(username: string, password: string): Promise<void> {
      const resp = await api<TokenResp>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      setToken(resp.access_token);
      this.username = resp.username;
      this.displayName = resp.display_name;
      this.perms = resp.perms;
      this.isAdmin = resp.is_admin;
      this.exam = resp.exam || "pet";
      // 登录后建立同步引擎（首次 pull 合并 + 45s 静默拉取），本地快照按用户隔离
      await useLearningStore().connect(resp.username);
    },
    /** 只清登录态，不动本地学习快照（切换/失效时更安全）。 */
    clearSession(): void {
      clearAiStatus();
      this.username = "";
      this.displayName = "";
      this.perms = "";
      this.isAdmin = false;
      this.exam = "pet";
    },
    logout(): void {
      useLearningStore().disconnect();
      clearMediaToken();
      setToken(null);
      this.clearSession();
    },
    /** 切换考试级别（KET / PET）：存服务端，各设备一致 */
    async setExam(exam: string): Promise<void> {
      await api("/auth/me/exam", { method: "PUT", body: JSON.stringify({ exam }) });
      this.exam = exam;
    },
    /** 刷新页面 / 路由跳转前恢复登录态（perms 决定口语权限弹框，必须还原） */
    async restore(): Promise<void> {
      const token = getToken();
      if (!token) {
        this.logout();
        return;
      }
      // 本地先看 JWT 过期时间，避免拿一个必然 401 的 token 继续渲染页面
      if (isTokenExpired(token)) {
        this.logout();
        return;
      }
      if (!this.username) {
        try {
          const me = await api<{ username: string; display_name: string; perms: string; is_admin: boolean; exam: string }>("/auth/me");
          this.username = me.username;
          this.displayName = me.display_name;
          this.perms = me.perms;
          this.isAdmin = me.is_admin;
          this.exam = me.exam || "pet";
        } catch (e) {
          // token 失效 → 清会话；网络错误也保持未登录，路由守卫统一回登录页
          if ((e as { status?: number }).status === 401) this.logout();
          else this.clearSession();
          return;
        }
      }
      // 刷新后同样要接上同步引擎，否则本次会话只写本地、永远不推服务端。
      // 不 await：先渲染本地快照，pull 回来再合并，避免弱网时白屏等待。
      void useLearningStore().connect(this.username);
    },
  },
});
