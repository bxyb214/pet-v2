<template>
  <section class="adm-panel">
    <div class="adm-panel-h row">
      <div>
        <h2>口语对话 · Qwen Realtime</h2>
        <p>浏览器直连，服务端只签发临时凭证；主模型失败时自动回退一次。</p>
      </div>
      <div class="adm-actions">
        <n-button size="small" secondary :loading="testBusy" @click="$emit('test')">检查配置</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="$emit('save')">保存本组</n-button>
      </div>
    </div>

    <h3 class="adm-grp">连接</h3>
    <div class="adm-grid2">
      <label class="adm-field adm-span2">
        <span class="adm-flabel">API Key</span>
        <n-input v-model:value="qwen.api_key" type="password" show-password-on="click" placeholder="sk-…（留空则复用 AI 加词的 Key）" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">业务空间 ID <i class="adm-req">必填</i></span>
        <n-input v-model:value="qwen.workspace" placeholder="ws-xxxx" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">服务地址</span>
        <n-input v-model:value="qwen.base" placeholder="https://dashscope.aliyuncs.com" />
      </label>
    </div>

    <h3 class="adm-grp">模型与轮次</h3>
    <div class="adm-grid2">
      <label class="adm-field">
        <span class="adm-flabel">对话模型</span>
        <n-input v-model:value="qwen.model" placeholder="qwen3.8-omni-flash-realtime" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">回退模型 <i class="adm-opt">可选</i></span>
        <n-input v-model:value="qwen.fallback_model" placeholder="主模型失败时重试一次" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">对话音色</span>
        <n-input v-model:value="qwen.voice" placeholder="Tina" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">轮次检测 <i class="adm-opt">可选</i></span>
        <n-input v-model:value="qwen.vad" placeholder="留空按模型默认；audio-3.1 用 smart_turn_v2" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">跟读模型 <i class="adm-opt">可选</i></span>
        <n-input v-model:value="qwen.shadow_model" placeholder="留空则同对话模型" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">跟读音色 <i class="adm-opt">可选</i></span>
        <n-input v-model:value="qwen.voice_shadow" placeholder="longanqian_v3.1" />
      </label>
      <div class="adm-field">
        <span class="adm-flabel">允许 MCP / 工具调用</span>
        <n-switch v-model:value="qwen.mcp" />
        <span class="adm-fhint">开启后模型可调用会话内工具；不需要时保持关闭。</span>
      </div>
    </div>

    <AiTestLine :r="test" />
    <p class="adm-foot">{{ saveMsg || "qwen3.8 系列必须绑定业务空间，否则报 Workspace endpoint access denied。" }}</p>
  </section>
</template>

<script setup lang="ts">
import { NButton, NInput, NSwitch } from "naive-ui";
import AiTestLine from "./AiTestLine.vue";
import type { QwenCfg, TestResult } from "./types";

const qwen = defineModel<QwenCfg>("qwen", { required: true });
defineProps<{ test: TestResult | null; saveMsg: string; busy: boolean; testBusy: boolean }>();
defineEmits<{ (e: "save"): void; (e: "test"): void }>();
</script>
