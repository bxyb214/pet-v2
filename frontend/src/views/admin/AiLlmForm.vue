<template>
  <section class="adm-panel">
    <div class="adm-panel-h row">
      <div>
        <h2>AI 加词补全</h2>
        <p>手动加生词时补词性、释义与例句，也用于造句改写与复盘。</p>
      </div>
      <div class="adm-actions">
        <n-button size="small" secondary :loading="testBusy" @click="$emit('test')">测试连接</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="$emit('save')">保存本组</n-button>
      </div>
    </div>

    <div class="adm-notice">
      <span class="adm-ni">i</span>
      <p>
        在
        <a href="https://bailian.console.aliyun.com/cn-beijing/model/settings/api-key" target="_blank" rel="noopener">阿里云百炼 · API-KEY</a>
        创建 Key，并开通通义千问文本模型。
      </p>
    </div>

    <div class="adm-grid2">
      <label class="adm-field adm-span2">
        <span class="adm-flabel">API Key</span>
        <n-input v-model:value="llm.api_key" type="password" show-password-on="click" placeholder="sk-…" />
        <span class="adm-fhint">保存后只回显尾 4 位，明文不出服务端</span>
      </label>
      <label class="adm-field">
        <span class="adm-flabel">接口地址</span>
        <n-input v-model:value="llm.base_url" placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">模型</span>
        <n-input v-model:value="llm.model" placeholder="qwen3.8-flash" />
      </label>
    </div>

    <AiTestLine :r="test" />
    <p class="adm-foot">{{ saveMsg || "改动后点右上「保存本组」。" }}</p>
  </section>
</template>

<script setup lang="ts">
import { NButton, NInput } from "naive-ui";
import AiTestLine from "./AiTestLine.vue";
import type { LlmCfg, TestResult } from "./types";

const llm = defineModel<LlmCfg>("llm", { required: true });
defineProps<{ test: TestResult | null; saveMsg: string; busy: boolean; testBusy: boolean }>();
defineEmits<{ (e: "save"): void; (e: "test"): void }>();
</script>
