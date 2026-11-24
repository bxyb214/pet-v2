<template>
  <section class="adm-panel">
    <div class="adm-panel-h row">
      <div>
        <h2>TTS 磁盘缓存</h2>
        <p>按最近使用时间做 LRU；超过上限自动清理最久未用的音频。</p>
      </div>
      <div class="adm-actions">
        <n-button size="small" type="error" secondary :disabled="!cache.files" @click="$emit('clear')">清空缓存</n-button>
        <n-button size="small" type="primary" :loading="busy" @click="$emit('save')">保存本组</n-button>
      </div>
    </div>

    <div class="adm-stats">
      <div class="adm-stat"><b class="tnum">{{ cache.files }}</b><span>缓存文件</span></div>
      <div class="adm-stat"><b class="tnum">{{ fmtMB(cache.bytes) }}</b><span>当前占用</span></div>
      <div class="adm-stat"><b class="tnum">{{ cache.max_mb }} MB</b><span>上限</span></div>
      <div class="adm-stat"><b class="tnum">{{ freeMB }}</b><span>剩余空间</span></div>
    </div>

    <div class="adm-grid2">
      <label class="adm-field">
        <span class="adm-flabel">缓存上限 <i class="adm-opt">MB</i></span>
        <n-input-number v-model:value="maxMb" :min="16" :step="64" :precision="0" :clearable="false" style="width: 100%" />
        <span class="adm-fhint">最小 16 MB；只缓存成功合成的音频。</span>
      </label>
    </div>
    <p class="adm-foot">{{ saveMsg || "清空后再次播放会重新合成并产生费用。" }}</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NButton, NInputNumber } from "naive-ui";
import { fmtMB } from "./format";
import type { CacheStats } from "./types";

const props = defineProps<{ cache: CacheStats; saveMsg: string; busy: boolean }>();
const maxMb = defineModel<number | null>("max", { required: true });
defineEmits<{ (e: "save"): void; (e: "clear"): void }>();

const freeMB = computed(
  () => Math.max(0, props.cache.max_mb - Math.round(props.cache.bytes / 1024 / 1024)) + " MB",
);
</script>
