<template>
  <section class="adm-panel">
    <div class="adm-panel-h row">
      <div>
        <h2>发音评测 · 腾讯 SOE</h2>
        <p>跟读页的「跟读评分」走这套接口，配好即启用。</p>
      </div>
      <div class="adm-actions">
        <n-button size="small" secondary :loading="testBusy" @click="$emit('test')">检查签名</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="$emit('save')">保存本组</n-button>
      </div>
    </div>

    <div class="adm-notice">
      <span class="adm-ni">i</span>
      <p>
        在
        <a href="https://console.cloud.tencent.com/soenew" target="_blank" rel="noopener">SOE 控制台</a>
        开通「口语评测（新版）」并购买资源包；SecretKey 只存服务端。
      </p>
    </div>

    <div class="adm-grid2">
      <label class="adm-field">
        <span class="adm-flabel">AppID</span>
        <n-input v-model:value="soe.appid" placeholder="1300000000" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">引擎</span>
        <n-select v-model:value="soe.engine" :options="engineOptions" placeholder="16k_en（英文，默认）" />
        <span class="adm-fhint">英文句子选 16k_en；留空按 16k_en 处理</span>
      </label>
      <label class="adm-field">
        <span class="adm-flabel">SecretId</span>
        <n-input v-model:value="soe.secret_id" type="password" show-password-on="click" placeholder="AKID…" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">SecretKey</span>
        <n-input v-model:value="soe.secret_key" type="password" show-password-on="click" placeholder="签名用密钥" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">苛刻指数</span>
        <n-input-number v-model:value="soe.coeff" :min="1" :max="4" :step="0.1" style="width: 100%" />
        <span class="adm-fhint">1.0 最宽松，适合儿童；4.0 最严格</span>
      </label>
    </div>

    <AiTestLine :r="test" />
    <p class="adm-foot">{{ saveMsg || "测试只校验配置完整与签名生成，不会发起真实评测。" }}</p>
  </section>
</template>

<script setup lang="ts">
import { NButton, NInput, NInputNumber, NSelect } from "naive-ui";
import AiTestLine from "./AiTestLine.vue";
import type { SoeCfg, TestResult } from "./types";

const engineOptions = [
  { label: "16k_en（英文标准版）", value: "16k_en" },
  { label: "16k_zh（中文标准版）", value: "16k_zh" },
];

const soe = defineModel<SoeCfg>("soe", { required: true });
defineProps<{ test: TestResult | null; saveMsg: string; busy: boolean; testBusy: boolean }>();
defineEmits<{ (e: "save"): void; (e: "test"): void }>();
</script>
