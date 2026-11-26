<template>
  <n-config-provider :theme-overrides="themeOverrides" style="min-height: 100vh">
    <n-message-provider>
      <n-dialog-provider>
        <router-view />
        <TtsDebugPanel />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { NConfigProvider, NDialogProvider, NMessageProvider } from "naive-ui";
import TtsDebugPanel from "./components/TtsDebugPanel.vue";
import { themeOverrides } from "./theme";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
onMounted(() => void auth.restore());
</script>

<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--font-base);
  background: var(--c-mint-bg);
  color: var(--c-text);
  /* 字重更实、边缘更清晰，视觉上更“精密” */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
</style>
