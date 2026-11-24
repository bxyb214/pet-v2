<template>
  <div class="page">
    <header class="adm-head">
      <div>
        <p class="adm-eyebrow">Admin Console</p>
        <h1>管理后台</h1>
        <p class="adm-sub">AI 能力与预算 · 账号额度 · 用量账本</p>
      </div>
      <div class="adm-actions">
        <span class="adm-chip">{{ todayText }}</span>
      </div>
    </header>

    <nav class="adm-tabs" role="tablist">
      <button
        v-for="t in TABS"
        :key="t.id"
        class="adm-tab"
        role="tab"
        :aria-selected="tab === t.id"
        :class="{ on: tab === t.id }"
        @click="tab = t.id"
      >{{ t.name }}</button>
    </nav>

    <AdminOverview v-if="tab === 'overview'" @navigate="tab = $event" />
    <AdminAiConfig v-else-if="tab === 'ai'" />
    <AdminUsers v-else-if="tab === 'users'" />
    <AdminUsage v-else-if="tab === 'usage'" />
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import AdminOverview from "./admin/AdminOverview.vue";
import AdminAiConfig from "./admin/AdminAiConfig.vue";
import AdminUsers from "./admin/AdminUsers.vue";
import AdminUsage from "./admin/AdminUsage.vue";
import "./admin/admin.css";

const TABS = [
  { id: "overview", name: "概览" },
  { id: "ai", name: "AI 配置" },
  { id: "users", name: "用户与额度" },
  { id: "usage", name: "用量与预算" },
];
const tab = ref("overview");

const d = new Date();
const todayText = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
</script>
