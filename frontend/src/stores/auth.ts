import { defineStore } from "pinia";
import { api, getToken, setToken } from "../core/api";
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
      // 登录后建立同步引擎（首次 pull 合并 + 45s 静默拉取）
      await useLearningStore().connect();
    },
    logout(): void {
      useLearningStore().disconnect();
      setToken(null);
      this.username = "";
      this.perms = "";
      this.isAdmin = false;
      this.exam = "pet";
    },
    /** 切换考试级别（KET / PET）：存服务端，各设备一致 */
    async setExam(exam: string): Promise<void> {
      await api("/auth/me/exam", { method: "PUT", body: JSON.stringify({ exam }) });
      this.exam = exam;
    },
    /** 刷新页面后恢复登录态（perms 决定口语权限弹框，必须还原） */
    async restore(): Promise<void> {
      if (!getToken() || this.username) return;
      try {
        const me = await api<{ username: string; display_name: string; perms: string; is_admin: boolean; exam: string }>("/auth/me");
        this.username = me.username;
        this.displayName = me.display_name;
        this.perms = me.perms;
        this.isAdmin = me.is_admin;
        this.exam = me.exam || "pet";
      } catch {
        // token 失效等：保持未登录态，路由守卫会跳登录页
      }
    },
  },
});
