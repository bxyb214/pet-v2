<template>
  <main class="page">
    <EmptyState
      title="这个页面不存在"
      desc="链接可能已经过期，或地址写错了。回到词库继续学习吧。"
    >
      <template #action>
        <n-button type="primary" size="large" @click="router.push('/english/words/browse')">
          回到词库
        </n-button>
      </template>
    </EmptyState>
  </main>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { NButton } from "naive-ui";
import EmptyState from "../components/EmptyState.vue";

const router = useRouter();
</script>

<style scoped>
.page { width: 100%; }
</style>
