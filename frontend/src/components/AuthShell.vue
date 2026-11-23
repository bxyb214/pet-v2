<template>
  <main class="auth">
    <!-- 登录/注册页没有顶栏，这里单独标出开发环境 -->
    <span
      v-if="devMode"
      class="dev-flag"
      title="开发环境：AI 接口返回模拟结果"
    >开发环境 · DEV</span>
    <div class="card">
      <!-- 左：品牌面板（桌面）。手机下图保留标题，其余收起来 -->
      <aside class="side">
        <header class="mark">
          <span class="mark-badge" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 21V9" />
              <path d="M12 12.5c0-3 2-5.5 5-6 .3 3-1.7 5.6-5 6Z" />
              <path d="M12 15c0-2.6-1.8-4.6-4.4-5-.2 2.6 1.6 4.7 4.4 5Z" />
            </svg>
          </span>
          <span class="mark-name">绿野英语</span>
        </header>

        <div class="side-main">
          <p class="eyebrow">{{ eyebrow }}</p>
          <h1>{{ title }}</h1>
          <ul class="pts">
            <li v-for="p in points" :key="p">
              <i class="bullet" aria-hidden="true"></i>
              <span>{{ p }}</span>
            </li>
          </ul>
        </div>

        <footer class="side-foot">{{ foot }}</footer>
      </aside>

      <!-- 右：表单 -->
      <section class="form">
        <div class="form-inner">
          <slot />
          <p v-if="$slots.alt" class="alt"><slot name="alt" /></p>
        </div>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { devMode, ensureDevMode } from "../core/devMode";

defineProps<{
  eyebrow: string;
  title: string;
  points: string[];
  foot?: string;
}>();

// 登录/注册页不走 AppLayout，需自己触发一次 healthz 探测
onMounted(() => {
  void ensureDevMode();
});
</script>

<style scoped>
.auth {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 28px 20px;
  position: relative;
  /* 极淡的双层径向光，营造纵深但不抢内容 */
  background:
    radial-gradient(900px 520px at 12% -8%, #e5f5eb 0%, transparent 62%),
    radial-gradient(720px 460px at 92% 108%, #eef7f1 0%, transparent 60%),
    var(--c-bg);
}

/* 开发环境标记：与顶栏 DEV 同款，未登录也能识别当前环境 */
.dev-flag {
  position: absolute;
  top: 14px;
  right: 18px;
  z-index: 5;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--c-accent-soft, #fff7ed);
  border: 1px solid var(--c-accent, #d97706);
  color: var(--c-text, #1f2d26);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  line-height: 1;
  box-shadow: var(--shadow-1);
}
.dev-flag::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--c-accent, #d97706);
}

.card {
  width: 100%;
  max-width: 900px;
  display: grid;
  grid-template-columns: 0.86fr 1fr;
  background: var(--c-card);
  border: 1px solid var(--c-line);
  border-radius: var(--r-xl);
  box-shadow: var(--shadow-3);
  overflow: hidden;
}

/* ---------- 品牌面板 ---------- */
.side {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 26px;
  padding: 30px 30px 26px;
  color: #eafaf0;
  background:
    radial-gradient(420px 220px at 82% 4%, rgba(74, 222, 128, 0.22), transparent 70%),
    linear-gradient(158deg, #0d3a26 0%, #12502f 46%, #14582f 100%);
  overflow: hidden;
}
/* 细点阵：科技感来自秩序感，不用发光条 */
.side::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.09) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: linear-gradient(180deg, #000 0%, transparent 78%);
  pointer-events: none;
}
.side > * { position: relative; }

.mark { display: flex; align-items: center; gap: 9px; }
.mark-badge {
  width: 30px; height: 30px; border-radius: 9px;
  display: inline-flex; align-items: center; justify-content: center;
  color: #0d3a26;
  background: linear-gradient(150deg, #d9f7e4, #a7e8bf);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}
.mark-name { font-size: 14px; font-weight: 800; letter-spacing: 0.5px; }

/* 与右侧表单标题基本齐平：左栏内容贴顶，脚注沉底 */
.side-main { margin: 34px 0 auto; }
.eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #86e0a8;
}
.side h1 {
  margin: 0 0 20px;
  font-size: 25px;
  line-height: 1.42;
  font-weight: 800;
  letter-spacing: 0.2px;
  color: #f3fdf7;
}
.pts { list-style: none; margin: 0; padding: 0; display: grid; gap: 11px; }
.pts li {
  display: flex; align-items: flex-start; gap: 9px;
  font-size: 13px; line-height: 1.6; color: rgba(226, 248, 235, 0.82);
}
.bullet {
  width: 5px; height: 5px; margin-top: 7px; flex: none;
  border-radius: 50%;
  background: #6ee7a4;
  box-shadow: 0 0 0 3px rgba(110, 231, 164, 0.16);
}
.side-foot {
  font-size: 11.5px;
  letter-spacing: 0.06em;
  color: rgba(203, 240, 218, 0.62);
}

/* ---------- 表单区 ---------- */
.form { display: flex; background: var(--c-card); }
.form-inner {
  width: 100%;
  max-width: 360px;
  margin: 0 auto;
  padding: 44px 34px 32px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.alt {
  margin: 20px 0 0;
  text-align: center;
  font-size: 12.5px;
  color: var(--c-text-2);
}
.alt :deep(a) {
  color: var(--c-primary-strong);
  font-weight: 700;
  text-decoration: none;
}
.alt :deep(a:hover) { text-decoration: underline; }

/* ---------- 平板：收窄左栏 ---------- */
@media (max-width: 899px) {
  .card { grid-template-columns: 1fr; max-width: 460px; }
  .dev-flag { top: 10px; right: 12px; padding: 4px 9px; font-size: 11px; }
  .side {
    gap: 16px;
    padding: 22px 24px 20px;
  }
  .side-main { margin: 0; }
  .side h1 { font-size: 19px; margin-bottom: 0; }
  .pts, .eyebrow, .side-foot { display: none; }
  .side::before { mask-image: none; opacity: 0.55; }
  .form-inner { padding: 28px 24px 26px; max-width: none; }
}
</style>
