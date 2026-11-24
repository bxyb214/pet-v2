<template>
  <div class="adm-page">
    <section class="adm-stats">
      <div v-for="s in stats" :key="s.label" class="adm-stat">
        <b class="tnum">{{ s.value }}</b>
        <span>{{ s.label }}</span>
      </div>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>服务状态</h2>
          <p>只判断“有没有配好”，真实连通性请到「AI 配置」里点测试。</p>
        </div>
        <n-button size="small" secondary :loading="loading" @click="load">刷新</n-button>
      </div>

      <div class="ov-status">
        <div class="ov-s">
          <span class="ov-k">文本模型</span>
          <span class="adm-chip" :class="ov?.providers?.llm ? 'ok' : 'bad'">{{ ov?.providers?.llm ? "已配置" : "未配置" }}</span>
          <span class="ov-v">AI 加词 / 造句改写 / 复盘</span>
        </div>
        <div class="ov-s">
          <span class="ov-k">Realtime 语音</span>
          <span class="adm-chip" :class="ov?.providers?.qwen ? 'ok' : 'bad'">{{ ov?.providers?.qwen ? "已配置" : "未配置" }}</span>
          <span class="ov-v">{{ ov?.providers?.qwen_model || "—" }}</span>
        </div>
        <div class="ov-s">
          <span class="ov-k">业务空间</span>
          <span class="adm-chip" :class="ov?.providers?.qwen_workspace ? 'ok' : 'bad'">{{ ov?.providers?.qwen_workspace ? "已绑定" : "未绑定" }}</span>
          <span class="ov-v">{{ ov?.providers?.fallback_model ? "回退：" + ov.providers.fallback_model : "未设回退模型" }}</span>
        </div>
        <div class="ov-s">
          <span class="ov-k">发音评测</span>
          <span class="adm-chip" :class="ov?.providers?.soe ? 'ok' : 'bad'">{{ ov?.providers?.soe ? "已配置" : "未配置" }}</span>
          <span class="ov-v">腾讯 SOE 跟读评分</span>
        </div>
      </div>

      <p class="adm-foot">
        Key 只存在服务端配置表，页面只回显尾 4 位，前端拿不到明文。
        <button class="ov-link" @click="$emit('navigate', 'ai')">去 AI 配置 →</button>
      </p>
    </section>

    <section class="adm-panel">
      <div class="adm-panel-h row">
        <div>
          <h2>今日用量 Top</h2>
          <p>只记账、不拦请求；超出额度由服务端在付费接口上拦截。</p>
        </div>
        <span class="adm-kv"><b>{{ ov?.today?.day || "—" }}</b></span>
      </div>

      <div v-if="topUsers.length" class="adm-rows">
        <div class="adm-thead"><span>用户</span><span>对话</span><span>TTS</span><span>评测</span><span>预估</span></div>
        <div v-for="r in topUsers" :key="r.user_id" class="adm-row">
          <span class="adm-name">{{ r.username }}</span>
          <span class="tnum">{{ Math.round(r.rt_seconds / 60) }} 分</span>
          <span class="tnum">{{ fmtInt(r.tts_chars) }} 字符</span>
          <span class="tnum">{{ r.soe_calls }} 次</span>
          <span class="adm-money tnum">{{ fmtYuan(r.est_cost_milli) }}</span>
        </div>
      </div>
      <p v-else class="adm-empty">今天还没有付费 AI 调用。</p>

      <p class="adm-foot">
        今日合计 <b>{{ fmtYuan(ov?.today?.total_cost_milli) }}</b> · TTS 缓存
        {{ ov?.tts_cache?.files ?? 0 }} 个文件 / {{ fmtMB(ov?.tts_cache?.bytes) }}
        <button class="ov-link" @click="$emit('navigate', 'usage')">看完整账本 →</button>
      </p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { NButton } from "naive-ui";
import { api } from "../../core/api";
import { fmtInt, fmtMB, fmtYuan } from "./format";

type UsageUser = {
  user_id: number; username: string; rt_seconds: number;
  tts_chars: number; soe_calls: number; est_cost_milli: number;
};
type Overview = {
  today: { day: string; total_cost_milli: number; users: UsageUser[] };
  users_total: number;
  ai_enabled_users: number;
  alerts_today: number;
  providers: {
    llm: boolean; qwen: boolean; qwen_workspace: boolean;
    qwen_model: string; fallback_model: string; soe: boolean;
  };
  tts_cache: { files: number; bytes: number; max_mb: number };
};

defineEmits<{ (e: "navigate", tab: string): void }>();

const ov = ref<Overview | null>(null);
const loading = ref(false);

const topUsers = computed(() =>
  [...(ov.value?.today?.users ?? [])]
    .filter((u) => u.est_cost_milli > 0)
    .sort((a, b) => b.est_cost_milli - a.est_cost_milli)
    .slice(0, 5),
);

const stats = computed(() => [
  { label: "今日费用", value: fmtYuan(ov.value?.today.total_cost_milli) },
  { label: "AI 已开通", value: `${ov.value?.ai_enabled_users ?? 0} / ${ov.value?.users_total ?? 0}` },
  { label: "今日额度告警", value: String(ov.value?.alerts_today ?? 0) },
  { label: "TTS 缓存", value: fmtMB(ov.value?.tts_cache.bytes) },
]);

async function load(): Promise<void> {
  loading.value = true;
  try {
    ov.value = await api<Overview>("/admin/ai/overview");
  } catch {
    /* 忽略：页面保留上次数据 */
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.ov-status { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.ov-s { display: flex; flex-direction: column; align-items: flex-start; gap: 5px; padding: 12px 14px; border: 1px solid var(--c-line); border-radius: var(--r-btn); background: var(--c-mint-bg); }
.ov-k { font-size: 13px; font-weight: 700; color: var(--c-text); }
.ov-v { font-size: 11.5px; color: var(--c-text-3); line-height: 1.5; overflow-wrap: anywhere; }
.ov-link { margin-left: 8px; border: 0; background: none; padding: 0; color: var(--c-primary-strong); font: inherit; font-weight: 700; cursor: pointer; }
.ov-link:hover { text-decoration: underline; }
@media (max-width: 767px) { .ov-status { grid-template-columns: 1fr; } }
</style>
