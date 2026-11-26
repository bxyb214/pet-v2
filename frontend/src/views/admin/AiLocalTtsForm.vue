<template>
  <section class="adm-panel">
    <div class="adm-panel-h row">
      <div>
        <h2>本地发音 · Piper</h2>
        <p>NAS 上的英音 TTS；固定内容预生成后秒开，未命中时按需合成并缓存。</p>
      </div>
      <div class="adm-actions">
        <n-button size="small" secondary :loading="testBusy" @click="$emit('test')">合成测试</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="$emit('save')">保存本组</n-button>
      </div>
    </div>

    <div class="adm-field row">
      <span class="adm-flabel">启用本地发音</span>
      <n-switch v-model:value="local.enabled" />
      <span class="adm-hint">关闭后不用重新部署；客户端 10 分钟内或刷新页面即回退浏览器朗读。</span>
    </div>

    <div class="adm-grid2">
      <label class="adm-field">
        <span class="adm-flabel">音色（英文）</span>
        <n-input v-model:value="local.voice" placeholder="en_GB-alan-medium" />
      </label>
      <p class="adm-hint">音色须与 sidecar 的 PIPER_VOICES 一致（默认 en_GB-alan-medium + zh_CN-huayan-medium），否则合成返回 502。</p>
      <label class="adm-field">
        <span class="adm-flabel">音色（中文）</span>
        <n-input v-model:value="local.voice_zh" placeholder="zh_CN-huayan-medium" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">引擎</span>
        <n-input v-model:value="local.engine" disabled placeholder="piper" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">语速</span>
        <n-input-number v-model:value="local.speed" :min="0.5" :max="2" :step="0.05" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">缓存版本</span>
        <n-input v-model:value="local.cache_version" placeholder="piper1" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">Sidecar 地址</span>
        <n-input v-model:value="local.sidecar" placeholder="http://tts:8100" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">单次文本上限</span>
        <n-input-number v-model:value="local.max_chars" :min="50" :max="400" :step="10" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">每用户未命中/分钟</span>
        <n-input-number v-model:value="local.rate_per_min" :min="1" :max="300" :step="5" />
      </label>
    </div>

    <AiTestLine :r="test" />
    <p class="adm-foot">
      {{ saveMsg || "改音色/语速/规范化规则后请升缓存版本，并重跑 tools/build_tts.py。" }}
    </p>
  </section>
</template>

<script setup lang="ts">
import { NButton, NInput, NInputNumber, NSwitch } from "naive-ui";
import AiTestLine from "./AiTestLine.vue";
import type { LocalTtsCfg, TestResult } from "./types";

const local = defineModel<LocalTtsCfg>("local", { required: true });
defineProps<{ test: TestResult | null; saveMsg: string; busy: boolean; testBusy: boolean }>();
defineEmits<{ (e: "save"): void; (e: "test"): void }>();
</script>
