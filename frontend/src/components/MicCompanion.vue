<template>
  <aside class="companion" :class="{ dev: devMode }" aria-label="AI 数字人陪练">
    <div class="stage">
      <span class="ring r1" aria-hidden="true"></span>
      <span class="ring r2" aria-hidden="true"></span>
      <span class="ring r3" aria-hidden="true"></span>

      <svg class="dh" viewBox="0 0 220 220" role="img" aria-label="戴耳机的数字人小绿">
        <defs>
          <linearGradient id="mc-shirt" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="#34d399" />
            <stop offset="1" stop-color="#15803d" />
          </linearGradient>
          <linearGradient id="mc-hair" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#3f2d23" />
            <stop offset="1" stop-color="#6b4a35" />
          </linearGradient>
          <radialGradient id="mc-glow" cx="50%" cy="42%" r="58%">
            <stop offset="0" stop-color="#bbf7d0" stop-opacity=".9" />
            <stop offset="1" stop-color="#bbf7d0" stop-opacity="0" />
          </radialGradient>
        </defs>

        <circle cx="110" cy="104" r="96" fill="url(#mc-glow)" />
        <!-- 肩膀 -->
        <path d="M38 212c5-40 32-60 72-60s67 20 72 60z" fill="url(#mc-shirt)" />
        <path d="M88 154l22 13 22-13" stroke="#d1fae5" stroke-width="5" fill="none" stroke-linecap="round" />
        <!-- 脖子 + 头 -->
        <rect x="98" y="130" width="24" height="28" rx="12" fill="#f3bd98" />
        <ellipse cx="110" cy="100" rx="52" ry="56" fill="#ffd9bd" />
        <circle cx="57" cy="106" r="10" fill="#f3bd98" />
        <circle cx="163" cy="106" r="10" fill="#f3bd98" />
        <!-- 头发 -->
        <path
          d="M56 96c0-35 24-58 54-58s54 23 54 58c0 7-1 13-4 19-2-23-14-32-31-34-14-2-27 2-37 10-10 8-14 20-15 35-9-8-13-19-14-30z"
          fill="url(#mc-hair)"
        />
        <path d="M73 63c13-13 32-18 50-14 12 3 21 10 26 21-19-7-39-9-59-4-7 2-13 4-17 8z" fill="#2f211a" opacity=".85" />
        <!-- 眼睛（眨眼） -->
        <g class="eyes">
          <ellipse cx="90" cy="102" rx="5.6" ry="7.2" fill="#2f241e" />
          <ellipse cx="130" cy="102" rx="5.6" ry="7.2" fill="#2f241e" />
          <circle cx="92" cy="99" r="1.9" fill="#fff" />
          <circle cx="132" cy="99" r="1.9" fill="#fff" />
        </g>
        <!-- 腮红 + 微笑 -->
        <ellipse cx="75" cy="119" rx="9" ry="5" fill="#f7a8a8" opacity=".5" />
        <ellipse cx="145" cy="119" rx="9" ry="5" fill="#f7a8a8" opacity=".5" />
        <path d="M99 123c7 8 17 8 23 0" stroke="#b45309" stroke-width="3.4" stroke-linecap="round" fill="none" />
        <!-- 耳机 -->
        <path d="M52 97c0-39 26-65 58-65s58 26 58 65" stroke="#15803d" stroke-width="9" fill="none" stroke-linecap="round" />
        <rect x="42" y="89" width="19" height="35" rx="9.5" fill="#16a34a" />
        <rect x="159" y="89" width="19" height="35" rx="9.5" fill="#16a34a" />
        <path d="M61 121c6 18 20 25 35 25" stroke="#15803d" stroke-width="4" fill="none" stroke-linecap="round" />
        <circle class="boom" cx="98" cy="146" r="5.5" fill="#22c55e" />
      </svg>

      <div class="wave" aria-hidden="true">
        <i v-for="n in 5" :key="n" :style="{ animationDelay: `${(n - 1) * 0.12}s` }"></i>
      </div>
    </div>

    <div class="meta">
      <span class="live"><i class="dot"></i>{{ devMode ? "模拟语音中" : "麦克风开启中" }}</span>
      <p class="name">小绿 · AI 陪练</p>
      <p class="tip">
        {{ devMode ? "开发环境：数字人为预览，未调用真实麦克风。" : "我在听，慢慢说。读完点提交，或直接和我对话。" }}
      </p>
    </div>

    <div class="btns">
      <button class="mic-off" :class="{ submit: isSubmit }" type="button" :aria-label="label" @click="stopMic">
        <svg v-if="isSubmit" viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="m5 12.5 4.5 4.5L19 7" />
        </svg>
        <svg v-else viewBox="0 0 24 24" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M9 9v3a3 3 0 0 0 5.1 2.1M15 10V6a3 3 0 0 0-5.7-1.3" />
          <path d="M5 11a7 7 0 0 0 10.4 6.2M19 11a7 7 0 0 1-.6 2.8M12 18.5V21M8.5 21h7" />
          <path d="M4 4l16 16" />
        </svg>
        <span>{{ label }}</span>
      </button>
      <!-- 跟读评分：取消本次录音，不提交评分；取消后回到页内「跟读评分」重新开始 -->
      <button v-if="cancelLabel" class="mic-cancel" type="button" :aria-label="cancelLabel" @click="cancelMic">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M6 6l12 12M18 6 6 18" />
        </svg>
        <span>{{ cancelLabel }}</span>
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { devMode } from "../core/devMode";
import { cancelMic, micAction, stopMic } from "../core/micPresence";

const label = computed(() => micAction.value.label ?? "关闭麦克风");
const isSubmit = computed(() => micAction.value.tone === "submit");
const cancelLabel = computed(() => micAction.value.cancelLabel ?? "");
</script>

<style scoped>
.companion {
  position: fixed;
  right: 18px;
  top: 50%;
  transform: translateY(-50%);
  z-index: 40;
  width: clamp(320px, 33vw, 420px);
  height: min(72vh, 640px);
  min-height: 430px;
  max-height: calc(100vh - 96px);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 18px 18px 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f3fbf6 52%, #e8f7ee 100%);
  border: 1px solid var(--c-line-strong, #d3e0d8);
  border-radius: 26px;
  box-shadow: 0 26px 64px rgba(16, 60, 38, 0.2), 0 2px 0 rgba(255, 255, 255, 0.8) inset;
  animation: mc-in 0.28s ease-out;
}

.stage {
  position: relative;
  flex: 1;
  width: 100%;
  min-height: 0;
  display: grid;
  place-items: center;
}

.dh {
  position: relative;
  width: min(86%, 330px);
  max-height: 100%;
  filter: drop-shadow(0 16px 22px rgba(21, 128, 61, 0.16));
  animation: mc-bob 4.2s ease-in-out infinite;
}

.eyes {
  transform-box: fill-box;
  transform-origin: center;
  animation: mc-blink 5.4s infinite;
}
.boom {
  animation: mc-boom 1.8s ease-in-out infinite;
}

.ring {
  position: absolute;
  left: 50%;
  top: 46%;
  width: 62%;
  aspect-ratio: 1;
  border-radius: 50%;
  border: 2px solid rgba(34, 197, 94, 0.35);
  transform: translate(-50%, -50%);
  animation: mc-ring 3s ease-out infinite;
  pointer-events: none;
}
.r2 { animation-delay: 1s; }
.r3 { animation-delay: 2s; }

.wave {
  position: absolute;
  bottom: 2%;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: flex-end;
  gap: 5px;
  height: 26px;
}
.wave i {
  width: 5px;
  height: 8px;
  border-radius: 3px;
  background: var(--c-primary, #16a34a);
  opacity: 0.55;
  animation: mc-wave 1s ease-in-out infinite;
}

.meta {
  text-align: center;
  padding: 0 6px;
}
.live {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 12px;
  border-radius: 999px;
  background: var(--c-primary-soft, #e7f6ec);
  color: var(--c-primary-strong, #15803d);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.02em;
}
.dev .live {
  background: var(--c-accent-soft, #fff7ed);
  color: #b45309;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
  animation: mc-pulse 1.6s ease-in-out infinite;
}
.dev .dot { animation-duration: 2.4s; }
.name {
  margin: 7px 0 2px;
  font-size: 17px;
  font-weight: 800;
  color: var(--c-text, #16211c);
}
.tip {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--c-text-2, #64756c);
}

.btns {
  width: 100%;
  flex: none;
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.mic-off {
  flex: 1;
  min-width: 0;
  min-height: 50px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  border: none;
  border-radius: 999px;
  background: var(--c-danger, #dc2626);
  color: #fff;
  font-size: 15.5px;
  font-weight: 800;
  cursor: pointer;
  box-shadow: 0 10px 20px rgba(220, 38, 38, 0.24);
  transition: transform 0.12s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.mic-off:hover { background: #b91c1c; box-shadow: 0 12px 24px rgba(220, 38, 38, 0.3); }
.mic-off:active { transform: scale(0.985); }
.mic-off:focus-visible { outline: 3px solid var(--c-accent, #d97706); outline-offset: 3px; }
/* 跟读评分：同一个按钮变成主操作「提交」，用主色而不是红色 */
.mic-off.submit {
  background: var(--c-primary-strong, #15803d);
  box-shadow: 0 10px 20px rgba(21, 128, 61, 0.24);
}
.mic-off.submit:hover { background: var(--c-primary-strong, #15803d); filter: brightness(1.06); box-shadow: 0 12px 24px rgba(21, 128, 61, 0.3); }
.mic-off.submit:focus-visible { outline-color: var(--c-primary, #16a34a); }

/* 跟读的「取消」：放弃这次录音，不提交评分 */
.mic-cancel {
  flex: none;
  min-height: 50px;
  padding: 0 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border: 1.5px solid var(--c-line-strong, #d3e0d8);
  border-radius: 999px;
  background: #fff;
  color: var(--c-text-2, #64756c);
  font-size: 14.5px;
  font-weight: 700;
  cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, background 0.15s ease;
}
.mic-cancel:hover { border-color: var(--c-danger, #dc2626); color: var(--c-danger, #dc2626); background: #fff7f7; }
.mic-cancel:active { transform: scale(0.985); }
.mic-cancel:focus-visible { outline: 3px solid var(--c-accent, #d97706); outline-offset: 3px; }

@keyframes mc-in {
  from { opacity: 0; transform: translateY(-50%) translateX(16px) scale(0.98); }
  to { opacity: 1; transform: translateY(-50%) translateX(0) scale(1); }
}
@keyframes mc-bob {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-7px); }
}
@keyframes mc-blink {
  0%, 93%, 100% { transform: scaleY(1); }
  95% { transform: scaleY(0.12); }
  97% { transform: scaleY(1); }
}
@keyframes mc-ring {
  0% { opacity: 0.55; transform: translate(-50%, -50%) scale(0.86); }
  70% { opacity: 0; transform: translate(-50%, -50%) scale(1.28); }
  100% { opacity: 0; transform: translate(-50%, -50%) scale(1.28); }
}
@keyframes mc-wave {
  0%, 100% { height: 8px; }
  50% { height: 26px; }
}
@keyframes mc-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.35; transform: scale(0.8); }
}

/* 窄一点的笔记本 / 竖屏平板：数字人收窄，给内容留空间 */
@media (max-width: 1100px) {
  .companion { width: 300px; right: 14px; }
}

/* 手机与竖屏 iPad：改为底部 1/3 屏，按钮仍在数字人下方 */
@media (max-width: 899px) {
  .companion {
    left: 10px;
    right: 10px;
    top: auto;
    bottom: 10px;
    transform: none;
    width: auto;
    height: 38vh;
    min-height: 250px;
    max-height: 330px;
    padding: 10px 12px 10px;
    border-radius: 20px;
    gap: 4px;
    animation: mc-in-bottom 0.28s ease-out;
  }
  .stage { flex: 1; }
  .dh { width: auto; height: 100%; max-width: 46%; }
  .wave { display: none; }
  .meta { padding: 0; }
  .name { margin: 3px 0 0; font-size: 15px; }
  .tip { display: none; }
  .live { padding: 3px 9px; font-size: 11px; }
  .mic-off { min-height: 42px; font-size: 14.5px; }
  .mic-cancel { min-height: 42px; padding: 0 12px; font-size: 13.5px; }
  .ring { top: 50%; width: 42%; }
}

@keyframes mc-in-bottom {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .companion, .dh, .eyes, .ring, .wave i, .dot, .boom { animation: none !important; }
}
</style>
