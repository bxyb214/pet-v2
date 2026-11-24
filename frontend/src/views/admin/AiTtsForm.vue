<template>
  <section class="adm-panel">
    <div class="adm-panel-h row">
      <div>
        <h2>语音合成 · TTS</h2>
        <p>示范音、单词发音与句子朗读；未命中缓存时才调用模型。</p>
      </div>
      <div class="adm-actions">
        <n-button size="small" secondary :loading="testBusy" @click="$emit('test')">合成测试</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="$emit('save')">保存本组</n-button>
      </div>
    </div>

    <div class="adm-grid2">
      <label class="adm-field">
        <span class="adm-flabel">TTS 模型</span>
        <n-input v-model:value="qwen.tts_model" placeholder="qwen3-tts-flash" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">TTS 音色</span>
        <n-input v-model:value="qwen.tts_voice" placeholder="Ryan" />
      </label>
    </div>

    <AiTestLine :r="test" />
    <p class="adm-foot">{{ saveMsg || "TTS 与实时对话共用 speak.qwen 配置；Key 留空时复用 AI 加词的 Key。" }}</p>
  </section>
</template>

<script setup lang="ts">
import { NButton, NInput } from "naive-ui";
import AiTestLine from "./AiTestLine.vue";
import type { QwenCfg, TestResult } from "./types";

const qwen = defineModel<QwenCfg>("qwen", { required: true });
defineProps<{ test: TestResult | null; saveMsg: string; busy: boolean; testBusy: boolean }>();
defineEmits<{ (e: "save"): void; (e: "test"): void }>();
</script>
