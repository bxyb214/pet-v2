<template>
  <section class="adm-panel">
    <div class="adm-panel-h row">
      <div>
        <h2>单价与全局预算</h2>
        <p>改价只影响之后的费用重算；日/月预算可被单个账号覆盖。</p>
      </div>
      <n-button size="small" type="primary" :loading="busy" @click="$emit('save')">保存本组</n-button>
    </div>

    <h3 class="adm-grp">单价</h3>
    <div class="adm-grid2">
      <label v-for="f in PRICE_FIELDS" :key="f.key" class="adm-field">
        <span class="adm-flabel">{{ f.label }} <i class="adm-opt">{{ f.unit }}</i></span>
        <n-input-number v-model:value="prices[f.key]" :min="0" :step="0.01" :precision="4" style="width: 100%" />
      </label>
    </div>

    <h3 class="adm-grp">全局预算</h3>
    <div class="adm-grid2">
      <label class="adm-field">
        <span class="adm-flabel">每日预算 <i class="adm-opt">元</i></span>
        <n-input-number v-model:value="daily" :min="0" :step="1" :precision="2" :clearable="false" style="width: 100%" />
        <span class="adm-fhint">用尽后付费 AI 接口返回 429，免费功能不受影响。</span>
      </label>
      <label class="adm-field">
        <span class="adm-flabel">每月预算 <i class="adm-opt">元</i></span>
        <n-input-number v-model:value="monthly" :min="0" :step="10" :precision="2" :clearable="false" style="width: 100%" />
      </label>
      <label class="adm-field">
        <span class="adm-flabel">告警阈值 <i class="adm-opt">%</i></span>
        <n-input-number v-model:value="alert" :min="10" :max="100" :step="5" :precision="0" :clearable="false" style="width: 100%" />
        <span class="adm-fhint">达到该比例记一条告警，同一周期只记一次。</span>
      </label>
      <div class="adm-field">
        <span class="adm-flabel">用量用尽时硬停</span>
        <n-switch v-model:value="hard" />
        <span class="adm-fhint">关闭后只告警不拦截（不建议）。</span>
      </div>
    </div>

    <p class="adm-foot">{{ saveMsg || "单价默认按 2026-11 官方价，调整后保存即可。" }}</p>
  </section>
</template>

<script setup lang="ts">
import { NButton, NInputNumber, NSwitch } from "naive-ui";

const PRICE_FIELDS = [
  { key: "rt_audio_in", label: "实时音频输入", unit: "元/百万 token" },
  { key: "rt_audio_out", label: "实时音频输出", unit: "元/百万 token" },
  { key: "rt_text_in", label: "实时文本输入", unit: "元/百万 token" },
  { key: "rt_text_out", label: "实时文本输出", unit: "元/百万 token" },
  { key: "llm_in", label: "文本模型输入", unit: "元/百万 token" },
  { key: "llm_out", label: "文本模型输出", unit: "元/百万 token" },
  { key: "soe", label: "发音评测", unit: "元/次" },
  { key: "tts_per_kchar", label: "语音合成", unit: "元/千字符" },
];

const prices = defineModel<Record<string, number>>("prices", { required: true });
const daily = defineModel<number | null>("daily", { required: true });
const monthly = defineModel<number | null>("monthly", { required: true });
const alert = defineModel<number | null>("alert", { required: true });
const hard = defineModel<boolean>("hard", { required: true });
defineProps<{ saveMsg: string; busy: boolean }>();
defineEmits<{ (e: "save"): void }>();
</script>
