import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { router } from "./router";
import { setUnauthorizedHandler } from "./core/api";
import { loadTtsConfig } from "./core/ttsConfig";
import { useAuthStore } from "./stores/auth";
import "./tokens.css";

const pinia = createPinia();
const app = createApp(App).use(pinia).use(router);

// 任一接口 401：清会话并强制回登录页，避免停留在业务页面继续点
setUnauthorizedHandler(() => {
  useAuthStore(pinia).logout();
  if (router.currentRoute.value.path !== "/login") {
    void router.replace("/login");
  }
});

app.mount("#app");

// 本地 TTS 配置是公开只读的；每次启动强制刷新，管理页开关不必等 10 分钟 TTL。
void loadTtsConfig(true);

// 首屏启动图：等路由完成首次导航再淡出，避免先闪登录页再跳首页
void router.isReady().then(() => {
  const boot = document.getElementById("boot");
  if (!boot) return;
  boot.classList.add("gone");
  window.setTimeout(() => boot.remove(), 240);
});
