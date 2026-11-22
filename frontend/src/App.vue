<template>
  <n-config-provider :theme-overrides="themeOverrides" style="min-height: 100vh">
    <n-message-provider>
      <n-dialog-provider>
        <router-view />
      </n-dialog-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { NConfigProvider, NDialogProvider, NMessageProvider } from "naive-ui";
import { themeOverrides } from "./theme";
import { useAuthStore } from "./stores/auth";

const auth = useAuthStore();
onMounted(() => void auth.restore());
</script>

<style>
* { box-sizing: border-box; }
body { margin: 0; font-family: "PingFang SC", "Microsoft YaHei", system-ui, sans-serif; background: var(--c-mint-bg); color: var(--c-text); }
</style>
