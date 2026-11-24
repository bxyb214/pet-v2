<template>
  <button
    v-if="visible"
    class="install-chip"
    type="button"
    aria-label="把火焰学习安装到主屏幕"
    @click="open"
  >
    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M12 15V3m0 0L8 7m4-4 4 4" />
      <path d="M4 13v6a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-6" />
    </svg>
    <span class="label">安装到主屏</span>
  </button>

  <Teleport to="body">
    <div v-if="show" class="pwa-mask" @click.self="close">
      <div class="pwa-card" role="dialog" aria-modal="true" aria-labelledby="pwa-title">
        <header class="pwa-head">
          <span class="pwa-badge">iPad 全屏</span>
          <h2 id="pwa-title">把火焰学习装到主屏</h2>
          <button class="pwa-x" type="button" aria-label="关闭" @click="close">×</button>
        </header>
        <p class="pwa-lead">从主屏图标打开没有地址栏，和 App 一样全屏使用。</p>
        <ol class="pwa-steps">
          <li>
            <b>用 Safari 打开本站</b>
            <span>地址栏输入 bxyb214.de5.net:18089；微信 / QQ 内打开无法安装</span>
          </li>
          <li>
            <b>点「分享」按钮</b>
            <span>iPad 在顶部、iPhone 在底部，方框向上的箭头</span>
          </li>
          <li>
            <b>选「添加到主屏幕」</b>
            <span>再点右上角「添加」，主屏出现火焰图标即完成</span>
          </li>
        </ol>
        <div class="pwa-foot">
          <button class="pwa-later" type="button" @click="dismiss">不再提示</button>
          <button class="pwa-ok" type="button" @click="close">知道了</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

type InstallPromptEvent = Event & { prompt: () => Promise<void> };

const DISMISS_KEY = "pet_pwa_hint";

const standalone = ref(false);
const ios = ref(false);
const dismissed = ref(false);
const show = ref(false);
const deferred = ref<InstallPromptEvent | null>(null);

/** 已经全屏运行或用户选择不再提示时，不再显示入口 */
const visible = computed(() =>
  !standalone.value && !dismissed.value && (ios.value || deferred.value !== null),
);

function readDismissed(): boolean {
  try {
    return localStorage.getItem(DISMISS_KEY) === "1";
  } catch {
    return false;
  }
}

function onPrompt(e: Event): void {
  // 桌面/安卓 Chrome：先拦下，等用户点「安装」时再触发
  e.preventDefault();
  deferred.value = e as InstallPromptEvent;
}

function onInstalled(): void {
  standalone.value = true;
}

function open(): void {
  if (deferred.value) {
    void deferred.value.prompt();
    deferred.value = null;
    return;
  }
  show.value = true;
}

function close(): void {
  show.value = false;
}

function dismiss(): void {
  show.value = false;
  dismissed.value = true;
  try {
    localStorage.setItem(DISMISS_KEY, "1");
  } catch {
    /* 隐私模式：仅本次会话不再弹出 */
  }
}

onMounted(() => {
  const mq = window.matchMedia("(display-mode: standalone)");
  const nav = navigator as Navigator & { standalone?: boolean };
  standalone.value = mq.matches || nav.standalone === true;
  ios.value =
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  dismissed.value = readDismissed();
  window.addEventListener("beforeinstallprompt", onPrompt);
  window.addEventListener("appinstalled", onInstalled);
});

onBeforeUnmount(() => {
  window.removeEventListener("beforeinstallprompt", onPrompt);
  window.removeEventListener("appinstalled", onInstalled);
});
</script>

<style scoped>
.install-chip {
  display: inline-flex; align-items: center; gap: 6px; flex: none;
  min-height: 44px; padding: 6px 12px;
  border: 1px solid var(--c-line-strong, #d3e0d8); border-radius: 999px;
  background: var(--c-primary-soft, #e7f6ec); color: var(--c-primary-strong, #15803d);
  font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer;
}
.install-chip:hover { border-color: var(--c-primary, #16a34a); background: var(--c-mint-bg, #f2faf5); }
.install-chip:focus-visible { outline: 3px solid var(--c-primary, #16a34a); outline-offset: 2px; }

.pwa-mask {
  position: fixed; inset: 0; z-index: 90;
  display: flex; align-items: center; justify-content: center;
  padding: calc(20px + env(safe-area-inset-top, 0px)) 20px calc(20px + env(safe-area-inset-bottom, 0px));
  background: rgba(16, 38, 27, 0.38); backdrop-filter: blur(3px);
}
.pwa-card {
  width: min(440px, 100%); max-height: 100%; overflow-y: auto;
  background: var(--c-surface, #fff); border-radius: 20px;
  padding: 20px 22px 18px; box-shadow: 0 24px 60px rgba(17, 57, 36, 0.28);
}
.pwa-head { display: flex; align-items: center; gap: 9px; flex-wrap: wrap; }
.pwa-head h2 { margin: 0; font-size: 18px; color: var(--c-text, #1f2d26); }
.pwa-badge { font-size: 11px; font-weight: 800; color: #fff; background: var(--c-primary-strong, #15803d); border-radius: 999px; padding: 3px 9px; }
.pwa-x {
  margin-left: auto; width: 44px; height: 44px; border-radius: 50%;
  border: 1px solid var(--c-line, #e5efe9); background: var(--c-surface, #fff); color: var(--c-text-2, #6b7f74);
  font-size: 21px; line-height: 1; cursor: pointer;
}
.pwa-lead { margin: 12px 0 14px; color: var(--c-text-2, #6b7f74); font-size: 13.5px; line-height: 1.6; }
.pwa-steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; counter-reset: step; }
.pwa-steps li {
  position: relative; counter-increment: step;
  padding: 11px 12px 11px 46px; border: 1px solid var(--c-line, #e5efe9);
  border-radius: 13px; background: var(--c-mint-bg, #f2faf5);
}
.pwa-steps li::before {
  content: counter(step); position: absolute; left: 12px; top: 11px;
  width: 24px; height: 24px; border-radius: 50%;
  display: grid; place-items: center; background: var(--c-primary-soft, #e7f6ec);
  color: var(--c-primary-strong, #15803d); font-size: 12px; font-weight: 800;
}
.pwa-steps b { display: block; font-size: 14px; color: var(--c-text, #1f2d26); }
.pwa-steps span { display: block; margin-top: 3px; font-size: 12.5px; line-height: 1.55; color: var(--c-text-2, #6b7f74); }
.pwa-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 16px; }
.pwa-foot button { min-height: 44px; padding: 8px 16px; border-radius: 11px; font: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer; }
.pwa-later { border: 1px solid var(--c-line, #e5efe9); background: #fff; color: var(--c-text-2, #6b7f74); }
.pwa-ok { border: 1px solid var(--c-primary-strong, #15803d); background: var(--c-primary-strong, #15803d); color: #fff; }

@media (max-width: 767px) {
  .install-chip .label { display: none; }
  .install-chip { width: 44px; padding: 0; justify-content: center; }
}
</style>
